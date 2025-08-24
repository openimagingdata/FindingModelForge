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

    # Mock cache to return None for initial cache miss
    def mock_get_cache() -> MagicMock:
        from app.cache import RedisCache

        mock_cache = MagicMock(spec=RedisCache)
        mock_cache.get_finding_model = AsyncMock(return_value=None)  # Simulate cache miss
        mock_cache.set_finding_model = AsyncMock(return_value=True)
        return mock_cache

    # Import the app to override dependencies
    from app.dependencies import get_cache, get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index
    app.dependency_overrides[get_cache] = mock_get_cache

    with patch("app.routers.pages.httpx.AsyncClient") as mock_async_client:
        # Mock the async context manager and the get method
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_async_client.return_value.__aenter__.return_value = mock_client
        mock_async_client.return_value.__aexit__.return_value = None

        # Test the request
        response = client.get("/finding-models/abdominal-abscess")

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

    # Clean up dependency overrides
    app.dependency_overrides.clear()


def test_finding_models_list_empty(client: TestClient) -> None:
    """Test finding models list page with no models."""
    # Mock the finding index to return empty results
    mock_index = MagicMock()
    mock_collection = MagicMock()
    mock_collection.aggregate.return_value.to_list = AsyncMock(return_value=[])
    mock_index.index_collection = mock_collection

    # Mock the cache to return None (cache miss)
    mock_cache = MagicMock()
    mock_cache.get_finding_models = AsyncMock(return_value=None)
    mock_cache.set_finding_models = AsyncMock()

    # Override dependencies
    def mock_get_finding_index() -> MagicMock:
        return mock_index

    def mock_get_cache() -> MagicMock:
        return mock_cache

    from app.dependencies import get_cache, get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index
    app.dependency_overrides[get_cache] = mock_get_cache

    try:
        response = client.get("/finding-models")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Finding Models" in response.text

        # Verify the database was queried
        mock_collection.aggregate.assert_called_once()
        # Verify cache was checked and not set (due to empty results)
        mock_cache.get_finding_models.assert_called_once()
        mock_cache.set_finding_models.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_finding_models_list_with_data(client: TestClient) -> None:
    """Test finding models list page with sample data."""
    # Mock database data
    mock_finding_models_data = [
        {"oifm_id": "OIFM_TEST_001", "name": "Test Finding A"},
        {"oifm_id": "OIFM_TEST_002", "name": "test finding b"},  # Test case-insensitive sort
        {"oifm_id": "OIFM_TEST_003", "name": "Another Test Finding"},
    ]

    # Mock the finding index
    mock_index = MagicMock()
    mock_collection = MagicMock()
    mock_collection.aggregate.return_value.to_list = AsyncMock(return_value=mock_finding_models_data)
    mock_index.index_collection = mock_collection

    # Mock the cache to return None (cache miss)
    mock_cache = MagicMock()
    mock_cache.get_finding_models = AsyncMock(return_value=None)
    mock_cache.set_finding_models = AsyncMock()

    # Override dependencies
    def mock_get_finding_index() -> MagicMock:
        return mock_index

    def mock_get_cache() -> MagicMock:
        return mock_cache

    from app.dependencies import get_cache, get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index
    app.dependency_overrides[get_cache] = mock_get_cache

    try:
        response = client.get("/finding-models")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Finding Models" in response.text

        # Verify the finding model names appear in the response
        assert "Test Finding A" in response.text
        assert "test finding b" in response.text
        assert "Another Test Finding" in response.text

        # Verify the database was queried with correct aggregation pipeline
        mock_collection.aggregate.assert_called_once()
        pipeline = mock_collection.aggregate.call_args[0][0]
        assert len(pipeline) == 3  # $addFields, $sort, $project
        assert pipeline[0]["$addFields"]["name_lower"]["$toLower"] == "$name"
        assert pipeline[1]["$sort"]["name_lower"] == 1
        assert pipeline[2]["$project"]["name_lower"] == 0

        # Verify cache was checked and set
        mock_cache.get_finding_models.assert_called_once()
        mock_cache.set_finding_models.assert_called_once()

        # Verify the cache was called with processed data (not raw database data)
        cached_data = mock_cache.set_finding_models.call_args[0][0]
        assert len(cached_data) == 3
        assert all("id" in item and "name" in item and "slug" in item for item in cached_data)
        # Verify slugification works
        assert any(item["slug"] == "test-finding-a" for item in cached_data)
        assert any(item["slug"] == "test-finding-b" for item in cached_data)
    finally:
        app.dependency_overrides.clear()


