# ruff: noqa: B008
# mypy: disable-error-code="prop-decorator"
import re
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Annotated, Any, cast

import httpx
import humanize
from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from findingmodel import FindingModelFull

from app.auth import OptionalUserDep
from app.config import logger, settings
from app.dependencies import CacheDep, DraftRepoDep, FindingIndexDep
from app.vite_manifest import get_vite_asset_path

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Add vite asset helper to template globals
templates.env.globals["vite_asset"] = get_vite_asset_path


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, current_user: OptionalUserDep) -> HTMLResponse:
    """Home page."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"user": current_user, "title": "Finding Model Forge"},
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    """Login page."""
    return templates.TemplateResponse(request=request, name="login.html", context={"title": "Login"})


def _extract_attribute_names_from_generated_json(generated_json: str | None) -> list[str]:
    """Extract attribute names from a FindingModelFull JSON payload.

    Conservative parser that looks for an 'attributes' list and returns readable names.
    """
    if not generated_json:
        return []
    try:
        data = FindingModelFull.model_validate_json(generated_json).model_dump(mode="json", exclude_none=True)
        attrs: list[str] = []
        for item in data.get("attributes", []) or []:
            if isinstance(item, dict):
                # Try common name fields
                name = item.get("name") or item.get("title") or item.get("id")
                if isinstance(name, str) and name:
                    attrs.append(name)
        return attrs
    except Exception:
        return []


@router.get("/profile", response_class=HTMLResponse)
async def profile(
    request: Request,
    current_user: OptionalUserDep,
    draft_repo: DraftRepoDep,
) -> HTMLResponse:
    """Protected profile page with user's drafts list."""
    logger.info(f"Accessing profile for user: {current_user.login if current_user else 'Guest'}")
    if not current_user:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "title": "Login Required",
                "message": "Please log in to access your profile.",
            },
        )

    # Load user's drafts
    user_drafts: list[dict[str, Any]] = []
    try:
        drafts = await draft_repo.list_for_user(current_user.id)
        for d in drafts:
            # Humanized timestamp
            try:
                updated_dt = d.updated_at
                if updated_dt.tzinfo is None:
                    updated_dt = updated_dt.replace(tzinfo=UTC)
                updated_display = humanize.naturaltime(datetime.now(UTC) - updated_dt)
            except Exception:
                updated_display = d.updated_at.isoformat()
            # Slug for view links
            name_slug = (d.name or "").lower().replace(" ", "-").replace("_", "-")
            has_generated = bool(getattr(d, "generated_json", None))
            user_drafts.append(
                {
                    "id": d.id,
                    "name": d.name,
                    "status": d.status,
                    "updated_at": d.updated_at.isoformat(),
                    "updated_display": updated_display,
                    "slug": name_slug,
                    "has_generated": has_generated,
                    "attribute_names": _extract_attribute_names_from_generated_json(getattr(d, "generated_json", None)),
                }
            )
    except Exception as e:
        logger.warning(f"Failed to load drafts for user {current_user.login}: {e}")
        user_drafts = []

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "user": current_user,
            "title": "Profile",
            "drafts": user_drafts,
        },
    )


@router.get("/create-finding-model", response_class=HTMLResponse)
async def create_finding_model_page(
    request: Request, current_user: OptionalUserDep, name: str | None = None, draft_id: str | None = None
) -> HTMLResponse:
    """Finding model creation page - now using HTMX workflow."""
    logger.info(f"Accessing finding model creation for user: {current_user.login if current_user else 'Guest'}")

    if not current_user:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "title": "Login Required",
                "message": "Please log in to create finding models.",
            },
        )

    # Use the new HTMX-based template
    return templates.TemplateResponse(
        request=request,
        name="create_finding_model_htmx.html",
        context={
            "user": current_user,
            "title": "Create Finding Model",
            "start_name": name or "",
            "start_draft_id": draft_id or "",
        },
    )


