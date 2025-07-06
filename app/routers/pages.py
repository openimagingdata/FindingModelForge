# ruff: noqa: B008
# mypy: disable-error-code="prop-decorator"
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import get_optional_user
from app.config import logger
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
    return RedirectResponse(url="/profile", status_code=301)


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
