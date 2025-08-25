"""User profile page routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth import OptionalUserDep
from app.config import logger
from app.dependencies import DraftServiceDep
from app.vite_manifest import get_vite_asset_path

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Add vite asset helper to template globals
templates.env.globals["vite_asset"] = get_vite_asset_path


@router.get("/profile", response_class=HTMLResponse)
async def profile(
    request: Request,
    current_user: OptionalUserDep,
    draft_service: DraftServiceDep,
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

    # Load user's drafts using service
    user_drafts = await draft_service.get_drafts_for_user(current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "user": current_user,
            "title": "Profile",
            "drafts": user_drafts,
        },
    )
