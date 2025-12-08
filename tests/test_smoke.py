"""Smoke tests to verify imports and DI annotations resolve correctly.

These tests catch dependency injection failures and import errors that unit tests
miss because they mock out dependencies. They run fast (< 0.1 second) and are
marked as integration tests (run via `task test-integration`).

The key insight: The DI failure we experienced was a NameError at import time -
FastAPI couldn't resolve `Annotated["CreationService", Depends(...)]` because
the class wasn't imported at runtime. These tests verify that all imports and
type annotations resolve without errors.
"""

import pytest


@pytest.mark.integration
class TestImportsResolve:
    """Verify all modules can be imported without errors.

    This catches the exact bug we hit: CreationService only imported in
    TYPE_CHECKING block, causing NameError when FastAPI resolves DI annotations.
    """

    def test_dependencies_module_imports(self):
        """Verify dependencies.py imports without NameError."""
        # This import exercises all the Annotated[...] type aliases
        from app.dependencies import (
            CreationServiceDep,
            DraftServiceDep,
            FindingModelServiceDep,
            CommentServiceDep,
            DatabaseDep,
            CacheDep,
        )

        # If we get here, all forward references resolved
        assert CreationServiceDep is not None
        assert DraftServiceDep is not None
        assert FindingModelServiceDep is not None
        assert CommentServiceDep is not None
        assert DatabaseDep is not None
        assert CacheDep is not None

    def test_all_routers_import(self):
        """Verify all routers can be imported without errors."""
        from app.routers import creation, home, profile, auth_pages
        from app.routers import finding_models_browse
        from app.routers.drafts import views, mutations, workflows, comments

        assert creation.router is not None
        assert home.router is not None
        assert profile.router is not None
        assert auth_pages.router is not None
        assert finding_models_browse.router is not None
        assert views.router is not None
        assert mutations.router is not None
        assert workflows.router is not None
        assert comments.router is not None

    def test_all_services_import(self):
        """Verify all services can be imported without errors."""
        from app.services.creation_service import CreationService
        from app.services.draft_service import DraftService
        from app.services.finding_model_service import FindingModelService
        from app.services.comment_service import CommentService

        assert CreationService is not None
        assert DraftService is not None
        assert FindingModelService is not None
        assert CommentService is not None

    def test_main_app_imports(self):
        """Verify main app module imports without errors."""
        from app.main import app

        # App should have routers registered
        assert len(app.routes) > 0
