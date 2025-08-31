"""Finding Model creation workflow routes."""

# ruff: noqa: B008, I001

import json
from typing import Annotated, Any

from fastapi import APIRouter, Form, HTTPException, Path, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response


from findingmodel.tools.similar_finding_models import SimilarModelAnalysis  # noqa: F401

from app.auth import CurrentUserDep
from app.config import logger
from app.templates import templates
from app.vite_manifest import get_vite_asset_path
from app.dependencies import (
    CreationServiceDep,
    CreationSessionDep,
    DraftServiceDep,
    FindingModelCreationSession,
    SessionManagerDep,
)
from app.models import FindingModelInputs

TEST_USER_ID = 999999

# Type definition for step numbers in the creation workflow
StepNumber = Annotated[int, Path(ge=1, le=3, description="Step number (1-3) in the creation workflow")]


def parse_synonyms(synonyms: str) -> list[str]:
    """Parse synonyms from JSON string."""
    if not synonyms.strip():
        return []

    try:
        synonyms_parsed = json.loads(synonyms)
        if not isinstance(synonyms_parsed, list) and not all(s and isinstance(s, str) for s in synonyms_parsed):
            raise ValueError("Synonyms must be a JSON array of strings")
        return [s.strip() for s in synonyms_parsed]
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid synonyms format: {str(e)}"
        ) from e


def render_step_template(
    request: Request, step_number: int, session: FindingModelCreationSession, **extra_context: Any
) -> str:
    """Helper function to render step templates with common context."""
    step_templates = {
        1: "components/finding_model_creation/step_1_enter_name.html",
        2: "components/finding_model_creation/step_2_edit_description.html",
        3: "components/finding_model_creation/step_3_review_overlap.html",
    }

    if step_number not in step_templates:
        raise ValueError(f"Invalid step number: {step_number}")

    context = {"request": request, "current_step": step_number, "session_data": session, **extra_context}

    return templates.get_template(step_templates[step_number]).render(**context)


router = APIRouter()

# Ensure shared template globals are set (e.g., vite asset helper used by base.html)
templates.env.globals["vite_asset"] = get_vite_asset_path


# ===== HTMX ENDPOINTS FOR STEP-BY-STEP CREATION =====


@router.get("/step/{step_number}")
async def get_creation_step(
    step_number: StepNumber,
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
) -> HTMLResponse:
    """Get a specific step in the creation workflow."""
    try:
        # Update session step
        session.current_step = step_number

        # Add step-specific context
        extra_context = {}
        if step_number == 3:  # Similar models review
            extra_context["similar_models"] = session.similar_models

        html_content = render_step_template(request, step_number, session, **extra_context)
        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(f"Error getting creation step {step_number}: {str(e)}", exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error loading step {step_number}: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)


