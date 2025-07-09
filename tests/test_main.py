"""Tests for main application setup and configuration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app


def test_create_app_returns_fastapi_instance() -> None:
    """Test that create_app returns a properly configured FastAPI instance."""
    app = create_app()

    assert isinstance(app, FastAPI)
    assert app.title == "Finding Model Forge"  # Actual title from settings
    assert "GitHub OAuth" in app.description
    # Debug mode depends on environment settings, so just check it's a boolean
    assert isinstance(app.debug, bool)


def test_app_has_required_routes() -> None:
    """Test that the app includes all required routers."""
    app = create_app()

    # Check that the app has routes (indicating routers were included)
    assert len(app.router.routes) > 0

    # Check that static files are mounted by verifying route names
    route_names = [getattr(route, "name", "") for route in app.router.routes]
    assert "static" in route_names, "Static files route not found"


def test_app_static_files_mounted() -> None:
    """Test that static files are properly mounted."""
    app = create_app()
    client = TestClient(app)

    # Test that we can access static files (even if they don't exist, we should get 404, not 500)
    response = client.get("/static/nonexistent.css")
    # Should be 404 (file not found) rather than 500 (route not found)
    assert response.status_code == 404


@patch("app.main.settings")
def test_create_app_with_debug_mode(mock_settings: MagicMock) -> None:
    """Test app creation with debug mode enabled."""
    mock_settings.app_name = "TestApp"
    mock_settings.app_version = "1.0.0"
    mock_settings.debug = True

    app = create_app()

    assert app.debug is True
    assert app.title == "TestApp"


@pytest.mark.asyncio
async def test_lifespan_startup_success() -> None:
    """Test successful lifespan startup sequence."""
    app = FastAPI()

    # Mock the database and its methods
    mock_database = AsyncMock()
    mock_database.connect = AsyncMock()
    mock_database.disconnect = AsyncMock()
    mock_database.client = MagicMock()

    # Mock the Index and its methods
    mock_index = AsyncMock()
    mock_index.setup_indexes = AsyncMock()

    with (
        patch("app.main.Database", return_value=mock_database),
        patch("findingmodel.index.Index", return_value=mock_index),
        patch("app.main.settings") as mock_settings,
    ):
        mock_settings.app_name = "TestApp"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mock_settings.debug = False
        mock_settings.github_client_id = "test_client_id"
        mock_settings.mongodb_db = "test_db"

        # Import and test the lifespan function
        from app.main import lifespan

        # Test startup
        async with lifespan(app):
            # Verify startup calls
            mock_database.connect.assert_called_once()

            # Verify app state is set
            assert hasattr(app.state, "database")

        # Verify shutdown calls
        mock_database.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_startup_database_failure() -> None:
    """Test lifespan startup when database connection fails."""
    app = FastAPI()

    # Mock database that fails to connect
    mock_database = AsyncMock()
    mock_database.connect = AsyncMock(side_effect=Exception("Connection failed"))

    with (
        patch("app.main.Database", return_value=mock_database),
        patch("app.main.settings") as mock_settings,
    ):
        mock_settings.app_name = "TestApp"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mock_settings.debug = False
        mock_settings.github_client_id = "test_client_id"

        from app.main import lifespan

        # Should raise the connection exception
        with pytest.raises(Exception, match="Connection failed"):
            async with lifespan(app):
                pass


@pytest.mark.asyncio
async def test_lifespan_warns_when_github_not_configured() -> None:
    """Test that lifespan warns when GitHub OAuth is not configured."""
    app = FastAPI()

    mock_database = AsyncMock()
    mock_database.connect = AsyncMock()
    mock_database.disconnect = AsyncMock()
    mock_database.client = MagicMock()

    with (
        patch("app.main.Database", return_value=mock_database),
        patch("app.main.settings") as mock_settings,
        patch("app.main.logger") as mock_logger,
    ):
        mock_settings.app_name = "TestApp"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mock_settings.debug = False
        mock_settings.github_client_id = None  # Not configured

        from app.main import lifespan

        async with lifespan(app):
            pass

        # Verify warning was logged
        mock_logger.warning.assert_called_with("GitHub OAuth not configured - authentication will not work")
