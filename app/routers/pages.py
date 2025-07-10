# ruff: noqa: B008
# mypy: disable-error-code="prop-decorator"
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from findingmodel import FindingModelFull
from findingmodel.index import Index

from app.auth import get_optional_user
from app.config import logger, settings
from app.dependencies import get_finding_index
from app.models import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# Use get_optional_user directly as a dependency
get_optional_user_dependency = get_optional_user


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request, current_user: Annotated[User | None, Depends(get_optional_user_dependency)]
) -> HTMLResponse:
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
async def profile(request: Request, current_user: User = Depends(get_optional_user_dependency)) -> HTMLResponse:
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
async def create_finding_model_page(
    request: Request, current_user: Annotated[User | None, Depends(get_optional_user_dependency)]
) -> HTMLResponse:
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


@router.get("/finding-model/{slug}", response_class=HTMLResponse)
async def finding_model_display(
    request: Request,
    slug: str,
    current_user: Annotated[User | None, Depends(get_optional_user_dependency)],
    index: Annotated[Index, Depends(get_finding_index)],
) -> HTMLResponse:
    """Display a finding model by slug."""
    logger.info(f"Accessing finding model '{slug}' for user: {current_user.login if current_user else 'Guest'}")

    slug = slug.replace("-", " ").replace("_", " ").lower().strip()
    try:
        # Look up the finding model in the index by slug
        index_entry = await index.get(slug)
        if not index_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Finding model '{slug}' not found in index",
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
                "slug": slug,
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
