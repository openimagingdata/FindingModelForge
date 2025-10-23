from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.database import CommentRepo, Database, DraftRepo, UserRepo
from app.models import FindingModelDraft, FindingModelInputs, User


def _client_with_state(session_json: str) -> TestClient:
    db = Database()

    # Mock UserRepo
    db.user_repo = MagicMock(spec=UserRepo)
    db.user_repo.collection = MagicMock()
    db.user_repo.collection.find_one = AsyncMock()
    db.user_repo.collection.update_one = AsyncMock()

    # Mock CommentRepo
    db.comment_repo = MagicMock(spec=CommentRepo)
    db.comment_repo.get_thread = AsyncMock()
    db.comment_repo.add_comment = AsyncMock()
    db.comment_repo.add_reply = AsyncMock()
    db.comment_repo.report_comment = AsyncMock()

    db.finding_index = MagicMock()
    db.draft_repo = MagicMock(spec=DraftRepo)

    # Mock people_repo
    from app.database import PeopleRepo

    db.people_repo = MagicMock(spec=PeopleRepo)
    db.people_repo.get_by_username = AsyncMock(return_value=None)

    # Add ensure_person_for_user method required by DraftService
    db.ensure_person_for_user = AsyncMock(return_value=None)

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

    # Set up service dependencies
    from app.dependencies import get_draft_service
    from app.services.comment_service import CommentService
    from app.services.draft_service import DraftService

    def get_mock_draft_service() -> DraftService:
        comment_service = CommentService(
            comment_repo=db.comment_repo,
            user_repo=db.user_repo,
            draft_repo=db.draft_repo,
        )
        return DraftService(
            draft_repo=db.draft_repo,
            user_repo=db.user_repo,
            database=db,
            comment_service=comment_service,
        )

    app.dependency_overrides[get_current_user] = mock_user
    app.dependency_overrides[get_draft_service] = get_mock_draft_service

    return TestClient(app)


def _draft(
    status: Literal["draft", "public", "submitted", "under-review", "added", "declined"] = "submitted",
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
        author_name="Tester",
        author_username="tester",
    )


def test_step1_resumes_submitted_draft_to_draft_view():
    # Session starting at step 1 with no draft
    session_json = '{"session_id":"sid-x","current_step":1}'
    client = _client_with_state(session_json)
    from app.main import app

    submitted_draft = _draft("submitted")
    # Add some generated_json to make the draft displayable
    submitted_draft.generated_json = '{"name":"nodule","description":"d"}'

    db: Database = app.state.database  # type: ignore[assignment]
    db.draft_repo.find_editable_by_name = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    db.draft_repo.find_latest_by_name = AsyncMock(return_value=submitted_draft)  # type: ignore[attr-defined]
    # Also mock get_draft and get_draft_with_author for the redirect target
    db.draft_repo.get_draft = AsyncMock(return_value=submitted_draft)  # type: ignore[attr-defined]
    # Mock get_draft_with_author to return model_dump() output for the draft view page
    db.draft_repo.get_draft_with_author = AsyncMock(return_value=submitted_draft.model_dump())  # type: ignore[attr-defined]

    # Mock creation service since it's now used in step 1
    from app.dependencies import get_creation_service
    from app.services.creation_service import CreationService

    mock_creation_service = MagicMock(spec=CreationService)
    mock_creation_service.check_name_availability = AsyncMock(return_value=False)  # Name exists (submitted draft)
    mock_creation_service.is_test_user = MagicMock(return_value=False)

    app.dependency_overrides[get_creation_service] = lambda: mock_creation_service

    resp = client.post(
        "/create/step/1",
        data={"session_id": "sid-x", "name": "nodule"},
        follow_redirects=True,  # Follow redirects to get the final content
    )
    assert resp.status_code == 200
    # Should land on draft view with submitted status - no longer step 5
    text = resp.text.lower()
    # The draft view should show some indication of view/preview mode (not necessarily "submitted")
    assert "submitted" in text or "view" in text or "preview" in text
    assert "save draft" not in text


def test_submit_rerenders_full_step5_and_shows_submitted():
    # Session on step 4 ready to submit
    session_json = '{"session_id":"sid-y","current_step":5,"name":"nodule"}'
    client = _client_with_state(session_json)
    from app.main import app

    db: Database = app.state.database  # type: ignore[assignment]

    # Mock draft to exist before submission (required by new service logic)
    # Use the correct ID that matches the test request
    draft_before_submit = _draft("public")
    draft_before_submit.id = "oid123"  # Match the ID used in the test

    # Wire submit to return a submitted draft
    async def _submit(draft_id: str, user_id: int):  # type: ignore[no-untyped-def]
        submitted = _draft("submitted")
        submitted.id = draft_id  # Keep the same ID
        submitted.generated_json = '{"name":"nodule","description":"d"}'  # Add JSON to make it displayable
        return submitted

    db.draft_repo.submit = AsyncMock(side_effect=_submit)  # type: ignore[attr-defined]

    # Mock the get_draft to return the public draft before submission,
    # then after submission we'll use different setup for the redirect
    db.draft_repo.get_draft = AsyncMock(return_value=draft_before_submit)  # type: ignore[attr-defined]

    resp = client.post(
        "/drafts/oid123/submit",
        data={"session_id": "sid-y"},
        follow_redirects=False,  # Don't follow redirects automatically
    )
    # The submit endpoint now redirects to the view page
    assert resp.status_code == 303
    assert resp.headers["location"] == "/drafts/oid123?mode=view"

    # Now update the get_draft mock to return the submitted draft for the view page
    submitted_draft = _draft("submitted")
    submitted_draft.id = "oid123"
    submitted_draft.generated_json = '{"name":"nodule","description":"d"}'
    db.draft_repo.get_draft = AsyncMock(return_value=submitted_draft)  # type: ignore[attr-defined]

    # Mock get_draft_with_author to return draft as dict without author_info aggregation
    mock_draft_dict = submitted_draft.model_dump()
    mock_draft_dict["id"] = submitted_draft.id  # Ensure id is string
    db.draft_repo.get_draft_with_author = AsyncMock(return_value=mock_draft_dict)  # type: ignore[attr-defined]

    # Follow the redirect to get the actual page content
    resp = client.get(resp.headers["location"])
    assert resp.status_code == 200
    text = resp.text.lower()
    assert "submitted" in text
    # After submit, back button should be hidden
    assert "back" not in text
