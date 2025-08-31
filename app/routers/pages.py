# ruff: noqa: B008
# mypy: disable-error-code="prop-decorator"
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.auth import OptionalUserDep
from app.config import logger
from app.templates import templates
from app.vite_manifest import get_vite_asset_path

router = APIRouter()

# Add vite asset helper to template globals
templates.env.globals["vite_asset"] = get_vite_asset_path


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