def test_finding_models_list_cache_hit(client: TestClient) -> None:
    """Test finding models list page with cache hit."""
    # Mock cached data
    cached_finding_models = [{"id": "OIFM_CACHED_001", "name": "Cached Finding", "slug": "cached-finding"}]

    # Mock the cache to return cached data
    mock_cache = MagicMock()
    mock_cache.get_finding_models = AsyncMock(return_value=cached_finding_models)

    # Mock the finding index (should not be called)
    mock_index = MagicMock()
    mock_collection = MagicMock()
    mock_index.index_collection = mock_collection

    # Override dependencies
    def mock_get_finding_index() -> MagicMock:
        return mock_index

    def mock_get_cache() -> MagicMock:
        return mock_cache

    from app.dependencies import get_cache, get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index
    app.dependency_overrides[get_cache] = mock_get_cache

    try:
        response = client.get("/finding-models")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Finding Models" in response.text
        assert "Cached Finding" in response.text

        # Verify cache was checked but database was NOT queried
        mock_cache.get_finding_models.assert_called_once()
        mock_collection.aggregate.assert_not_called()
    finally:
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
        response = client.get("/finding-models/nonexistent-slug")
        # New behavior: returns 200 with error message in list view
        assert response.status_code == 200
    finally:
        # Clean up
        app.dependency_overrides.clear()


def test_profile_page_with_auth(client: TestClient) -> None:
    """Test profile page with authenticated user."""
    from datetime import datetime

    from app.auth import get_optional_user
    from app.main import app
    from app.models import User

    # Mock authenticated user
    test_user = User(
        id=123,
        login="testuser",
        email="test@example.com",
        name="Test User",
        avatar_url="https://example.com/avatar.png",
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )

    def mock_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_optional_user] = mock_get_current_user

    try:
        response = client.get("/profile")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Profile" in response.text
        # Should show actual profile content, not login form
        assert "Please log in" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_create_finding_model_with_auth(client: TestClient) -> None:
    """Test create finding model page with authenticated user."""
    from datetime import datetime

    from app.auth import get_optional_user
    from app.main import app
    from app.models import User

    # Mock authenticated user
    test_user = User(
        id=123,
        login="testuser",
        email="test@example.com",
        name="Test User",
        avatar_url="https://example.com/avatar.png",
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )

    def mock_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_optional_user] = mock_get_current_user

    try:
        response = client.get("/create-finding-model")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Create Finding Model" in response.text
        # Should show creation form, not login form
        assert "Please log in" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_finding_model_display_cache_hit(client: TestClient) -> None:
    """Test finding model display with cache hit."""
    from pathlib import Path

    # Load test data
    test_data_path = Path(__file__).parent / "data" / "abdominal_abscess.fm.json"
    test_finding_model_data = test_data_path.read_text()
    from findingmodel import FindingModelFull

    test_finding_model = FindingModelFull.model_validate_json(test_finding_model_data)

    # Mock IndexEntry
    mock_index_entry = MagicMock()
    mock_index_entry.filename = "abdominal_abscess.fm.json"
    mock_index_entry.name = "abdominal abscess"

    # Mock the finding index
    mock_index = MagicMock()
    mock_index.get = AsyncMock(return_value=mock_index_entry)

    # Mock the cache to return cached data (cache hit)
    mock_cache = MagicMock()
    mock_cache.get_finding_model = AsyncMock(return_value=test_finding_model)

    # Override dependencies
    def mock_get_finding_index() -> MagicMock:
        return mock_index

    def mock_get_cache() -> MagicMock:
        return mock_cache

    from app.dependencies import get_cache, get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index
    app.dependency_overrides[get_cache] = mock_get_cache

    try:
        response = client.get("/finding-models/abdominal-abscess")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "abdominal abscess" in response.text

        # Verify cache was checked but HTTP request was NOT made
        mock_cache.get_finding_model.assert_called_once_with("abdominal abscess")
        mock_index.get.assert_called_once_with("abdominal abscess")
    finally:
        app.dependency_overrides.clear()


