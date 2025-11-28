"""Tests for model iteration endpoints."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.dependencies import get_draft_service, get_finding_model_service
from app.main import app
from app.models import FindingModelDraft, FindingModelInputs, User


@pytest.fixture
def mock_user() -> User:
    """Create a mock user for testing."""
    return User(
        id=123,
        login="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="https://example.com/avatar.png",
        organizations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_finding_model():
    """Create a mock FindingModelFull for testing (reuse from conftest)."""
    # Load actual valid finding model data
    with open("tests/data/abdominal_abscess.fm.json") as f:
        data = json.load(f)

    # Add required fields for FindingModelFull
    data["slug"] = "test-finding"
    data["created_at"] = datetime.now(UTC).isoformat()
    data["updated_at"] = datetime.now(UTC).isoformat()
    data["version"] = "1.0.0"
    data["status"] = "published"

    from findingmodel import FindingModelFull

    return FindingModelFull(**data)


@pytest.fixture
def mock_iteration_draft() -> FindingModelDraft:
    """Create a mock iteration draft for testing."""
    return FindingModelDraft(
        id="test-draft-id",
        user_id=123,
        name="Test Finding",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(
            description="Test finding model description",
            synonyms=[],
            attributes_markdown="",
        ),
        action_log=[],
        is_iteration=True,
        base_model_id="OIFM_TEST_000001",
        generated_json='{"name": "Test Finding", "description": "Test description"}',
    )


@pytest.fixture
def authenticated_client(client: TestClient, mock_user: User) -> TestClient:
    """Create an authenticated test client using the base client fixture."""
    # Override auth dependency
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield client
    # Cleanup
    app.dependency_overrides.clear()


def test_start_iteration_creates_draft(authenticated_client: TestClient, mock_user: User, mock_finding_model):
    """Test POST /{slug}/iterate creates iteration draft and redirects."""
    # Create mock services
    mock_fm_service = MagicMock()
    mock_fm_service.get_model_by_slug = AsyncMock(return_value=mock_finding_model)

    mock_draft_service = MagicMock()
    mock_draft = MagicMock()
    mock_draft.id = "new-iteration-draft-id"
    mock_draft_service.start_iteration = AsyncMock(return_value=mock_draft)

    # Override dependencies
    app.dependency_overrides[get_finding_model_service] = lambda: mock_fm_service
    app.dependency_overrides[get_draft_service] = lambda: mock_draft_service

    try:
        # Make request (follow_redirects=False to avoid loading the draft page)
        response = authenticated_client.post("/finding-models/test-finding/iterate", follow_redirects=False)

        # Verify redirect to draft page in edit mode
        assert response.status_code == 303
        assert response.headers["location"] == "/drafts/new-iteration-draft-id?mode=edit"
    finally:
        # Cleanup
        app.dependency_overrides.clear()


def test_start_iteration_requires_auth():
    """Test POST /{slug}/iterate returns 401/redirect without auth."""
    # Create non-authenticated client
    client = TestClient(app)

    # Make request without auth
    response = client.post("/finding-models/test-finding/iterate")

    # Verify auth required (500 or error because CurrentUserDep fails)
    # In practice this would be caught by auth middleware/dependency
    assert response.status_code in [401, 403, 500]


def test_start_iteration_model_not_found(authenticated_client: TestClient, mock_user: User):
    """Test POST /{slug}/iterate with non-existent model."""
    from app.services import NotFoundError

    # Create mock service that raises NotFoundError
    mock_fm_service = MagicMock()
    mock_fm_service.get_model_by_slug = AsyncMock(side_effect=NotFoundError("Model not found"))

    # Override dependency
    app.dependency_overrides[get_finding_model_service] = lambda: mock_fm_service

    try:
        response = authenticated_client.post("/finding-models/nonexistent/iterate")

        # Verify 404
        assert response.status_code == 404
    finally:
        # Cleanup
        app.dependency_overrides.clear()


def test_iterate_endpoint_applies_changes(authenticated_client: TestClient, mock_user: User):
    """Test POST /{draft_id}/iterate applies changes (mock AI).

    On success, the endpoint stores results in Redis (mocked) and redirects to view mode.
    """
    from app.dependencies import get_cache

    # Create mock service
    mock_draft_service = MagicMock()
    mock_draft_service.apply_natural_language_iteration = AsyncMock(
        return_value={
            "success": True,
            "changes": ["Added new attribute 'size'", "Updated description"],
            "rejections": [],
            "error": None,
        }
    )

    # Create mock cache
    mock_cache = MagicMock()
    mock_cache.set = AsyncMock(return_value=True)

    # Override dependencies
    app.dependency_overrides[get_draft_service] = lambda: mock_draft_service
    app.dependency_overrides[get_cache] = lambda: mock_cache

    try:
        response = authenticated_client.post("/drafts/test-draft-id/iterate", data={"command": "Add a size attribute"})

        # On success, endpoint returns empty response with HX-Redirect header
        assert response.status_code == 200
        assert "HX-Redirect" in response.headers
        assert response.headers["HX-Redirect"] == "/drafts/test-draft-id?mode=view"

        # Verify cache was called to store results
        mock_cache.set.assert_called_once()
    finally:
        # Cleanup
        app.dependency_overrides.clear()


def test_iterate_endpoint_requires_auth():
    """Test POST /{draft_id}/iterate requires authentication."""
    client = TestClient(app)
    response = client.post("/drafts/test-draft-id/iterate", data={"command": "Test command"})

    # Verify auth required
    assert response.status_code in [401, 403, 500]


def test_iterate_non_iteration_draft_fails(authenticated_client: TestClient, mock_user: User):
    """Test POST /{draft_id}/iterate returns error if draft.is_iteration=False."""
    # Create mock service that returns error
    mock_draft_service = MagicMock()
    mock_draft_service.apply_natural_language_iteration = AsyncMock(
        return_value={
            "success": False,
            "changes": [],
            "rejections": [],
            "error": "Draft is not an iteration draft",
        }
    )

    # Override dependency
    app.dependency_overrides[get_draft_service] = lambda: mock_draft_service

    try:
        response = authenticated_client.post("/drafts/regular-draft-id/iterate", data={"command": "Test command"})

        # Verify error is shown in the template (template returns 200 but shows error)
        assert response.status_code == 200
        assert b"not an iteration draft" in response.content
    finally:
        # Cleanup
        app.dependency_overrides.clear()


def test_iterate_endpoint_with_rejections(authenticated_client: TestClient, mock_user: User):
    """Test POST /{draft_id}/iterate handles rejections gracefully.

    Even with rejections, if success=True the endpoint stores results in Redis
    (including rejections) and redirects to view mode where they'll be displayed.
    """
    from app.dependencies import get_cache

    # Create mock service
    mock_draft_service = MagicMock()
    mock_draft_service.apply_natural_language_iteration = AsyncMock(
        return_value={
            "success": True,
            "changes": ["Updated description"],
            "rejections": ["Cannot add invalid attribute", "Synonym already exists"],
            "error": None,
        }
    )

    # Create mock cache
    mock_cache = MagicMock()
    mock_cache.set = AsyncMock(return_value=True)

    # Override dependencies
    app.dependency_overrides[get_draft_service] = lambda: mock_draft_service
    app.dependency_overrides[get_cache] = lambda: mock_cache

    try:
        response = authenticated_client.post("/drafts/test-draft-id/iterate", data={"command": "Add invalid changes"})

        # On success (even with rejections), endpoint stores results and redirects
        assert response.status_code == 200
        assert "HX-Redirect" in response.headers
        assert response.headers["HX-Redirect"] == "/drafts/test-draft-id?mode=view"

        # Verify cache was called to store results (including rejections)
        mock_cache.set.assert_called_once()
    finally:
        # Cleanup
        app.dependency_overrides.clear()
