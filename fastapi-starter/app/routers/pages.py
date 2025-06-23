# ruff: noqa: B008
# mypy: disable-error-code="prop-decorator"
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth import get_optional_user
from app.config import logger
from app.models import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, current_user: User | None = Depends(get_optional_user)) -> HTMLResponse:
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


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: User = Depends(get_optional_user)) -> HTMLResponse:
    """Protected dashboard page."""
    logger.info(f"Accessing dashboard for user: {current_user.login if current_user else 'Guest'}")
    if not current_user:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "title": "Login Required",
                "message": "Please log in to access the dashboard.",
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"user": current_user, "title": "Dashboard"},
    )
