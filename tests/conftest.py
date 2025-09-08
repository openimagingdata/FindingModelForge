"""Test configuration and fixtures."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from findingmodel import FindingModelFull

from app.database import CommentRepo, Database, DraftRepo, UserRepo
from app.main import app
from app.models import FindingModelDraft, FindingModelInputs


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    # Mock database for tests
    mock_database = Database()

    # Create a mock UserRepo
    mock_user_repo = MagicMock(spec=UserRepo)
    mock_user_repo.collection = MagicMock()
    mock_user_repo.collection.find_one = AsyncMock()
    mock_user_repo.collection.update_one = AsyncMock()
    mock_database.user_repo = mock_user_repo

    # Create a mock CommentRepo
    mock_comment_repo = MagicMock(spec=CommentRepo)
    mock_comment_repo.get_thread = AsyncMock()
    mock_comment_repo.add_comment = AsyncMock()
    mock_comment_repo.add_reply = AsyncMock()
    mock_comment_repo.report_comment = AsyncMock()
    mock_database.comment_repo = mock_comment_repo

    # Create a mock DraftRepo with minimal async behavior
    mock_draft_repo = MagicMock(spec=DraftRepo)

    # Async helpers returning reasonable defaults
    async def _find_editable_by_name(user_id: int, name: str):  # type: ignore[no-untyped-def]
        return None

    async def _save_draft(  # type: ignore[no-untyped-def]
        user_id: int,
        name: str,
        inputs,
        draft_id: str | None = None,
        generated_json: str | None = None,
    ):
        return FindingModelDraft(
            id="mock-id",
            user_id=user_id,
            name=name,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            inputs=inputs if isinstance(inputs, FindingModelInputs) else FindingModelInputs(**inputs.model_dump()),
            generated_json=generated_json,
            status="draft",
            action_log=[],
        )

    mock_draft_repo.find_editable_by_name = AsyncMock(side_effect=_find_editable_by_name)
    mock_draft_repo.save_draft = AsyncMock(side_effect=_save_draft)
    mock_database.draft_repo = mock_draft_repo

    # Create a mock finding_index
    from findingmodel.index import Index

    mock_finding_index = MagicMock(spec=Index)
    mock_database.finding_index = mock_finding_index

    # Mock cache for tests
    from app.cache import RedisCache

    mock_cache = MagicMock(spec=RedisCache)
    mock_cache.enabled = True  # Set enabled property for health checks
    mock_cache.is_healthy = AsyncMock(return_value=True)  # Mock health check method

    # Set up app state
    app.state.database = mock_database
    app.state.cache = mock_cache

    return TestClient(app)


@pytest.fixture
def mock_finding_model() -> FindingModelFull:
    """Create a mock FindingModelFull with valid data from test data.

    Returns:
        A valid FindingModelFull instance based on abdominal_abscess.fm.json
    """
    # Load actual valid finding model data
    with open("tests/data/abdominal_abscess.fm.json") as f:
        data = json.load(f)

    # Add required fields for FindingModelFull
    data["slug"] = "test-slug"
    data["created_at"] = datetime.now(UTC)
    data["updated_at"] = datetime.now(UTC)
    data["version"] = "1.0.0"
    data["status"] = "published"
    data["generated_json"] = {}

    return FindingModelFull(**data)


@pytest.fixture
def mock_github_user() -> dict[str, str | int | bool]:
    """Mock GitHub user data."""
    return {
        "id": 12345,
        "login": "testuser",
        "name": "Test User",
        "email": "test@example.com",
        "avatar_url": "https://github.com/images/error/testuser_happy.gif",
        "html_url": "https://github.com/testuser",
        "type": "User",
        "site_admin": False,
    }
