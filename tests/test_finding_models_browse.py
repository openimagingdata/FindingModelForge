"""Test finding models browse router.

These tests verify the finding models browsing functionality that was extracted
from pages.py into finding_models_browse.py during the router refactoring.
"""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.dependencies import get_finding_model_service
from app.main import app
from app.services import NotFoundError


def test_finding_models_list_empty(client: TestClient) -> None:
    """Test finding models list page with no models."""
    response = client.get("/finding-models")
    assert response.status_code == 200
    assert (
        "finding-models-browse" in response.headers.get("content-type", "").lower()
        or "text/html" in response.headers.get("content-type", "").lower()
    )


def test_finding_models_list_with_search(client: TestClient) -> None:
    """Test finding models list with search parameter."""
    response = client.get("/finding-models?search=abscess")
    assert response.status_code == 200


def test_finding_models_list_with_pagination(client: TestClient) -> None:
    """Test finding models list with pagination parameters."""
    response = client.get("/finding-models?page=2&per_page=10")
    assert response.status_code == 200


def test_finding_models_list_htmx_request(client: TestClient) -> None:
    """Test that HTMX requests return proper headers and fragments."""
    response = client.get("/finding-models", headers={"HX-Request": "true"})
    assert response.status_code == 200
    # Should have HX-Push-Url header for HTMX history management
    assert "HX-Push-Url" in response.headers


def test_finding_models_detail_valid_slug(client: TestClient) -> None:
    """Test finding model detail page with valid slug."""
    # Mock the service with a proper finding model mock
    mock_service = AsyncMock()
    mock_finding_model = MagicMock()
    mock_finding_model.name = "Abdominal Abscess"
    mock_finding_model.description = "Test description"
    mock_finding_model.synonyms = []
    mock_finding_model.tags = []
    mock_finding_model.contributors = []
    mock_finding_model.attributes = []
    mock_finding_model.created_date = None
    mock_finding_model.last_modified = None
    mock_finding_model.version = None
    mock_finding_model.oifm_id = None
    mock_index_entry = MagicMock()
    mock_service.get_model_by_slug.return_value = (mock_finding_model, mock_index_entry)

    app.dependency_overrides[get_finding_model_service] = lambda: mock_service
    try:
        response = client.get("/finding-models/abdominal-abscess")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_finding_models_detail_htmx_request(client: TestClient) -> None:
    """Test that HTMX detail requests return HX-Push-Url header."""
    # Mock the service with a proper finding model mock
    mock_service = AsyncMock()
    mock_finding_model = MagicMock()
    mock_finding_model.name = "Abdominal Abscess"
    mock_finding_model.description = "Test description"
    mock_finding_model.synonyms = []
    mock_finding_model.tags = []
    mock_finding_model.contributors = []
    mock_finding_model.attributes = []
    mock_finding_model.created_date = None
    mock_finding_model.last_modified = None
    mock_finding_model.version = None
    mock_finding_model.oifm_id = None
    mock_index_entry = MagicMock()
    mock_service.get_model_by_slug.return_value = (mock_finding_model, mock_index_entry)

    app.dependency_overrides[get_finding_model_service] = lambda: mock_service
    try:
        response = client.get("/finding-models/abdominal-abscess", headers={"HX-Request": "true"})
        assert response.status_code == 200
        # Should have HX-Push-Url header
        assert "HX-Push-Url" in response.headers
        assert response.headers["HX-Push-Url"] == "/finding-models/abdominal-abscess"
    finally:
        app.dependency_overrides.clear()


def test_finding_models_detail_not_found(client: TestClient) -> None:
    """Test finding model detail with non-existent slug returns 404."""
    mock_service = AsyncMock()
    mock_service.get_model_by_slug.side_effect = NotFoundError("Model not found")
    # For fallback list call
    mock_service.list_models.return_value = ([], 0)

    app.dependency_overrides[get_finding_model_service] = lambda: mock_service
    try:
        response = client.get("/finding-models/nonexistent-slug")
        # Should fallback to list view with error message
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_finding_models_detail_not_found_htmx(client: TestClient) -> None:
    """Test finding model detail with non-existent slug in HTMX request returns 404."""
    mock_service = AsyncMock()
    mock_service.get_model_by_slug.side_effect = NotFoundError("Model not found")

    app.dependency_overrides[get_finding_model_service] = lambda: mock_service
    try:
        response = client.get("/finding-models/nonexistent-slug", headers={"HX-Request": "true"})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_finding_models_service_integration(client: TestClient) -> None:
    """Test that the router properly uses the FindingModelService."""
    mock_service = AsyncMock()
    mock_service.list_models.return_value = ([], 0)

    app.dependency_overrides[get_finding_model_service] = lambda: mock_service
    try:
        response = client.get("/finding-models")
        assert response.status_code == 200
        mock_service.list_models.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_finding_models_service_detail_integration(client: TestClient) -> None:
    """Test that detail route properly uses the FindingModelService."""
    mock_service = AsyncMock()
    mock_finding_model = MagicMock()
    mock_finding_model.name = "Test Finding Model"
    mock_finding_model.description = "Test description"
    mock_finding_model.synonyms = []
    mock_finding_model.tags = []
    mock_finding_model.contributors = []
    mock_finding_model.attributes = []
    mock_finding_model.created_date = None
    mock_finding_model.last_modified = None
    mock_finding_model.version = None
    mock_finding_model.oifm_id = None
    mock_index_entry = MagicMock()
    mock_service.get_model_by_slug.return_value = (mock_finding_model, mock_index_entry)

    app.dependency_overrides[get_finding_model_service] = lambda: mock_service
    try:
        response = client.get("/finding-models/test-slug")
        assert response.status_code == 200
        mock_service.get_model_by_slug.assert_called_once_with("test-slug")
    finally:
        app.dependency_overrides.clear()


