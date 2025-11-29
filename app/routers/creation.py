"""Finding Model creation workflow routes."""

# ruff: noqa: B008, I001

from typing import Annotated, Any

from fastapi import APIRouter, Form, HTTPException, Path, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from findingmodel.tools.similar_finding_models import SimilarModelAnalysis  # noqa: F401

from app.auth import CurrentUserDep
from app.config import logger
from app.services.creation_service import SessionData, WorkflowAction
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
from app.utils.forms import parse_synonyms

TEST_USER_ID = 999999

# Type definition for step numbers in the creation workflow
StepNumber = Annotated[int, Path(ge=1, le=3, description="Step number (1-3) in the creation workflow")]


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


def _apply_session_data(session: FindingModelCreationSession, data: SessionData) -> None:
    """Apply extracted session data to a session object."""
    session.name = data.name
    session.description = data.description
    session.synonyms = data.synonyms
    session.attributes_markdown = data.attributes_markdown
    session.draft_id = data.draft_id
    session.draft_status = data.draft_status
    session.submitted_display_time = data.submitted_display_time


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
    name: str = Form(min_length=3, max_length=200),
) -> Response:
    """Process step 1: Check name and generate description."""
    try:
        logger.info(f"Step 1 processing started for user {current_user.login}")
        logger.info(f"Received name: '{name}' (length: {len(name)})")

        # Resolve what to do with this name
        resolution = await creation_service.resolve_name_input(current_user.id, name)

        if resolution.action == WorkflowAction.RESUME_EDITABLE:
            assert resolution.draft is not None
            assert resolution.redirect_url is not None
            session_data = creation_service.extract_session_data(resolution.draft)
            _apply_session_data(session, session_data)
            await session_manager.update_session(session)
            return RedirectResponse(url=resolution.redirect_url, status_code=303)

        if resolution.action == WorkflowAction.VIEW_SUBMITTED:
            assert resolution.draft is not None
            assert resolution.redirect_url is not None
            session_data = creation_service.extract_session_data(resolution.draft)
            _apply_session_data(session, session_data)
            await session_manager.update_session(session)
            return RedirectResponse(url=resolution.redirect_url, status_code=303)

        # CREATE_NEW path
        is_available = await creation_service.check_name_availability(name, current_user.id)
        if not is_available:
            session.error_message = f"Name '{name}' already exists in the index"
            await session_manager.update_session(session)
            html_content = render_step_template(request, 1, session, form_data={"name": name})
            return HTMLResponse(content=html_content)

        # Generate finding info
        test_mode = creation_service.is_test_user(current_user.id)
        finding_info = await creation_service.generate_finding_info(name, test_mode=test_mode)

        # Update session for step 2
        session.name = name
        session.draft_id = None
        session.description = finding_info.description
        session.synonyms = finding_info.synonyms or []
        session.current_step = 2
        await session_manager.update_session(session)

        return HTMLResponse(content=render_step_template(request, 2, session))

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
            user_id=current_user.id, name=session.name, inputs=inputs, draft_id=session.draft_id, user=current_user
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
                user_id=current_user.id, name=session.name, inputs=inputs, draft_id=session.draft_id, user=current_user
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

        # Extract session data from draft
        session_data = creation_service.extract_session_data(draft)
        _apply_session_data(session, session_data)
        await session_manager.update_session(session)

        # Redirect based on draft status
        if draft.status == "submitted":
            return RedirectResponse(url=f"/drafts/{draft.id}?mode=view", status_code=303)
        else:
            return RedirectResponse(url=f"/drafts/{draft.id}?mode=edit", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming creation: {e}", exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error resuming creation: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)
