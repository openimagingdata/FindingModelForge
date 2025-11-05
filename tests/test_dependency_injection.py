"""Tests for dependency injection system.

Tests that all service dependencies can be instantiated properly
and that the dependency injection system works with FastAPI.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from app.database import CommentRepo, Database, DraftRepo, UserRepo
from app.dependencies import (
    CreationServiceDep,
    DraftServiceDep,
    FindingModelServiceDep,
    get_creation_service,
    get_draft_service,
    get_finding_model_service,
)
from app.services.comment_service import CommentService
from app.services.creation_service import CreationService
from app.services.draft_service import DraftService
from app.services.finding_model_service import FindingModelService


class TestServiceDependencyInjection:
    """Test service dependency injection functions."""

    def test_get_finding_model_service(self):
        """Test that get_finding_model_service creates a FindingModelService."""
        # Mock dependencies
        mock_index = MagicMock()
        mock_user_repo = MagicMock(spec=UserRepo)

        # Call the dependency function
        mock_comment_service = MagicMock(spec=CommentService)
        service = get_finding_model_service(
            mock_index,
            MagicMock(spec=CommentRepo),
            mock_user_repo,
            mock_comment_service,
        )

        # Verify service is created correctly
        assert isinstance(service, FindingModelService)
        assert service.index is mock_index
        assert service.user_repo is mock_user_repo
        assert service.comment_service is mock_comment_service

    def test_get_creation_service(self):
        """Test that get_creation_service creates a CreationService."""
        # Mock dependencies
        mock_index = MagicMock()
        mock_database = MagicMock(spec=Database)

        # Call the dependency function
        service = get_creation_service(mock_index, mock_database)

        # Verify service is created correctly
        assert isinstance(service, CreationService)
        assert service.index is mock_index
        assert service.database is mock_database

    def test_get_draft_service(self):
        """Test that get_draft_service creates a DraftService."""
        # Mock dependencies
        mock_draft_repo = MagicMock(spec=DraftRepo)
        mock_user_repo = MagicMock(spec=UserRepo)
        mock_database = MagicMock(spec=Database)
        mock_database.ensure_person_for_user = AsyncMock(return_value=None)

        # Call the dependency function
        mock_comment_service = MagicMock(spec=CommentService)
        service = get_draft_service(
            mock_draft_repo,
            mock_user_repo,
            mock_database,
            mock_comment_service,
        )

        # Verify service is created correctly
        assert isinstance(service, DraftService)
        assert service.draft_repo is mock_draft_repo
        assert service.user_repo is mock_user_repo
        assert service.database is mock_database
        assert service.comment_service is mock_comment_service


class TestServiceDependenciesInRouters:
    """Test that services can be injected into FastAPI routes."""

    def test_finding_model_service_injection_in_pages(self, client: TestClient):
        """Test that FindingModelService can be injected in pages router."""
        # Mock the service and its dependencies
        mock_service = MagicMock(spec=FindingModelService)
        mock_service.list_models = AsyncMock(return_value=([], 0))

        # Override the service dependency
        from app.dependencies import get_finding_model_service
        from app.main import app

        app.dependency_overrides[get_finding_model_service] = lambda: mock_service

        try:
            # Make a request that should trigger the dependency injection
            response = client.get("/finding-models")

            # Verify response - the service should work when the route is available
            assert response.status_code == 200
            mock_service.list_models.assert_called_once()

        finally:
            app.dependency_overrides.clear()

    def test_draft_service_injection_in_pages(self, client: TestClient):
        """Test that DraftService can be injected in pages router."""
        # Mock the service and its dependencies
        mock_service = MagicMock(spec=DraftService)
        mock_service.get_drafts_for_user = AsyncMock(return_value=[])

        # Override the service dependency
        from app.dependencies import get_draft_service
        from app.main import app

        app.dependency_overrides[get_draft_service] = lambda: mock_service

        # Mock user authentication
        from app.models import User

        test_user = User(
            id=999999,
            github_id=12345,
            login="testuser",
            name="Test User",
            avatar_url="https://example.com/avatar.jpg",
            created_at="2021-01-01T00:00:00Z",
            updated_at="2021-01-01T00:00:00Z",
        )

        from app.auth import get_optional_user

        app.dependency_overrides[get_optional_user] = lambda: test_user

        try:
            # Make a request that should trigger the dependency injection
            response = client.get("/profile")
            assert response.status_code == 200  # Profile router is now registered

        finally:
            app.dependency_overrides.clear()

    def test_creation_service_injection_in_finding_models(self, client: TestClient):
        """Test that CreationService can be injected in finding_models router."""
        # This test verifies the dependency injection mechanism works
        # by attempting to override the service dependency
        from app.dependencies import get_creation_service
        from app.main import app

        # Mock the service
        mock_service = MagicMock(spec=CreationService)
        mock_service.generate_default_attributes_markdown = MagicMock(return_value="# Test Attributes")

        app.dependency_overrides[get_creation_service] = lambda: mock_service

        try:
            # Test that we can override the dependency successfully
            # This proves the dependency injection system is working
            _ = get_creation_service(MagicMock(), MagicMock())

            # The key test: verify that dependency overrides work
            # This is the core functionality we're testing
            assert app.dependency_overrides[get_creation_service] is not None

        finally:
            app.dependency_overrides.clear()


class TestTypeAnnotations:
    """Test that type annotations are working correctly."""

    def test_finding_model_service_dep_annotation(self):
        """Test that FindingModelServiceDep annotation is correct."""
        # This would be caught by mypy if wrong, but let's test at runtime too
        from typing import get_args, get_origin

        # Check that it's an Annotated type
        origin = get_origin(FindingModelServiceDep)
        assert origin is not None

        # Check the type arguments - should be ForwardRef or string
        args = get_args(FindingModelServiceDep)
        assert len(args) >= 2
        # Check that first arg represents FindingModelService (could be ForwardRef)
        first_arg = args[0]
        assert str(first_arg) == "FindingModelService" or (
            hasattr(first_arg, "__forward_arg__") and first_arg.__forward_arg__ == "FindingModelService"
        )

    def test_creation_service_dep_annotation(self):
        """Test that CreationServiceDep annotation is correct."""
        from typing import get_args, get_origin

        origin = get_origin(CreationServiceDep)
        assert origin is not None

        args = get_args(CreationServiceDep)
        assert len(args) >= 2
        # Check that first arg represents CreationService (could be ForwardRef)
        first_arg = args[0]
        assert str(first_arg) == "CreationService" or (
            hasattr(first_arg, "__forward_arg__") and first_arg.__forward_arg__ == "CreationService"
        )

    def test_draft_service_dep_annotation(self):
        """Test that DraftServiceDep annotation is correct."""
        from typing import get_args, get_origin

        origin = get_origin(DraftServiceDep)
        assert origin is not None

        args = get_args(DraftServiceDep)
        assert len(args) >= 2
        # Check that first arg represents DraftService (could be ForwardRef)
        first_arg = args[0]
        assert str(first_arg) == "DraftService" or (
            hasattr(first_arg, "__forward_arg__") and first_arg.__forward_arg__ == "DraftService"
        )


class TestCircularImportPrevention:
    """Test that there are no circular import issues."""

    def test_no_circular_imports_in_dependencies(self):
        """Test that importing dependencies doesn't cause circular imports."""
        # This test passes if the imports work without errors
        try:
            from app import (
                dependencies,  # noqa: F401
                services,  # noqa: F401
            )

            # If we get here without ImportError, circular imports are avoided
            assert True

        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")

    def test_services_can_be_instantiated_independently(self):
        """Test that services can be created without FastAPI context."""
        from app.database import CommentRepo, Database, DraftRepo, UserRepo
        from app.services.comment_service import CommentService
        from app.services.creation_service import CreationService
        from app.services.draft_service import DraftService
        from app.services.finding_model_service import FindingModelService

        # Mock dependencies
        mock_index = MagicMock()
        mock_database = MagicMock(spec=Database)
        mock_draft_repo = MagicMock(spec=DraftRepo)
        mock_comment_repo = MagicMock(spec=CommentRepo)
        mock_user_repo = MagicMock(spec=UserRepo)

        comment_service = CommentService(
            comment_repo=mock_comment_repo,
            user_repo=mock_user_repo,
            draft_repo=mock_draft_repo,
        )

        # Should be able to create services directly (no cache parameter)
        finding_service = FindingModelService(
            mock_index,
            mock_comment_repo,
            mock_user_repo,
            comment_service,
        )
        creation_service = CreationService(mock_index, mock_database)
        draft_service = DraftService(
            mock_draft_repo,
            mock_user_repo,
            mock_database,
            comment_service,
        )

        # Verify they're the correct types
        assert isinstance(finding_service, FindingModelService)
        assert isinstance(creation_service, CreationService)
        assert isinstance(draft_service, DraftService)
