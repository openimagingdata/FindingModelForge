"""Finding Model creation and management routes."""

# ruff: noqa: B008, I001

import json
from typing import Any
from datetime import UTC, datetime

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from findingmodel import FindingInfo, FindingModelFull
from findingmodel.tools import (
    add_ids_to_model,
    add_standard_codes_to_model,
    create_info_from_name,
    create_model_from_markdown,
    find_similar_models,
)

from app.auth import CurrentUserDep
from app.config import logger
from app.dependencies import (
    CreationSessionDep,
    DatabaseDep,
    DraftRepoDep,
    FindingIndexDep,
    FindingModelCreationSession,
    SessionManagerDep,
)
from app.models import FindingModelInputs
import humanize


def generate_default_attributes_markdown(finding_name: str) -> str:
    """Generate default attributes markdown template for a finding."""
    return f"""### presence

Presence of {finding_name}

- absent: {finding_name.capitalize()} is not visible
- present: {finding_name.capitalize()} is clearly visible
- indeterminate: Presence of {finding_name} cannot be determined
- unknown: Presence of {finding_name} is unknown

### change from prior

How the {finding_name} has changed compared to prior imaging

- unchanged: {finding_name.capitalize()} is unchanged from prior imaging
- stable: {finding_name.capitalize()} is stable
- new: New {finding_name} not seen on prior imaging
- resolved: {finding_name.capitalize()} seen on a prior exam has resolved
- increased: {finding_name.capitalize()} has increased
- decreased: {finding_name.capitalize()} has decreased
- larger: {finding_name.capitalize()} is larger
- smaller: {finding_name.capitalize()} is smaller
"""


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
        4: "components/finding_model_creation/step_4_edit_attributes.html",
        5: "components/finding_model_creation/step_5_review_model.html",
    }

    if step_number not in step_templates:
        raise ValueError(f"Invalid step number: {step_number}")

    context = {"request": request, "current_step": step_number, "session_data": session, **extra_context}

    return templates.get_template(step_templates[step_number]).render(**context)


router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ===== HTMX ENDPOINTS FOR STEP-BY-STEP CREATION =====


@router.get("/create/step/{step_number}")
async def get_creation_step(
    step_number: int,
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
        elif step_number == 4:  # Attributes editing
            # Generate default attributes markdown if not already set
            if not session.attributes_markdown:
                session.attributes_markdown = generate_default_attributes_markdown(session.name or "the finding")
                await session_manager.update_session(session)
            # Autosave a draft on entering step 4
            try:
                if session.name:
                    inputs = FindingModelInputs(
                        description=session.description or "",
                        synonyms=session.synonyms,
                        attributes_markdown=session.attributes_markdown or "",
                    )
                    draft = await draft_repo.save_draft(
                        user_id=current_user.id, name=session.name, inputs=inputs, draft_id=session.draft_id
                    )
                    session.draft_id = draft.id
                    await session_manager.update_session(session)
            except Exception as e:
                logger.warning(f"Autosave on step 4 failed: {e}")
        elif step_number == 5 and session.final_model:  # Final display
            # Don't pass model_display_html so the template uses session_data.final_model
            pass

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
    name: str = Form(min_length=3, max_length=200),
) -> HTMLResponse:
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
                else generate_default_attributes_markdown(draft.name)
            )
            session.draft_id = draft.id
            session.current_step = 4
            await session_manager.update_session(session)
            html_content = render_step_template(request, 4, session)
            return HTMLResponse(content=html_content)

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
                else generate_default_attributes_markdown(latest.name)
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
            # Load model from generated_json when available
            finding_model: FindingModelFull | None = None
            if latest.generated_json:
                try:
                    finding_model = FindingModelFull.model_validate_json(latest.generated_json)
                    session.final_model = finding_model.model_dump(mode="json", exclude_none=True)
                except Exception as e:
                    logger.warning(f"Failed to parse generated_json for submitted draft {latest.id}: {e}")
            session.current_step = 5
            await session_manager.update_session(session)
            html_content = render_step_template(
                request,
                5,
                session,
                finding_model=finding_model if finding_model else None,
                show_ids=True,
                show_json=True,
            )
            return HTMLResponse(content=html_content)

        # Check name availability
        existing_entry = await index.get(name)
        if existing_entry:
            session.error_message = f"Name '{name}' already exists in the index"
            await session_manager.update_session(session)
            html_content = render_step_template(request, 1, session, form_data={"name": name})
            return HTMLResponse(content=html_content)

        # Generate finding info
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
    synonyms: str = Form(default=""),
    description: str = Form(min_length=10, max_length=1000),
) -> Response:
    """Process step 2: Update description and find similar models."""
    try:
        # Parse synonyms manually
        synonyms_list = parse_synonyms(synonyms)
        logger.info(f"Step 2: Parsed synonyms: {synonyms_list}")

        # Update session
        session.description = description
        session.synonyms = synonyms_list
        session.current_step = 3

        # Find similar models
        analysis = await find_similar_models(
            finding_name=session.name or "",
            description=description,
            synonyms=synonyms_list,
            index=index,
        )
        # Convert SearchResult objects to plain dictionaries for session storage
        session.similar_models = [dict(model) for model in analysis.similar_models]

        await session_manager.update_session(session)

        # If no similar models found, render step 4 directly (attributes editing)
        if not session.similar_models:
            session.current_step = 4
            # Ensure attributes have defaults when entering step 4
            if not session.attributes_markdown:
                session.attributes_markdown = generate_default_attributes_markdown(session.name or "the finding")
                await session_manager.update_session(session)
            await session_manager.update_session(session)
            # Autosave immediately when entering step 4
            try:
                if session.name:
                    inputs = FindingModelInputs(
                        description=session.description or "",
                        synonyms=session.synonyms,
                        attributes_markdown=session.attributes_markdown or "",
                    )
                    draft = await draft_repo.save_draft(
                        user_id=current_user.id, name=session.name, inputs=inputs, draft_id=session.draft_id
                    )
                    session.draft_id = draft.id
                    await session_manager.update_session(session)
            except Exception as e:
                logger.warning(f"Autosave on step 4 entry (from step 2) failed: {e}")
            html_content = render_step_template(request, 4, session)
            return HTMLResponse(content=html_content)
        else:
            # Move to step 3 to review similar models
            html_content = render_step_template(request, 3, session, similar_models=session.similar_models)

        return HTMLResponse(content=html_content)

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
) -> HTMLResponse:
    """Process step 3: Review similar models and proceed to attributes editing."""
    try:
        # Update session
        session.current_step = 4
        # Ensure attributes have defaults when entering step 4
        if not session.attributes_markdown:
            session.attributes_markdown = generate_default_attributes_markdown(session.name or "the finding")
        await session_manager.update_session(session)
        # Autosave immediately when entering step 4 from step 3
        try:
            if session.name:
                inputs = FindingModelInputs(
                    description=session.description or "",
                    synonyms=session.synonyms,
                    attributes_markdown=session.attributes_markdown or "",
                )
                draft = await draft_repo.save_draft(
                    user_id=current_user.id, name=session.name, inputs=inputs, draft_id=session.draft_id
                )
                session.draft_id = draft.id
                await session_manager.update_session(session)
        except Exception as e:
            logger.warning(f"Autosave on step 4 entry (from step 3) failed: {e}")

        # Move to step 4
        html_content = render_step_template(request, 4, session)
        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(f"Error processing step 3: {str(e)}", exc_info=True)
        session.error_message = f"Error generating attributes: {str(e)}"
        await session_manager.update_session(session)

        html_content = render_step_template(
            request, 3, session, similar_models=session.similar_models, error_message=session.error_message
        )
        return HTMLResponse(content=html_content, status_code=500)


