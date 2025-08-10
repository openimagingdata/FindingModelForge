# ruff: noqa: B008
"""Finding Model creation and management routes."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
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
from app.models import (
    FindingInfoEditRequest,
    FindingInfoRequest,
    FindingInfoResponse,
    FindingNameCheck,
    GenerateModelRequest,
    NameAvailabilityResponse,
    SimilarModelsAnalysis,
    SimilarModelsRequest,
    StepNameForm,
    StepDescriptionForm,
    StepAttributesForm,
)

def render_step_template(
    request: Request,
    step_number: int,
    session: FindingModelCreationSession,
    **extra_context
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
    
    context = {
        "request": request,
        "current_step": step_number,
        "session_data": session,
        **extra_context
    }
    
    return templates.get_template(step_templates[step_number]).render(**context)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/check-name", response_model=NameAvailabilityResponse)
async def check_finding_name(
    request: FindingNameCheck,
    current_user: CurrentUserDep,
    index: FindingIndexDep,
) -> NameAvailabilityResponse:
    """Check if a finding name already exists in the index."""
    try:
        # Use Index.get() to look for exact match on name/synonym
        existing_entry = await index.get(request.name)

        if existing_entry:
            return NameAvailabilityResponse(
                available=False, message=f"Name '{request.name}' already exists in the index"
            )

        return NameAvailabilityResponse(available=True, message="Name is available")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check name availability",
        ) from e


@router.post("/create-info", response_model=FindingInfoResponse)
async def create_finding_info(
    request: FindingInfoRequest,
    current_user: CurrentUserDep,
) -> FindingInfoResponse:
    """Create finding information from just a name using AI generation."""
    try:
        logger.debug(f"Creating finding info for name: {request.name}")

        # Use create_info_from_name to generate FindingInfo from the name
        finding_info = await create_info_from_name(request.name)

        logger.debug(f"Generated finding info: {finding_info}")

        return FindingInfoResponse(
            name=request.name,  # Use the user-provided name
            description=finding_info.description,  # Use AI-generated description
            synonyms=finding_info.synonyms,  # Use AI-generated synonyms
        )

    except Exception as e:
        logger.error(f"Error in create_finding_info: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error creating finding info: {str(e)}"
        ) from e


@router.post("/find-similar", response_model=SimilarModelsAnalysis)
async def find_similar(
    request: SimilarModelsRequest,
    current_user: CurrentUserDep,
    index: FindingIndexDep,
) -> SimilarModelsAnalysis:
    """Find similar models to avoid duplicates."""
    try:
        logger.debug(f"Finding similar models for name: {request.name[:100]}...")
        logger.debug(f"Description: {request.description[:100]}")
        logger.debug(f"Synonyms: {request.synonyms}")

        # Use find_similar_models to look for overlaps
        analysis = await find_similar_models(
            finding_name=request.name,
            description=request.description,
            synonyms=request.synonyms or [],
            index=index,
        )

        logger.debug(f"Analysis result: {analysis}")

        from app.models import SimilarModelResponse

        similar_models = [
            SimilarModelResponse(
                oifm_id=model["oifm_id"],
                name=model["name"],
                description=model.get("description"),
                synonyms=model.get("synonyms"),
            )
            for model in analysis.similar_models
        ]

        logger.debug(f"Found {len(similar_models)} similar models")

        return SimilarModelsAnalysis(
            similar_models=similar_models,
            recommendation=analysis.recommendation,
            confidence=analysis.confidence,
        )

    except Exception as e:
        logger.error(f"Error in find_similar: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error finding similar models: {str(e)}"
        ) from e


@router.post("/generate-stub")
async def generate_stub_markdown(
    request: FindingInfoEditRequest,
    current_user: CurrentUserDep,
) -> JSONResponse:
    """Generate basic attributes markdown stub for editing."""
    try:
        # Generate a basic attributes markdown template for the user to edit
        stub_markdown = f"""## Attributes

### presence

Whether {request.name} is visible on the imaging study

- absent: {request.name.capitalize()} is not visible
- present: {request.name.capitalize()} is clearly visible
- indeterminate: Presence of {request.name} cannot be determined
- unknown: Presence of {request.name} is unknown

### change from prior

How the {request.name} has changed compared to prior imaging

