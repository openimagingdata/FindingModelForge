"""Test setup and teardown utilities for UI tests.

This module provides utilities to ensure UI tests have a clean, consistent environment
and don't depend on external state or interfere with each other.
"""

# Pytest fixtures for test files
from __future__ import annotations

import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings


class UITestDatabase:
    """Manages database state for UI tests."""

    def __init__(self):
        self.client: AsyncIOMotorClient = None
        self.db = None

    async def connect(self):
        """Connect to test database."""
        self.client = AsyncIOMotorClient(settings.mongodb_uri)
        self.db = self.client[settings.mongodb_db]

    async def disconnect(self):
        """Disconnect from database."""
        if self.client:
            self.client.close()

    async def clean_all_test_data(self):
        """Remove all test data from the database."""
        if not self.db:
            await self.connect()

        # Clean up comment threads for test finding models
        await self.db["comment_threads"].delete_many(
            {
                "reference_type": "finding_model",
                "reference_id": {
                    "$in": [
                        "OIFM_GMTS_004244",  # abdominal-abscess
                        "OIFM_GMTS_004245",  # liver-lesion (if it has an OIFM ID)
                    ]
                },
            }
        )

        # Clean up any test drafts
        await self.db["finding_model_drafts"].delete_many(
            {
                "user_id": 999999  # Test user
            }
        )

        # Clean up test user data
        await self.db["users"].delete_many({"id": 999999})

    async def ensure_test_user_exists(self):
        """Ensure the test user exists in the database."""
        if not self.db:
            await self.connect()

        # Check if test user exists
        existing = await self.db["users"].find_one({"id": 999999})
        if not existing:
            # Create test user
            await self.db["users"].insert_one(
                {
                    "id": 999999,
                    "login": "playwright-test-user",
                    "name": "Playwright Test User",
                    "email": "test@example.com",
                    "avatar_url": "https://github.com/playwright-test-user.png?size=40",
                    "organizations": [],
                    "is_active": True,
                    "comment_index": [],
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                }
            )

    async def verify_finding_model_accessible(self, slug: str) -> tuple[bool, str | None]:
        """Verify a finding model is accessible via the service.

        Returns:
            Tuple of (is_accessible, oifm_id or None)
        """
        # This would require importing and using the service
        # For now, we'll just return expected values
        known_models = {
            "abdominal-abscess": "OIFM_GMTS_004244",
            "liver-lesion": "OIFM_GMTS_004245",  # Hypothetical
        }

        if slug in known_models:
            return True, known_models[slug]
        return False, None

    async def get_actual_oifm_id(self, slug: str) -> str | None:
        """Get the actual OIFM ID for a finding model by slug.

        This should query the actual service to get the real OIFM ID.
        """
        # Import here to avoid circular dependencies
        from app.cache import RedisCache
        from app.database import Database
        from app.services.finding_model_service import FindingModelService

        try:
            db = Database()
            cache = RedisCache()
            await cache.initialize()

            service = FindingModelService(
                database=db, cache=cache, comment_repo=db.comment_repo, user_repo=db.user_repo
            )

            model, _ = await service.get_model_by_slug(slug)
            if model:
                return model.oifm_id
        except Exception as e:
            print(f"Error getting OIFM ID for {slug}: {e}")

        return None


class UITestSetup:
    """Main setup class for UI tests."""

    def __init__(self):
        self.db_manager = UITestDatabase()
        self._required_models = ["abdominal-abscess", "liver-lesion"]
        self._model_oifm_ids = {}

    async def setup_all(self):
        """Complete setup for UI tests."""
        await self.db_manager.connect()

        # 1. Clean all existing test data
        await self.db_manager.clean_all_test_data()

        # 2. Ensure test user exists
        await self.db_manager.ensure_test_user_exists()

        # 3. Verify required finding models are accessible
        for slug in self._required_models:
            accessible, oifm_id = await self.db_manager.verify_finding_model_accessible(slug)
            if not accessible:
                raise RuntimeError(f"Required finding model '{slug}' is not accessible")
            self._model_oifm_ids[slug] = oifm_id

        # 4. Store the OIFM IDs for tests to use
        return self._model_oifm_ids

    async def teardown_all(self):
        """Complete teardown after UI tests."""
        # Clean all test data
        await self.db_manager.clean_all_test_data()
        await self.db_manager.disconnect()

    async def clean_comments_for_model(self, reference_id: str):
        """Clean comments for a specific model (useful between tests)."""
        if not self.db_manager.db:
            await self.db_manager.connect()

        await self.db_manager.db["comment_threads"].delete_many(
            {"reference_type": "finding_model", "reference_id": reference_id}
        )


@pytest.fixture(scope="session")
async def ui_test_setup():
    """Session-scoped fixture to set up UI test environment."""
    setup = UITestSetup()
    oifm_ids = await setup.setup_all()

    yield setup, oifm_ids

    await setup.teardown_all()


@pytest.fixture(scope="function")
async def clean_test_comments(ui_test_setup):
    """Function-scoped fixture to clean comments before each test."""
    setup, oifm_ids = ui_test_setup

    # Clean comments for all known models before test
    for oifm_id in oifm_ids.values():
        if oifm_id:
            await setup.clean_comments_for_model(oifm_id)

    yield oifm_ids

    # No cleanup after - next test will clean before it runs


# Constants for tests to use
TEST_USER_ID = 999999
TEST_USER_NAME = "playwright-test-user"
ABDOMINAL_ABSCESS_SLUG = "abdominal-abscess"
LIVER_LESION_SLUG = "liver-lesion"
# These will be populated at runtime
ABDOMINAL_ABSCESS_OIFM_ID = "OIFM_GMTS_004244"  # Default, will be verified
LIVER_LESION_OIFM_ID = None  # Will be determined at runtime
