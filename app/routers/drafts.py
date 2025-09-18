"""Finding Model draft management routes."""

# ruff: noqa: B008, I001

import asyncio
import contextlib
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from bson import ObjectId

from findingmodel import FindingInfo, FindingModelBase, FindingModelFull
from findingmodel.tools import (
    add_ids_to_model,
    add_standard_codes_to_model,
    create_model_from_markdown,
)

from app.auth import CurrentUserDep, OptionalCurrentUserDep, OptionalUserDep
from app.config import logger
from app.templates import templates
from app.vite_manifest import get_vite_asset_path
from app.dependencies import (
    CacheDep,
    CommentRepoDep,
    CreationSessionDep,
    DatabaseDep,
    DraftServiceDep,
    SessionManagerDep,
    UserRepoDep,
)
from app.models import DraftStatus, FindingModelDraft, FindingModelInputs, UserCommentEntry
from app.services.comment_helpers import check_rate_limit
import humanize

TEST_USER_ID = 999999


def parse_synonyms(synonyms: str) -> list[str]:
    """Parse synonyms from JSON string."""
    if not synonyms.strip():
        return []

    try:
        synonyms_parsed = json.loads(synonyms)
        if not isinstance(synonyms_parsed, list) and not all(s and isinstance(s, str) for s in synonyms_parsed):
            raise ValueError("Synonyms must be a JSON array of strings")
        return [s.strip() for s in synonyms_parsed]
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid synonyms format: {str(e)}"
        ) from e


router = APIRouter()

# Ensure shared template globals are set (e.g., vite asset helper used by base.html)
templates.env.globals["vite_asset"] = get_vite_asset_path


# ===== DRAFT MANAGEMENT (HTMX) =====


@router.post("/save")
async def save_draft(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    draft_service: DraftServiceDep,
    draft_id: str | None = Form(default=None),
    description: str | None = Form(default=None),
    attributes_markdown: str | None = Form(default=None),
    synonyms: str = Form(default=""),
) -> HTMLResponse:
    """Save current inputs as a draft owned by the user. Returns a small fragment."""
    try:
        # Prevent saving if already submitted
        if session.draft_status == "submitted":
            html = templates.get_template("components/drafts/locked_result.html").render(
                request=request,
                reason="This draft has been submitted and is now read-only.",
            )
            return HTMLResponse(content=html, status_code=409)
        # Use provided values or fall back to session to support Step 5 quick save
        new_description = description if description is not None else (session.description or "")
        new_attributes = attributes_markdown if attributes_markdown is not None else (session.attributes_markdown or "")
        new_synonyms = parse_synonyms(synonyms) if isinstance(synonyms, str) else (session.synonyms or [])

        # Minimal validation to maintain previous constraints
        if len(new_description.strip()) < 10 or len(new_attributes.strip()) < 20:
            raise HTTPException(status_code=422, detail="Description or attributes are too short")

        # Update session with latest form values
        session.description = new_description
        session.attributes_markdown = new_attributes
        session.synonyms = new_synonyms
        await session_manager.update_session(session)

        # Normalize draft_id: treat empty string as None; validate if provided
        if draft_id is not None:
            draft_id = draft_id.strip()
            if draft_id == "":
                draft_id = None
            elif not ObjectId.is_valid(draft_id):
                raise HTTPException(status_code=400, detail="Invalid draft id")

        inputs = FindingModelInputs(
            description=session.description or "",
            synonyms=session.synonyms,
            attributes_markdown=session.attributes_markdown,
        )
        draft = await draft_service.save_draft(
            user_id=current_user.id,
            name=session.name or "",
            inputs=inputs,
            draft_id=draft_id,
            user=current_user,
        )

        # Track draft in session
        session.draft_id = draft.id
        session.draft_status = draft.status
        await session_manager.update_session(session)

        # Render a tiny success badge/button group fragment for the UI
        html = templates.get_template("components/drafts/save_result.html").render(
            request=request,
            draft=draft,
        )
        return HTMLResponse(content=html)
    except HTTPException:
        # Let FastAPI handle HTTP errors with proper status codes
        raise
    except Exception as e:
        # If error indicates not editable, show locked fragment
        msg = str(e)
        if "not editable" in msg or "not in draft status" in msg:
            html = templates.get_template("components/drafts/locked_result.html").render(
                request=request,
                reason="This draft has been submitted and is now read-only.",
            )
            return HTMLResponse(content=html, status_code=409)
        logger.error("Error saving draft: {}", e, exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error saving draft: {msg}"
        )
        return HTMLResponse(content=error_html, status_code=500)


