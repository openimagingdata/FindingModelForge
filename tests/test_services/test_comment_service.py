"""Unit tests for CommentService."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.database import CommentRepo, DraftRepo, UserRepo
from app.models import Comment, CommentThread, DraftStatus, User, UserCommentEntry
from app.services.comment_service import CommentService


@pytest.fixture
def mock_comment_repo() -> MagicMock:
    repo = MagicMock(spec=CommentRepo)
    repo.get_thread = AsyncMock()
    repo.add_comment = AsyncMock()
    repo.add_reply = AsyncMock(return_value=True)
    repo.report_comment = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_user_repo() -> MagicMock:
    repo = MagicMock(spec=UserRepo)
    repo.add_comment_to_index = AsyncMock()
    return repo


@pytest.fixture
def mock_draft_repo() -> MagicMock:
    repo = MagicMock(spec=DraftRepo)
    repo.get_draft = AsyncMock()
    return repo


@pytest.fixture
def service(mock_comment_repo: MagicMock, mock_user_repo: MagicMock, mock_draft_repo: MagicMock) -> CommentService:
    return CommentService(
        comment_repo=mock_comment_repo,
        user_repo=mock_user_repo,
        draft_repo=mock_draft_repo,
    )


@pytest.fixture
def user() -> User:
    now = datetime.now(UTC)
    return User(
        id=123,
        login="tester",
        name="Tester",
        email="tester@example.com",
        avatar_url="https://example.com/avatar.png",
        html_url=None,
        organizations=[],
        created_at=now,
        updated_at=now,
        comment_index=[],
    )


def _thread(reference_type: str, reference_id: str, comments: list[Comment]) -> CommentThread:
    now = datetime.now(UTC)
    return CommentThread(
        id="thread-id",
        reference_type=reference_type,
        reference_id=reference_id,
        created_at=now,
        updated_at=now,
        comments=comments,
    )


@pytest.mark.asyncio
async def test_get_thread_returns_repo_result(service: CommentService, mock_comment_repo: MagicMock) -> None:
    thread = _thread("draft", "draft-1", [])
    mock_comment_repo.get_thread.return_value = thread

    result = await service.get_thread("draft", "draft-1")

    mock_comment_repo.get_thread.assert_awaited_once_with("draft", "draft-1")
    assert result is thread


@pytest.mark.asyncio
async def test_add_comment_top_level_draft_success(
    service: CommentService,
    mock_comment_repo: MagicMock,
    mock_user_repo: MagicMock,
    mock_draft_repo: MagicMock,
    user: User,
) -> None:
    mock_draft_repo.get_draft.return_value = SimpleNamespace(status=DraftStatus.PUBLIC, name="Public Draft")
    mock_comment_repo.add_comment.return_value = _thread("draft", "d1", [])

    with patch("app.services.comment_service.get_blacklist_user_ids", return_value=[]):
        comment = await service.add_comment("draft", "d1", user, "Valid content")

    mock_draft_repo.get_draft.assert_awaited_once_with("d1")
    mock_comment_repo.add_comment.assert_awaited_once()
    args = mock_comment_repo.add_comment.await_args.args
    assert args[0] == "draft"
    assert args[1] == "d1"
    assert isinstance(args[2], Comment)

    mock_user_repo.add_comment_to_index.assert_awaited_once()
    index_args = mock_user_repo.add_comment_to_index.await_args.args
    assert index_args[0] == user.id
    entry = index_args[1]
    assert isinstance(entry, UserCommentEntry)
    assert entry.reference_type == "draft"
    assert entry.reference_id == "d1"
    assert entry.finding_name == "Public Draft"
    assert comment.user_id == user.id


@pytest.mark.asyncio
async def test_add_comment_reply_success(
    service: CommentService,
    mock_comment_repo: MagicMock,
    mock_draft_repo: MagicMock,
    user: User,
) -> None:
    comment_parent = Comment(
        user_id=999,
        user_name="other",
        content="Parent",
        created_at=datetime.now(UTC),
    )
    thread = _thread("draft", "d1", [comment_parent])
    mock_draft_repo.get_draft.return_value = SimpleNamespace(status=DraftStatus.PUBLIC, name="Draft")
    mock_comment_repo.get_thread.return_value = thread

    with patch("app.services.comment_service.get_blacklist_user_ids", return_value=[]):
        await service.add_comment("draft", "d1", user, "Reply", parent_id=comment_parent.id)

    mock_comment_repo.add_reply.assert_awaited_once()
    args = mock_comment_repo.add_reply.await_args.args
    assert args[0] == thread.id
    assert args[1] == comment_parent.id
    assert isinstance(args[2], Comment)


@pytest.mark.asyncio
async def test_add_comment_reply_missing_thread_raises(
    service: CommentService,
    mock_comment_repo: MagicMock,
    mock_draft_repo: MagicMock,
    user: User,
) -> None:
    mock_draft_repo.get_draft.return_value = SimpleNamespace(status=DraftStatus.PUBLIC, name="Draft")
    mock_comment_repo.get_thread.return_value = None

    with (
        patch("app.services.comment_service.get_blacklist_user_ids", return_value=[]),
        pytest.raises(HTTPException, match="Parent comment not found") as exc,
    ):
        await service.add_comment("draft", "d1", user, "Reply", parent_id="parent")

    assert exc.value.status_code == 404
    mock_comment_repo.add_reply.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_comment_reply_addition_failure(
    service: CommentService,
    mock_comment_repo: MagicMock,
    mock_draft_repo: MagicMock,
    user: User,
) -> None:
    parent = Comment(
        user_id=1,
        user_name="parent",
        content="Parent",
        created_at=datetime.now(UTC),
    )
    mock_draft_repo.get_draft.return_value = SimpleNamespace(status=DraftStatus.PUBLIC, name="Draft")
    mock_comment_repo.get_thread.return_value = _thread("draft", "d1", [parent])
    mock_comment_repo.add_reply.return_value = False

    with (
        patch("app.services.comment_service.get_blacklist_user_ids", return_value=[]),
        pytest.raises(HTTPException, match="Unable to add reply") as exc,
    ):
        await service.add_comment("draft", "d1", user, "Reply", parent_id=parent.id)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_add_comment_draft_status_forbidden(
    service: CommentService,
    mock_draft_repo: MagicMock,
    user: User,
) -> None:
    mock_draft_repo.get_draft.return_value = SimpleNamespace(status=DraftStatus.DRAFT, name="Draft")

    with pytest.raises(HTTPException, match="Comments are only allowed") as exc:
        await service.add_comment("draft", "d1", user, "content")

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_add_comment_blacklisted_user(service: CommentService, mock_draft_repo: MagicMock, user: User) -> None:
    mock_draft_repo.get_draft.return_value = SimpleNamespace(status=DraftStatus.PUBLIC, name="Draft")

    with (
        patch("app.services.comment_service.get_blacklist_user_ids", return_value=[user.id]),
        pytest.raises(HTTPException) as exc,
    ):
        await service.add_comment("draft", "d1", user, "content")

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_add_comment_rate_limited(service: CommentService, mock_draft_repo: MagicMock, user: User) -> None:
    now = datetime.now(UTC)
    user.comment_index = [
        UserCommentEntry(
            reference_type="draft",
            reference_id="d1",
            finding_name="Draft",
            comment_id=f"c{i}",
            created_at=now - timedelta(seconds=10),
        )
        for i in range(3)
    ]
    mock_draft_repo.get_draft.return_value = MagicMock(status=DraftStatus.PUBLIC, name="Draft")

    with (
        patch("app.services.comment_service.get_blacklist_user_ids", return_value=[]),
        pytest.raises(HTTPException) as exc,
    ):
        await service.add_comment("draft", "d1", user, "content")

    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_add_comment_invalid_content(service: CommentService, mock_draft_repo: MagicMock, user: User) -> None:
    """Test that invalid content raises ValidationError from Pydantic model.

    Note: Length validation now happens at API boundary (FastAPI Form constraints),
    but the Pydantic Comment model also validates on creation.
    """
    mock_draft_repo.get_draft.return_value = MagicMock(status=DraftStatus.PUBLIC, name="Draft")

    # Pydantic ValidationError is raised when Comment model rejects empty content
    from pydantic import ValidationError

    with (
        patch("app.services.comment_service.get_blacklist_user_ids", return_value=[]),
        pytest.raises(ValidationError) as exc,
    ):
        await service.add_comment("draft", "d1", user, " ")

    # Verify it's a content validation error
    assert "content" in str(exc.value)


@pytest.mark.asyncio
async def test_add_comment_finding_model_success(
    service: CommentService,
    mock_comment_repo: MagicMock,
    mock_user_repo: MagicMock,
    user: User,
) -> None:
    mock_comment_repo.add_comment.return_value = _thread("finding_model", "fm-1", [])

    with patch("app.services.comment_service.get_blacklist_user_ids", return_value=[]):
        await service.add_comment("finding_model", "fm-1", user, "Content", reference_name="Model Name")

    mock_comment_repo.add_comment.assert_awaited_once()
    args = mock_comment_repo.add_comment.await_args.args
    assert args[0] == "finding_model"
    assert args[1] == "fm-1"

    entry = mock_user_repo.add_comment_to_index.await_args.args[1]
    assert entry.finding_name == "Model Name"


@pytest.mark.asyncio
async def test_add_comment_finding_model_name_fallback(
    service: CommentService,
    mock_comment_repo: MagicMock,
    mock_user_repo: MagicMock,
    user: User,
) -> None:
    mock_comment_repo.add_comment.return_value = _thread("finding_model", "fm-1", [])

    with patch("app.services.comment_service.get_blacklist_user_ids", return_value=[]):
        await service.add_comment("finding_model", "fm-1", user, "Content")

    entry = mock_user_repo.add_comment_to_index.await_args.args[1]
    assert entry.finding_name == "fm-1"


@pytest.mark.asyncio
async def test_report_comment_success(service: CommentService, mock_comment_repo: MagicMock) -> None:
    comment = Comment(
        user_id=1,
        user_name="author",
        content="comment",
        created_at=datetime.now(UTC),
    )
    thread = _thread("finding_model", "fm-1", [comment])
    mock_comment_repo.get_thread.return_value = thread

    await service.report_comment("finding_model", "fm-1", comment.id, 999)

    mock_comment_repo.report_comment.assert_awaited_once_with(thread.id, comment.id, 999)


@pytest.mark.asyncio
async def test_report_comment_duplicate_raise(service: CommentService, mock_comment_repo: MagicMock) -> None:
    comment = Comment(
        user_id=1,
        user_name="author",
        content="comment",
        created_at=datetime.now(UTC),
        reported=True,
        reported_by=999,
        reported_at=datetime.now(UTC),
    )
    thread = _thread("finding_model", "fm-1", [comment])
    mock_comment_repo.get_thread.return_value = thread

    with pytest.raises(HTTPException) as exc:
        await service.report_comment("finding_model", "fm-1", comment.id, 999)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_report_comment_missing_thread(service: CommentService, mock_comment_repo: MagicMock) -> None:
    mock_comment_repo.get_thread.return_value = None

    with pytest.raises(HTTPException) as exc:
        await service.report_comment("draft", "d1", "c1", 1)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_report_comment_not_found(service: CommentService, mock_comment_repo: MagicMock) -> None:
    comment = Comment(
        user_id=1,
        user_name="author",
        content="comment",
        created_at=datetime.now(UTC),
    )
    thread = _thread("finding_model", "fm-1", [comment])
    mock_comment_repo.get_thread.return_value = thread
    mock_comment_repo.report_comment.return_value = False

    with pytest.raises(HTTPException) as exc:
        await service.report_comment("finding_model", "fm-1", "missing", 1)

    assert exc.value.status_code == 404