async def _get_finding_models_list(
    index: Any,  # Index type from findingmodel.index
    cache: Any,  # RedisCache type
) -> list[dict[str, Any]]:
    """
    Shared logic to fetch the finding models list with caching.

    Returns:
        List of finding model dictionaries with id, name, and slug
    """
    # Check cache first
    finding_models = await cache.get_finding_models()
    if finding_models:
        logger.debug("Cache hit for finding models list")
        return cast(list[dict[str, Any]], finding_models)

    logger.debug("Cache miss for finding models list, fetching from index")

    # Fetch all finding models from the index
    # Use a case-insensitive sort by adding a computed field for lowercase name
    finding_models_data: list[dict[str, Any]] = await index.index_collection.aggregate(
        [
            {"$addFields": {"name_lower": {"$toLower": "$name"}}},
            {"$sort": {"name_lower": 1}},
            {"$project": {"name_lower": 0}},  # Exclude the helper field from results
        ]
    ).to_list(length=None)

    if not finding_models_data:
        logger.warning("No finding models found in index")
        return []

    def slugify(name: str) -> str:
        """Convert a name to a URL-friendly slug."""
        return name.lower().replace(" ", "-").replace("_", "-")

    finding_models = [
        {"id": model["oifm_id"], "name": model["name"], "slug": slugify(model["name"])} for model in finding_models_data
    ]

    # Cache the finding models list for 1 hour
    await cache.set_finding_models(finding_models)

    return finding_models


@router.get("/finding-models", response_class=HTMLResponse)
@router.get("/finding-models/{slug}", response_class=HTMLResponse)
async def finding_models(
    request: Request,
    current_user: OptionalUserDep,
    index: FindingIndexDep,
    cache: CacheDep,
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
                finding_model, index_entry = await _get_finding_model_with_cache(slug, index, cache)
                response = templates.TemplateResponse(
                    request=request,
                    name="fragments/finding_model_detail_content.html",
                    context={
                        "finding_model": finding_model,
                        "index_entry": index_entry,
                        "show_json": True,
                        "show_ids": True,
                        "is_htmx_request": True,
                        "page_title": f"{finding_model.name} - Finding Model Forge",
                    },
                )
                # Tell HTMX what URL to push to browser history
                response.headers["HX-Push-Url"] = f"/finding-models/{slug}"
                return response
            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching finding model '{slug}': {e}")
                error_content = (
                    '<div class="p-4 text-red-600 bg-red-50 dark:bg-red-900 dark:text-red-200 rounded-lg">'
                    "Failed to load finding model</div>"
                )
                return HTMLResponse(content=error_content, status_code=500)
            except HTTPException:
                # Let HTTPException propagate as-is
                raise
            except Exception as e:
                logger.error(f"Error displaying finding model '{slug}': {e}")
                error_content = (
                    '<div class="p-4 text-red-600 bg-red-50 dark:bg-red-900 dark:text-red-200 rounded-lg">'
                    "Error loading finding model</div>"
                )
                return HTMLResponse(content=error_content, status_code=500)
        else:
            # Return list fragment with search and pagination
            finding_models_list = await _get_finding_models_list(index, cache)

            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                finding_models_list = [
                    model
                    for model in finding_models_list
                    if search_lower in model["name"].lower() or search_lower in str(model["id"]).lower()
                ]

            # Calculate pagination
            total_count = len(finding_models_list)
            total_pages = max(1, (total_count + per_page - 1) // per_page)
            start_index = (page - 1) * per_page
            end_index = min(start_index + per_page, total_count)
            paginated_models = finding_models_list[start_index:end_index]

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
    context = {
        "user": current_user,
        "title": "Finding Models",
    }

    if slug:
        # Preload the detail data for initial render
        try:
            finding_model, index_entry = await _get_finding_model_with_cache(slug, index, cache)
            context.update(
                cast(
                    dict[str, Any],
                    {
                        "initial_model": finding_model,
                        "finding_model": finding_model,  # Also add for fragment compatibility
                        "index_entry": index_entry,
                        "show_detail": True,
                        "model_slug": slug,
                    },
                )
            )
        except Exception as e:
            logger.error(f"Error loading finding model '{slug}' for initial render: {e}")
            # Fall back to showing list view with error
            finding_models_list = await _get_finding_models_list(index, cache)
            context.update(
                cast(
                    dict[str, Any],
                    {
                        "finding_models": finding_models_list,
                        "show_detail": False,
                        "error_message": f"Finding model '{slug}' not found",
                        "search_query": "",
                        "current_page": 1,
                        "total_pages": 1,
                        "per_page": 20,
                        "page_range": [1],
                        "start_index": 1,
                        "end_index": len(finding_models_list),
                        "total_count": len(finding_models_list),
                        "url_params": {},
                    },
                )
            )
    else:
        # Preload the list data for initial render with search/pagination
        finding_models_list = await _get_finding_models_list(index, cache)

        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            finding_models_list = [
                model
                for model in finding_models_list
                if search_lower in model["name"].lower() or search_lower in str(model["id"]).lower()
            ]

        # Calculate pagination
        total_count = len(finding_models_list)
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        start_index = (page - 1) * per_page
        end_index = min(start_index + per_page, total_count)
        paginated_models = finding_models_list[start_index:end_index]

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
            cast(
                dict[str, Any],
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
                },
            )
        )

    return templates.TemplateResponse(request=request, name="finding_models_base.html", context=context)


