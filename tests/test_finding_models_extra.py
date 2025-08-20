"""Extra coverage for finding_models routes: step2 error, restart, and step4 autosave."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.database import Database, DraftRepo
from app.main import app
from app.models import User


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


@patch("app.routers.finding_models.find_similar_models", new=AsyncMock(return_value=MagicMock(similar_models=[])))
@patch("app.routers.finding_models.create_info_from_name")
def test_step2_invalid_synonyms_returns_500(mock_create_info: AsyncMock) -> None:
    client = _setup_minimal()

    # Mock all async dependencies properly
    from findingmodel import FindingInfo

    from app.main import app

    async def mock_find_editable_by_name(user_id: int, name: str):
        return None

    async def mock_index_get(name: str):
        return None  # Name is available

    db: Database = app.state.database  # type: ignore[assignment]
    db.draft_repo.find_editable_by_name = mock_find_editable_by_name  # type: ignore[assignment]
    db.finding_index.get = mock_index_get  # type: ignore[assignment]

    # Mock AI info generation
    mock_create_info.return_value = FindingInfo(
        name="test-finding", description="A test description that is long enough", synonyms=["test", "synonym"]
    )

    # First, create a session with a name (step 1)
    step1_resp = client.post(
        "/api/finding-models/create/step/1",
        data={
            "session_id": "sid-x",
            "name": "test-finding",
        },
    )
    assert step1_resp.status_code in [200, 303]  # Either HTML or redirect

    # Now try step 2 with invalid synonyms
    resp = client.post(
        "/api/finding-models/create/step/2",
        data={
            "session_id": "sid-x",
            "description": "A sufficiently long description",
            "synonyms": "not json",
        },
    )
    # The test validates that invalid input triggers error handling (500 status)
    # The specific error may vary depending on session state
    assert resp.status_code == 500


def test_restart_creation_sets_cookie() -> None:
    client = _setup_minimal()
    resp = client.post("/api/finding-models/create/restart")
    assert resp.status_code == 200
    # Check new cookie present
    cookies = resp.headers.get("set-cookie", "")
    assert "creation_session_id=" in cookies


# NOTE: Step 4 autosave functionality has been moved to the draft system.
# The old step 4 GET endpoint no longer exists as it's been replaced by the draft workflow.
