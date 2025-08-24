"""Finding Model creation and management routes."""

# ruff: noqa: B008, I001

import asyncio
import json
from typing import Annotated, Any
from datetime import UTC, datetime

from fastapi import APIRouter, Form, HTTPException, Path, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from findingmodel import FindingInfo, FindingModelBase, FindingModelFull
from findingmodel.tools import (
    add_ids_to_model,
    add_standard_codes_to_model,
    create_info_from_name,
    create_model_from_markdown,
    find_similar_models,
)
from findingmodel.tools.similar_finding_models import SimilarModelAnalysis  # noqa: F401

from app.auth import CurrentUserDep
from app.config import logger
from app.vite_manifest import get_vite_asset_path
from app.dependencies import (
    CreationServiceDep,
    CreationSessionDep,
    DatabaseDep,
    DraftRepoDep,
    FindingIndexDep,
    FindingModelCreationSession,
    SessionManagerDep,
)
from app.models import FindingModelInputs
import humanize

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
templates = Jinja2Templates(directory="templates")
# Ensure shared template globals are set (e.g., vite asset helper used by base.html)
templates.env.globals["vite_asset"] = get_vite_asset_path


# ===== HTMX ENDPOINTS FOR STEP-BY-STEP CREATION =====


@router.get("/create/step/{step_number}")
async def get_creation_step(
    step_number: StepNumber,
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    draft_repo: DraftRepoDep,
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


@router.post("/create/step/1")
async def process_step_1(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    index: FindingIndexDep,
    draft_repo: DraftRepoDep,
    creation_service: CreationServiceDep,
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
            draft = await draft_repo.find_editable_by_name(user_id=current_user.id, name=name)
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
            return RedirectResponse(url=f"/api/finding-models/drafts/{draft.id}?mode=edit", status_code=303)

        # If there's a submitted draft with this name, jump to step 5 with read-only view
        try:
            latest = None
            # Guard for environments where the method may not be available at type-check time
            if hasattr(draft_repo, "find_latest_by_name"):
                latest = await draft_repo.find_latest_by_name(user_id=current_user.id, name=name)
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
                submitted_time = latest.updated_at
                # Ensure timezone-aware
                if submitted_time.tzinfo is None:
                    submitted_time = submitted_time.replace(tzinfo=UTC)
                session.submitted_display_time = humanize.naturaltime(datetime.now(UTC) - submitted_time)
            except Exception:
                session.submitted_display_time = None
            await session_manager.update_session(session)
            return RedirectResponse(url=f"/api/finding-models/drafts/{latest.id}?mode=view", status_code=303)

        # Check name availability
        existing_entry = await index.get(name)
        if existing_entry:
            session.error_message = f"Name '{name}' already exists in the index"
            await session_manager.update_session(session)
            html_content = render_step_template(request, 1, session, form_data={"name": name})
            return HTMLResponse(content=html_content)

        # Generate finding info (skip AI for test user)
        if current_user.id == TEST_USER_ID:
            # Mock AI response for test user (999999)
            logger.info(f"Step 1: Using MOCK AI response for create_info_from_name (test user {current_user.id})")
            await asyncio.sleep(2.0)  # Simulate AI processing time
            finding_info = FindingInfo(
                name=name,
                description=f"Test description for {name}. This is a mock response for UI testing.",
                synonyms=[f"{name}_synonym1", f"{name}_synonym2"],
            )
        else:
            logger.info("Step 1: Using REAL AI response for create_info_from_name")
            finding_info = await create_info_from_name(name)

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


@router.post("/create/step/2")
async def process_step_2(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    index: FindingIndexDep,
    draft_repo: DraftRepoDep,
    creation_service: CreationServiceDep,
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

        # Find similar models (skip AI for test user)
        if current_user.id == TEST_USER_ID:
            # Mock AI response for test user (999999)
            logger.info(f"Step 2: Using MOCK AI response for find_similar_models (test user {current_user.id})")
            await asyncio.sleep(2.0)  # Simulate AI processing time
            # Use the already imported SimilarModelAnalysis
            analysis = SimilarModelAnalysis(
                similar_models=[],
                recommendation="create_new",
                confidence=1.0,
            )
        else:
            logger.info("Step 2: Using REAL AI response for find_similar_models")
            analysis = await find_similar_models(
                finding_name=session.name or "",
                description=description,
                synonyms=synonyms_list,
                index=index,
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
        draft = await draft_repo.save_draft(
            user_id=current_user.id, name=session.name, inputs=inputs, draft_id=session.draft_id
        )

        # Update session and redirect to draft editor
        session.draft_id = draft.id
        await session_manager.update_session(session)

        return RedirectResponse(url=f"/api/finding-models/drafts/{draft.id}?mode=edit&created=true", status_code=303)

    except Exception as e:
        logger.error(f"Error processing step 2: {str(e)}", exc_info=True)
        session.error_message = f"Error finding similar models: {str(e)}"
        await session_manager.update_session(session)

        html_content = render_step_template(request, 2, session, error_message=session.error_message)
        return HTMLResponse(content=html_content, status_code=500)


@router.post("/create/step/3")
async def process_step_3(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    draft_repo: DraftRepoDep,
    creation_service: CreationServiceDep,
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
            draft = await draft_repo.save_draft(
                user_id=current_user.id, name=session.name, inputs=inputs, draft_id=session.draft_id
            )

            # Clear session as we're moving to draft workflow
            session.draft_id = draft.id
            await session_manager.update_session(session)

            # Redirect to draft editor
            return RedirectResponse(
                url=f"/api/finding-models/drafts/{draft.id}?mode=edit&created=true", status_code=303
            )
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


# ===== DRAFT MANAGEMENT (HTMX) =====


@router.post("/drafts/save")
async def save_draft(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    draft_repo: DraftRepoDep,
    draft_id: str | None = Form(default=None),
    description: str | None = Form(default=None),
    attributes_markdown: str | None = Form(default=None),
    synonyms: str = Form(default=""),
) -> HTMLResponse:
    """Save current inputs as a draft owned by the user. Returns a small fragment."""
    try:
        # Prevent saving if already submitted
        if session.draft_status == "submitted":
            html = templates.get_template("components/drafts/locked_result.html").render(
                request=request,
                reason="This draft has been submitted and is now read-only.",
            )
            return HTMLResponse(content=html, status_code=409)
        # Use provided values or fall back to session to support Step 5 quick save
        new_description = description if description is not None else (session.description or "")
        new_attributes = attributes_markdown if attributes_markdown is not None else (session.attributes_markdown or "")
        new_synonyms = parse_synonyms(synonyms) if isinstance(synonyms, str) else (session.synonyms or [])

        # Minimal validation to maintain previous constraints
        if len(new_description.strip()) < 10 or len(new_attributes.strip()) < 20:
            raise HTTPException(status_code=422, detail="Description or attributes are too short")

        # Update session with latest form values
        session.description = new_description
        session.attributes_markdown = new_attributes
        session.synonyms = new_synonyms
        await session_manager.update_session(session)

        # Normalize draft_id: treat empty string as None; validate if provided
        if draft_id is not None:
            draft_id = draft_id.strip()
            if draft_id == "":
                draft_id = None
            elif not ObjectId.is_valid(draft_id):
                raise HTTPException(status_code=400, detail="Invalid draft id")

        inputs = FindingModelInputs(
            description=session.description or "",
            synonyms=session.synonyms,
            attributes_markdown=session.attributes_markdown,
        )
        draft = await draft_repo.save_draft(
            user_id=current_user.id,
            name=session.name or "",
            inputs=inputs,
            draft_id=draft_id,
        )

        # Track draft in session
        session.draft_id = draft.id
        session.draft_status = draft.status
        await session_manager.update_session(session)

        # Render a tiny success badge/button group fragment for the UI
        html = templates.get_template("components/drafts/save_result.html").render(
            request=request,
            draft=draft,
        )
        return HTMLResponse(content=html)
    except HTTPException:
        # Let FastAPI handle HTTP errors with proper status codes
        raise
    except Exception as e:
        # If error indicates not editable, show locked fragment
        msg = str(e)
        if "not editable" in msg or "not in draft status" in msg:
            html = templates.get_template("components/drafts/locked_result.html").render(
                request=request,
                reason="This draft has been submitted and is now read-only.",
            )
            return HTMLResponse(content=html, status_code=409)
        logger.error("Error saving draft: {}", e, exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error saving draft: {msg}"
        )
        return HTMLResponse(content=error_html, status_code=500)


@router.post("/drafts/{draft_id}/submit")
async def submit_draft(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    draft_repo: DraftRepoDep,
    draft_id: str,
) -> HTMLResponse:
    """Submit a draft (freeze edits)."""
    try:
        draft = await draft_repo.submit(draft_id=draft_id, user_id=current_user.id)
        session.draft_id = draft.id
        session.draft_status = draft.status
        # Human-friendly submitted time (UTC)
        try:
            submitted_time = draft.updated_at
            if submitted_time.tzinfo is None:
                submitted_time = submitted_time.replace(tzinfo=UTC)
            session.submitted_display_time = humanize.naturaltime(datetime.now(UTC) - submitted_time)
        except Exception:
            session.submitted_display_time = None
        await session_manager.update_session(session)

        # Build finding model object for display
        finding_model: FindingModelFull | None = None
        if session.final_model:
            try:
                finding_model = FindingModelFull.model_validate(session.final_model)
            except Exception:
                finding_model = None
        if finding_model is None and getattr(draft, "generated_json", None):
            try:
                finding_model = FindingModelFull.model_validate_json(draft.generated_json)  # type: ignore[arg-type]
            except Exception:
                finding_model = None

        # Render submitted draft content for HTMX swap into #step-container
        # Note: Use a custom template context since we need #step-container target, not #draft-content
        template_content = templates.get_template("components/draft_preview_containerless.html").render(
            request=request,
            user=current_user,
            draft=draft,
            finding_model=finding_model,
            show_ids=True,
            show_json=True,
        )

        # Replace the HTMX target to work with creation workflow
        html_content = template_content.replace('hx-target="#draft-content"', 'hx-target="#step-container"')
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error("Error submitting draft: {}", e, exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error submitting draft: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)


@router.post("/drafts/{draft_id}/delete")
async def delete_draft(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    draft_repo: DraftRepoDep,
    draft_id: str,
) -> HTMLResponse:
    """Delete a draft if it's still in draft status."""
    try:
        # First check if the draft exists and its status
        draft = await draft_repo.get_draft(draft_id=draft_id, user_id=current_user.id)
        if not draft:
            error_html = templates.get_template("components/error_display.html").render(
                request=request, error_message="Draft not found or access denied"
            )
            return HTMLResponse(content=error_html, status_code=404)

        if draft.status != "draft":
            error_html = templates.get_template("components/error_display.html").render(
                request=request, error_message="Cannot delete submitted drafts"
            )
            return HTMLResponse(content=error_html, status_code=400)

        # Proceed with deletion
        ok = await draft_repo.delete_draft(draft_id=draft_id, user_id=current_user.id)
        if ok and session.draft_id == draft_id:
            session.draft_id = None
            await session_manager.update_session(session)

        # Redirect to profile page after successful deletion
        if ok:
            return HTMLResponse(content="", headers={"HX-Redirect": "/profile"})
        else:
            # This shouldn't happen if the checks above passed
            error_html = templates.get_template("components/error_display.html").render(
                request=request, error_message="Failed to delete draft"
            )
            return HTMLResponse(content=error_html, status_code=500)
    except Exception as e:
        logger.error(f"Error deleting draft: {e}", exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error deleting draft: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)


@router.post("/create/restart")
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


@router.post("/create/resume")
async def resume_creation(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    draft_repo: DraftRepoDep,
    creation_service: CreationServiceDep,
    draft_id: str = Form(...),
) -> Response:
    """Resume the creation process from a specific draft id.

    If the draft is in 'draft' status, redirect to unified draft edit page.
    If the draft is 'submitted', redirect to unified draft view page.
    """
    try:
        draft = await draft_repo.get_draft(draft_id=draft_id, user_id=current_user.id)
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
                submitted_time = draft.updated_at
                if submitted_time.tzinfo is None:
                    submitted_time = submitted_time.replace(tzinfo=UTC)
                session.submitted_display_time = humanize.naturaltime(datetime.now(UTC) - submitted_time)
            except Exception:
                session.submitted_display_time = None
            await session_manager.update_session(session)
            return RedirectResponse(url=f"/api/finding-models/drafts/{draft.id}?mode=view", status_code=303)
        else:
            await session_manager.update_session(session)
            return RedirectResponse(url=f"/api/finding-models/drafts/{draft.id}?mode=edit", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming creation: {e}", exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error resuming creation: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)


# ===== DRAFT EDITING WORKFLOW =====


@router.get("/drafts/{draft_id}/edit", response_class=HTMLResponse)
async def edit_draft(
    request: Request,
    current_user: CurrentUserDep,
    draft_repo: DraftRepoDep,
    draft_id: str,
) -> HTMLResponse:
    """Edit a draft - main editing interface with form."""
    try:
        draft = await draft_repo.get_draft(draft_id=draft_id, user_id=current_user.id)
        if draft is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

        # Only allow editing of drafts in 'draft' status
        if draft.status != "draft":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Draft is not editable")

        # Check if this is an HTMX request (for mode switching)
        hx_request = request.headers.get("HX-Request")
        if hx_request:
            # Return just the edit form partial for HTMX swaps
            return templates.TemplateResponse(
                request=request,
                name="components/draft_edit_form.html",
                context={
                    "user": current_user,
                    "draft": draft,
                },
            )
        else:
            # Return full page for direct navigation
            return templates.TemplateResponse(
                request=request,
                name="draft_editor.html",
                context={
                    "user": current_user,
                    "title": f"Edit Draft: {draft.name}",
                    "draft": draft,
                    "mode": "edit",
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading draft editor: {e}", exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error loading draft: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)


@router.get("/drafts/{draft_id}", response_model=None)
async def unified_draft_page(
    request: Request,
    current_user: CurrentUserDep,
    draft_repo: DraftRepoDep,
    draft_id: str,
    mode: str = "view",  # Default to view mode
) -> Response:
    """Unified draft page that handles both view and edit modes."""
    try:
        draft = await draft_repo.get_draft(draft_id=draft_id, user_id=current_user.id)
        if draft is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

        # Validate mode parameter
        if mode not in ["view", "edit"]:
            mode = "view"

        # For edit mode, only allow if draft is editable
        if mode == "edit" and draft.status != "draft":
            # Redirect to view mode for submitted drafts
            mode = "view"

        # Parse finding model if available
        finding_model: FindingModelFull | None = None
        if draft.generated_json:
            try:
                finding_model = FindingModelFull.model_validate_json(draft.generated_json)
            except Exception:
                finding_model = None

        # If trying to view a draft without generated JSON, redirect to edit mode
        if mode == "view" and not finding_model and draft.status == "draft":
            # Use HTMX redirect or browser redirect depending on request type
            hx_request = request.headers.get("HX-Request")
            if hx_request:
                # HTMX request - swap to edit form and update URL (use containerless version)
                return templates.TemplateResponse(
                    request=request,
                    name="components/draft_edit_form_content.html",
                    context={
                        "user": current_user,
                        "draft": draft,
                    },
                    headers={"HX-Push-Url": f"/api/finding-models/drafts/{draft_id}?mode=edit"},
                )
            else:
                # Browser request - redirect to edit mode, preserving query parameters
                query_params = dict(request.query_params)
                query_params["mode"] = "edit"
                query_string = "&".join(f"{k}={v}" for k, v in query_params.items())
                return RedirectResponse(url=f"/api/finding-models/drafts/{draft_id}?{query_string}", status_code=303)

        # Check if this is an HTMX request (for mode switching)
        hx_request = request.headers.get("HX-Request")
        if hx_request:
            # Return containerless content for HTMX swaps (prevents nested boxes)
            if mode == "edit":
                main_content = templates.get_template("components/draft_edit_form_content.html").render(
                    request=request,
                    user=current_user,
                    draft=draft,
                )
            else:  # view mode
                main_content = templates.get_template("components/draft_preview_containerless.html").render(
                    request=request,
                    user=current_user,
                    draft=draft,
                    finding_model=finding_model,
                    show_ids=bool(draft.status == "submitted"),
                    show_json=bool(draft.status == "submitted"),
                )

            # Only include mode toggle header OOB swap if the draft has generated JSON
            # (means there's something to preview - buttons are useful)
            if draft.generated_json:
                # Use unified container across all workflows
                target_container = "#main-content"

                # Include mode toggle header OOB swap
                mode_toggle_header = templates.get_template("components/draft_mode_toggle_header.html").render(
                    request=request,
                    user=current_user,
                    draft=draft,
                    mode=mode,  # Pass the current mode
                    can_edit=draft.status == "draft",
                    target_container=target_container,
                )

                # Combine main content with OOB swap for mode toggle header
                combined_content = f"""{main_content}
<div id="draft-mode-toggle-header" hx-swap-oob="true">
{mode_toggle_header}
</div>"""

                return HTMLResponse(content=combined_content)
            else:
                # Regular unified draft page - no mode toggle buttons needed
                return HTMLResponse(content=main_content)
        else:
            # Return full page for direct navigation
            page_title = f"{'Edit' if mode == 'edit' else 'Preview'} Finding Model Draft"

            return templates.TemplateResponse(
                request=request,
                name="draft_unified.html",
                context={
                    "user": current_user,
                    "title": page_title,
                    "draft": draft,
                    "finding_model": finding_model,
                    "mode": mode,
                    "can_edit": draft.status == "draft",
                    "show_ids": draft.status == "submitted",
                    "show_json": draft.status == "submitted",
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading unified draft page: {e}", exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error loading draft: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)


@router.post("/drafts/{draft_id}/update-and-redirect")
async def update_draft_and_redirect(
    request: Request,
    current_user: CurrentUserDep,
    draft_repo: DraftRepoDep,
    database: DatabaseDep,
    draft_id: str,
    description: str = Form(min_length=10, max_length=1000),
    attributes_markdown: str = Form(min_length=20),
    synonyms: str = Form(default=""),
) -> Response:
    """Update draft and redirect to unified draft page - used when coming from creation workflow."""
    try:
        # Call the same update logic as the regular update endpoint
        draft = await draft_repo.get_draft(draft_id=draft_id, user_id=current_user.id)
        if draft is None:
            logger.error(f"Draft not found: draft_id={draft_id}, user_id={current_user.id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

        if draft.status != "draft":
            logger.error(f"Draft not editable: draft_id={draft_id}, status={draft.status}, user_id={current_user.id}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Draft is not editable")

        # Parse synonyms
        synonyms_list = parse_synonyms(synonyms)

        # Update draft with new inputs
        new_inputs = FindingModelInputs(
            description=description,
            synonyms=synonyms_list,
            attributes_markdown=attributes_markdown,
        )

        # Check if inputs have actually changed
        inputs_changed = (
            draft.inputs.description != new_inputs.description
            or draft.inputs.synonyms != new_inputs.synonyms
            or draft.inputs.attributes_markdown != new_inputs.attributes_markdown
        )

        # Initialize generated_json variable
        generated_json: str | None

        # Generate the model if inputs changed OR if no generated JSON exists (fresh draft)
        has_no_generated_json = not draft.generated_json
        should_generate = inputs_changed or has_no_generated_json

        if should_generate:
            # Generate the model from the updated inputs
            finding_info = FindingInfo(name=draft.name, description=description, synonyms=synonyms_list)
            complete_markdown = f"""# {draft.name}
## Description
{description}
{attributes_markdown}
"""
            if current_user.id == TEST_USER_ID:
                # Mock AI response for test user (999999)
                logger.info(
                    f"Update draft: Using MOCK AI response for create_model_from_markdown (test user {current_user.id})"
                )
                await asyncio.sleep(2.0)  # Simulate AI processing time
                # Create mock FindingModel directly without AI call
                mock_model_dict = {
                    "name": draft.name if len(draft.name) >= 5 else f"{draft.name} Test",
                    "description": description,
                    "synonyms": synonyms_list,
                    "tags": None,
                    "contributors": None,
                    "attributes": [
                        {
                            "name": "presence",
                            "description": f"Presence of {draft.name}",
                            "type": "choice",
                            "values": [
                                {"name": "absent", "description": f"{draft.name} is not visible"},
                                {"name": "present", "description": f"{draft.name} is clearly visible"},
                            ],
                            "required": False,
                            "max_selected": 1,
                        }
                    ],
                }
                finding_model_generated = FindingModelBase.model_validate(mock_model_dict)
            else:
                logger.info("Update draft: Using REAL AI response for create_model_from_markdown")
                finding_model_generated = await create_model_from_markdown(
                    finding_info, markdown_text=complete_markdown
                )

            # Add IDs and contributors
            assert database.finding_index, "FindingIndex must be initialized in the database"
            author = database.people.get(current_user.login)
            source = (
                author.organization_code
                if author
                else (current_user.organizations[0] if current_user.organizations else "OIDM")
            )
            fm = add_ids_to_model(finding_model_generated, source=source)
            add_standard_codes_to_model(fm)

            # Convert to JSON
            generated_json = fm.model_dump_json(indent=2)
        else:
            generated_json = draft.generated_json

        # Update the draft
        updated_draft = await draft_repo.save_draft(
            user_id=current_user.id,
            name=draft.name,
            inputs=new_inputs,
            draft_id=draft_id,
            generated_json=generated_json,
        )

        # Check if this is an HTMX request
        hx_request = request.headers.get("HX-Request")
        if hx_request:
            # For HTMX requests, return the draft preview content AND update the mode toggle header
            # Parse the generated finding model
            finding_model: FindingModelFull | None = None
            if generated_json:
                try:
                    finding_model = FindingModelFull.model_validate_json(generated_json)
                except Exception:
                    finding_model = None

            # Set headers including reuse indicator and URL push
            response_headers = {
                "HX-Push-Url": f"/api/finding-models/drafts/{draft_id}?mode=view&created=true",
                "x-model-reused": "0" if should_generate else "1",
            }

            # Render the main draft preview content
            draft_content = templates.get_template("components/draft_preview_containerless.html").render(
                request=request,
                user=current_user,
                draft=updated_draft,
                finding_model=finding_model,
                show_ids=False,  # Always False for drafts in this endpoint
                show_json=False,  # Always False for drafts in this endpoint
                show_success_message=True,  # Show success message for HTMX transitions
            )

            # Include mode toggle header OOB swap if the draft now has generated JSON
            if updated_draft.generated_json:
                # Use unified container across all workflows
                target_container = "#main-content"

                # Include mode toggle header OOB swap
                mode_toggle_header = templates.get_template("components/draft_mode_toggle_header.html").render(
                    request=request,
                    user=current_user,
                    draft=updated_draft,
                    mode="view",  # We're transitioning to view mode
                    can_edit=updated_draft.status == "draft",
                    target_container=target_container,
                )

                # Combine main content with OOB swap for mode toggle header
                combined_content = f"""{draft_content}
<div id="draft-mode-toggle-header" hx-swap-oob="true">
{mode_toggle_header}
</div>"""

                return HTMLResponse(
                    content=combined_content,
                    headers=response_headers,
                )
            else:
                return HTMLResponse(
                    content=draft_content,
                    headers=response_headers,
                )
        else:
            # Redirect to unified draft page in view mode
            return RedirectResponse(
                url=f"/api/finding-models/drafts/{draft_id}?mode=view&created=true", status_code=303
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating draft: {e}", exc_info=True)
        error_html = templates.get_template("components/error_display.html").render(
            request=request, error_message=f"Error updating draft: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)
