"""Test drafts router endpoints.

These tests verify the draft management functionality that includes
comment reporting endpoints added as part of the comments feature.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.dependencies import get_draft_service
from app.main import app
from app.models import User

# ===== DRAFT COMMENT REPORTING TESTS =====


def test_report_draft_comment_success(client: TestClient) -> None:
    """Test successfully report comment on draft."""
    # Mock draft service
    mock_draft_service = AsyncMock()
    mock_draft = MagicMock()
    mock_draft.id = "507f1f77bcf86cd799439011"
    mock_draft.status = "submitted"
    mock_draft_service.get_draft = AsyncMock(return_value=mock_draft)
    mock_draft_service.report_draft_comment = AsyncMock()

    # Mock current user
    now = datetime.now(UTC)
    mock_user = User(
        id=999999,
        login="test_user",
        name="Test User",
        email="test@example.com",
        avatar_url="https://example.com/avatar.jpg",
        organizations=[],
        created_at=now,
        updated_at=now,
    )

    # Override dependencies
    app.dependency_overrides[get_draft_service] = lambda: mock_draft_service
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # Make request
        response = client.post(
            "/drafts/507f1f77bcf86cd799439011/comments/comment123/report",
            headers={"HX-Request": "true"},  # Include for HTMX context
        )

        # Assertions
        assert response.status_code == 200
        assert "Reported" in response.text

        # Verify service calls
        mock_draft_service.get_draft.assert_called_once_with("507f1f77bcf86cd799439011", 999999)
        mock_draft_service.report_draft_comment.assert_called_once_with(
            "507f1f77bcf86cd799439011", "comment123", 999999
        )
    finally:
        app.dependency_overrides.clear()


def test_report_draft_comment_unauthenticated(client: TestClient) -> None:
    """Test unauthenticated user gets 401."""

    # Override get_current_user to raise authentication error
    def mock_get_current_user():
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Authentication required")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        response = client.post("/drafts/507f1f77bcf86cd799439011/comments/comment123/report")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_report_draft_comment_draft_not_found(client: TestClient) -> None:
    """Test invalid draft ID returns 404."""
    # Mock draft service to return None
    mock_draft_service = AsyncMock()
    mock_draft_service.get_draft = AsyncMock(return_value=None)

    # Mock current user
    now = datetime.now(UTC)
    mock_user = User(
        id=999999,
        login="test_user",
        name="Test User",
        email="test@example.com",
        avatar_url="https://example.com/avatar.jpg",
        organizations=[],
        created_at=now,
        updated_at=now,
    )

    app.dependency_overrides[get_draft_service] = lambda: mock_draft_service
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        response = client.post("/drafts/507f1f77bcf86cd799439011/comments/comment123/report")
        assert response.status_code == 404
        assert "Draft not found" in response.text
    finally:
        app.dependency_overrides.clear()


def test_report_draft_comment_no_thread(client: TestClient) -> None:
    """Test no comment thread returns 404."""
    # Mock draft service with valid draft
    mock_draft_service = AsyncMock()
    mock_draft = MagicMock()
    mock_draft.id = "507f1f77bcf86cd799439011"
    mock_draft.status = "submitted"
    mock_draft_service.get_draft = AsyncMock(return_value=mock_draft)

    # Mock comment repo to return None for thread
    mock_comment_repo = AsyncMock()
    mock_comment_repo.get_thread = AsyncMock(return_value=None)

    # Mock current user
    now = datetime.now(UTC)
    mock_user = User(
        id=999999,
        login="test_user",
        name="Test User",
        email="test@example.com",
        avatar_url="https://example.com/avatar.jpg",
        organizations=[],
        created_at=now,
        updated_at=now,
    )

    app.dependency_overrides[get_draft_service] = lambda: mock_draft_service
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        mock_draft_service.report_draft_comment.side_effect = HTTPException(404, "No comments found")
        response = client.post("/drafts/507f1f77bcf86cd799439011/comments/comment123/report")
        assert response.status_code == 404
        assert "No comments found" in response.text
    finally:
        app.dependency_overrides.clear()


def test_report_draft_comment_already_reported(client: TestClient) -> None:
    """Test already reported comment returns 400."""
    # Mock draft service
    mock_draft_service = AsyncMock()
    mock_draft = MagicMock()
    mock_draft.id = "507f1f77bcf86cd799439011"
    mock_draft.status = "submitted"
    mock_draft_service.get_draft = AsyncMock(return_value=mock_draft)

    # Mock comment repo - report_comment returns False (already reported)
    mock_comment_repo = AsyncMock()
    mock_thread = MagicMock()
    mock_thread.id = "thread123"
    mock_comment_repo.get_thread = AsyncMock(return_value=mock_thread)
    mock_comment_repo.report_comment = AsyncMock(return_value=False)

    # Mock current user
    now = datetime.now(UTC)
    mock_user = User(
        id=999999,
        login="test_user",
        name="Test User",
        email="test@example.com",
        avatar_url="https://example.com/avatar.jpg",
        organizations=[],
        created_at=now,
        updated_at=now,
    )

    app.dependency_overrides[get_draft_service] = lambda: mock_draft_service
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        mock_draft_service.report_draft_comment.side_effect = HTTPException(400, "Already reported")
        response = client.post("/drafts/507f1f77bcf86cd799439011/comments/comment123/report")
        assert response.status_code == 400
        assert "Already reported" in response.text
    finally:
        app.dependency_overrides.clear()