@router.post("/create/step/4")
async def process_step_4(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    database: DatabaseDep,
    draft_repo: DraftRepoDep,
    synonyms: str = Form(default=""),
    description: str = Form(min_length=10, max_length=1000),
    attributes_markdown: str = Form(min_length=20),
) -> HTMLResponse:
    """Process step 4: Generate final model."""
    try:
        # Prevent edits if draft is submitted
        if session.draft_status == "submitted":
            raise HTTPException(status_code=403, detail="Editing is locked after submission")
        # Parse synonyms manually
        synonyms_list = parse_synonyms(synonyms)

        # Update session
        session.description = description
        session.synonyms = synonyms_list
        session.attributes_markdown = attributes_markdown

        # Generate final model
        finding_info = FindingInfo(name=session.name or "", description=description, synonyms=synonyms_list)

        complete_markdown = f"""# {session.name}

## Description
{description}

{attributes_markdown}
"""

        finding_model_generated = await create_model_from_markdown(finding_info, markdown_text=complete_markdown)

        # Add IDs and contributors
        assert database.finding_index, "FindingIndex must be initialized in the database"
        author = database.people.get(current_user.login)
        source = (
            author.organization_code
            if author
            else (current_user.organizations[0] if current_user.organizations else "OIDM")
        )

        finding_model = add_ids_to_model(finding_model_generated, source=source)
        add_standard_codes_to_model(finding_model)

        if author:
            finding_model.contributors = [author]
        if source and (organization := database.organizations.get(source)):
            if finding_model.contributors:
                finding_model.contributors.append(organization)
            else:
                finding_model.contributors = [organization]

        # Store in session for template rendering - serialize to dict but handle HttpUrl types
        session.final_model = finding_model.model_dump(mode="json", exclude_none=True)
        session.current_step = 5
        await session_manager.update_session(session)

        # Save draft including generated model JSON (best-effort)
        try:
            # Build inputs from session
            inputs = FindingModelInputs(
                description=session.description or "",
                synonyms=session.synonyms,
                attributes_markdown=session.attributes_markdown or "",
            )
            generated_json = finding_model.model_dump_json()
            if session.name:
                draft = await draft_repo.save_draft(
                    user_id=current_user.id,
                    name=session.name,
                    inputs=inputs,
                    draft_id=session.draft_id,
                    generated_json=generated_json,
                )
                session.draft_id = draft.id
                session.draft_status = draft.status
                await session_manager.update_session(session)
        except Exception as e:
            logger.warning(f"Autosave with generated model failed: {e}")

        # Move to step 5 - pass the actual finding_model object to template
        # In review step, hide IDs and JSON until submitted
        html_content = render_step_template(
            request, 5, session, finding_model=finding_model, show_ids=False, show_json=False
        )
        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(f"Error processing step 4: {str(e)}", exc_info=True)
        session.error_message = f"Error generating final model: {str(e)}"
        await session_manager.update_session(session)

        html_content = render_step_template(request, 4, session, error_message=session.error_message)
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

        # Re-render full step 5 with IDs/JSON and no back button
        html_content = render_step_template(
            request,
            5,
            session,
            finding_model=finding_model if finding_model else None,
            show_ids=True,
            show_json=True,
        )
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
        ok = await draft_repo.delete_draft(draft_id=draft_id, user_id=current_user.id)
        if ok and session.draft_id == draft_id:
            session.draft_id = None
            await session_manager.update_session(session)
        html = templates.get_template("components/drafts/delete_result.html").render(
            request=request,
            deleted=ok,
        )
        return HTMLResponse(content=html)
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
