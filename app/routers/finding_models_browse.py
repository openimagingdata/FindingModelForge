# ruff: noqa: B008
# mypy: disable-error-code="prop-decorator"
from typing import Annotated, Any

from fastapi import APIRouter, Form, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import CurrentUserDep, OptionalUserDep
from app.config import logger
from app.dependencies import FindingModelServiceDep
from app.services import NotFoundError
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
                ctx = await finding_model_service.prepare_detail_context(slug)
                response = templates.TemplateResponse(
                    request=request,
                    name="fragments/finding_model_detail_content.html",
                    context={
                        "finding_model": ctx.finding_model,
                        "thread": ctx.thread,
                        "reference_type": ctx.reference_type,
                        "reference_id": ctx.reference_id,
                        "current_user": current_user,
                        "show_json": True,
                        "show_ids": True,
                        "is_htmx_request": True,
                        "page_title": f"{ctx.finding_model.name} - Finding Model Forge",
                    },
                )
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
            list_ctx = await finding_model_service.prepare_list_context(search, page, per_page)

            response = templates.TemplateResponse(
                request=request,
                name="fragments/finding_models_list_content.html",
                context={
                    "finding_models": list_ctx.models,
                    "search_query": search or "",
                    "current_page": list_ctx.current_page,
                    "total_pages": list_ctx.total_pages,
                    "per_page": list_ctx.per_page,
                    "page_range": list_ctx.page_range,
                    "start_index": list_ctx.start_index,
                    "end_index": list_ctx.end_index,
                    "total_count": list_ctx.total_count,
                    "url_params": list_ctx.url_params,
                    "is_htmx_request": True,
                    "page_title": list_ctx.page_title,
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
    context: dict[str, Any] = {
        "user": current_user,
        "title": "Finding Models",
    }

    if slug:
        # Preload the detail data for initial render
        try:
            ctx = await finding_model_service.prepare_detail_context(slug)
            context.update(
                {
                    "initial_model": ctx.finding_model,
                    "finding_model": ctx.finding_model,
                    "thread": ctx.thread,
                    "reference_type": ctx.reference_type,
                    "reference_id": ctx.reference_id,
                    "current_user": current_user,
                    "show_detail": True,
                    "model_slug": slug,
                }
            )
        except NotFoundError:
            logger.error(f"Finding model '{slug}' not found for initial render")
            # Fall back to showing list view with error
            fallback_ctx = await finding_model_service.prepare_list_context(None, 1, 20)
            context.update(
                {
                    "finding_models": fallback_ctx.models,
                    "show_detail": False,
                    "error_message": f"Finding model '{slug}' not found",
                    "search_query": "",
                    "current_page": fallback_ctx.current_page,
                    "total_pages": fallback_ctx.total_pages,
                    "per_page": fallback_ctx.per_page,
                    "page_range": fallback_ctx.page_range,
                    "start_index": fallback_ctx.start_index,
                    "end_index": fallback_ctx.end_index,
                    "total_count": fallback_ctx.total_count,
                    "url_params": fallback_ctx.url_params,
                }
            )
        except Exception as e:
            logger.error(f"Error loading finding model '{slug}' for initial render: {e}")
            # Fall back to showing list view with error
            fallback_ctx = await finding_model_service.prepare_list_context(None, 1, 20)
            context.update(
                {
                    "finding_models": fallback_ctx.models,
                    "show_detail": False,
                    "error_message": "Error loading finding model",
                    "search_query": "",
                    "current_page": fallback_ctx.current_page,
                    "total_pages": fallback_ctx.total_pages,
                    "per_page": fallback_ctx.per_page,
                    "page_range": fallback_ctx.page_range,
                    "start_index": fallback_ctx.start_index,
                    "end_index": fallback_ctx.end_index,
                    "total_count": fallback_ctx.total_count,
                    "url_params": fallback_ctx.url_params,
                }
            )
    else:
        # Preload the list data for initial render with search/pagination
        list_ctx = await finding_model_service.prepare_list_context(search, page, per_page)
        context.update(
            {
                "finding_models": list_ctx.models,
                "show_detail": False,
                "search_query": search or "",
                "current_page": list_ctx.current_page,
                "total_pages": list_ctx.total_pages,
                "per_page": list_ctx.per_page,
                "page_range": list_ctx.page_range,
                "start_index": list_ctx.start_index,
                "end_index": list_ctx.end_index,
                "total_count": list_ctx.total_count,
                "url_params": list_ctx.url_params,
            }
        )

    return templates.TemplateResponse(request=request, name="finding_models_base.html", context=context)


@router.post("/finding-models/{slug}/comments", response_model=None)
async def add_finding_model_comment(
    slug: str,
    request: Request,
    current_user: CurrentUserDep,
    finding_model_service: FindingModelServiceDep,
    content: str = Form(...),
    parent_comment_id: str | None = Form(None),
) -> HTMLResponse | RedirectResponse:
    """Add a comment to a finding model."""
    try:
        # Check if user is logged in
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Get the finding model to get its oifm_id
        finding_model = await finding_model_service.get_model_by_slug(slug)
        if not finding_model:
            raise HTTPException(status_code=404, detail=f"Finding model '{slug}' not found")

        # Add the comment (service handles rate limiting, validation, and threading)
        if parent_comment_id:
            await finding_model_service.add_comment_to_model(
                finding_model.oifm_id, current_user, content, parent_comment_id
            )
        else:
            await finding_model_service.add_comment_to_model(finding_model.oifm_id, current_user, content)

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
) -> HTMLResponse:
    """Report a comment on a finding model."""
    # Check if user is logged in
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        # Get the finding model to verify it exists and get its oifm_id
        finding_model = await finding_model_service.get_model_by_slug(slug)
        if not finding_model:
            return HTMLResponse('<div class="alert alert-danger">Model not found</div>', status_code=404)

        # Report the comment (service handles validation)
        await finding_model_service.report_model_comment(finding_model.oifm_id, comment_id, current_user.id)

        # Return a success message that replaces the report button
        success_html = '<span class="text-xs text-green-600 dark:text-green-400">Reported</span>'
        return HTMLResponse(success_html)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reporting comment on model '{slug}': {e}")
        error_html = '<span class="text-xs text-red-600 dark:text-red-400">Error</span>'
        return HTMLResponse(error_html, status_code=500)
