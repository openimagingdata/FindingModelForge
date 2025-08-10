"""Test finding models router."""

from collections.abc import Generator
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from findingmodel.index import Index

from app.auth import get_current_user
from app.database import Database, UserRepo
from app.main import app
from app.models import User


@pytest.fixture
def client() -> TestClient:
    """Create a test client without authentication."""
    # Mock database like in conftest.py
    mock_database = Database()
    mock_user_repo = MagicMock(spec=UserRepo)
    mock_database.user_repo = mock_user_repo

    # Create a mock finding_index
    mock_finding_index = MagicMock(spec=Index)
    mock_database.finding_index = mock_finding_index

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
    mock_database.finding_index = mock_finding_index

    app.state.database = mock_database

    def mock_get_current_user() -> User:
        return User(
            id=123,
            login="testuser",  # GitHub username
            email="test@example.com",
            name="Test User",
            avatar_url="https://example.com/avatar.png",
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
            organizations=["test-org"],
        )

    # Override only the auth dependency
    app.dependency_overrides[get_current_user] = mock_get_current_user

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides = {}
