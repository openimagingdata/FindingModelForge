"""Test page routes."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def test_index_page(client: TestClient) -> None:
    """Test index page loads correctly."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Finding Model Forge" in response.text


def test_login_page(client: TestClient) -> None:
    """Test login page loads correctly."""
    response = client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Sign in to your account" in response.text


def test_profile_page_requires_auth(client: TestClient) -> None:
    """Test profile page requires authentication."""
    response = client.get("/profile")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # Should show login form when not authenticated
    assert "Please log in" in response.text


def test_dashboard_redirect(client: TestClient) -> None:
    """Test dashboard redirects to profile."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["location"] == "/profile"


def test_create_finding_model_requires_auth(client: TestClient) -> None:
    """Test create finding model page requires authentication."""
    response = client.get("/create-finding-model")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # Should show login form when not authenticated
    assert "Please log in to create finding models" in response.text


def test_finding_model_display(client: TestClient) -> None:
    """Test finding model display loads correctly."""

    # Load test data
    test_data_path = Path(__file__).parent / "data" / "abdominal_abscess.fm.json"
    test_finding_model_data = test_data_path.read_text()

    # Mock IndexEntry
    mock_index_entry = MagicMock()
    mock_index_entry.filename = "abdominal_abscess.fm.json"
    mock_index_entry.name = "abdominal abscess"
    mock_index_entry.description = "A localized collection of pus in the abdomen"

    # Mock HTTP response
    mock_response = MagicMock()
    mock_response.text = test_finding_model_data
    mock_response.raise_for_status.return_value = None

    # Mock AsyncClient.get as an async function
    mock_get = AsyncMock(return_value=mock_response)

    # Mock the finding index
    mock_index = MagicMock()
    mock_index.get = AsyncMock(return_value=mock_index_entry)

    # Override the dependency
    def mock_get_finding_index() -> MagicMock:
        return mock_index

    # Import the app to override dependencies
    from app.dependencies import get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index

    with patch("app.routers.pages.httpx.AsyncClient") as mock_async_client:
        # Mock the async context manager and the get method
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_async_client.return_value.__aenter__.return_value = mock_client
        mock_async_client.return_value.__aexit__.return_value = None

        # Test the request
        response = client.get("/finding-model/abdominal_abscess")

        # Verify response
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Verify the finding model content is displayed
        assert "abdominal abscess" in response.text
        assert "A localized collection of pus in the abdomen" in response.text
        assert "intra-abdominal abscess" in response.text  # synonym from test data
        assert "OIFM_GMTS_004244" in response.text  # oifm_id from test data

        # Verify mocks were called correctly
        mock_index.get.assert_called_once_with("abdominal abscess")
        mock_get.assert_called_once_with(
            "https://raw.githubusercontent.com/openimagingdata/findingmodels/refs/heads/main/defs/abdominal_abscess.fm.json"
        )

    # Clean up
    app.dependency_overrides.clear()


def test_finding_model_display_not_found(client: TestClient) -> None:
    """Test finding model display with non-existent slug returns 404."""

    # Mock the finding index
    mock_index = MagicMock()
    mock_index.get = AsyncMock(return_value=None)  # Return None for not found

    # Override the dependency
    def mock_get_finding_index() -> MagicMock:
        return mock_index

    # Import the app to override dependencies
    from app.dependencies import get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index

    try:
        response = client.get("/finding-model/nonexistent-slug")
        assert response.status_code == 404
    finally:
        # Clean up
        app.dependency_overrides.clear()
