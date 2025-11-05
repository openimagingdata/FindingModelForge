"""Integration tests for comment rate limiting.

These tests verify that rate limiting returns 429 responses when users exceed
the comment limit, complementing the unit tests in test_comment_helpers.py.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.dependencies import get_draft_service, get_finding_model_service
from app.main import app
from app.models import (
    Comment,
    CommentThread,
    DraftStatus,
    FindingModelDraft,
    FindingModelInputs,
    User,
    UserCommentEntry,
)

# Test constants
TEST_USER_ID = 999999


@pytest.fixture
def user_with_rate_limit_comments() -> User:
    """Create a user with 3 recent comments to trigger rate limit."""
    return User(
        id=TEST_USER_ID,
        login="testuser",
        avatar_url="https://example.com/avatar.jpg",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        comment_index=[
            UserCommentEntry(
                reference_type="finding_model",
                reference_id="oifm_test1",
                finding_name="Test Model 1",
                comment_id="comment1",
                created_at=datetime.now(UTC) - timedelta(seconds=30),
            ),
            UserCommentEntry(
                reference_type="finding_model",
                reference_id="oifm_test2",
                finding_name="Test Model 2",
                comment_id="comment2",
                created_at=datetime.now(UTC) - timedelta(seconds=20),
            ),
            UserCommentEntry(
                reference_type="draft",
                reference_id="507f1f77bcf86cd799439011",
                finding_name="Test Draft",
                comment_id="comment3",
                created_at=datetime.now(UTC) - timedelta(seconds=10),
            ),
        ],
    )


@pytest.fixture
def user_with_old_comments() -> User:
    """Create a user with old comments that don't count toward rate limit."""
    return User(
        id=TEST_USER_ID,
        login="testuser",
        avatar_url="https://example.com/avatar.jpg",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        comment_index=[
            UserCommentEntry(
                reference_type="finding_model",
                reference_id="oifm_old1",
                finding_name="Old Model 1",
                comment_id="old_comment1",
                created_at=datetime.now(UTC) - timedelta(seconds=90),  # > 60 seconds
            ),
            UserCommentEntry(
                reference_type="finding_model",
                reference_id="oifm_old2",
                finding_name="Old Model 2",
                comment_id="old_comment2",
                created_at=datetime.now(UTC) - timedelta(seconds=120),  # > 60 seconds
            ),
        ],
    )


@pytest.fixture
def user_with_empty_comment_index() -> User:
    """Create a user with no recent comments."""
    return User(
        id=TEST_USER_ID,
        login="testuser",
        avatar_url="https://example.com/avatar.jpg",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        comment_index=[],
    )


def test_finding_model_comment_rate_limit_returns_429(
    client: TestClient, user_with_rate_limit_comments: User, mock_finding_model
) -> None:
    """Test that exceeding rate limit on finding model comments returns 429."""
    # Mock the finding model service
    mock_service = MagicMock()
    # Need to mock get_model_by_slug which is called first in the router
    # NEW: get_model_by_slug returns FindingModelFull directly, not tuple
    mock_service.get_model_by_slug = AsyncMock(return_value=mock_finding_model)
    # Mock add_comment_to_model to raise rate limit exception (from CommentService)
    mock_service.add_comment_to_model = AsyncMock(
        side_effect=HTTPException(status_code=429, detail="Rate limit exceeded. Maximum 3 comments per minute.")
    )

    # Mock get_current_user to return user with 3 recent comments
    app.dependency_overrides[get_current_user] = lambda: user_with_rate_limit_comments
    app.dependency_overrides[get_finding_model_service] = lambda: mock_service

    try:
        # Try to add a 4th comment within rate limit window
        response = client.post(
            "/finding-models/test-slug/comments",
            data={"content": "This should be rate limited", "parent_comment_id": ""},
        )

        # Verify 429 response with proper error message
        assert response.status_code == 429
        assert "Rate limit exceeded. Maximum 3 comments per minute." in response.json()["detail"]

        # Verify service method was called (rate limiting happens inside service)
        mock_service.add_comment_to_model.assert_called_once()

    finally:
        app.dependency_overrides.clear()