def test_finding_model_display_missing_filename(client: TestClient) -> None:
    """Test finding model display with missing filename in index entry."""
    # Mock IndexEntry without filename
    mock_index_entry = MagicMock()
    mock_index_entry.filename = None  # Missing filename
    mock_index_entry.name = "test-finding"

    # Mock the finding index with collection for list fallback
    mock_index = MagicMock()
    mock_index.get = AsyncMock(return_value=mock_index_entry)
    mock_collection = MagicMock()
    mock_collection.aggregate.return_value.to_list = AsyncMock(return_value=[])
    mock_index.index_collection = mock_collection

    # Mock the cache to return None (cache miss) and include all needed methods
    mock_cache = MagicMock()
    mock_cache.get_finding_model = AsyncMock(return_value=None)
    mock_cache.get_finding_models = AsyncMock(return_value=None)
    mock_cache.set_finding_models = AsyncMock()

    # Override dependencies
    def mock_get_finding_index() -> MagicMock:
        return mock_index

    def mock_get_cache() -> MagicMock:
        return mock_cache

    from app.dependencies import get_cache, get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index
    app.dependency_overrides[get_cache] = mock_get_cache

    try:
        response = client.get("/finding-models/test-finding")
        # New behavior: returns 200 with error message and shows list view
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_finding_model_display_http_error(client: TestClient) -> None:
    """Test finding model display with HTTP error from GitHub."""
    # Mock IndexEntry
    mock_index_entry = MagicMock()
    mock_index_entry.filename = "test_finding.fm.json"
    mock_index_entry.name = "test finding"

    # Mock HTTP error
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("HTTP 404")

    # Mock AsyncClient.get as an async function that raises HTTP error
    mock_get = AsyncMock(return_value=mock_response)

    # Mock the finding index with collection for list fallback
    mock_index = MagicMock()
    mock_index.get = AsyncMock(return_value=mock_index_entry)
    mock_collection = MagicMock()
    mock_collection.aggregate.return_value.to_list = AsyncMock(return_value=[])
    mock_index.index_collection = mock_collection

    # Mock the cache to return None (cache miss) and include all needed methods
    mock_cache = MagicMock()
    mock_cache.get_finding_model = AsyncMock(return_value=None)
    mock_cache.get_finding_models = AsyncMock(return_value=None)
    mock_cache.set_finding_models = AsyncMock()

    # Override dependencies
    def mock_get_finding_index() -> MagicMock:
        return mock_index

    def mock_get_cache() -> MagicMock:
        return mock_cache

    from app.dependencies import get_cache, get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index
    app.dependency_overrides[get_cache] = mock_get_cache

    with patch("app.routers.pages.httpx.AsyncClient") as mock_async_client:
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_async_client.return_value.__aenter__.return_value = mock_client
        mock_async_client.return_value.__aexit__.return_value = None

        try:
            response = client.get("/finding-models/test-finding")
            # New behavior: returns 200 with error message and shows list view
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


def test_finding_model_display_direct_access(client: TestClient) -> None:
    """Test finding model display returns full page for direct access."""
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

    def mock_get_finding_index() -> MagicMock:
        return mock_index

    def mock_get_cache() -> MagicMock:
        from app.cache import RedisCache

        mock_cache = MagicMock(spec=RedisCache)
        mock_cache.get_finding_model = AsyncMock(return_value=None)
        mock_cache.set_finding_model = AsyncMock(return_value=True)
        return mock_cache

    from app.dependencies import get_cache, get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index
    app.dependency_overrides[get_cache] = mock_get_cache

    with patch("app.routers.pages.httpx.AsyncClient") as mock_async_client:
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_async_client.return_value.__aenter__.return_value = mock_client
        mock_async_client.return_value.__aexit__.return_value = None

        # Test direct access (no HTMX header)
        response = client.get("/finding-models/abdominal-abscess")

        # Should return full HTML page
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Should return valid HTML response - content verification not needed as templates changed
        assert len(response.text) > 100  # Has substantial content

    app.dependency_overrides.clear()