async def _get_finding_model_with_cache(
    slug: str,
    index: Any,  # Index type from findingmodel.index
    cache: Any,  # RedisCache type
) -> tuple[FindingModelFull, Any]:
    """
    Shared logic to fetch a finding model with caching.

    Returns:
        Tuple of (finding_model, index_entry)
    """
    # Prepare candidate lookups: prefer the space-normalized variant first (backward-compatible
    # with existing tests and behavior), then try the raw slug and separator swaps so we handle
    # names that truly include hyphens like "acro-osteolysis".
    raw_slug = (slug or "").strip().lower()
    variant_spaces = raw_slug.replace("-", " ").replace("_", " ")
    variant_hyphen = raw_slug.replace("_", "-")
    variant_underscore = raw_slug.replace("-", "_")
    candidates: list[str] = []
    for c in (variant_spaces, raw_slug, variant_hyphen, variant_underscore):
        if c and c not in candidates:
            candidates.append(c)

    index_entry = None
    matched_variant = None
    for candidate in candidates:
        try:
            index_entry = await index.get(candidate)
        except Exception:
            index_entry = None
        if index_entry:
            matched_variant = candidate
            break

    if not index_entry:
        # Fallback: query the backing collection by a flexible regex that allows
        # spaces, hyphens, or underscores between tokens, to handle cases like
        # "bow-tie" vs "bow tie".
        tokens = [t for t in re.split(r"[-_\s]+", raw_slug) if t]
        if tokens:
            sep = r"[\s\-_]+"
            pattern = "^" + sep.join(re.escape(t) for t in tokens) + "$"
            try:
                doc = await index.index_collection.find_one({"name": {"$regex": pattern, "$options": "i"}})
            except Exception:
                doc = None
            if not doc:
                # Try matching by filename if name lookup fails
                base = raw_slug.replace("-", "_").replace(" ", "_")
                filename_regex = rf"{re.escape(base)}.*\.fm\.json$"
                try:
                    doc = await index.index_collection.find_one(
                        {"filename": {"$regex": filename_regex, "$options": "i"}}
                    )
                except Exception:
                    doc = None
            if doc and doc.get("filename"):
                index_entry = SimpleNamespace(
                    filename=doc.get("filename"),
                    name=doc.get("name"),
                    description=doc.get("description"),
                )
                matched_variant = raw_slug
        if not index_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Finding model '{raw_slug}' not found in index",
            )

    # Use the space-normalized variant as the canonical cache key to remain compatible
    # with existing expectations/tests while ensuring consistent keys.
    cache_slug = variant_spaces

    # Check cache first
    finding_model = await cache.get_finding_model(cache_slug)
    if finding_model:
        logger.debug(
            f"Cache hit for finding model '{raw_slug}' (matched variant: {matched_variant}, cache key: {cache_slug})"
        )
    else:
        logger.debug(
            f"Cache miss for finding model '{raw_slug}' (matched variant: {matched_variant}), fetching from GitHub"
        )

        # Extract filename from index entry
        if not index_entry.filename:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Finding model entry missing filename",
            )

        # Construct the GitHub raw URL
        github_url = f"{settings.finding_models_github_base_url}{index_entry.filename}"
        logger.debug(f"Fetching finding model from: {github_url}")

        # Fetch the finding model JSON from GitHub
        async with httpx.AsyncClient() as client:
            response = await client.get(github_url)
            response.raise_for_status()
            finding_model = FindingModelFull.model_validate_json(response.text)

        # Cache the result
        await cache.set_finding_model(cache_slug, finding_model)
        logger.debug(f"Cached finding model '{raw_slug}' (cache key: {cache_slug}) for future requests")

    return finding_model, index_entry
