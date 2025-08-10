# ruff: noqa: B008
"""Finding Model creation and management routes."""

import json
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from findingmodel import FindingInfo
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
    FindingIndexDep,
    FindingModelCreationSession,
    SessionManagerDep,
)


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
    name: str = Form(min_length=3, max_length=200),
) -> HTMLResponse:
    """Process step 1: Check name and generate description."""
    try:
        logger.info(f"Step 1 processing started for user {current_user.login}")
        logger.info(f"Received name: '{name}' (length: {len(name)})")

        # FastAPI + Pydantic already validated the form data
        # name is already validated by Form() parameter

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

        # If no similar models found, redirect to step 4 (attributes editing)
        if not session.similar_models:
            session.current_step = 4
            await session_manager.update_session(session)
            # Redirect to step 4
            return RedirectResponse(url="/api/finding-models/create/step/4", status_code=303)
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
) -> HTMLResponse:
    """Process step 3: Review similar models and proceed to attributes editing."""
    try:
        # Update session
        session.current_step = 4
        await session_manager.update_session(session)

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
    synonyms: str = Form(default=""),
    description: str = Form(min_length=10, max_length=1000),
    attributes_markdown: str = Form(min_length=20),
) -> HTMLResponse:
    """Process step 4: Generate final model."""
    try:
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

        # Move to step 5 - pass the actual finding_model object to template
        html_content = render_step_template(request, 5, session, finding_model=finding_model)
        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(f"Error processing step 4: {str(e)}", exc_info=True)
        session.error_message = f"Error generating final model: {str(e)}"
        await session_manager.update_session(session)

        html_content = render_step_template(request, 4, session, error_message=session.error_message)
        return HTMLResponse(content=html_content, status_code=500)


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
