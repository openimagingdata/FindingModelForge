# ruff: noqa: B008
# mypy: disable-error-code="prop-decorator"
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Form, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import CurrentUserDep, OptionalUserDep
from app.config import logger
from app.dependencies import CommentRepoDep, FindingModelServiceDep, UserRepoDep
from app.models import UserCommentEntry
from app.services import NotFoundError
from app.services.comment_helpers import check_rate_limit
from app.templates import templates
from app.vite_manifest import get_vite_asset_path

router = APIRouter()


# Add vite asset helper to template globals
templates.env.globals["vite_asset"] = get_vite_asset_path


@router.get("/finding-models", response_class=HTMLResponse)
@router.get("/finding-models/{slug}", response_class=HTMLResponse)
async def finding_models(
    request: Request,
    current_user: OptionalUserDep,
    finding_model_service: FindingModelServiceDep,
    slug: str | None = None,
    hx_request: Annotated[str | None, Header()] = None,
    search: str = Query(None, description="Search term for filtering models"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=10, le=50, description="Items per page"),
) -> HTMLResponse:
    """Unified finding models endpoint - shows list or detail based on slug."""
    logger.info(
        f"Accessing finding models {'(detail: ' + slug + ')' if slug else '(list)'} "
        f"for user: {current_user.login if current_user else 'Guest'}"
        f"{' with search: ' + search if search else ''}"
        f"{' page: ' + str(page) if page > 1 else ''}"
    )

    # For HTMX requests, return just the content fragment
    if hx_request == "true":
        if slug:
            # Return detail fragment
            try:
                finding_model, index_entry = await finding_model_service.get_model_by_slug(slug)
                # Get the comment thread for this finding model
                thread = await finding_model_service.get_comments_for_model(finding_model.oifm_id)
                response = templates.TemplateResponse(
                    request=request,
                    name="fragments/finding_model_detail_content.html",
                    context={
                        "finding_model": finding_model,
                        "index_entry": index_entry,
                        "thread": thread,
                        "reference_type": "finding_model",
                        "reference_id": slug,
                        "current_user": current_user,
                        "show_json": True,
                        "show_ids": True,
                        "is_htmx_request": True,
                        "page_title": f"{finding_model.name} - Finding Model Forge",
                    },
                )
                # Tell HTMX what URL to push to browser history
                response.headers["HX-Push-Url"] = f"/finding-models/{slug}"
                return response
            except NotFoundError:
                raise HTTPException(status_code=404, detail=f"Finding model '{slug}' not found") from None
            except Exception as e:
                logger.error(f"Error displaying finding model '{slug}': {e}")
                error_content = (
                    '<div class="p-4 text-red-600 bg-red-50 dark:bg-red-900 dark:text-red-200 rounded-lg">'
                    "Error loading finding model</div>"
                )
                return HTMLResponse(content=error_content, status_code=500)
        else:
            # Return list fragment with search and pagination
            paginated_models, total_count = await finding_model_service.list_models(search, page, per_page)

            # Calculate pagination info
            total_pages = max(1, (total_count + per_page - 1) // per_page)
            start_index = (page - 1) * per_page
            end_index = min(start_index + per_page, total_count)

            # Calculate page range for pagination display (show 5 pages around current)
            page_range = []
            start_page = max(1, page - 2)
            end_page = min(total_pages, page + 2)
            page_range = list(range(start_page, end_page + 1))

            # Build URL parameters for pagination
            url_params = {}
            if search:
                url_params["search"] = search
            if per_page != 20:
                url_params["per_page"] = str(per_page)

            # Generate dynamic title based on search
            page_title = "Finding Models - Finding Model Forge"
            if search:
                page_title = f"Search: {search} - Finding Model Forge"

            response = templates.TemplateResponse(
                request=request,
                name="fragments/finding_models_list_content.html",
                context={
                    "finding_models": paginated_models,
                    "search_query": search or "",
                    "current_page": page,
                    "total_pages": total_pages,
                    "per_page": per_page,
                    "page_range": page_range,
                    "start_index": start_index + 1 if total_count > 0 else 0,
                    "end_index": end_index,
                    "total_count": total_count,
                    "url_params": url_params,
                    "is_htmx_request": True,
                    "page_title": page_title,
                },
            )

            # Build URL for browser history
            url_parts = ["/finding-models"]
            query_params = []
            if search:
                query_params.append(f"search={search}")
            if page > 1:
                query_params.append(f"page={page}")
            if per_page != 20:
                query_params.append(f"per_page={per_page}")

            push_url = f"{url_parts[0]}?{'&'.join(query_params)}" if query_params else url_parts[0]

            response.headers["HX-Push-Url"] = push_url
            return response

    # For full page requests, return the base template
    # It will determine what to show based on slug presence
    context: dict[str, Any] = {
        "user": current_user,
        "title": "Finding Models",
    }

    if slug:
        # Preload the detail data for initial render
        try:
            finding_model, index_entry = await finding_model_service.get_model_by_slug(slug)
            # Get the comment thread for this finding model
            thread = await finding_model_service.get_comments_for_model(finding_model.oifm_id)
            context.update(
                {
                    "initial_model": finding_model,
                    "finding_model": finding_model,  # Also add for fragment compatibility
                    "index_entry": index_entry,
                    "thread": thread,
                    "reference_type": "finding_model",
                    "reference_id": slug,
                    "current_user": current_user,
                    "show_detail": True,
                    "model_slug": slug,
                }
            )
        except NotFoundError:
            logger.error(f"Finding model '{slug}' not found for initial render")
            # Fall back to showing list view with error
            finding_models_list, total_count = await finding_model_service.list_models(None, 1, 20)
            context.update(
                {
                    "finding_models": finding_models_list,
                    "show_detail": False,
                    "error_message": f"Finding model '{slug}' not found",
                    "search_query": "",
                    "current_page": 1,
                    "total_pages": max(1, (total_count + 19) // 20),
                    "per_page": 20,
                    "page_range": [1],
                    "start_index": 1,
                    "end_index": min(20, total_count),
                    "total_count": total_count,
                    "url_params": {},
                }
            )
        except Exception as e:
            logger.error(f"Error loading finding model '{slug}' for initial render: {e}")
            # Fall back to showing list view with error
            finding_models_list, total_count = await finding_model_service.list_models(None, 1, 20)
            context.update(
                {
                    "finding_models": finding_models_list,
                    "show_detail": False,
                    "error_message": "Error loading finding model",
                    "search_query": "",
                    "current_page": 1,
                    "total_pages": max(1, (total_count + 19) // 20),
                    "per_page": 20,
                    "page_range": [1],
                    "start_index": 1,
                    "end_index": min(20, total_count),
                    "total_count": total_count,
                    "url_params": {},
                }
            )
    else:
        # Preload the list data for initial render with search/pagination
        paginated_models, total_count = await finding_model_service.list_models(search, page, per_page)

        # Calculate pagination
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        start_index = (page - 1) * per_page
        end_index = min(start_index + per_page, total_count)

        # Calculate page range for pagination display
        page_range = []
        start_page = max(1, page - 2)
        end_page = min(total_pages, page + 2)
        page_range = list(range(start_page, end_page + 1))

        # Build URL parameters for pagination
        url_params = {}
        if search:
            url_params["search"] = search
        if per_page != 20:
            url_params["per_page"] = str(per_page)

        context.update(
            {
                "finding_models": paginated_models,
                "show_detail": False,
                "search_query": search or "",
                "current_page": page,
                "total_pages": total_pages,
                "per_page": per_page,
                "page_range": page_range,
                "start_index": start_index + 1 if total_count > 0 else 0,
                "end_index": end_index,
                "total_count": total_count,
                "url_params": url_params,
            }
        )

    return templates.TemplateResponse(request=request, name="finding_models_base.html", context=context)


@router.post("/finding-models/{slug}/comments", response_model=None)
async def add_finding_model_comment(
    slug: str,
    request: Request,
    current_user: CurrentUserDep,
    finding_model_service: FindingModelServiceDep,
    user_repo: UserRepoDep,
    content: str = Form(...),
    parent_comment_id: str | None = Form(None),
) -> HTMLResponse | RedirectResponse:
    """Add a comment to a finding model."""
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

        # Get the finding model to get its oifm_id
        finding_model, _ = await finding_model_service.get_model_by_slug(slug)
        if not finding_model:
            raise HTTPException(status_code=404, detail=f"Finding model '{slug}' not found")

        # Add the comment (service handles validation and threading)
        if parent_comment_id:
            comment = await finding_model_service.add_comment_to_model(
                finding_model.oifm_id, current_user, content, parent_comment_id
            )
        else:
            comment = await finding_model_service.add_comment_to_model(finding_model.oifm_id, current_user, content)

        # Update user's comment index for rate limiting
        await user_repo.add_comment_to_index(
            user_id=current_user.id,
            entry=UserCommentEntry(
                reference_type="finding_model",
                reference_id=finding_model.oifm_id,
                finding_name=finding_model.name,
                comment_id=comment.id,
                created_at=datetime.now(UTC),
            ),
        )

        # Get updated thread
        thread = await finding_model_service.get_comments_for_model(finding_model.oifm_id)

        # Check if this is an HTMX request
        is_htmx = request.headers.get("HX-Request") == "true"

        if is_htmx:
            # Return rendered comment thread for HTMX swap
            return templates.TemplateResponse(
                request=request,
                name="components/comment_thread.html",
                context={
                    "thread": thread,
                    "reference_type": "finding_model",
                    "reference_id": slug,
                    "current_user": current_user,
                },
            )
        else:
            # Non-HTMX: redirect back to the finding model page
            return RedirectResponse(url=f"/finding-models/{slug}", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding comment to finding model '{slug}': {e}")
        if request.headers.get("HX-Request") == "true":
            error_html = (
                f'<div class="p-4 text-red-600 bg-red-50 dark:bg-red-900 dark:text-red-200 rounded-lg">'
                f"Error adding comment: {str(e)}</div>"
            )
            return HTMLResponse(content=error_html, status_code=500)
        else:
            raise HTTPException(status_code=500, detail=f"Error adding comment: {str(e)}") from e


@router.post("/finding-models/{slug}/comments/{comment_id}/report", response_model=None)
async def report_model_comment(
    slug: str,
    comment_id: str,
    request: Request,
    current_user: CurrentUserDep,
    finding_model_service: FindingModelServiceDep,
    comment_repo: CommentRepoDep,
) -> HTMLResponse:
    """Report a comment on a finding model."""
    # Check if user is logged in
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        # Get the finding model to verify it exists and get its oifm_id
        finding_model, _ = await finding_model_service.get_model_by_slug(slug)
        if not finding_model:
            return HTMLResponse('<div class="alert alert-danger">Model not found</div>', status_code=404)

        # Get the comment thread
        thread = await comment_repo.get_thread("finding_model", finding_model.oifm_id)
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
        logger.error(f"Error reporting comment on model '{slug}': {e}")
        error_html = '<span class="text-xs text-red-600 dark:text-red-400">Error</span>'
        return HTMLResponse(error_html, status_code=500)
