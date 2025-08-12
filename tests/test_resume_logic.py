from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.database import Database, DraftRepo, UserRepo
from app.models import FindingModelDraft, FindingModelInputs, User


def _client_with_state(session_json: str) -> TestClient:
    db = Database()
    db.user_repo = MagicMock(spec=UserRepo)
    db.finding_index = MagicMock()
    db.draft_repo = MagicMock(spec=DraftRepo)
    db.people = {}
    db.organizations = {}

    from app.main import app

    app.state.database = db

    from app.cache import RedisCache

    mock_cache = MagicMock(spec=RedisCache)
    mock_cache.enabled = True
    mock_cache.is_healthy = AsyncMock(return_value=True)
    mock_cache.get = AsyncMock(return_value=session_json)
    mock_cache.set = AsyncMock(return_value=None)
    mock_cache.delete = AsyncMock(return_value=None)
    app.state.cache = mock_cache

    def mock_user() -> User:
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

    app.dependency_overrides[get_current_user] = mock_user

    return TestClient(app)


def _draft(
    status: Literal["draft", "submitted", "under-review", "added", "declined"] = "submitted",
) -> FindingModelDraft:
    return FindingModelDraft(
        id="d1",
        user_id=1,
        name="nodule",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="d", synonyms=["s"], attributes_markdown="# a"),
        generated_json=None,
        status=status,
        action_log=[],
    )


def test_step1_resumes_submitted_draft_to_step5():
    # Session starting at step 1 with no draft
    session_json = '{"session_id":"sid-x","current_step":1}'
    client = _client_with_state(session_json)
    from app.main import app

    db: Database = app.state.database  # type: ignore[assignment]
    db.draft_repo.find_editable_by_name = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    db.draft_repo.find_latest_by_name = AsyncMock(return_value=_draft("submitted"))  # type: ignore[attr-defined]

    resp = client.post(
        "/api/finding-models/create/step/1",
        data={"session_id": "sid-x", "name": "nodule"},
    )
    assert resp.status_code == 200
    # Should land on review step with submitted badge and no Save Draft
    text = resp.text.lower()
    assert "submitted" in text
    assert "save draft" not in text


def test_submit_rerenders_full_step5_and_shows_submitted():
    # Session on step 4 ready to submit
    session_json = '{"session_id":"sid-y","current_step":5,"name":"nodule"}'
    client = _client_with_state(session_json)
    from app.main import app

    db: Database = app.state.database  # type: ignore[assignment]

    # Wire submit to return a submitted draft
    async def _submit(draft_id: str, user_id: int):  # type: ignore[no-untyped-def]
        return _draft("submitted")

    db.draft_repo.submit = AsyncMock(side_effect=_submit)  # type: ignore[attr-defined]

    resp = client.post(
        "/api/finding-models/drafts/oid123/submit",
        data={"session_id": "sid-y"},
    )
    assert resp.status_code == 200
    text = resp.text.lower()
    assert "submitted" in text
    # After submit, back button should be hidden
    assert "back" not in text
