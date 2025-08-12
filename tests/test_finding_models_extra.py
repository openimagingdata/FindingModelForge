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
def test_step2_invalid_synonyms_returns_500() -> None:
    client = _setup_minimal()
    resp = client.post(
        "/api/finding-models/create/step/2",
        data={
            "session_id": "sid-x",
            "description": "A sufficiently long description",
            "synonyms": "not json",
        },
    )
    # parse_synonyms raises HTTPException -> caught by route and returns 500 error fragment
    assert resp.status_code == 500
    assert "Error finding similar models" in resp.text


def test_restart_creation_sets_cookie() -> None:
    client = _setup_minimal()
    resp = client.post("/api/finding-models/create/restart")
    assert resp.status_code == 200
    # Check new cookie present
    cookies = resp.headers.get("set-cookie", "")
    assert "creation_session_id=" in cookies


@patch(
    "app.routers.finding_models.generate_default_attributes_markdown",
    new=lambda name: "### presence\n- absent: no\n",
)
@patch("app.routers.finding_models.FindingModelInputs", new=lambda **kw: MagicMock())
def test_get_step4_triggers_autosave() -> None:
    client = _setup_minimal()

    # Provide session with a name so autosave path runs
    session_json = '{"session_id":"sid-4","current_step":3,"name":"nodule","description":"d","synonyms":["a"]}'
    app.state.cache.get = AsyncMock(return_value=session_json)  # type: ignore[attr-defined]

    # Track calls to save_draft
    saved = {"count": 0}

    async def _save_draft(*args, **kwargs):  # type: ignore[no-untyped-def]
        saved["count"] += 1
        m = MagicMock()
        m.id = "oid1234567890abcdef123456"
        m.status = "draft"
        return m

    app.state.database.draft_repo.save_draft = AsyncMock(side_effect=_save_draft)  # type: ignore[attr-defined]

    resp = client.get("/api/finding-models/create/step/4?session_id=sid-4")
    assert resp.status_code == 200
    assert saved["count"] >= 1
