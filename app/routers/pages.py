# ruff: noqa: B008
# mypy: disable-error-code="prop-decorator"
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from findingmodel import FindingModelFull

from app.auth import OptionalUserDep
from app.config import logger, settings
from app.dependencies import CacheDep, FindingIndexDep

router = APIRouter()
templates = Jinja2Templates(directory="templates")


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


@router.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, current_user: OptionalUserDep) -> HTMLResponse:
    """Protected profile page."""
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

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={"user": current_user, "title": "Profile"},
    )


@router.get("/dashboard", response_class=RedirectResponse)
async def dashboard_redirect() -> RedirectResponse:
    """Redirect old dashboard route to profile."""
    return RedirectResponse(url="/profile", status_code=status.HTTP_301_MOVED_PERMANENTLY)


@router.get("/create-finding-model", response_class=HTMLResponse)
async def create_finding_model_page(request: Request, current_user: OptionalUserDep) -> HTMLResponse:
    """Finding model creation page."""
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

    return templates.TemplateResponse(
        request=request,
        name="create_finding_model.html",
        context={"user": current_user, "title": "Create Finding Model"},
    )


@router.get("/finding-models", response_class=HTMLResponse)
async def finding_models_list(
    request: Request,
    current_user: OptionalUserDep,
    index: FindingIndexDep,
    cache: CacheDep,
) -> HTMLResponse:
    """List all finding models."""
    logger.info(f"Accessing finding models list for user: {current_user.login if current_user else 'Guest'}")

    def make_response(finding_models: list[dict[str, Any]]) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="finding_models_list.html",
            context={"user": current_user, "title": "Finding Models", "finding_models": finding_models},
        )

    # Check cache first
    finding_models = await cache.get_finding_models()
    if finding_models:
        logger.debug("Cache hit for finding models list")
        return make_response(finding_models)

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
        return templates.TemplateResponse(
            request=request,
            name="finding_models_list.html",
            context={"user": current_user, "title": "Finding Models", "finding_models": []},
        )

    def slugify(name: str) -> str:
        """Convert a name to a URL-friendly slug."""
        return name.lower().replace(" ", "-").replace("_", "-")

    finding_models = [
        {"id": model["oifm_id"], "name": model["name"], "slug": slugify(model["name"])} for model in finding_models_data
    ]

    # Cache the finding models list for 1 hour
    await cache.set_finding_models(finding_models)

    return make_response(finding_models)


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
    slug = slug.replace("-", " ").replace("_", " ").lower().strip()

    # Look up the finding model in the index by slug (needed for metadata)
    index_entry = await index.get(slug)
    if not index_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding model '{slug}' not found in index",
        )

    # Check cache first
    finding_model = await cache.get_finding_model(slug)
    if finding_model:
        logger.debug(f"Cache hit for finding model '{slug}'")
    else:
        logger.debug(f"Cache miss for finding model '{slug}', fetching from GitHub")

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
        await cache.set_finding_model(slug, finding_model)
        logger.debug(f"Cached finding model '{slug}' for future requests")

    return finding_model, index_entry


@router.get("/finding-model/{slug}/partial", response_class=HTMLResponse)
async def finding_model_partial(
    request: Request,
    slug: str,
    current_user: OptionalUserDep,
    index: FindingIndexDep,
    cache: CacheDep,
) -> HTMLResponse:
    """Return partial HTML for finding model display."""
    logger.info(f"Accessing finding model partial '{slug}' for user: {current_user.login if current_user else 'Guest'}")

    try:
        finding_model, index_entry = await _get_finding_model_with_cache(slug, index, cache)

        # Return just the component template
        return templates.TemplateResponse(
            request=request,
            name="components/finding_model_display.html",
            context={
                "finding_model": finding_model,
                "index_entry": index_entry,
                "slug": slug.replace("-", " ").replace("_", " ").lower().strip(),
            },
        )

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
        logger.error(f"Error displaying finding model partial '{slug}': {e}")
        error_content = (
            '<div class="p-4 text-red-600 bg-red-50 dark:bg-red-900 dark:text-red-200 rounded-lg">'
            "Error loading finding model</div>"
        )
        return HTMLResponse(content=error_content, status_code=500)


@router.get("/finding-model/{slug}", response_class=HTMLResponse)
async def finding_model_display(
    request: Request,
    slug: str,
    current_user: OptionalUserDep,
    index: FindingIndexDep,
    cache: CacheDep,
) -> HTMLResponse:
    """Display a finding model by slug with caching."""
    logger.info(f"Accessing finding model '{slug}' for user: {current_user.login if current_user else 'Guest'}")

    try:
        finding_model, index_entry = await _get_finding_model_with_cache(slug, index, cache)

        # Normalize slug for template context
        normalized_slug = slug.replace("-", " ").replace("_", " ").lower().strip()

        # Pass the data to the template
        return templates.TemplateResponse(
            request=request,
            name="finding_model_display.html",
            context={
                "user": current_user,
                "title": f"Finding Model: {finding_model.name}",
                "finding_model": finding_model,
                "finding_model_json": finding_model.model_dump_json(indent=2, exclude_none=True),
                "filename": index_entry.filename,
                "index_entry": index_entry,
                "slug": normalized_slug,
            },
        )

    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching finding model '{slug}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch finding model data: {e}",
        ) from e
    except HTTPException:
        # Let HTTPException propagate as-is
        raise
    except Exception as e:
        logger.error(f"Error displaying finding model '{slug}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to display finding model: {e}",
        ) from e
