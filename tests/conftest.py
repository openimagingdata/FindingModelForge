"""Test configuration and fixtures."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.database import Database, UserRepo
from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    # Mock database for tests
    mock_database = Database()

    # Create a mock UserRepo
    mock_user_repo = MagicMock(spec=UserRepo)
    mock_database.user_repo = mock_user_repo

    # Create a mock finding_index
    from findingmodel.index import Index

    mock_finding_index = MagicMock(spec=Index)
    mock_database.finding_index = mock_finding_index

    # Mock cache for tests
    from app.cache import RedisCache

    mock_cache = MagicMock(spec=RedisCache)
    mock_cache.enabled = True  # Set enabled property for health checks
    mock_cache.is_healthy = AsyncMock(return_value=True)  # Mock health check method

    # Set up app state
    app.state.database = mock_database
    app.state.cache = mock_cache

    return TestClient(app)


@pytest.fixture
def mock_github_user() -> dict[str, str | int | bool]:
    """Mock GitHub user data."""
    return {
        "id": 12345,
        "login": "testuser",
        "name": "Test User",
        "email": "test@example.com",
        "avatar_url": "https://github.com/images/error/testuser_happy.gif",
        "html_url": "https://github.com/testuser",
        "type": "User",
        "site_admin": False,
    }
