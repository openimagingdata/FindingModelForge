"""Comment management routes for drafts."""

import contextlib

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import CurrentUserDep
from app.config import logger
from app.dependencies import CacheDep, DraftServiceDep
from app.templates import templates

router = APIRouter()


@router.post("/{draft_id}/comments", response_model=None)
async def add_draft_comment(
    draft_id: str,
    request: Request,
    current_user: CurrentUserDep,
    draft_service: DraftServiceDep,
    cache: CacheDep,
    content: str = Form(...),
    parent_comment_id: str | None = Form(None),
) -> HTMLResponse | RedirectResponse:
    """Add a comment to a draft (submitted drafts only)."""
    try:
        # Check if user is logged in
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Add the comment (service handles rate limiting, validation, and threading)
        if parent_comment_id:
            await draft_service.add_comment_to_draft(draft_id, current_user, content, parent_comment_id)
        else:
            await draft_service.add_comment_to_draft(draft_id, current_user, content)

        # Fetch updated draft for status/cache handling
        draft = await draft_service.get_draft(draft_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Draft not found")

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

        await draft_service.report_draft_comment(draft_id, comment_id, current_user.id)

        success_html = '<span class="text-xs text-green-600 dark:text-green-400">Reported</span>'
        return HTMLResponse(success_html)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reporting comment on draft '{draft_id}': {e}")
        error_html = '<span class="text-xs text-red-600 dark:text-red-400">Error</span>'
        return HTMLResponse(error_html, status_code=500)
