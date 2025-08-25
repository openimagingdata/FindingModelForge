"""Authentication-related page routes (login, logout, callback pages)."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.vite_manifest import get_vite_asset_path

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Add vite asset helper to template globals
templates.env.globals["vite_asset"] = get_vite_asset_path


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    """Login page."""
    return templates.TemplateResponse(request=request, name="login.html", context={"title": "Login"})