def test_finding_models_search_parameters(client: TestClient) -> None:
    """Test that search parameters are properly passed to the service."""
    mock_service = AsyncMock()
    mock_service.list_models.return_value = ([], 0)

    app.dependency_overrides[get_finding_model_service] = lambda: mock_service
    try:
        response = client.get("/finding-models?search=test&page=2&per_page=15")
        assert response.status_code == 200
        mock_service.list_models.assert_called_once_with("test", 2, 15)
    finally:
        app.dependency_overrides.clear()


def test_finding_models_pagination_validation(client: TestClient) -> None:
    """Test pagination parameter validation."""
    # Test invalid page number (too low)
    response = client.get("/finding-models?page=0")
    assert response.status_code == 422

    # Test invalid per_page (too low)
    response = client.get("/finding-models?per_page=5")
    assert response.status_code == 422

    # Test invalid per_page (too high)
    response = client.get("/finding-models?per_page=100")
    assert response.status_code == 422


def test_finding_models_detail_dynamic_title(client: TestClient) -> None:
    """Test that finding model detail page has dynamic title."""
    mock_service = AsyncMock()
    mock_finding_model = MagicMock()
    mock_finding_model.name = "Abdominal Abscess"
    mock_finding_model.description = "Test description"
    mock_finding_model.synonyms = []
    mock_finding_model.tags = []
    mock_finding_model.contributors = []
    mock_finding_model.attributes = []
    mock_finding_model.created_date = None
    mock_finding_model.last_modified = None
    mock_finding_model.version = None
    mock_finding_model.oifm_id = None
    mock_index_entry = MagicMock()
    mock_service.get_model_by_slug.return_value = (mock_finding_model, mock_index_entry)

    app.dependency_overrides[get_finding_model_service] = lambda: mock_service
    try:
        response = client.get("/finding-models/abdominal-abscess", headers={"HX-Request": "true"})
        assert response.status_code == 200
        # The template should include the dynamic title
        response_text = response.text
        assert "Abdominal Abscess - Finding Model Forge" in response_text
    finally:
        app.dependency_overrides.clear()


def test_finding_models_list_search_dynamic_title(client: TestClient) -> None:
    """Test that search results have dynamic title."""
    mock_service = AsyncMock()
    mock_service.list_models.return_value = ([], 0)

    app.dependency_overrides[get_finding_model_service] = lambda: mock_service
    try:
        response = client.get("/finding-models?search=abscess", headers={"HX-Request": "true"})
        assert response.status_code == 200
        # The template should include the search term in title
        response_text = response.text
        assert "Search: abscess - Finding Model Forge" in response_text
    finally:
        app.dependency_overrides.clear()


def test_finding_models_error_handling(client: TestClient) -> None:
    """Test error handling for service exceptions."""
    mock_service = AsyncMock()
    mock_service.get_model_by_slug.side_effect = Exception("Database error")
    # For fallback list call
    mock_service.list_models.return_value = ([], 0)

    app.dependency_overrides[get_finding_model_service] = lambda: mock_service
    try:
        # For full page request, should fallback to list view
        response = client.get("/finding-models/test-slug")
        assert response.status_code == 200

        # For HTMX request, should return error fragment
        response = client.get("/finding-models/test-slug", headers={"HX-Request": "true"})
        assert response.status_code == 500
        assert "Error loading finding model" in response.text
    finally:
        app.dependency_overrides.clear()


def test_finding_models_url_parameters_coverage(client: TestClient) -> None:
    """Test URL parameter handling for complete coverage."""
    mock_service = AsyncMock()
    mock_service.list_models.return_value = ([], 0)

    app.dependency_overrides[get_finding_model_service] = lambda: mock_service
    try:
        # Test per_page parameter in URL building (covers line 92)
        response = client.get("/finding-models?per_page=10", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "HX-Push-Url" in response.headers
        assert "per_page=10" in response.headers["HX-Push-Url"]

        # Test page parameter in URL building (covers line 124)
        response = client.get("/finding-models?page=2", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "page=2" in response.headers["HX-Push-Url"]

        # Test both page and per_page parameters (covers line 126)
        response = client.get("/finding-models?page=3&per_page=15", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "page=3" in response.headers["HX-Push-Url"]
        assert "per_page=15" in response.headers["HX-Push-Url"]
    finally:
        app.dependency_overrides.clear()
