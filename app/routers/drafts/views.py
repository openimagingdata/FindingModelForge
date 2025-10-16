"""Finding Model draft viewing routes - GET endpoints for draft display."""

# ruff: noqa: B008, I001

import json

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import CurrentUserDep, OptionalCurrentUserDep, OptionalUserDep
from app.config import logger
from app.dependencies import CacheDep, DraftServiceDep
from app.routers.drafts.helpers import (
    build_htmx_response_with_oob,
    check_draft_permissions,
    fetch_draft_with_context,
    parse_finding_model_from_draft,
    render_draft_edit_content,
    render_draft_preview_content,
)
from app.templates import templates
from app.vite_manifest import get_vite_asset_path

router = APIRouter()

# Ensure shared template globals are set (e.g., vite asset helper used by base.html)
templates.env.globals["vite_asset"] = get_vite_asset_path


# ===== DRAFT VIEWING ENDPOINTS =====


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
    except HTTPException as exc:
        if request.headers.get("HX-Request") == "true" and exc.detail:
            error_html = (
                f'<div class="p-4 text-red-600 bg-red-50 dark:bg-red-900 dark:text-red-200 rounded-lg">'
                f"{exc.detail}</div>"
            )
            return HTMLResponse(content=error_html, status_code=exc.status_code)
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

        # Fetch draft with author information using helper
        draft, author_name = await fetch_draft_with_context(draft_id, user_id, draft_service)

        # Check permissions using helper
        can_edit, can_delete = check_draft_permissions(draft, current_user)

        # Validate mode parameter
        if mode not in ["view", "edit"]:
            mode = "view"

        if mode == "edit" and not can_edit:
            # Redirect to view mode for non-editable drafts, non-owners, or unauthenticated users
            mode = "view"

        # Parse finding model using helper
        finding_model = parse_finding_model_from_draft(draft)

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
            # Check if this request comes from the public drafts table or creation workflow
            from_public = request.query_params.get("from") == "public"
            current_url = request.headers.get("HX-Current-URL", "")
            from_creation = "create-finding-model" in current_url

            # Render appropriate content based on mode
            if mode == "edit":
                main_content = render_draft_edit_content(request, current_user, draft, templates)
            else:  # view mode
                main_content = render_draft_preview_content(
                    request, current_user, draft, finding_model, thread, author_name, can_edit, can_delete, templates
                )

            # Determine if OOB swaps should be included
            include_oob = not from_public and not from_creation

            # Build and return response with optional OOB swaps
            return build_htmx_response_with_oob(
                main_content, draft, mode, can_edit, include_oob, request, current_user, templates
            )
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
    except HTTPException as exc:
        if request.headers.get("HX-Request") == "true" and exc.detail:
            error_html = f'<span class="text-xs text-red-600 dark:text-red-400">{exc.detail}</span>'
            return HTMLResponse(error_html, status_code=exc.status_code)
        raise
    except Exception as e:
        logger.error(f"Error loading unified draft page: {e}", exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error loading draft: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)


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