@router.post("/step/1")
async def process_step_1(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    creation_service: CreationServiceDep,
    draft_service: DraftServiceDep,
    name: str = Form(min_length=3, max_length=200),
) -> Response:
    """Process step 1: Check name and generate description."""
    try:
        logger.info(f"Step 1 processing started for user {current_user.login}")
        logger.info(f"Received name: '{name}' (length: {len(name)})")

        # FastAPI + Pydantic already validated the form data
        # name is already validated by Form() parameter

        # Auto-resume: if the user has an editable draft with this name, jump to step 4
        draft = None
        try:
            draft = await draft_service.find_editable_by_name(user_id=current_user.id, name=name)
        except Exception as e:
            logger.warning(f"Draft lookup failed for name '{name}': {e}")
        if draft is not None:
            logger.info(f"Resuming editable draft {draft.id} for name '{name}'")
            session.name = draft.name
            session.description = draft.inputs.description
            session.synonyms = draft.inputs.synonyms or []
            session.attributes_markdown = (
                draft.inputs.attributes_markdown
                if draft.inputs.attributes_markdown
                else creation_service.generate_default_attributes_markdown(draft.name)
            )
            session.draft_id = draft.id
            await session_manager.update_session(session)
            return RedirectResponse(url=f"/drafts/{draft.id}?mode=edit", status_code=303)

        # If there's a submitted draft with this name, jump to step 5 with read-only view
        try:
            latest = await draft_service.find_latest_by_name(user_id=current_user.id, name=name)
        except Exception:
            latest = None
        if latest is not None and latest.status == "submitted":
            logger.info(f"Resuming submitted draft {latest.id} for name '{name}' into review step")
            session.name = latest.name
            session.description = latest.inputs.description
            session.synonyms = latest.inputs.synonyms or []
            session.attributes_markdown = (
                latest.inputs.attributes_markdown
                if latest.inputs.attributes_markdown
                else creation_service.generate_default_attributes_markdown(latest.name)
            )
            session.draft_id = latest.id
            session.draft_status = latest.status
            # Human-friendly submitted time (UTC)
            try:
                session.submitted_display_time = draft_service.format_submitted_time(latest.updated_at)
            except Exception:
                session.submitted_display_time = None
            await session_manager.update_session(session)
            return RedirectResponse(url=f"/drafts/{latest.id}?mode=view", status_code=303)

        # Check name availability
        is_available = await creation_service.check_name_availability(name, current_user.id)
        if not is_available:
            session.error_message = f"Name '{name}' already exists in the index"
            await session_manager.update_session(session)
            html_content = render_step_template(request, 1, session, form_data={"name": name})
            return HTMLResponse(content=html_content)

        # Generate finding info (using service layer)
        test_mode = creation_service.is_test_user(current_user.id)
        finding_info = await creation_service.generate_finding_info(name, test_mode=test_mode)

        # Update session
        session.name = name
        # New name path: ensure we aren't carrying over an old draft id
        session.draft_id = None
        session.description = finding_info.description
        session.synonyms = finding_info.synonyms or []
        session.current_step = 2
        await session_manager.update_session(session)

        # Move to step 2
        html_content = render_step_template(request, 2, session)
        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(f"Error processing step 1: {str(e)}", exc_info=True)
        session.error_message = f"Error generating description: {str(e)}"
        await session_manager.update_session(session)

        html_content = render_step_template(
            request, 1, session, form_data={"name": name}, error_message=session.error_message
        )
        return HTMLResponse(content=html_content, status_code=500)


@router.post("/step/2")
async def process_step_2(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    creation_service: CreationServiceDep,
    draft_service: DraftServiceDep,
    synonyms: str = Form(default=""),
    description: str = Form(min_length=10, max_length=1000),
) -> Response:
    """Process step 2: Update description and find similar models."""
    try:
        assert session.name, "Session name must be set before processing step 2"
        # Parse synonyms manually; if Alpine hasn't initialized yet, the hidden
        # synonyms field may post as an empty string. In that case, fall back to
        # the session's synonyms to preserve reuse behavior when inputs are unchanged.
        raw_synonyms = synonyms
        synonyms_list = parse_synonyms(raw_synonyms)
        if (not raw_synonyms.strip()) and session.synonyms:
            # Treat blank post as "no client value provided yet" rather than an intentional clear.
            # If the user actually clears synonyms via UI, Alpine will send "[]", which is non-blank.
            synonyms_list = session.synonyms
        logger.info(f"Step 2: Parsed synonyms: {synonyms_list}")

        # Update session
        session.description = description
        session.synonyms = synonyms_list
        session.current_step = 3

        # Find similar models (using service layer)
        test_mode = creation_service.is_test_user(current_user.id)
        analysis = await creation_service.find_similar_models(
            name=session.name or "", description=description, synonyms=synonyms_list, test_mode=test_mode
        )

        # Convert SearchResult objects to plain dictionaries for session storage
        session.similar_models = [dict(model) for model in analysis.similar_models]

        await session_manager.update_session(session)

        if session.similar_models:
            # If similar models found, move to step 3 to review them
            html_content = render_step_template(
                request, 3, session, similar_models=session.similar_models, form_data={"synonyms": raw_synonyms}
            )
            return HTMLResponse(content=html_content)

        # Generate default attributes markdown
        if not session.attributes_markdown:
            session.attributes_markdown = creation_service.generate_default_attributes_markdown(
                session.name or "the finding"
            )

        # Create draft with current session data
        inputs = FindingModelInputs(
            description=session.description or "",
            synonyms=session.synonyms,
            attributes_markdown=session.attributes_markdown,
        )
        draft = await draft_service.save_draft(
            user_id=current_user.id, name=session.name, inputs=inputs, draft_id=session.draft_id
        )

        # Update session and redirect to draft editor
        session.draft_id = draft.id
        await session_manager.update_session(session)

        return RedirectResponse(url=f"/drafts/{draft.id}?mode=edit&created=true", status_code=303)

    except Exception as e:
        logger.error(f"Error processing step 2: {str(e)}", exc_info=True)
        session.error_message = f"Error finding similar models: {str(e)}"
        await session_manager.update_session(session)

        html_content = render_step_template(request, 2, session, error_message=session.error_message)
        return HTMLResponse(content=html_content, status_code=500)