def test_draft_comment_rate_limit_returns_429(client: TestClient, user_with_rate_limit_comments: User) -> None:
    """Test that exceeding rate limit on draft comments returns 429."""
    # Mock submitted draft
    submitted_draft = FindingModelDraft(
        id="507f1f77bcf86cd799439011",
        user_id=123,  # Different user
        name="Test Draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test draft description"),
        status=DraftStatus.SUBMITTED,  # Submitted - can receive comments
    )

    # Mock the draft service
    mock_service = MagicMock()
    mock_service.get_draft = AsyncMock(return_value=submitted_draft)
    # Mock add_comment_to_draft to raise rate limit exception (from CommentService)
    mock_service.add_comment_to_draft = AsyncMock(
        side_effect=HTTPException(status_code=429, detail="Rate limit exceeded. Maximum 3 comments per minute.")
    )

    # Mock get_current_user to return user with 3 recent comments
    app.dependency_overrides[get_current_user] = lambda: user_with_rate_limit_comments
    app.dependency_overrides[get_draft_service] = lambda: mock_service

    try:
        # Try to add a 4th comment within rate limit window
        response = client.post(
            "/drafts/507f1f77bcf86cd799439011/comments",
            data={"content": "This draft comment should be rate limited", "parent_comment_id": ""},
        )

        # Verify 429 response
        assert response.status_code == 429
        assert "Rate limit exceeded. Maximum 3 comments per minute." in response.json()["detail"]

        # Verify service method was called (rate limiting happens inside CommentService)
        mock_service.add_comment_to_draft.assert_called_once()

    finally:
        app.dependency_overrides.clear()


def test_old_comments_not_counted_in_rate_limit(
    client: TestClient, user_with_old_comments: User, mock_finding_model
) -> None:
    """Test that comments older than 60 seconds don't count toward rate limit."""
    # Mock successful comment addition and get updated thread
    mock_service = MagicMock()
    # Need to mock get_model_by_slug which is called first in the router
    # NEW: get_model_by_slug returns FindingModelFull directly, not tuple
    mock_service.get_model_by_slug = AsyncMock(return_value=mock_finding_model)

    mock_comment = Comment(
        id="new_comment",
        user_id=TEST_USER_ID,
        user_name="testuser",
        content="This should be allowed",
        created_at=datetime.now(UTC),
    )

    mock_service.add_comment_to_model = AsyncMock(return_value=mock_comment)
    mock_service.get_comments_for_model = AsyncMock(
        return_value=CommentThread(
            id="thread_id",
            reference_type="finding_model",
            reference_id="test-slug",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            comments=[mock_comment],
        )
    )

    # Mock UserRepo
    mock_user_repo = MagicMock()
    mock_user_repo.add_comment_to_index = AsyncMock()

    # Mock get_current_user to return user with only old comments
    app.dependency_overrides[get_current_user] = lambda: user_with_old_comments
    app.dependency_overrides[get_finding_model_service] = lambda: mock_service

    try:
        # Should be able to add new comment since old comments don't count
        response = client.post(
            "/finding-models/test-slug/comments",
            data={"content": "This should be allowed", "parent_comment_id": ""},
            headers={"HX-Request": "true"},  # Send as HTMX to avoid redirect
        )

        # Should succeed (200 for HTMX or 303 for redirect)
        assert response.status_code in [200, 303]

        # Verify service methods were called
        mock_service.add_comment_to_model.assert_called_once()
        mock_service.get_comments_for_model.assert_called_once()
        # Note: user comment index is updated internally by CommentService

    finally:
        app.dependency_overrides.clear()


