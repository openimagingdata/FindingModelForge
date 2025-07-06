"""Test finding models router."""

from collections.abc import Generator
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from findingmodel import FindingInfo
from findingmodel.index import Index

from app.auth import get_current_user
from app.database import Database, UserRepo
from app.main import app
from app.models import SimilarModelsAnalysis, User


@pytest.fixture
def client() -> TestClient:
    """Create a test client without authentication."""
    # Mock database like in conftest.py
    mock_database = Database()
    mock_user_repo = MagicMock(spec=UserRepo)
    mock_database.user_repo = mock_user_repo

    app.state.database = mock_database

    return TestClient(app)


@pytest.fixture
def mock_finding_index() -> MagicMock:
    """Create a mock FindingModel Index."""
    mock_index = MagicMock(spec=Index)
    return mock_index


@pytest.fixture
def authenticated_client(mock_finding_index: MagicMock) -> Generator[TestClient, None, None]:
    """Create an authenticated test client with mocked dependencies."""
    # Mock database like in conftest.py
    mock_database = Database()
    mock_user_repo = MagicMock(spec=UserRepo)
    mock_database.user_repo = mock_user_repo

    app.state.database = mock_database
    app.state.finding_index = mock_finding_index

    def mock_get_current_user() -> User:
        return User(
            id=123,
            login="testuser",  # GitHub username
            email="test@example.com",
            name="Test User",
            avatar_url="https://example.com/avatar.png",
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )

    # Override only the auth dependency
    app.dependency_overrides[get_current_user] = mock_get_current_user

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides = {}


class TestCheckFindingName:
    """Test the /check-name endpoint."""

    def test_check_name_available(self, authenticated_client: TestClient, mock_finding_index: MagicMock) -> None:
        """Test checking an available name."""
        # Mock Index.get() to return None (name not found)
        mock_finding_index.get = AsyncMock(return_value=None)

        response = authenticated_client.post("/api/finding-models/check-name", json={"name": "new-finding"})

        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert "available" in data["message"]
        mock_finding_index.get.assert_called_once_with("new-finding")

    def test_check_name_unavailable(self, authenticated_client: TestClient, mock_finding_index: MagicMock) -> None:
        """Test checking an unavailable name."""
        # Mock Index.get() to return an existing entry
        mock_entry = {"name": "existing-finding", "description": "Some description"}
        mock_finding_index.get = AsyncMock(return_value=mock_entry)

        response = authenticated_client.post("/api/finding-models/check-name", json={"name": "existing-finding"})

        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert "already exists" in data["message"]
        mock_finding_index.get.assert_called_once_with("existing-finding")

    def test_check_name_invalid_input(self, authenticated_client: TestClient) -> None:
        """Test checking with invalid input."""
        response = authenticated_client.post(
            "/api/finding-models/check-name",
            json={"name": ""},  # Empty name should fail validation
        )

        assert response.status_code == 422  # Validation error

    def test_check_name_index_error(self, authenticated_client: TestClient, mock_finding_index: MagicMock) -> None:
        """Test handling index errors."""
        # Mock Index.get() to raise an exception
        mock_finding_index.get = AsyncMock(side_effect=Exception("Index error"))

        response = authenticated_client.post("/api/finding-models/check-name", json={"name": "test-finding"})

        assert response.status_code == 500
        assert "Failed to check name availability" in response.json()["detail"]

    def test_check_name_requires_auth(self, client: TestClient) -> None:
        """Test that the endpoint requires authentication."""
        response = client.post("/api/finding-models/check-name", json={"name": "test-finding"})

        assert response.status_code == 401  # Unauthorized