@router.post("/step/3")
async def process_step_3(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    creation_service: CreationServiceDep,
    draft_service: DraftServiceDep,
) -> Response:
    """Process step 3: Review similar models and create draft for editing."""
    try:
        # Generate default attributes markdown
        if not session.attributes_markdown:
            session.attributes_markdown = creation_service.generate_default_attributes_markdown(
                session.name or "the finding"
            )

        # Create draft with current session data
        if session.name:
            inputs = FindingModelInputs(
                description=session.description or "",
                synonyms=session.synonyms,
                attributes_markdown=session.attributes_markdown,
            )
            draft = await draft_service.save_draft(
                user_id=current_user.id, name=session.name, inputs=inputs, draft_id=session.draft_id
            )

            # Clear session as we're moving to draft workflow
            session.draft_id = draft.id
            await session_manager.update_session(session)

            # Redirect to draft editor
            return RedirectResponse(url=f"/drafts/{draft.id}?mode=edit&created=true", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Missing session name")

    except Exception as e:
        logger.error(f"Error processing step 3: {str(e)}", exc_info=True)
        session.error_message = f"Error creating draft: {str(e)}"
        await session_manager.update_session(session)

        html_content = render_step_template(
            request, 3, session, similar_models=session.similar_models, error_message=session.error_message
        )
        return HTMLResponse(content=html_content, status_code=500)


@router.post("/restart")
async def restart_creation(
    request: Request,
    current_user: CurrentUserDep,
    session_manager: SessionManagerDep,
) -> HTMLResponse:
    """Restart the creation process with a new session."""
    try:
        # Create new session
        new_session_id = await session_manager.create_session()
        new_session = await session_manager.get_session(new_session_id)

        # If cache is failing, create a fallback session
        if not new_session:
            new_session = FindingModelCreationSession(session_id=new_session_id)

        # Return step 1
        html_content = render_step_template(request, 1, new_session)

        # Set new session cookie in response
        response = HTMLResponse(content=html_content)
        response.set_cookie(
            key="creation_session_id",
            value=new_session_id,
            max_age=3600 * 4,  # 4 hours
            httponly=True,
        )
        return response

    except Exception as e:
        logger.error(f"Error restarting creation: {str(e)}", exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error restarting creation: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)


@router.post("/resume")
async def resume_creation(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    creation_service: CreationServiceDep,
    draft_service: DraftServiceDep,
    draft_id: str = Form(...),
) -> Response:
    """Resume the creation process from a specific draft id.

    If the draft is in 'draft' status, redirect to unified draft edit page.
    If the draft is 'submitted', redirect to unified draft view page.
    """
    try:
        draft = await draft_service.get_draft(draft_id=draft_id, user_id=current_user.id)
        if draft is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

        # Populate session from the draft
        session.name = draft.name
        session.description = draft.inputs.description if draft.inputs else ""
        session.synonyms = draft.inputs.synonyms if draft.inputs and draft.inputs.synonyms else []
        session.attributes_markdown = (
            draft.inputs.attributes_markdown
            if draft.inputs and draft.inputs.attributes_markdown
            else creation_service.generate_default_attributes_markdown(draft.name)
        )
        session.draft_id = draft.id
        session.draft_status = draft.status

        if draft.status == "submitted":
            # Human-friendly submitted time (UTC)
            try:
                session.submitted_display_time = draft_service.format_submitted_time(draft.updated_at)
            except Exception:
                session.submitted_display_time = None
            await session_manager.update_session(session)
            return RedirectResponse(url=f"/drafts/{draft.id}?mode=view", status_code=303)
        else:
            await session_manager.update_session(session)
            return RedirectResponse(url=f"/drafts/{draft.id}?mode=edit", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming creation: {e}", exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error resuming creation: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)