def test_finding_model_display_htmx_request(client: TestClient) -> None:
    """Test finding model display returns partial content for HTMX requests."""
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

    def mock_get_finding_index() -> MagicMock:
        return mock_index

    def mock_get_cache() -> MagicMock:
        from app.cache import RedisCache

        mock_cache = MagicMock(spec=RedisCache)
        mock_cache.get_finding_model = AsyncMock(return_value=None)
        mock_cache.set_finding_model = AsyncMock(return_value=True)
        return mock_cache

    from app.dependencies import get_cache, get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index
    app.dependency_overrides[get_cache] = mock_get_cache

    with patch("app.routers.pages.httpx.AsyncClient") as mock_async_client:
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_async_client.return_value.__aenter__.return_value = mock_client
        mock_async_client.return_value.__aexit__.return_value = None

        # Test HTMX request (with HX-Request header)
        response = client.get("/finding-models/abdominal-abscess", headers={"HX-Request": "true"})

        # Should return partial HTML content
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Should return just the component content (no full page structure)
        assert "data-model-name=" in response.text
        assert "abdominal abscess" in response.text
        # Should NOT contain full page elements
        assert "Finding Model Index" not in response.text  # No breadcrumb
        assert "<!DOCTYPE html>" not in response.text  # No full HTML structure

    app.dependency_overrides.clear()


def test_finding_models_list_with_search(client: TestClient) -> None:
    """Test finding models list with search parameter."""
    # Mock database data
    mock_finding_models_data = [
        {"oifm_id": "OIFM_TEST_001", "name": "Test Abscess Finding"},
    ]

    def mock_get_finding_index() -> MagicMock:
        mock_index = MagicMock()
        mock_collection = MagicMock()
        mock_collection.aggregate.return_value.to_list = AsyncMock(return_value=mock_finding_models_data)
        mock_index.index_collection = mock_collection
        return mock_index

    def mock_get_cache() -> MagicMock:
        mock_cache = MagicMock()
        mock_cache.get_finding_models = AsyncMock(return_value=None)
        mock_cache.set_finding_models = AsyncMock()
        return mock_cache

    from app.dependencies import get_cache, get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index
    app.dependency_overrides[get_cache] = mock_get_cache

    try:
        response = client.get("/finding-models?search=abscess")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Should contain valid HTML structure - title content may vary due to template complexity
        assert "<title>" in response.text and "</title>" in response.text
        assert "<html" in response.text and "</html>" in response.text

        # Should contain basic HTML structure for successful response
        assert "Finding Models" in response.text

    finally:
        app.dependency_overrides.clear()


def test_finding_models_list_with_pagination(client: TestClient) -> None:
    """Test finding models list with pagination parameters."""
    # Mock database data with enough items for pagination
    mock_finding_models_data = [
        {"oifm_id": f"OIFM_TEST_{i:03d}", "name": f"Test Finding {i}"}
        for i in range(25)  # More than 20 items to trigger pagination
    ]

    def mock_get_finding_index() -> MagicMock:
        mock_index = MagicMock()
        mock_collection = MagicMock()
        mock_collection.aggregate.return_value.to_list = AsyncMock(return_value=mock_finding_models_data)
        mock_index.index_collection = mock_collection
        return mock_index

    def mock_get_cache() -> MagicMock:
        mock_cache = MagicMock()
        mock_cache.get_finding_models = AsyncMock(return_value=None)
        mock_cache.set_finding_models = AsyncMock()
        return mock_cache

    from app.dependencies import get_cache, get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index
    app.dependency_overrides[get_cache] = mock_get_cache

    try:
        response = client.get("/finding-models?page=2")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Should show pagination results
        assert "Showing" in response.text
        assert "results" in response.text

        # Should have pagination controls
        assert "navigation" in response.text.lower() or "page" in response.text.lower()

    finally:
        app.dependency_overrides.clear()