@router.post("/{draft_id}/submit")
async def submit_draft(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    draft_service: DraftServiceDep,
    cache: CacheDep,
    draft_id: str,
) -> Response:
    """Submit a draft (freeze edits)."""
    try:
        # First check if draft exists and is in correct status
        draft_to_check = await draft_service.get_draft(draft_id=draft_id, user_id=current_user.id)
        if not draft_to_check:
            raise HTTPException(status_code=404, detail="Draft not found")

        # Validate that draft is PUBLIC before submission
        if draft_to_check.status != DraftStatus.PUBLIC:
            raise HTTPException(status_code=400, detail="Draft must be public before submission")

        draft = await draft_service.submit_draft(draft_id=draft_id, user_id=current_user.id)

        # Invalidate the public drafts cache since this draft is no longer public
        with contextlib.suppress(Exception):
            await cache.delete("public_drafts_list")
        session.draft_id = draft.id
        session.draft_status = draft.status
        # Human-friendly submitted time (UTC)
        try:
            submitted_time = draft.updated_at
            if submitted_time.tzinfo is None:
                submitted_time = submitted_time.replace(tzinfo=UTC)
            session.submitted_display_time = humanize.naturaltime(datetime.now(UTC) - submitted_time)
        except Exception:
            session.submitted_display_time = None
        await session_manager.update_session(session)

        # Check if this is an HTMX request
        is_htmx = request.headers.get("HX-Request") == "true"

        if is_htmx:
            # For HTMX requests, send a redirect header to reload the page
            # This ensures the comment thread and all elements are properly initialized
            return HTMLResponse(content="", headers={"HX-Redirect": f"/drafts/{draft_id}?mode=view"})
        else:
            # For non-HTMX requests, do a standard redirect
            return RedirectResponse(url=f"/drafts/{draft_id}?mode=view", status_code=303)
    except Exception as e:
        logger.error("Error submitting draft: {}", e, exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error submitting draft: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)


@router.post("/{draft_id}/delete")
async def delete_draft(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    draft_service: DraftServiceDep,
    draft_id: str,
) -> HTMLResponse:
    """Delete a draft if it's in draft or public status."""
    try:
        # First check if the draft exists and its status
        draft = await draft_service.get_draft(draft_id=draft_id, user_id=current_user.id)
        if not draft:
            error_html = templates.get_template("components/error_display.html").render(
                request=request, error_message="Draft not found or access denied"
            )
            return HTMLResponse(content=error_html, status_code=404)

        if draft.status not in ["draft", "public"]:
            error_html = templates.get_template("components/error_display.html").render(
                request=request, error_message="Cannot delete submitted drafts"
            )
            return HTMLResponse(content=error_html, status_code=400)

        # Proceed with deletion
        ok = await draft_service.delete_draft(draft_id=draft_id, user_id=current_user.id)
        if ok and session.draft_id == draft_id:
            session.draft_id = None
            await session_manager.update_session(session)

        # Redirect to profile page after successful deletion
        if ok:
            return HTMLResponse(content="", headers={"HX-Redirect": "/profile"})
        else:
            # This shouldn't happen if the checks above passed
            error_html = templates.get_template("components/error_display.html").render(
                request=request, error_message="Failed to delete draft"
            )
            return HTMLResponse(content=error_html, status_code=500)
    except Exception as e:
        logger.error(f"Error deleting draft: {e}", exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error deleting draft: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)


# ===== DRAFT EDITING WORKFLOW =====