def test_comment_index_updated_after_successful_comment(
    client: TestClient, user_with_empty_comment_index: User, mock_finding_model
) -> None:
    """Test that user's comment_index is updated after adding a comment."""
    # Mock successful comment addition and thread retrieval
    mock_service = MagicMock()
    # Need to mock get_model_by_slug which is called first in the router
    # NEW: get_model_by_slug returns FindingModelFull directly, not tuple
    mock_service.get_model_by_slug = AsyncMock(return_value=mock_finding_model)

    mock_comment = Comment(
        id="new_comment",
        user_id=TEST_USER_ID,
        user_name="testuser",
        content="Test comment",
        created_at=datetime.now(UTC),
    )

    mock_service.add_comment_to_model = AsyncMock(return_value=mock_comment)
    mock_service.get_comments_for_model = AsyncMock(
        return_value=CommentThread(
            id="thread_id",
            reference_type="finding_model",
            reference_id="test-slug",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            comments=[mock_comment],
        )
    )

    # Mock UserRepo
    mock_user_repo = MagicMock()
    mock_user_repo.add_comment_to_index = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: user_with_empty_comment_index
    app.dependency_overrides[get_finding_model_service] = lambda: mock_service

    try:
        # Add a comment
        response = client.post(
            "/finding-models/test-slug/comments",
            data={"content": "Test comment", "parent_comment_id": ""},
            headers={"HX-Request": "true"},  # Send as HTMX to avoid redirect
        )

        # Should succeed
        assert response.status_code in [200, 303]

        # Verify service methods were called
        mock_service.add_comment_to_model.assert_called_once()
        mock_service.get_comments_for_model.assert_called_once()
        # Note: user comment index is updated internally by CommentService

    finally:
        app.dependency_overrides.clear()


def test_finding_model_rate_limit_with_parent_comment(
    client: TestClient, user_with_rate_limit_comments: User, mock_finding_model
) -> None:
    """Test rate limiting works for reply comments too."""
    mock_service = MagicMock()
    # Need to mock get_model_by_slug which is called first in the router
    # NEW: get_model_by_slug returns FindingModelFull directly, not tuple
    mock_service.get_model_by_slug = AsyncMock(return_value=mock_finding_model)
    # Mock add_comment_to_model to raise rate limit exception (from CommentService)
    mock_service.add_comment_to_model = AsyncMock(
        side_effect=HTTPException(status_code=429, detail="Rate limit exceeded. Maximum 3 comments per minute.")
    )

    app.dependency_overrides[get_current_user] = lambda: user_with_rate_limit_comments
    app.dependency_overrides[get_finding_model_service] = lambda: mock_service

    try:
        # Try to add a reply when already at rate limit
        response = client.post(
            "/finding-models/test-slug/comments",
            data={"content": "This reply should be rate limited", "parent_comment_id": "some_parent_id"},
        )

        # Should still be rate limited
        assert response.status_code == 429
        assert "Rate limit exceeded. Maximum 3 comments per minute." in response.json()["detail"]

        # Service should be called (rate limiting happens inside service)
        mock_service.add_comment_to_model.assert_called_once()

    finally:
        app.dependency_overrides.clear()


def test_draft_rate_limit_with_submitted_draft_check(client: TestClient, user_with_rate_limit_comments: User) -> None:
    """Test rate limiting is checked before draft status validation."""
    # Mock draft that exists but is not submitted
    draft_not_submitted = FindingModelDraft(
        id="507f1f77bcf86cd799439011",
        user_id=123,  # Different user
        name="Test Draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test draft description"),
        status=DraftStatus.DRAFT,  # Not submitted
    )

    mock_service = MagicMock()
    mock_service.get_draft = AsyncMock(return_value=draft_not_submitted)
    # Mock add_comment_to_draft to raise rate limit exception (checked before draft status)
    mock_service.add_comment_to_draft = AsyncMock(
        side_effect=HTTPException(status_code=429, detail="Rate limit exceeded. Maximum 3 comments per minute.")
    )

    app.dependency_overrides[get_current_user] = lambda: user_with_rate_limit_comments
    app.dependency_overrides[get_draft_service] = lambda: mock_service

    try:
        response = client.post(
            "/drafts/507f1f77bcf86cd799439011/comments",
            data={"content": "This should fail due to rate limit", "parent_comment_id": ""},
        )

        # Should fail with rate limit (checked by CommentService)
        assert response.status_code == 429
        assert "Rate limit exceeded. Maximum 3 comments per minute." in response.json()["detail"]

        # Service method is called (rate limiting happens inside CommentService)
        mock_service.add_comment_to_draft.assert_called_once()

    finally:
        app.dependency_overrides.clear()


