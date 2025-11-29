"""CRUD mutation routes for drafts (save, update, delete)."""

from bson import ObjectId
from fastapi import APIRouter, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import CurrentUserDep
from app.config import logger
from app.dependencies import CreationSessionDep, DraftServiceDep, SessionManagerDep
from app.models import FindingModelInputs
from app.routers.drafts.helpers import (
    build_update_htmx_response,
    check_draft_permissions,
    fetch_draft_with_context,
)
from app.templates import templates
from app.utils.forms import parse_synonyms

TEST_USER_ID = 999999

router = APIRouter()


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


@router.post("/{draft_id}/update-and-redirect")
async def update_draft_and_redirect(
    request: Request,
    current_user: CurrentUserDep,
    draft_service: DraftServiceDep,
    draft_id: str,
    description: str = Form(min_length=10, max_length=1000),
    attributes_markdown: str = Form(min_length=20),
    synonyms: str = Form(default=""),
) -> Response:
    """Update draft and redirect to unified draft page - used when coming from creation workflow."""
    try:
        # Fetch draft with author information using helper
        draft, author_name = await fetch_draft_with_context(draft_id, current_user.id, draft_service)

        # Check permissions using helper (will raise 403 if not editable)
        check_draft_permissions(draft, current_user)

        # This route can be called for draft and public statuses (owned by user)
        # Submitted drafts are locked and cannot be edited
        if draft.status not in ["draft", "public"]:
            logger.error(f"Draft not editable: draft_id={draft_id}, status={draft.status}, user_id={current_user.id}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Draft is not editable")

        # Parse synonyms using utility
        synonyms_list = parse_synonyms(synonyms)

        # Update draft with new inputs
        new_inputs = FindingModelInputs(
            description=description,
            synonyms=synonyms_list,
            attributes_markdown=attributes_markdown,
        )

        # Check if model needs regeneration
        should_generate = draft_service.should_regenerate_model(draft, new_inputs)

        # Generate finding model JSON if needed
        generated_json: str | None
        if should_generate:
            generated_json = await draft_service.generate_finding_model_json(
                draft=draft,
                description=description,
                synonyms_list=synonyms_list,
                attributes_markdown=attributes_markdown,
                current_user=current_user,
                is_test_user=current_user.id == TEST_USER_ID,
            )
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
            # Build HTMX response with draft preview and OOB swaps
            return build_update_htmx_response(
                request=request,
                draft=updated_draft,
                generated_json=generated_json,
                author_name=author_name,
                current_user=current_user,
                was_regenerated=should_generate,
                templates=templates,
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