@router.get("/{draft_id}/edit", response_class=HTMLResponse)
async def edit_draft(
    request: Request,
    current_user: CurrentUserDep,
    draft_service: DraftServiceDep,
    draft_id: str,
) -> HTMLResponse:
    """Edit a draft - main editing interface with form."""
    try:
        draft = await draft_service.get_draft(draft_id=draft_id, user_id=current_user.id)
        if draft is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

        # Only allow editing of drafts in 'draft' status
        # Public drafts are NOT editable (they can only be submitted or deleted)
        if draft.status != "draft":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Draft is not editable")

        # Check if this is an HTMX request (for mode switching)
        hx_request = request.headers.get("HX-Request")
        if hx_request:
            # Return just the edit form partial for HTMX swaps
            return templates.TemplateResponse(
                request=request,
                name="components/draft_edit_form.html",
                context={
                    "user": current_user,
                    "draft": draft,
                },
            )
        else:
            # Return full page for direct navigation
            return templates.TemplateResponse(
                request=request,
                name="draft_editor.html",
                context={
                    "user": current_user,
                    "title": f"Edit Draft: {draft.name}",
                    "draft": draft,
                    "mode": "edit",
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading draft editor: {e}", exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error loading draft: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)


@router.get("/{draft_id}", response_model=None)
async def unified_draft_page(
    request: Request,
    current_user: OptionalCurrentUserDep,
    draft_service: DraftServiceDep,
    draft_id: str,
    mode: str = "view",  # Default to view mode
) -> Response:
    """Unified draft page that handles both view and edit modes."""
    try:
        # Handle optional user for draft access
        user_id = current_user.id if current_user else None

        # Get the draft with author information (single aggregation call)
        draft_dict = await draft_service.get_draft_with_author(draft_id=draft_id, user_id=user_id)
        if draft_dict is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

        # Extract author name from the draft
        author_name = draft_dict.get("author_name") or draft_dict.get("author_username", "Unknown")

        # Validate the draft from the dict
        draft = FindingModelDraft.model_validate(draft_dict)

        # For private drafts, ensure user is authenticated and owns the draft
        if draft.status == "draft" and (not current_user or draft.user_id != current_user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

        # Validate mode parameter
        if mode not in ["view", "edit"]:
            mode = "view"

        # For edit mode, only allow if user is authenticated, draft is editable, and user owns it
        # Authors can edit their own drafts in 'draft' or 'public' status (but not submitted)
        can_edit = current_user is not None and draft.status in ["draft", "public"] and draft.user_id == current_user.id
        # Authors can delete their drafts in 'draft' or 'public' status (but not submitted)
        can_delete = (
            current_user is not None and draft.status in ["draft", "public"] and draft.user_id == current_user.id
        )
        if mode == "edit" and not can_edit:
            # Redirect to view mode for non-editable drafts, non-owners, or unauthenticated users
            mode = "view"

        # Parse finding model if available
        finding_model: FindingModelFull | None = None
        if draft.generated_json:
            try:
                finding_model = FindingModelFull.model_validate_json(draft.generated_json)
            except Exception:
                finding_model = None

        # Get comment thread for PUBLIC and SUBMITTED drafts (only if user is authenticated)
        thread = None
        if current_user and draft.status in ["public", "submitted"]:
            thread = await draft_service.get_comments_for_draft(str(draft.id))

        # If trying to view a draft without generated JSON, redirect to edit mode (only if user can edit)
        if mode == "view" and not finding_model and draft.status == "draft" and can_edit:
            # Use HTMX redirect or browser redirect depending on request type
            hx_request = request.headers.get("HX-Request")
            if hx_request:
                # HTMX request - swap to edit form and update URL (use containerless version)
                return templates.TemplateResponse(
                    request=request,
                    name="components/draft_edit_form_content.html",
                    context={
                        "user": current_user,
                        "draft": draft,
                    },
                    headers={"HX-Push-Url": f"/drafts/{draft_id}?mode=edit"},
                )
            else:
                # Browser request - redirect to edit mode, preserving query parameters
                query_params = dict(request.query_params)
                query_params["mode"] = "edit"
                query_string = "&".join(f"{k}={v}" for k, v in query_params.items())
                return RedirectResponse(url=f"/drafts/{draft_id}?{query_string}", status_code=303)

        # Check if this is an HTMX request (for mode switching)
        hx_request = request.headers.get("HX-Request")
        if hx_request:
            # Check if this request comes from the public drafts table
            from_public = request.query_params.get("from") == "public"

            # Return containerless content for HTMX swaps (prevents nested boxes)
            if mode == "edit":
                main_content = templates.get_template("components/draft_edit_form_content.html").render(
                    request=request,
                    user=current_user,
                    draft=draft,
                )
            else:  # view mode
                main_content = templates.get_template("components/draft_preview_content.html").render(
                    request=request,
                    user=current_user,
                    draft=draft,
                    finding_model=finding_model,
                    thread=thread,
                    reference_type="draft",
                    reference_id=str(draft.id),
                    current_user=current_user,
                    show_ids=bool(draft.status == "submitted"),
                    show_json=bool(draft.status == "submitted"),
                    author_name=author_name,
                    can_edit=can_edit,
                    can_delete=can_delete,
                )

            # Only include OOB swaps if NOT coming from public drafts table and draft has generated JSON
            # (means there's something to preview - buttons are useful)
            if not from_public and draft.generated_json:
                # Use unified container across all workflows
                target_container = "#main-content"

                # Include mode toggle header OOB swap
                mode_toggle_header = templates.get_template("components/draft_mode_toggle_header.html").render(
                    request=request,
                    user=current_user,
                    draft=draft,
                    mode=mode,  # Pass the current mode
                    can_edit=can_edit,
                    target_container=target_container,
                )

                # Create OOB swap for page title
                page_title_text = "Edit Finding Model Draft" if mode == "edit" else "Preview Finding Model Draft"
                title_oob = f"""<h1 id="page-title" class="text-3xl font-bold text-gray-900 dark:text-white mb-2" hx-swap-oob="true">
                        {page_title_text}
                    </h1>"""  # noqa: E501

                # Combine main content with OOB swaps for both mode toggle header and title
                combined_content = f"""{main_content}
<div id="draft-mode-toggle-header" hx-swap-oob="true">
{mode_toggle_header}
</div>
{title_oob}"""

                return HTMLResponse(content=combined_content)
            else:
                # Regular unified draft page - no OOB swaps for public drafts table navigation
                return HTMLResponse(content=main_content)
        else:
            # Return full page for direct navigation
            page_title = f"{'Edit' if mode == 'edit' else 'Preview'} Finding Model Draft"

            return templates.TemplateResponse(
                request=request,
                name="draft_unified.html",
                context={
                    "user": current_user,
                    "title": page_title,
                    "draft": draft,
                    "finding_model": finding_model,
                    "thread": thread,
                    "reference_type": "draft",
                    "reference_id": str(draft.id),
                    "current_user": current_user,
                    "mode": mode,
                    "can_edit": can_edit,
                    "can_delete": can_delete,
                    "show_ids": draft.status == "submitted",
                    "show_json": draft.status == "submitted",
                    "author_name": author_name,
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading unified draft page: {e}", exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error loading draft: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)


@router.post("/{draft_id}/update-and-redirect")
async def update_draft_and_redirect(
    request: Request,
    current_user: CurrentUserDep,
    draft_service: DraftServiceDep,
    database: DatabaseDep,
    draft_id: str,
    description: str = Form(min_length=10, max_length=1000),
    attributes_markdown: str = Form(min_length=20),
    synonyms: str = Form(default=""),
) -> Response:
    """Update draft and redirect to unified draft page - used when coming from creation workflow."""
    try:
        # Call the same update logic as the regular update endpoint
        # Get draft with author information
        draft_dict = await draft_service.get_draft_with_author(draft_id=draft_id, user_id=current_user.id)
        if draft_dict is None:
            logger.error(f"Draft not found: draft_id={draft_id}, user_id={current_user.id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

        # Extract author name from the draft
        author_name = draft_dict.get("author_name") or draft_dict.get("author_username", "Unknown")

        # Validate the draft from the dict
        draft = FindingModelDraft.model_validate(draft_dict)

        # This route can be called for draft and public statuses (owned by user)
        # Submitted drafts are locked and cannot be edited
        if draft.status not in ["draft", "public"]:
            logger.error(f"Draft not editable: draft_id={draft_id}, status={draft.status}, user_id={current_user.id}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Draft is not editable")

        # Parse synonyms
        synonyms_list = parse_synonyms(synonyms)

        # Update draft with new inputs
        new_inputs = FindingModelInputs(
            description=description,
            synonyms=synonyms_list,
            attributes_markdown=attributes_markdown,
        )

        # Check if inputs have actually changed
        inputs_changed = (
            draft.inputs.description != new_inputs.description
            or draft.inputs.synonyms != new_inputs.synonyms
            or draft.inputs.attributes_markdown != new_inputs.attributes_markdown
        )

        # Initialize generated_json variable
        generated_json: str | None

        # Generate the model if inputs changed OR if no generated JSON exists (fresh draft)
        has_no_generated_json = not draft.generated_json
        should_generate = inputs_changed or has_no_generated_json

        if should_generate:
            # Generate the model from the updated inputs
            finding_info = FindingInfo(name=draft.name, description=description, synonyms=synonyms_list)
            complete_markdown = f"""# {draft.name}
## Description
{description}
{attributes_markdown}
"""
            if current_user.id == TEST_USER_ID:
                # Mock AI response for test user (999999)
                logger.info(
                    f"Update draft: Using MOCK AI response for create_model_from_markdown (test user {current_user.id})"
                )
                await asyncio.sleep(2.0)  # Simulate AI processing time
                # Create mock FindingModel directly without AI call
                mock_model_dict = {
                    "name": draft.name if len(draft.name) >= 5 else f"{draft.name} Test",
                    "description": description,
                    "synonyms": synonyms_list,
                    "tags": None,
                    "contributors": None,
                    "attributes": [
                        {
                            "name": "presence",
                            "description": f"Presence of {draft.name}",
                            "type": "choice",
                            "values": [
                                {"name": "absent", "description": f"{draft.name} is not visible"},
                                {"name": "present", "description": f"{draft.name} is clearly visible"},
                            ],
                            "required": False,
                            "max_selected": 1,
                        }
                    ],
                }
                finding_model_generated = FindingModelBase.model_validate(mock_model_dict)
            else:
                logger.info("Update draft: Using REAL AI response for create_model_from_markdown")
                finding_model_generated = await create_model_from_markdown(
                    finding_info, markdown_text=complete_markdown
                )

            # Add IDs and contributors
            assert database.finding_index, "FindingIndex must be initialized in the database"
            author = database.people.get(current_user.login)
            source = (
                author.organization_code
                if author
                else (current_user.organizations[0] if current_user.organizations else "OIDM")
            )
            fm = add_ids_to_model(finding_model_generated, source=source)
            add_standard_codes_to_model(fm)

            # Convert to JSON
            generated_json = fm.model_dump_json(indent=2)
        else:
            generated_json = draft.generated_json

        # Update the draft
        updated_draft = await draft_service.save_draft(
            user_id=current_user.id,
            name=draft.name,
            inputs=new_inputs,
            draft_id=draft_id,
            generated_json=generated_json,
            user=current_user,
        )

        # Check if this is an HTMX request
        hx_request = request.headers.get("HX-Request")
        if hx_request:
            # For HTMX requests, return the draft preview content AND update the mode toggle header
            # Parse the generated finding model
            finding_model: FindingModelFull | None = None
            if generated_json:
                try:
                    finding_model = FindingModelFull.model_validate_json(generated_json)
                except Exception:
                    finding_model = None

            # Set headers including reuse indicator and URL push
            response_headers = {
                "HX-Push-Url": f"/drafts/{draft_id}?mode=view&created=true",
                "x-model-reused": "0" if should_generate else "1",
            }

            # Render the main draft preview content
            draft_content = templates.get_template("components/draft_preview_content.html").render(
                request=request,
                user=current_user,
                draft=updated_draft,
                finding_model=finding_model,
                thread=None,  # No comment thread in update context
                reference_type="draft",
                reference_id=str(updated_draft.id),
                current_user=current_user,
                show_ids=False,  # Always False for drafts in this endpoint
                show_json=False,  # Always False for drafts in this endpoint
                show_success_message=True,  # Show success message for HTMX transitions
                can_edit=updated_draft.status in ["draft", "public"],
                can_delete=updated_draft.status in ["draft", "public"] and updated_draft.user_id == current_user.id,
                author_name=author_name,  # Use the actual draft author, not current user
            )

            # Include mode toggle header OOB swap if the draft now has generated JSON
            if updated_draft.generated_json:
                # Use unified container across all workflows
                target_container = "#main-content"

                # Include mode toggle header OOB swap
                mode_toggle_header = templates.get_template("components/draft_mode_toggle_header.html").render(
                    request=request,
                    user=current_user,
                    draft=updated_draft,
                    mode="view",  # We're transitioning to view mode
                    can_edit=updated_draft.status in ["draft", "public"],
                    target_container=target_container,
                )

                # Combine main content with OOB swap for mode toggle header
                combined_content = f"""{draft_content}
<div id="draft-mode-toggle-header" hx-swap-oob="true">
{mode_toggle_header}
</div>"""

                return HTMLResponse(
                    content=combined_content,
                    headers=response_headers,
                )
            else:
                return HTMLResponse(
                    content=draft_content,
                    headers=response_headers,
                )
        else:
            # Redirect to unified draft page in view mode
            return RedirectResponse(url=f"/drafts/{draft_id}?mode=view&created=true", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating draft: {e}", exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error updating draft: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)


@router.post("/{draft_id}/comments", response_model=None)
async def add_draft_comment(
    draft_id: str,
    request: Request,
    current_user: CurrentUserDep,
    draft_service: DraftServiceDep,
    user_repo: UserRepoDep,
    cache: CacheDep,
    content: str = Form(...),
    parent_comment_id: str | None = Form(None),
) -> HTMLResponse | RedirectResponse:
    """Add a comment to a draft (submitted drafts only)."""
    try:
        # Check if user is logged in
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Check rate limit
        allowed, error_msg = check_rate_limit(current_user)
        if not allowed:
            if request.headers.get("HX-Request") == "true":
                error_html = (
                    f'<div class="p-4 text-red-600 bg-red-50 dark:bg-red-900 dark:text-red-200 rounded-lg">'
                    f"{error_msg}</div>"
                )
                return HTMLResponse(content=error_html, status_code=429)
            else:
                raise HTTPException(status_code=429, detail=error_msg)

        # Verify draft exists and is submitted (no user_id check - anyone can comment on submitted drafts)
        draft = await draft_service.get_draft(draft_id=draft_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Draft not found")

        if draft.status not in ["public", "submitted"]:
            raise HTTPException(status_code=400, detail="Comments can only be added to public and submitted drafts")

        # Add the comment (service handles validation and threading)
        if parent_comment_id:
            comment = await draft_service.add_comment_to_draft(draft_id, current_user, content, parent_comment_id)
        else:
            comment = await draft_service.add_comment_to_draft(draft_id, current_user, content)

        # Update user's comment index for rate limiting
        await user_repo.add_comment_to_index(
            user_id=current_user.id,
            entry=UserCommentEntry(
                reference_type="draft",
                reference_id=draft_id,
                finding_name=draft.name,
                comment_id=comment.id,
                created_at=datetime.now(UTC),
            ),
        )

        # Get updated thread
        thread = await draft_service.get_comments_for_draft(draft_id)

        # Invalidate the public drafts cache since comment count changed
        if draft.status == "public":
            with contextlib.suppress(Exception):
                await cache.delete("public_drafts_list")

        # Check if this is an HTMX request
        is_htmx = request.headers.get("HX-Request") == "true"

        if is_htmx:
            # Return rendered comment thread for HTMX swap
            return templates.TemplateResponse(
                request=request,
                name="components/comment_thread.html",
                context={
                    "thread": thread,
                    "reference_type": "draft",
                    "reference_id": draft_id,
                    "current_user": current_user,
                },
            )
        else:
            # Non-HTMX: redirect back to the draft page
            return RedirectResponse(url=f"/drafts/{draft_id}", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding comment to draft '{draft_id}': {e}")
        if request.headers.get("HX-Request") == "true":
            error_html = (
                f'<div class="p-4 text-red-600 bg-red-50 dark:bg-red-900 dark:text-red-200 rounded-lg">'
                f"Error adding comment: {str(e)}</div>"
            )
            return HTMLResponse(content=error_html, status_code=500)
        else:
            raise HTTPException(status_code=500, detail=f"Error adding comment: {str(e)}") from e


@router.post("/{draft_id}/comments/{comment_id}/report", response_model=None)
async def report_draft_comment(
    draft_id: str,
    comment_id: str,
    request: Request,
    current_user: CurrentUserDep,
    draft_service: DraftServiceDep,
    comment_repo: CommentRepoDep,
) -> HTMLResponse:
    """Report a comment on a draft."""
    # Check if user is logged in
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        # Verify draft exists and user can access it
        draft = await draft_service.get_draft(draft_id, current_user.id)
        if not draft:
            return HTMLResponse('<div class="alert alert-danger">Draft not found</div>', status_code=404)

        # Get the comment thread
        thread = await comment_repo.get_thread("draft", draft_id)
        if not thread:
            return HTMLResponse('<div class="alert alert-danger">No comments found</div>', status_code=404)

        # Report the comment
        success = await comment_repo.report_comment(thread.id, comment_id, current_user.id)

        if success:
            # Return a success message that replaces the report button
            success_html = '<span class="text-xs text-green-600 dark:text-green-400">Reported</span>'
            return HTMLResponse(success_html)
        else:
            # Return error message that replaces the button
            error_html = '<span class="text-xs text-red-600 dark:text-red-400">Already reported</span>'
            return HTMLResponse(error_html, status_code=400)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reporting comment on draft '{draft_id}': {e}")
        error_html = '<span class="text-xs text-red-600 dark:text-red-400">Error</span>'
        return HTMLResponse(error_html, status_code=500)


@router.post("/{draft_id}/make-public")
async def make_draft_public(
    draft_id: str,
    current_user: CurrentUserDep,
    draft_service: DraftServiceDep,
    cache: CacheDep,
) -> Response:
    """Make a draft public for review."""
    try:
        # Check ownership and make public
        await draft_service.make_public_draft(draft_id, current_user.id)

        # Invalidate the public drafts cache
        with contextlib.suppress(Exception):
            await cache.delete("public_drafts_list")

        # Redirect to the draft page
        return RedirectResponse(url=f"/drafts/{draft_id}", status_code=303)
    except Exception as e:
        logger.error(f"Error making draft public {draft_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error making draft public: {str(e)}") from e


@router.get("/", name="drafts_table")
async def list_public_drafts(
    request: Request,
    current_user: OptionalUserDep,
    draft_service: DraftServiceDep,
    cache: CacheDep,
) -> HTMLResponse:
    """List all public drafts."""
    try:
        # Try to get from cache first
        public_drafts = None
        try:
            cached_data = await cache.get("public_drafts_list")
            if cached_data:
                public_drafts = json.loads(str(cached_data))
        except Exception:
            # Cache errors are not critical
            pass

        # If not in cache, fetch from service and cache it
        if public_drafts is None:
            public_drafts = await draft_service.get_public_drafts()
            try:
                from datetime import timedelta

                await cache.set("public_drafts_list", json.dumps(public_drafts), expires_in=timedelta(minutes=5))
            except Exception:
                # Cache errors are not critical
                pass

        return templates.TemplateResponse(
            request=request,
            name="drafts_table.html",
            context={
                "drafts": public_drafts,
                "title": "Public Drafts",
                "user": current_user,
            },
        )
    except Exception as e:
        logger.error(f"Error listing public drafts: {e}")
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error loading public drafts: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)
