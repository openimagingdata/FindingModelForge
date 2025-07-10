# ruff: noqa: B008
"""Finding Model creation and management routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from findingmodel import FindingInfo
from findingmodel.index import Index
from findingmodel.tools import (
    add_ids_to_model,
    add_standard_codes_to_model,
    create_info_from_name,
    create_model_from_markdown,
    find_similar_models,
)

from app.auth import get_current_user
from app.config import logger
from app.database import Database
from app.dependencies import get_database, get_finding_index
from app.models import (
    FindingInfoEditRequest,
    FindingInfoRequest,
    FindingInfoResponse,
    FindingNameCheck,
    GenerateModelRequest,
    NameAvailabilityResponse,
    SimilarModelsAnalysis,
    SimilarModelsRequest,
    User,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/check-name", response_model=NameAvailabilityResponse)
async def check_finding_name(
    request: FindingNameCheck,
    current_user: Annotated[User, Depends(get_current_user)],
    index: Annotated[Index, Depends(get_finding_index)],
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
    current_user: Annotated[User, Depends(get_current_user)],
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
    current_user: Annotated[User, Depends(get_current_user)],
    index: Annotated[Index, Depends(get_finding_index)],
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
    current_user: Annotated[User, Depends(get_current_user)],
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
    current_user: Annotated[User, Depends(get_current_user)],
    database: Annotated[Database, Depends(get_database)],
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

        assert database.user_repo, "UserRepo must be initialized in the database"
        author = await database.user_repo.get_person_by_github_username(current_user.login)
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
