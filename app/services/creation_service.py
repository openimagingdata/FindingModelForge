"""Creation service for finding model generation and workflow."""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any

from findingmodel import FindingInfo, FindingModelBase
from findingmodel.tools import (
    add_ids_to_model,
    add_standard_codes_to_model,
    create_info_from_name,
    create_model_from_markdown,
    find_similar_models,
)
from findingmodel.tools.similar_finding_models import SimilarModelAnalysis

from app.config import logger
from app.database import Database, DraftRepo
from app.models import FindingModelDraft, User
from app.utils.draft_formatting import humanize_timestamp

TEST_USER_ID = 999999


class WorkflowAction(Enum):
    """Possible outcomes of name resolution."""

    CREATE_NEW = "create_new"  # No existing draft, proceed with AI generation
    RESUME_EDITABLE = "resume_editable"  # Found editable draft, redirect to edit
    VIEW_SUBMITTED = "view_submitted"  # Found submitted draft, redirect to view


@dataclass
class NameResolutionResult:
    """Result of resolving a name input."""

    action: WorkflowAction
    draft: FindingModelDraft | None = None
    redirect_url: str | None = None


@dataclass
class SessionData:
    """Data needed to populate a session from a draft."""

    name: str
    description: str
    synonyms: list[str]
    attributes_markdown: str
    draft_id: str | None
    draft_status: str | None
    submitted_display_time: str | None


