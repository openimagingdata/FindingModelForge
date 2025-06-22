from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth import get_optional_user
from app.models import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request, current_user: User | None = Depends(get_optional_user)
) -> HTMLResponse:
    """Home page."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "user": current_user, "title": "FastAPI Starter"},
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    """Login page."""
    return templates.TemplateResponse(
        "login.html", {"request": request, "title": "Login"}
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request, current_user: User = Depends(get_optional_user)
) -> HTMLResponse:
    """Protected dashboard page."""
    if not current_user:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "title": "Login Required",
                "message": "Please log in to access the dashboard.",
            },
        )

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": current_user, "title": "Dashboard"},
    )
