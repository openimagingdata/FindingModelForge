"""Finding Model draft management routes."""

# ruff: noqa: B008, I001

import asyncio
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from bson import ObjectId

from findingmodel import FindingInfo, FindingModelBase, FindingModelFull
from findingmodel.tools import (
    add_ids_to_model,
    add_standard_codes_to_model,
    create_model_from_markdown,
)

from app.auth import CurrentUserDep
from app.config import logger
from app.templates import templates
from app.vite_manifest import get_vite_asset_path
from app.dependencies import (
    CreationSessionDep,
    DatabaseDep,
    DraftServiceDep,
    SessionManagerDep,
)
from app.models import FindingModelInputs
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
    draft_id: str,
) -> HTMLResponse:
    """Submit a draft (freeze edits)."""
    try:
        draft = await draft_service.submit_draft(draft_id=draft_id, user_id=current_user.id)
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

        # Build finding model object for display
        finding_model: FindingModelFull | None = None
        if session.final_model:
            try:
                finding_model = FindingModelFull.model_validate(session.final_model)
            except Exception:
                finding_model = None
        if finding_model is None and getattr(draft, "generated_json", None):
            try:
                finding_model = FindingModelFull.model_validate_json(draft.generated_json)
            except Exception:
                finding_model = None

        # Render submitted draft content for HTMX swap into #step-container
        # Note: Use a custom template context since we need #step-container target, not #draft-content
        template_content = templates.get_template("components/draft_preview_containerless.html").render(
            request=request,
            user=current_user,
            draft=draft,
            finding_model=finding_model,
            show_ids=True,
            show_json=True,
        )

        # Replace the HTMX target to work with creation workflow
        html_content = template_content.replace('hx-target="#draft-content"', 'hx-target="#step-container"')
        return HTMLResponse(content=html_content)
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
    """Delete a draft if it's still in draft status."""
    try:
        # First check if the draft exists and its status
        draft = await draft_service.get_draft(draft_id=draft_id, user_id=current_user.id)
        if not draft:
            error_html = templates.get_template("components/error_display.html").render(
                request=request, error_message="Draft not found or access denied"
            )
            return HTMLResponse(content=error_html, status_code=404)

        if draft.status != "draft":
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
    current_user: CurrentUserDep,
    draft_service: DraftServiceDep,
    draft_id: str,
    mode: str = "view",  # Default to view mode
) -> Response:
    """Unified draft page that handles both view and edit modes."""
    try:
        draft = await draft_service.get_draft(draft_id=draft_id, user_id=current_user.id)
        if draft is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

        # Validate mode parameter
        if mode not in ["view", "edit"]:
            mode = "view"

        # For edit mode, only allow if draft is editable
        if mode == "edit" and draft.status != "draft":
            # Redirect to view mode for submitted drafts
            mode = "view"

        # Parse finding model if available
        finding_model: FindingModelFull | None = None
        if draft.generated_json:
            try:
                finding_model = FindingModelFull.model_validate_json(draft.generated_json)
            except Exception:
                finding_model = None

        # If trying to view a draft without generated JSON, redirect to edit mode
        if mode == "view" and not finding_model and draft.status == "draft":
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
            # Return containerless content for HTMX swaps (prevents nested boxes)
            if mode == "edit":
                main_content = templates.get_template("components/draft_edit_form_content.html").render(
                    request=request,
                    user=current_user,
                    draft=draft,
                )
            else:  # view mode
                main_content = templates.get_template("components/draft_preview_containerless.html").render(
                    request=request,
                    user=current_user,
                    draft=draft,
                    finding_model=finding_model,
                    show_ids=bool(draft.status == "submitted"),
                    show_json=bool(draft.status == "submitted"),
                )

            # Only include mode toggle header OOB swap if the draft has generated JSON
            # (means there's something to preview - buttons are useful)
            if draft.generated_json:
                # Use unified container across all workflows
                target_container = "#main-content"

                # Include mode toggle header OOB swap
                mode_toggle_header = templates.get_template("components/draft_mode_toggle_header.html").render(
                    request=request,
                    user=current_user,
                    draft=draft,
                    mode=mode,  # Pass the current mode
                    can_edit=draft.status == "draft",
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
                # Regular unified draft page - no mode toggle buttons needed
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
                    "mode": mode,
                    "can_edit": draft.status == "draft",
                    "show_ids": draft.status == "submitted",
                    "show_json": draft.status == "submitted",
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
        draft = await draft_service.get_draft(draft_id=draft_id, user_id=current_user.id)
        if draft is None:
            logger.error(f"Draft not found: draft_id={draft_id}, user_id={current_user.id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

        if draft.status != "draft":
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
            draft_content = templates.get_template("components/draft_preview_containerless.html").render(
                request=request,
                user=current_user,
                draft=updated_draft,
                finding_model=finding_model,
                show_ids=False,  # Always False for drafts in this endpoint
                show_json=False,  # Always False for drafts in this endpoint
                show_success_message=True,  # Show success message for HTMX transitions
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
                    can_edit=updated_draft.status == "draft",
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
