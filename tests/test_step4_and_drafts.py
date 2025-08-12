"""Targeted tests to cover step 4 processing and draft endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.database import Database, DraftRepo, UserRepo
from app.main import app
from app.models import FindingModelDraft, FindingModelInputs, User


def _setup_app_with_mocks() -> TestClient:
    """Prepare app state with mocked database and cache, and authenticated user."""
    db = Database()
    db.user_repo = MagicMock(spec=UserRepo)
    db.finding_index = MagicMock()
    db.draft_repo = MagicMock(spec=DraftRepo)
    # Minimal people/orgs maps
    db.people = {}
    db.organizations = {}

    app.state.database = db

    # Mock cache with working get/set
    from app.cache import RedisCache

    mock_cache = MagicMock(spec=RedisCache)
    mock_cache.enabled = True
    mock_cache.is_healthy = AsyncMock(return_value=True)
    # Session id used by tests
    session_json = '{"session_id":"sid-123","current_step":4,"name":"nodule","description":"desc"}'
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


class _SimpleModel:
    def __init__(self, name: str = "nodule", description: str = "desc") -> None:
        self.contributors = None
        self._payload = {"name": name, "description": description}

    def model_dump(self, mode: str = "json", exclude_none: bool = True):  # type: ignore[no-untyped-def]
        return self._payload

    def model_dump_json(self) -> str:
        return '{"name":"nodule","description":"desc"}'


@patch("app.routers.finding_models.add_standard_codes_to_model", new=lambda *args, **kwargs: None)
@patch("app.routers.finding_models.add_ids_to_model", new=lambda *args, **kwargs: _SimpleModel())
@patch("app.routers.finding_models.create_model_from_markdown", new=AsyncMock(return_value=_SimpleModel()))
def test_step4_generates_model_and_saves_draft() -> None:
    client = _setup_app_with_mocks()
    db: Database = app.state.database  # type: ignore[assignment]

    # Mock DraftRepo.save_draft to return a minimal FindingModelDraft
    async def _save_draft(  # type: ignore[no-untyped-def]
        user_id: int,
        name: str,
        inputs: FindingModelInputs,
        draft_id: str | None = None,
        generated_json: str | None = None,
    ):
        return FindingModelDraft(
            id="draft1",
            user_id=user_id,
            name=name,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            inputs=inputs,
            generated_json=generated_json,
            status="draft",
            action_log=[],
        )

    db.draft_repo.save_draft = AsyncMock(side_effect=_save_draft)  # type: ignore[assignment]

    resp = client.post(
        "/api/finding-models/create/step/4",
        data={
            "session_id": "sid-123",
            "description": "A long enough description for the model",
            "synonyms": '["mass"]',
            "attributes_markdown": (
                "# Attributes\n\n### presence\n- present: present\n- absent: absent\n"
                "- indeterminate: maybe\n- unknown: ?"
            ),
        },
    )
    assert resp.status_code == 200
    # Should render review step
    assert "Your Finding Model" in resp.text or "Review" in resp.text


def test_draft_submit_endpoint() -> None:
    client = _setup_app_with_mocks()
    db: Database = app.state.database  # type: ignore[assignment]

    # Return a draft from submit
    async def _submit(draft_id: str, user_id: int):  # type: ignore[no-untyped-def]
        return FindingModelDraft(
            id=draft_id,
            user_id=user_id,
            name="nodule",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            inputs=FindingModelInputs(description="d", synonyms=["s"], attributes_markdown="# a"),
            generated_json=None,
            status="submitted",
            action_log=[],
        )

    db.draft_repo.submit = AsyncMock(side_effect=_submit)  # type: ignore[assignment]

    resp = client.post("/api/finding-models/drafts/abc123/submit", data={"session_id": "sid-123"})
    assert resp.status_code == 200
    # Should render submit result fragment
    assert "submitted" in resp.text.lower() or "review" in resp.text.lower()


def test_draft_save_happy_path() -> None:
    client = _setup_app_with_mocks()
    db: Database = app.state.database  # type: ignore[assignment]

    async def _save_draft(  # type: ignore[no-untyped-def]
        user_id: int,
        name: str,
        inputs: FindingModelInputs,
        draft_id: str | None = None,
        generated_json: str | None = None,
    ):
        return FindingModelDraft(
            id="oid1234567890abcdef123456",
            user_id=user_id,
            name=name,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            inputs=inputs,
            generated_json=generated_json,
            status="draft",
            action_log=[],
        )

    db.draft_repo.save_draft = AsyncMock(side_effect=_save_draft)  # type: ignore[assignment]

    resp = client.post(
        "/api/finding-models/drafts/save",
        data={
            "session_id": "sid-123",
            "description": "A valid description that is long enough",
            "attributes_markdown": "# A heading\n\n### presence\n- present: yes\n- absent: no",
            "synonyms": '["a", "b"]',
        },
    )
    assert resp.status_code == 200
    assert "draft" in resp.text.lower() or "saved" in resp.text.lower()


def test_draft_save_invalid_id_returns_400() -> None:
    client = _setup_app_with_mocks()
    db: Database = app.state.database  # type: ignore[assignment]

    db.draft_repo.save_draft = AsyncMock()  # type: ignore[assignment]

    resp = client.post(
        "/api/finding-models/drafts/save",
        data={
            "session_id": "sid-123",
            "draft_id": "not-an-oid",
            "description": "A valid description that is long enough",
            "attributes_markdown": "# A heading\n\n### presence\n- present: yes\n- absent: no",
            "synonyms": "[]",
        },
    )
    assert resp.status_code == 400


def test_draft_save_locked_returns_409() -> None:
    # Prepare app with a session already submitted
    client = _setup_app_with_mocks()

    # Override cache get to indicate submitted draft status in session
    session_json = (
        '{"session_id":"sid-123","current_step":5,"name":"nodule","description":"desc","draft_status":"submitted"}'
    )
    app.state.cache.get = AsyncMock(return_value=session_json)  # type: ignore[attr-defined]

    resp = client.post(
        "/api/finding-models/drafts/save",
        data={
            "session_id": "sid-123",
            "description": "A valid description that is long enough",
            "attributes_markdown": "# A heading\n\n### presence\n- present: yes\n- absent: no",
            "synonyms": "[]",
        },
    )
    assert resp.status_code == 409


def test_draft_delete_happy_path() -> None:
    client = _setup_app_with_mocks()
    db: Database = app.state.database  # type: ignore[assignment]

    db.draft_repo.delete_draft = AsyncMock(return_value=True)  # type: ignore[assignment]

    resp = client.post(
        "/api/finding-models/drafts/oid1234567890abcdef123456/delete",
        data={"session_id": "sid-123"},
    )
    assert resp.status_code == 200
    assert "deleted" in resp.text.lower() or "success" in resp.text.lower()
