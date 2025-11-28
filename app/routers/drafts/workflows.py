"""Workflow state transition routes for drafts."""

import contextlib
import json
from datetime import UTC, datetime, timedelta

import humanize
from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import CurrentUserDep
from app.config import logger
from app.dependencies import CacheDep, CreationSessionDep, DraftServiceDep, SessionManagerDep
from app.models import DraftStatus
from app.templates import templates

# Key prefix for storing iteration results in Redis
ITERATION_RESULT_KEY_PREFIX = "iteration_result:"
ITERATION_RESULT_TTL = timedelta(minutes=5)  # Results expire after 5 minutes

router = APIRouter()


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

        # Redirect to the draft page with query parameter to indicate creation context and success message
        return RedirectResponse(url=f"/drafts/{draft_id}?from=creation&success=made_public", status_code=303)
    except Exception as e:
        logger.error(f"Error making draft public {draft_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error making draft public: {str(e)}") from e


@router.post("/{draft_id}/iterate")
async def iterate_draft(
    draft_id: str,
    request: Request,
    current_user: CurrentUserDep,
    draft_service: DraftServiceDep,
    cache: CacheDep,
    command: str = Form(...),
) -> Response:
    """Apply a natural language iteration command to a draft."""
    try:
        # Apply the iteration command
        result = await draft_service.apply_natural_language_iteration(draft_id, current_user.id, command)

        if result.get("success"):
            # Store iteration results in Redis for display on preview page
            result_key = f"{ITERATION_RESULT_KEY_PREFIX}{draft_id}"
            result_data = {
                "command": command,
                "changes": result.get("changes", []),
                "rejections": result.get("rejections", []),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            await cache.set(result_key, json.dumps(result_data), expires_in=ITERATION_RESULT_TTL)
            logger.debug(f"Stored iteration result for draft {draft_id}")

            # Redirect to preview mode so user sees updated model with results banner
            response = HTMLResponse(content="", status_code=200)
            response.headers["HX-Redirect"] = f"/drafts/{draft_id}?mode=view"
            return response
        else:
            # On failure, show error in results container (stays on edit page)
            return templates.TemplateResponse(
                request=request,
                name="components/iteration_result.html",
                context={
                    "result": result,
                    "command": command,
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying iteration to draft {draft_id}: {e}")
        # Return error template
        return templates.TemplateResponse(
            request=request,
            name="components/iteration_result.html",
            context={
                "result": {
                    "success": False,
                    "changes": [],
                    "rejections": [],
                    "error": str(e),
                },
                "command": command,
            },
            status_code=500,
        )