- unchanged: {request.name.capitalize()} is unchanged from prior imaging
- stable: {request.name.capitalize()} is stable
- new: New {request.name.capitalize()} not seen on prior imaging
- resolved: {request.name.capitalize()} seen on a prior exam has resolved
- increased: {request.name.capitalize()} has increased
- decreased: {request.name.capitalize()} has decreased
- larger: {request.name.capitalize()} is larger
- smaller: {request.name.capitalize()} is smaller
"""
        return JSONResponse(content={"markdown": stub_markdown})

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error generating stub markdown: {str(e)}"
        ) from e


@router.post("/generate-model")
async def generate_model(
    request: Request,
    model_request: GenerateModelRequest,
    current_user: CurrentUserDep,
    database: DatabaseDep,
) -> JSONResponse:
    """Generate the final finding model from FindingInfo and attributes markdown."""
    try:
        # Create a FindingInfo object from the request
        finding_info = FindingInfo(
            name=model_request.name,
            description=model_request.description,
            synonyms=model_request.synonyms or [],
        )

        # Combine the FindingInfo with the attributes markdown to create complete markdown
        complete_markdown = f"""# {model_request.name}

## Description
{model_request.description}

{model_request.attributes_markdown}
"""

        # Generate the final FindingModel using findingmodel tools
        finding_model_generated = await create_model_from_markdown(finding_info, markdown_text=complete_markdown)

        assert database.finding_index, "FindingIndex must be initialized in the database"
        author = database.people.get(current_user.login)
        logger.info(f"Generating finding model for user: {current_user.login}, author: {author}")
        # Add IDs and standard codes to the model
        if author:
            source = author.organization_code
        elif current_user.organizations:
            source = current_user.organizations[0]
        else:
            source = "OIDM"
        finding_model = add_ids_to_model(finding_model_generated, source=source)
        add_standard_codes_to_model(finding_model)
        if author:
            finding_model.contributors = [author]
        if source and (organization := database.organizations.get(source)):
            if finding_model.contributors:
                finding_model.contributors.append(organization)
            else:
                finding_model.contributors = [organization]

        # Generate JSON for the model
        finding_model_json = finding_model.model_dump_json(indent=2, exclude_none=True)

        # Generate filename for downloads
        filename = f"{model_request.name.replace(' ', '_').lower()}.fm.json"

        # Render the HTML component
        display_html = templates.get_template("components/finding_model_full_display.html").render(
            finding_model=finding_model,
            finding_model_json=finding_model_json,
            finding_model_filename=filename,
        )

        return JSONResponse(
            content={
                "model": finding_model.model_dump(mode="json", exclude_none=True),
                "display_html": display_html,
                "filename": filename,
                "success": True,
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error generating finding model: {str(e)}"
        ) from e


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
    form_data: StepNameForm = Depends(),
) -> HTMLResponse:
    """Process step 1: Check name and generate description."""
    try:
        # FastAPI + Pydantic already validated the form data
        name = form_data.name





        # Check name availability
        existing_entry = await index.get(name)
        if existing_entry:
            session.error_message = f"Name '{name}' already exists in the index"
            await session_manager.update_session(session)
            html_content = render_step_template(request, 1, session, form_data={"name": form_data.name})
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

        html_content = render_step_template(request, 1, session, form_data={"name": form_data.name}, error_message=session.error_message)
        return HTMLResponse(content=html_content, status_code=500)


@router.post("/create/step/2")
async def process_step_2(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    index: FindingIndexDep,
    form_data: StepDescriptionForm = Depends(),
) -> HTMLResponse:
    """Process step 2: Update description and find similar models."""
    try:
        # FastAPI + Pydantic already validated the form data
        description = form_data.description
        synonyms_list = form_data.synonyms  # Already parsed and validated by Pydantic

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

        # If no similar models found, skip to step 4 (attributes editing)
        if not session.similar_models:
            # Generate stub markdown for attributes
            stub_markdown = f"""### presence

Presence of {session.name or "the finding"}

- absent: {(session.name or "Finding").capitalize()} is not visible
- present: {(session.name or "Finding").capitalize()} is clearly visible
- indeterminate: Presence of {session.name or "finding"} cannot be determined
- unknown: Presence of {session.name or "finding"} is unknown

### change from prior

How the {session.name or "finding"} has changed compared to prior imaging

