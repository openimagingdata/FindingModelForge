"""Home page and basic site navigation routes."""

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from loguru import logger
from pydantic import BaseModel, EmailStr, ValidationError

from app.auth import OptionalUserDep
from app.dependencies import SuggestionRepoDep
from app.templates import templates
from app.vite_manifest import get_vite_asset_path

router = APIRouter()

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


@router.post("/suggestions", response_class=HTMLResponse)
async def submit_suggestion(
    request: Request,
    current_user: OptionalUserDep,
    suggestion_repo: SuggestionRepoDep,
    content: str = Form(..., min_length=1, max_length=300),
    submitter_email: str | None = Form(None),
) -> HTMLResponse:
    """Submit a suggestion from authenticated or anonymous user."""
    try:
        # Validate email format if provided
        validated_email: str | None = None
        if submitter_email:
            try:
                # Use Pydantic model for email validation
                class EmailValidator(BaseModel):
                    email: EmailStr

                validator = EmailValidator(email=submitter_email)
                validated_email = str(validator.email)
            except ValidationError:
                logger.warning(f"Invalid email format: {submitter_email}")
                return templates.TemplateResponse(
                    request=request,
                    name="components/suggestion_alert.html",
                    context={
                        "success": False,
                        "message": "Invalid email address format. Please check and try again.",
                    },
                )

        # Determine user_id and email based on auth state
        user_id = current_user.id if current_user else None
        email = validated_email or (current_user.email if current_user else None)

        # Save suggestion
        suggestion_id = await suggestion_repo.create(
            content=content,
            user_id=user_id,
            submitter_email=email,
        )

        logger.info(f"Suggestion created: id={suggestion_id}, user_id={user_id}, has_email={bool(email)}")

        # Return success message
        if email:
            message = "Thanks for your suggestion! We'll notify you when we make progress."
        else:
            message = "Thanks for your suggestion! We'll review it soon."

        return templates.TemplateResponse(
            request=request,
            name="components/suggestion_alert.html",
            context={"success": True, "message": message},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting suggestion: {e}", exc_info=True)
        return templates.TemplateResponse(
            request=request,
            name="components/suggestion_alert.html",
            context={
                "success": False,
                "message": "Sorry, something went wrong. Please try again later.",
            },
        )