class CreationService:
    """Service for finding model creation workflow and generation."""

    def __init__(self, index: Any, database: Database, draft_repo: DraftRepo) -> None:
        """Initialize with required dependencies.

        Args:
            index: FindingModel index for database queries
            database: Database instance for contributor lookup
            draft_repo: DraftRepo instance for draft operations
        """
        self.index = index
        self.database = database
        self.draft_repo = draft_repo

    async def check_name_availability(self, name: str, user_id: int | None = None) -> bool:
        """Check if a finding model name is available.

        Args:
            name: Name to check availability for
            user_id: Optional user ID (for logging)

        Returns:
            True if name is available, False if already exists
        """
        try:
            existing_entry = await self.index.get(name)
            if existing_entry:
                logger.debug(f"Name '{name}' already exists in index (user: {user_id})")
                return False
            return True
        except Exception:
            # If we can't check, assume it's available (fail open)
            return True

    async def generate_finding_info(self, name: str, test_mode: bool = False) -> FindingInfo:
        """Generate finding info from name using AI or test data.

        Args:
            name: Finding name to generate info for
            test_mode: Whether to use mock data for testing

        Returns:
            FindingInfo with generated description and synonyms
        """
        if test_mode:
            # Mock AI response for test user
            logger.info("Using MOCK AI response for create_info_from_name (test mode)")
            await asyncio.sleep(2.0)  # Simulate AI processing time
            return FindingInfo(
                name=name,
                description=f"Test description for {name}. This is a mock response for UI testing.",
                synonyms=[f"{name}_synonym1", f"{name}_synonym2"],
            )
        else:
            logger.info("Using REAL AI response for create_info_from_name")
            return await create_info_from_name(name)

    async def find_similar_models(
        self, name: str, description: str, synonyms: list[str], test_mode: bool = False
    ) -> SimilarModelAnalysis:
        """Find similar models using AI or test data.

        Args:
            name: Finding name
            description: Finding description
            synonyms: List of synonyms
            test_mode: Whether to use mock data for testing

        Returns:
            SimilarModelAnalysis with similar models and recommendation
        """
        if test_mode:
            # Mock AI response for test user
            logger.info("Using MOCK AI response for find_similar_models (test mode)")
            await asyncio.sleep(2.0)  # Simulate AI processing time
            return SimilarModelAnalysis(
                similar_models=[],
                recommendation="create_new",
                confidence=1.0,
            )
        else:
            logger.info("Using REAL AI response for find_similar_models")
            return await find_similar_models(
                finding_name=name,
                description=description,
                synonyms=synonyms,
                index=self.index,
            )

    async def generate_from_inputs(
        self,
        name: str,
        inputs: Any,  # FindingModelInputs
        user: User,
        test_mode: bool = False,
    ) -> str:
        """Generate finding model JSON from inputs.

        Args:
            name: Finding model name
            inputs: FindingModelInputs with description, synonyms, attributes
            user: User creating the model
            test_mode: Whether to use mock data for testing

        Returns:
            Generated finding model as JSON string
        """
        # Create FindingInfo from inputs
        finding_info = FindingInfo(name=name, description=inputs.description, synonyms=inputs.synonyms or [])

        # Build complete markdown
        complete_markdown = f"""# {name}
## Description
{inputs.description}
{inputs.attributes_markdown}
"""

        if test_mode:
            # Mock AI response for test user
            logger.info("Using MOCK AI response for create_model_from_markdown (test mode)")
            await asyncio.sleep(2.0)  # Simulate AI processing time

            # Create mock FindingModel directly without AI call
            mock_model_dict = {
                "name": name if len(name) >= 5 else f"{name} Test",
                "description": inputs.description,
                "synonyms": inputs.synonyms or [],
                "tags": None,
                "contributors": None,
                "attributes": [
                    {
                        "name": "presence",
                        "description": f"Presence of {name}",
                        "type": "choice",
                        "values": [
                            {"name": "absent", "description": f"{name} is not visible"},
                            {"name": "present", "description": f"{name} is clearly visible"},
                        ],
                        "required": False,
                        "max_selected": 1,
                    }
                ],
            }
            finding_model_generated = FindingModelBase.model_validate(mock_model_dict)
        else:
            logger.info("Using REAL AI response for create_model_from_markdown")
            finding_model_generated = await create_model_from_markdown(finding_info, markdown_text=complete_markdown)

        # Add IDs and contributors
        if not self.database.finding_index:
            raise RuntimeError("FindingIndex must be initialized in the database")
        if not self.database.people_repo:
            raise RuntimeError("PeopleRepo must be initialized in the database")

        author = await self.database.people_repo.get_by_username(user.login)
        source = author.organization_code if author else (user.organizations[0] if user.organizations else "OIDM")
        fm = add_ids_to_model(finding_model_generated, source=source)
        add_standard_codes_to_model(fm)

        # Convert to JSON
        return fm.model_dump_json(indent=2)

    def generate_default_attributes_markdown(self, finding_name: str) -> str:
        """Generate default attributes markdown template for a finding.

        Args:
            finding_name: Name of the finding

        Returns:
            Default attributes markdown template
        """
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

    def is_test_user(self, user_id: int) -> bool:
        """Check if user ID is the test user.

        Args:
            user_id: User ID to check

        Returns:
            True if test user, False otherwise
        """
        return user_id == TEST_USER_ID

    async def resolve_name_input(self, user_id: int, name: str) -> NameResolutionResult:
        """Determine workflow path for a given name.

        Args:
            user_id: User ID submitting the name
            name: Finding model name to resolve

        Returns:
            NameResolutionResult with action and optional draft/redirect_url:
            - CREATE_NEW: Name is available, proceed with AI generation
            - RESUME_EDITABLE: Found editable draft, redirect to edit
            - VIEW_SUBMITTED: Found submitted draft, redirect to view
        """
        # Check for editable draft
        try:
            draft = await self.draft_repo.find_editable_by_name(user_id=user_id, name=name)
        except Exception as e:
            logger.warning(f"Draft lookup failed for name '{name}': {e}")
            draft = None

        if draft is not None:
            logger.info(f"Resuming editable draft {draft.id} for name '{name}'")
            return NameResolutionResult(
                action=WorkflowAction.RESUME_EDITABLE,
                draft=draft,
                redirect_url=f"/drafts/{draft.id}?mode=edit",
            )

        # Check for submitted draft
        try:
            latest = await self.draft_repo.find_latest_by_name(user_id=user_id, name=name)
        except Exception:
            latest = None

        if latest is not None and latest.status == "submitted":
            logger.info(f"Resuming submitted draft {latest.id} for name '{name}' into review step")
            return NameResolutionResult(
                action=WorkflowAction.VIEW_SUBMITTED,
                draft=latest,
                redirect_url=f"/drafts/{latest.id}?mode=view",
            )

        # Name is available for new creation
        return NameResolutionResult(action=WorkflowAction.CREATE_NEW)

    def extract_session_data(self, draft: FindingModelDraft) -> SessionData:
        """Extract session data from an existing draft.

        Args:
            draft: Draft document to extract data from

        Returns:
            SessionData with all necessary session fields populated
        """
        return SessionData(
            name=draft.name,
            description=draft.inputs.description if draft.inputs else "",
            synonyms=(draft.inputs.synonyms if draft.inputs and draft.inputs.synonyms else []),
            attributes_markdown=(
                draft.inputs.attributes_markdown
                if draft.inputs and draft.inputs.attributes_markdown
                else self.generate_default_attributes_markdown(draft.name)
            ),
            draft_id=str(draft.id),
            draft_status=draft.status,
            submitted_display_time=humanize_timestamp(draft.updated_at) if draft.updated_at else None,
        )
