"""Creation service for finding model generation and workflow."""

import asyncio
import json
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
from app.database import Database
from app.models import User

TEST_USER_ID = 999999


class CreationService:
    """Service for finding model creation workflow and generation."""

    def __init__(self, index: Any, database: Database) -> None:
        """Initialize with required dependencies.

        Args:
            index: FindingModel index for database queries
            database: Database instance for contributor lookup
        """
        self.index = index
        self.database = database

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

        author = self.database.people.get(user.login)
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

    def parse_synonyms(self, synonyms: str) -> list[str]:
        """Parse synonyms from JSON string.

        Args:
            synonyms: JSON string containing synonyms array

        Returns:
            List of parsed synonyms

        Raises:
            ValueError: If synonyms format is invalid
        """
        if not synonyms.strip():
            return []

        try:
            synonyms_parsed = json.loads(synonyms)
            if not isinstance(synonyms_parsed, list) or not all(s and isinstance(s, str) for s in synonyms_parsed):
                raise ValueError("Synonyms must be a JSON array of strings")
            return [s.strip() for s in synonyms_parsed]
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid synonyms format: {str(e)}") from e

    def is_test_user(self, user_id: int) -> bool:
        """Check if user ID is the test user.

        Args:
            user_id: User ID to check

        Returns:
            True if test user, False otherwise
        """
        return user_id == TEST_USER_ID
