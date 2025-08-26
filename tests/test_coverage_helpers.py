"""Small targeted tests to bump coverage for utilities and dependencies."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.database import Database, DraftRepo
from app.dependencies import SessionManager
from app.main import app
from app.models import User
from app.routers.drafts import parse_synonyms
from app.services.creation_service import CreationService


def test_parse_synonyms_valid() -> None:
    assert parse_synonyms('["a","b"]') == ["a", "b"]
    assert parse_synonyms("   []  ") == []


def test_parse_synonyms_invalid_raises_http_exception() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        parse_synonyms("not json")
    assert exc.value.status_code == 422


def test_generate_default_attributes_markdown_contains_sections() -> None:
    from unittest.mock import MagicMock

    # Mock dependencies that CreationService needs
    mock_index = MagicMock()
    mock_database = MagicMock()

    creation_service = CreationService(index=mock_index, database=mock_database)
    md = creation_service.generate_default_attributes_markdown("nodule")
    assert "### presence" in md
    assert "### change from prior" in md
    assert "nodule" in md


@pytest.mark.asyncio
async def test_session_manager_roundtrip() -> None:
    # In-memory fake cache with async get/set/delete
    store: dict[str, str] = {}

    class _FakeCache:  # minimal surface used by SessionManager
        async def set(self, key: str, value: str, expires_in: Any | None = None) -> bool:  # noqa: ANN401
            store[key] = value
            return True

        async def get(self, key: str) -> str | None:
            return store.get(key)

        async def delete(self, key: str) -> bool:
            return bool(store.pop(key, None))

    sm = SessionManager(_FakeCache())  # type: ignore[arg-type]
    sid = await sm.create_session()
    assert isinstance(sid, str) and sid
    session = await sm.get_session(sid)
    assert session is not None and session.session_id == sid
    await sm.delete_session(sid)
    # After deletion, getting again should return None
    assert await sm.get_session(sid) is None


def _client_with_cache_session(session_json: str) -> TestClient:
    # Provide a cache that returns the given session JSON
    from app.cache import RedisCache

    fake_cache = MagicMock(spec=RedisCache)
    fake_cache.get = AsyncMock(return_value=session_json)
    fake_cache.set = AsyncMock(return_value=True)
    fake_cache.delete = AsyncMock(return_value=True)
    app.state.cache = fake_cache

    # Minimal database with required repos for dependency injection
    db = Database()
    db.finding_index = MagicMock()
    db.draft_repo = MagicMock(spec=DraftRepo)
    app.state.database = db

    # Auth: override to return a mock user
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


def test_get_creation_session_from_query() -> None:
    # Prepare a session in cache and hit a GET endpoint reading the session
    session_json = '{"session_id":"sid-q","current_step":1,"name":"nodule","description":"d"}'
    client = _client_with_cache_session(session_json)
    resp = client.get("/create/step/1?session_id=sid-q")
    assert resp.status_code == 200


def test_get_creation_session_from_cookie() -> None:
    session_json = '{"session_id":"sid-c","current_step":1,"name":"nodule","description":"d"}'
    client = _client_with_cache_session(session_json)
    resp = client.get("/create/step/1", cookies={"creation_session_id": "sid-c"})
    assert resp.status_code == 200


def test_save_draft_min_validation_error() -> None:
    # Use cache session from helper
    session_json = '{"session_id":"sid-123","current_step":4,"name":"nodule","description":"d"}'
    client = _client_with_cache_session(session_json)

    resp = client.post(
        "/drafts/save",
        data={
            "session_id": "sid-123",
            "description": "short",
            "attributes_markdown": "x",
            "synonyms": "[]",
        },
    )
    assert resp.status_code == 422
