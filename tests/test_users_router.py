from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.database import Database, DraftRepo, UserRepo
from app.main import app
from app.models import User, UserUpdate


def _client_with_user_repo(user: User) -> TestClient:
    # Minimal database and repos
    db = Database()
    db.draft_repo = MagicMock(spec=DraftRepo)
    user_repo = MagicMock(spec=UserRepo)

    # Return a copy of the user with provided updates applied
    async def _update_user_side_effect(user_id: int, patch: UserUpdate) -> User:  # type: ignore[override]
        return user.model_copy(update=patch.model_dump(exclude_none=True))

    user_repo.update_user = AsyncMock(side_effect=_update_user_side_effect)
    db.user_repo = user_repo  # type: ignore[assignment]
    app.state.database = db

    # Auth override
    app.dependency_overrides[get_current_user] = lambda: user

    return TestClient(app)


def test_get_user_profile() -> None:
    user = User(
        id=42,
        login="u",
        email="u@e.st",
        name="Name",
        avatar_url="",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        organizations=["ORG"],
    )
    client = _client_with_user_repo(user)

    resp = client.get("/api/users/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 42


def test_update_user_profile() -> None:
    user = User(
        id=42,
        login="u",
        email="u@e.st",
        name="Name",
        avatar_url="",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        organizations=["ORG"],
    )
    client = _client_with_user_repo(user)

    payload = UserUpdate(name="New Name")
    resp = client.patch("/api/users/profile", json=payload.model_dump(exclude_none=True))
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


def test_update_user_profile_not_found() -> None:
    user = User(
        id=43,
        login="u2",
        email="u2@e.st",
        name="Name",
        avatar_url="",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        organizations=["ORG"],
    )
    # Prepare client and then override repo to return None
    client = _client_with_user_repo(user)
    from app.main import app

    # Replace update_user to simulate not found
    app.state.database.user_repo.update_user = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    payload = UserUpdate(name="X")
    resp = client.patch("/api/users/profile", json=payload.model_dump(exclude_none=True))
    assert resp.status_code == 404


def test_get_user_organizations() -> None:
    user = User(
        id=42,
        login="u",
        email="u@e.st",
        name="Name",
        avatar_url="",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        organizations=["O1", "O2"],
    )
    client = _client_with_user_repo(user)

    resp = client.get("/api/users/profile/organizations")
    assert resp.status_code == 200
    assert resp.json() == ["O1", "O2"]


def test_get_user_organizations_empty() -> None:
    user = User(
        id=44,
        login="u3",
        email="u3@e.st",
        name="Name",
        avatar_url="",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        organizations=[],
    )
    client = _client_with_user_repo(user)

    resp = client.get("/api/users/profile/organizations")
    assert resp.status_code == 200
    assert resp.json() == []
