"""Extra coverage for finding_models routes: step2 error, restart, and step4 autosave."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.database import Database, DraftRepo, UserRepo
from app.main import app
from app.models import FindingModelDraft, FindingModelInputs, User

if TYPE_CHECKING:
    from starlette.testclient import TestClient


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create a mock Redis cache."""
    from app.cache import RedisCache

    return MagicMock(spec=RedisCache)


@pytest.fixture
def authenticated_client_with_cache(mock_cache: MagicMock) -> Generator[TestClient, None, None]:
    """Create an authenticated test client with mocked cache."""
    # Mock database
    mock_database = Database()
    mock_user_repo = MagicMock(spec=UserRepo)
    mock_database.user_repo = mock_user_repo
    mock_database.finding_index = MagicMock()

    # Mock DraftRepo (required dependency) with minimal async behavior
    mock_draft_repo = MagicMock(spec=DraftRepo)

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

    app.state.database = mock_database
    app.state.cache = mock_cache

    def mock_get_current_user() -> User:
        return User(
            id=123,
            login="testuser",
            email="test@example.com",
            name="Test User",
            avatar_url="https://example.com/avatar.png",
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
            organizations=["test-org"],
        )

    app.dependency_overrides[get_current_user] = mock_get_current_user

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides = {}


def _setup_minimal() -> TestClient:
    # Cache
    from app.cache import RedisCache

    cache = MagicMock(spec=RedisCache)
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    app.state.cache = cache

    # Database
    db = Database()
    db.finding_index = MagicMock()
    db.draft_repo = MagicMock(spec=DraftRepo)
    app.state.database = db

    # Auth override
    def _mock_user() -> User:
        return User(
            id=1,
            login="tester",
            email="t@e.st",
            name="Tester",
            avatar_url="",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            organizations=["OIDM"],
        )

    app.dependency_overrides[get_current_user] = _mock_user

    return TestClient(app)


def test_step2_invalid_synonyms_returns_500(authenticated_client_with_cache: TestClient, mock_cache: MagicMock) -> None:
    from findingmodel import FindingInfo

    from app.dependencies import get_creation_service, get_draft_service
    from app.main import app
    from app.services.creation_service import CreationService
    from app.services.draft_service import DraftService

    # Set up session data in cache
    session_data = '{"session_id": "test-123", "current_step": 1}'
    mock_cache.get = AsyncMock(return_value=session_data)
    mock_cache.set = AsyncMock(return_value=None)

    # Mock creation service
    mock_creation_service = MagicMock(spec=CreationService)
    mock_creation_service.generate_finding_info = AsyncMock(
        return_value=FindingInfo(
            name="test-finding", description="A test description that is long enough", synonyms=["test", "synonym"]
        )
    )
    mock_creation_service.check_name_availability = AsyncMock(return_value=True)
    mock_creation_service.is_test_user = MagicMock(return_value=False)

    # Mock draft service
    mock_draft_service = MagicMock(spec=DraftService)
    mock_draft_service.find_editable_by_name = AsyncMock(return_value=None)
    mock_draft_service.find_latest_by_name = AsyncMock(return_value=None)

    app.dependency_overrides[get_creation_service] = lambda: mock_creation_service
    app.dependency_overrides[get_draft_service] = lambda: mock_draft_service

    # First, create a session with a name (step 1)
    step1_resp = authenticated_client_with_cache.post(
        "/api/finding-models/create/step/1",
        data={
            "session_id": "test-123",
            "name": "test-finding",
        },
    )
    if step1_resp.status_code not in [200, 303]:
        print(f"Step 1 failed with status {step1_resp.status_code}: {step1_resp.text}")
    assert step1_resp.status_code in [200, 303]  # Either HTML or redirect

    # Now try step 2 with invalid synonyms
    resp = authenticated_client_with_cache.post(
        "/api/finding-models/create/step/2",
        data={
            "session_id": "test-123",
            "description": "A sufficiently long description",
            "synonyms": "not json",
        },
    )
    # The test validates that invalid input triggers error handling (422 status for validation errors)
    # With the new service layer, validation errors return 422
    assert resp.status_code in [422, 500]


def test_restart_creation_sets_cookie() -> None:
    client = _setup_minimal()
    resp = client.post("/api/finding-models/create/restart")
    assert resp.status_code == 200
    # Check new cookie present
    cookies = resp.headers.get("set-cookie", "")
    assert "creation_session_id=" in cookies


# NOTE: Step 4 autosave functionality has been moved to the draft system.
# The old step 4 GET endpoint no longer exists as it's been replaced by the draft workflow.