class TestCreateFindingInfo:
    """Test the /create-info endpoint."""

    @patch("app.routers.finding_models.create_info_from_name")
    def test_create_info_success(self, mock_create_info: AsyncMock, authenticated_client: TestClient) -> None:
        """Test successful finding info creation."""
        # Mock the create_info_from_name function
        mock_finding_info = FindingInfo(
            name="test-finding", description="A test finding description", synonyms=["synonym1", "synonym2"]
        )
        mock_create_info.return_value = mock_finding_info

        response = authenticated_client.post("/api/finding-models/create-info", json={"name": "test-finding"})

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-finding"
        assert data["description"] == "A test finding description"
        assert data["synonyms"] == ["synonym1", "synonym2"]
        mock_create_info.assert_called_once_with("test-finding")

    @patch("app.routers.finding_models.create_info_from_name")
    def test_create_info_error(self, mock_create_info: AsyncMock, authenticated_client: TestClient) -> None:
        """Test handling errors during info creation."""
        # Mock the function to raise an exception
        mock_create_info.side_effect = Exception("AI service error")

        response = authenticated_client.post("/api/finding-models/create-info", json={"name": "test-finding"})

        assert response.status_code == 500
        assert "Error creating finding info" in response.json()["detail"]

    def test_create_info_invalid_input(self, authenticated_client: TestClient) -> None:
        """Test with invalid input."""
        response = authenticated_client.post(
            "/api/finding-models/create-info",
            json={"name": "a"},  # Too short
        )

        assert response.status_code == 422  # Validation error

    def test_create_info_requires_auth(self, client: TestClient) -> None:
        """Test that the endpoint requires authentication."""
        response = client.post("/api/finding-models/create-info", json={"name": "test-finding"})

        assert response.status_code == 401  # Unauthorized