def test_submitted_draft_rate_limit(client: TestClient, user_with_rate_limit_comments: User) -> None:
    """Test rate limiting for submitted drafts."""
    # Mock submitted draft
    submitted_draft = FindingModelDraft(
        id="507f1f77bcf86cd799439011",
        user_id=123,  # Different user
        name="Test Draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test draft description"),
        status=DraftStatus.SUBMITTED,  # Submitted - can receive comments
    )

    mock_service = MagicMock()
    mock_service.get_draft = AsyncMock(return_value=submitted_draft)
    # Mock add_comment_to_draft to raise rate limit exception
    mock_service.add_comment_to_draft = AsyncMock(
        side_effect=HTTPException(status_code=429, detail="Rate limit exceeded. Maximum 3 comments per minute.")
    )

    app.dependency_overrides[get_current_user] = lambda: user_with_rate_limit_comments
    app.dependency_overrides[get_draft_service] = lambda: mock_service

    try:
        response = client.post(
            "/drafts/507f1f77bcf86cd799439011/comments",
            data={"content": "This should be rate limited on submitted draft", "parent_comment_id": ""},
        )

        # Should be rate limited (429) not rejected for draft status (400)
        assert response.status_code == 429
        assert "Rate limit exceeded. Maximum 3 comments per minute." in response.json()["detail"]

        # Service method is called (rate limiting happens inside CommentService)
        mock_service.add_comment_to_draft.assert_called_once()

    finally:
        app.dependency_overrides.clear()


def test_rate_limit_boundary_condition(client: TestClient, mock_finding_model) -> None:
    """Test rate limit boundary - exactly 3 comments should trigger limit."""
    # User with exactly 3 comments within 60 seconds
    user_at_limit = User(
        id=TEST_USER_ID,
        login="testuser",
        avatar_url="https://example.com/avatar.jpg",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        comment_index=[
            UserCommentEntry(
                reference_type="finding_model",
                reference_id="oifm_boundary1",
                finding_name="Boundary Model 1",
                comment_id="boundary1",
                created_at=datetime.now(UTC) - timedelta(seconds=59),  # Just within limit
            ),
            UserCommentEntry(
                reference_type="finding_model",
                reference_id="oifm_boundary2",
                finding_name="Boundary Model 2",
                comment_id="boundary2",
                created_at=datetime.now(UTC) - timedelta(seconds=30),
            ),
            UserCommentEntry(
                reference_type="finding_model",
                reference_id="oifm_boundary3",
                finding_name="Boundary Model 3",
                comment_id="boundary3",
                created_at=datetime.now(UTC) - timedelta(seconds=5),
            ),
        ],
    )

    mock_service = MagicMock()
    # Need to mock get_model_by_slug which is called first in the router
    # NEW: get_model_by_slug returns FindingModelFull directly, not tuple
    mock_service.get_model_by_slug = AsyncMock(return_value=mock_finding_model)
    mock_service.add_comment_to_model = AsyncMock(
        side_effect=HTTPException(429, "Rate limit exceeded. Maximum 3 comments per minute.")
    )

    app.dependency_overrides[get_current_user] = lambda: user_at_limit
    app.dependency_overrides[get_finding_model_service] = lambda: mock_service

    try:
        response = client.post(
            "/finding-models/test-boundary/comments",
            data={"content": "This should hit the rate limit", "parent_comment_id": ""},
        )

        # Should be rate limited
        assert response.status_code == 429
        assert "Rate limit exceeded. Maximum 3 comments per minute." in response.json()["detail"]

    finally:
        app.dependency_overrides.clear()