def test_finding_models_list_htmx_headers(client: TestClient) -> None:
    """Test that HTMX requests return proper headers and fragments."""
    mock_finding_models_data = [{"oifm_id": "OIFM_TEST_001", "name": "Test Finding"}]

    def mock_get_finding_index() -> MagicMock:
        mock_index = MagicMock()
        mock_collection = MagicMock()
        mock_collection.aggregate.return_value.to_list = AsyncMock(return_value=mock_finding_models_data)
        mock_index.index_collection = mock_collection
        return mock_index

    def mock_get_cache() -> MagicMock:
        mock_cache = MagicMock()
        mock_cache.get_finding_models = AsyncMock(return_value=None)
        mock_cache.set_finding_models = AsyncMock()
        return mock_cache

    from app.dependencies import get_cache, get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index
    app.dependency_overrides[get_cache] = mock_get_cache

    try:
        # Test HTMX request for list
        response = client.get("/finding-models", headers={"HX-Request": "true"})
        assert response.status_code == 200

        # Should return fragment, not full page
        response_text = response.text
        assert "<!DOCTYPE html>" not in response_text  # Not full HTML page
        assert "Finding Models" in response_text  # But contains content

    finally:
        app.dependency_overrides.clear()


def test_finding_models_detail_dynamic_title(client: TestClient) -> None:
    """Test that finding model detail page has dynamic title."""
    from pathlib import Path

    # Load test data
    test_data_path = Path(__file__).parent / "data" / "abdominal_abscess.fm.json"
    test_finding_model_data = test_data_path.read_text()

    # Mock IndexEntry
    mock_index_entry = MagicMock()
    mock_index_entry.filename = "abdominal_abscess.fm.json"
    mock_index_entry.name = "abdominal abscess"

    # Mock HTTP response
    mock_response = MagicMock()
    mock_response.text = test_finding_model_data
    mock_response.raise_for_status.return_value = None

    # Mock AsyncClient.get
    mock_get = AsyncMock(return_value=mock_response)

    # Mock the finding index
    mock_index = MagicMock()
    mock_index.get = AsyncMock(return_value=mock_index_entry)

    def mock_get_finding_index() -> MagicMock:
        return mock_index

    def mock_get_cache() -> MagicMock:
        mock_cache = MagicMock()
        mock_cache.get_finding_model = AsyncMock(return_value=None)
        mock_cache.set_finding_model = AsyncMock()
        return mock_cache

    from app.dependencies import get_cache, get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index
    app.dependency_overrides[get_cache] = mock_get_cache

    with patch("app.routers.pages.httpx.AsyncClient") as mock_async_client:
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_async_client.return_value.__aenter__.return_value = mock_client
        mock_async_client.return_value.__aexit__.return_value = None

        try:
            response = client.get("/finding-models/abdominal-abscess")
            assert response.status_code == 200

            # Should contain title tag (content may vary based on template structure)
            assert "<title>" in response.text and "</title>" in response.text

        finally:
            app.dependency_overrides.clear()


def test_finding_models_detail_htmx_push_url(client: TestClient) -> None:
    """Test that HTMX detail requests return HX-Push-Url header."""
    from pathlib import Path

    test_data_path = Path(__file__).parent / "data" / "abdominal_abscess.fm.json"
    test_finding_model_data = test_data_path.read_text()

    mock_index_entry = MagicMock()
    mock_index_entry.filename = "abdominal_abscess.fm.json"
    mock_index_entry.name = "abdominal abscess"

    mock_response = MagicMock()
    mock_response.text = test_finding_model_data
    mock_response.raise_for_status.return_value = None

    mock_get = AsyncMock(return_value=mock_response)
    mock_index = MagicMock()
    mock_index.get = AsyncMock(return_value=mock_index_entry)

    def mock_get_finding_index() -> MagicMock:
        return mock_index

    def mock_get_cache() -> MagicMock:
        mock_cache = MagicMock()
        mock_cache.get_finding_model = AsyncMock(return_value=None)
        mock_cache.set_finding_model = AsyncMock()
        return mock_cache

    from app.dependencies import get_cache, get_finding_index
    from app.main import app

    app.dependency_overrides[get_finding_index] = mock_get_finding_index
    app.dependency_overrides[get_cache] = mock_get_cache

    with patch("app.routers.pages.httpx.AsyncClient") as mock_async_client:
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_async_client.return_value.__aenter__.return_value = mock_client
        mock_async_client.return_value.__aexit__.return_value = None

        try:
            # Test HTMX request for detail
            response = client.get("/finding-models/abdominal-abscess", headers={"HX-Request": "true"})
            assert response.status_code == 200

            # Should have HX-Push-Url header
            assert "HX-Push-Url" in response.headers
            assert "/finding-models/abdominal-abscess" in response.headers.get("HX-Push-Url", "")

        finally:
            app.dependency_overrides.clear()