class TestFindSimilar:
    """Test the /find-similar endpoint."""

    @patch("app.routers.finding_models.find_similar_models")
    def test_find_similar_success(self, mock_find_similar: AsyncMock, authenticated_client: TestClient) -> None:
        """Test successful similar models search."""
        # Mock the find_similar_models function
        mock_analysis = SimilarModelsAnalysis(similar_models=[], recommendation="create_new", confidence=0.9)
        mock_find_similar.return_value = mock_analysis

        response = authenticated_client.post(
            "/api/finding-models/find-similar",
            json={
                "name": "test-finding",
                "description": "A test finding description for similarity search",
                "synonyms": ["test", "finding"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["similar_models"] == []
        assert data["recommendation"] == "create_new"
        assert data["confidence"] == 0.9

    @patch("app.routers.finding_models.find_similar_models")
    def test_find_similar_with_matches(self, mock_find_similar: AsyncMock, authenticated_client: TestClient) -> None:
        """Test finding similar models with matches."""
        # Mock analysis with similar models
        mock_analysis = MagicMock()
        mock_analysis.similar_models = [
            {
                "oifm_id": "test-123",
                "name": "similar-finding",
                "description": "A similar finding",
                "synonyms": ["similar", "finding"],
            }
        ]
        mock_analysis.recommendation = "edit_existing"
        mock_analysis.confidence = 0.85
        mock_find_similar.return_value = mock_analysis

        response = authenticated_client.post(
            "/api/finding-models/find-similar",
            json={"name": "test-finding", "description": "A test finding description", "synonyms": ["test"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["similar_models"]) == 1
        assert data["similar_models"][0]["name"] == "similar-finding"
        assert data["recommendation"] == "edit_existing"

    @patch("app.routers.finding_models.find_similar_models")
    def test_find_similar_error(self, mock_find_similar: AsyncMock, authenticated_client: TestClient) -> None:
        """Test handling errors during similarity search."""
        mock_find_similar.side_effect = Exception("Search error")

        response = authenticated_client.post(
            "/api/finding-models/find-similar",
            json={"name": "test-finding", "description": "A test finding description", "synonyms": []},
        )

        assert response.status_code == 500
        assert "Error finding similar models" in response.json()["detail"]

    def test_find_similar_invalid_input(self, authenticated_client: TestClient) -> None:
        """Test with invalid input."""
        response = authenticated_client.post(
            "/api/finding-models/find-similar",
            json={"description": "short"},  # Too short
        )

        assert response.status_code == 422  # Validation error

    def test_find_similar_requires_auth(self, client: TestClient) -> None:
        """Test that the endpoint requires authentication."""
        response = client.post(
            "/api/finding-models/find-similar", json={"description": "A test finding description", "synonyms": []}
        )

        assert response.status_code == 401  # Unauthorized


class TestGenerateStubMarkdown:
    """Test the /generate-stub endpoint."""

    def test_generate_stub_success(self, authenticated_client: TestClient) -> None:
        """Test successful stub markdown generation."""
        response = authenticated_client.post(
            "/api/finding-models/generate-stub",
            json={"name": "test-finding", "description": "A test finding description", "synonyms": ["test", "finding"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "markdown" in data
        assert "## Attributes" in data["markdown"]
        assert "### presence" in data["markdown"]
        assert "### change_from_prior" in data["markdown"]

    def test_generate_stub_invalid_input(self, authenticated_client: TestClient) -> None:
        """Test with invalid input."""
        response = authenticated_client.post(
            "/api/finding-models/generate-stub",
            json={
                "name": "a",  # Too short
                "description": "short",  # Too short
                "synonyms": [],
            },
        )

        assert response.status_code == 422  # Validation error

    def test_generate_stub_requires_auth(self, client: TestClient) -> None:
        """Test that the endpoint requires authentication."""
        response = client.post(
            "/api/finding-models/generate-stub",
            json={"name": "test-finding", "description": "A test finding description", "synonyms": []},
        )

        assert response.status_code == 401  # Unauthorized


class TestGenerateModel:
    """Test the /generate-model endpoint."""

    @patch("app.routers.finding_models.create_model_from_markdown")
    def test_generate_model_success(self, mock_create_model: AsyncMock, authenticated_client: TestClient) -> None:
        """Test successful model generation."""
        # Mock the create_model_from_markdown function
        mock_model = MagicMock()
        mock_model.model_dump.return_value = {"name": "test-finding", "description": "A test finding", "attributes": {}}
        mock_create_model.return_value = mock_model

        response = authenticated_client.post(
            "/api/finding-models/generate-model",
            json={
                "name": "test-finding",
                "description": "A test finding description",
                "synonyms": ["test"],
                "attributes_markdown": "## Attributes\n### presence\nWhether finding is present",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "model" in data
        assert "markdown" in data
        assert "test-finding" in data["markdown"]

    @patch("app.routers.finding_models.create_model_from_markdown")
    def test_generate_model_error(self, mock_create_model: AsyncMock, authenticated_client: TestClient) -> None:
        """Test handling errors during model generation."""
        mock_create_model.side_effect = Exception("Model creation error")

        response = authenticated_client.post(
            "/api/finding-models/generate-model",
            json={
                "name": "test-finding",
                "description": "A test finding description",
                "synonyms": [],
                "attributes_markdown": "## Attributes\n### presence\nWhether finding is present",
            },
        )

        assert response.status_code == 500
        assert "Error generating finding model" in response.json()["detail"]

    def test_generate_model_invalid_input(self, authenticated_client: TestClient) -> None:
        """Test with invalid input."""
        response = authenticated_client.post(
            "/api/finding-models/generate-model",
            json={
                "name": "",  # Empty name
                "description": "A test finding description",
                "synonyms": [],
                "attributes_markdown": "short",  # Too short
            },
        )

        assert response.status_code == 422  # Validation error

    def test_generate_model_requires_auth(self, client: TestClient) -> None:
        """Test that the endpoint requires authentication."""
        response = client.post(
            "/api/finding-models/generate-model",
            json={
                "name": "test-finding",
                "description": "A test finding description",
                "synonyms": [],
                "attributes_markdown": "## Attributes\n### presence\nWhether finding is present",
            },
        )

        assert response.status_code == 401  # Unauthorized


class TestEndpointIntegration:
    """Test integration between endpoints."""

    def test_full_workflow_simulation(self, authenticated_client: TestClient, mock_finding_index: MagicMock) -> None:
        """Test a simulated full workflow from name check to model generation."""
        # Step 1: Check name availability
        mock_finding_index.get = AsyncMock(return_value=None)

        name_response = authenticated_client.post("/api/finding-models/check-name", json={"name": "workflow-test"})
        assert name_response.status_code == 200
        assert name_response.json()["available"] is True

        # Step 2: Generate stub markdown
        stub_response = authenticated_client.post(
            "/api/finding-models/generate-stub",
            json={
                "name": "workflow-test",
                "description": "A workflow test description",
                "synonyms": ["workflow", "test"],
            },
        )
        assert stub_response.status_code == 200
        assert "markdown" in stub_response.json()

    def test_endpoint_error_handling_consistency(self, authenticated_client: TestClient) -> None:
        """Test that all endpoints handle validation errors consistently."""
        endpoints = [
            ("/api/finding-models/check-name", {"name": ""}),
            ("/api/finding-models/create-info", {"name": "a"}),
            ("/api/finding-models/find-similar", {"description": "short"}),
            ("/api/finding-models/generate-stub", {"name": "", "description": "short"}),
            (
                "/api/finding-models/generate-model",
                {"name": "", "description": "short", "attributes_markdown": "short"},
            ),
        ]

        for endpoint, invalid_data in endpoints:
            response = authenticated_client.post(endpoint, json=invalid_data)
            assert response.status_code == 422, f"Endpoint {endpoint} should return 422 for invalid data"