- unchanged: {(session.name or "Finding").capitalize()} is unchanged from prior imaging
- stable: {(session.name or "Finding").capitalize()} is stable
- new: New {(session.name or "finding").capitalize()} not seen on prior imaging
- resolved: {(session.name or "Finding").capitalize()} seen on a prior exam has resolved
- increased: {(session.name or "Finding").capitalize()} has increased
- decreased: {(session.name or "Finding").capitalize()} has decreased
- larger: {(session.name or "Finding").capitalize()} is larger
- smaller: {(session.name or "Finding").capitalize()} is smaller
"""
            session.attributes_markdown = stub_markdown
            session.current_step = 4
            await session_manager.update_session(session)

            # Skip to step 4
            context = {
                "request": request,
                "current_step": 4,
                "session_data": session,
            }
            html_content = templates.get_template(
                "components/finding_model_creation/step_4_edit_attributes.html"
            ).render(**context)
        else:
            # Move to step 3 to review similar models
            context = {
                "request": request,
                "current_step": 3,
                "session_data": session,
                "similar_models": session.similar_models,
            }
            html_content = templates.get_template(
                "components/finding_model_creation/step_3_review_overlap.html"
            ).render(**context)

        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(f"Error processing step 2: {str(e)}", exc_info=True)
        session.error_message = f"Error finding similar models: {str(e)}"
        await session_manager.update_session(session)

        context = {
            "request": request,
            "current_step": 2,
            "session_data": session,
            "error_message": session.error_message,
        }
        html_content = templates.get_template("components/finding_model_creation/step_2_edit_description.html").render(
            **context
        )
        return HTMLResponse(content=html_content, status_code=500)


@router.post("/create/step/3")
async def process_step_3(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
) -> HTMLResponse:
    """Process step 3: Generate stub markdown for attributes."""
    try:
        # Generate stub markdown
        stub_markdown = f"""### presence

Presence of {session.name or "the finding"}

- absent: {(session.name or "Finding").capitalize()} is not visible
- present: {(session.name or "Finding").capitalize()} is clearly visible
- indeterminate: Presence of {session.name or "finding"} cannot be determined
- unknown: Presence of {session.name or "finding"} is unknown

### change from prior

How the {session.name or "finding"} has changed compared to prior imaging

- unchanged: {(session.name or "Finding").capitalize()} is unchanged from prior imaging
- stable: {(session.name or "Finding").capitalize()} is stable
- new: New {(session.name or "finding").capitalize()} not seen on prior imaging
- resolved: {(session.name or "Finding").capitalize()} seen on a prior exam has resolved
- increased: {(session.name or "Finding").capitalize()} has increased
- decreased: {(session.name or "Finding").capitalize()} has decreased
- larger: {(session.name or "Finding").capitalize()} is larger
- smaller: {(session.name or "Finding").capitalize()} is smaller
"""

        # Update session
        session.attributes_markdown = stub_markdown
        session.current_step = 4
        await session_manager.update_session(session)

        # Move to step 4
        context = {
            "request": request,
            "current_step": 4,
            "session_data": session,
        }
        html_content = templates.get_template("components/finding_model_creation/step_4_edit_attributes.html").render(
            **context
        )
        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(f"Error processing step 3: {str(e)}", exc_info=True)
        session.error_message = f"Error generating attributes: {str(e)}"
        await session_manager.update_session(session)

        context = {
            "request": request,
            "current_step": 3,
            "session_data": session,
            "similar_models": session.similar_models,
            "error_message": session.error_message,
        }
        html_content = templates.get_template("components/finding_model_creation/step_3_review_overlap.html").render(
            **context
        )
        return HTMLResponse(content=html_content, status_code=500)


@router.post("/create/step/4")
async def process_step_4(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    database: DatabaseDep,
    form_data: StepAttributesForm = Depends(),
) -> HTMLResponse:
    """Process step 4: Generate final model."""
    try:
        # FastAPI + Pydantic already validated the form data
        description = form_data.description
        synonyms_list = form_data.synonyms  # Already parsed and validated by Pydantic
        attributes_markdown = form_data.attributes_markdown

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
        context = {
            "request": request,
            "current_step": 5,
            "session_data": session,
            "finding_model": finding_model,  # Pass the actual Pydantic model object
        }
        html_content = templates.get_template("components/finding_model_creation/step_5_review_model.html").render(
            **context
        )
        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(f"Error processing step 4: {str(e)}", exc_info=True)
        session.error_message = f"Error generating final model: {str(e)}"
        await session_manager.update_session(session)

        context = {
            "request": request,
            "current_step": 4,
            "session_data": session,
            "error_message": session.error_message,
        }
        html_content = templates.get_template("components/finding_model_creation/step_4_edit_attributes.html").render(
            **context
        )
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
        context = {
            "request": request,
            "current_step": 1,
            "session_data": new_session,
        }
        html_content = templates.get_template("components/finding_model_creation/step_1_enter_name.html").render(
            **context
        )

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
