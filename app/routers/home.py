"""Home page and basic site navigation routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth import OptionalUserDep
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
