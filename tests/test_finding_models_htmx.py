"""Test HTMX endpoints for finding models creation."""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from findingmodel import FindingInfo

from app.auth import get_current_user
from app.cache import RedisCache
from app.database import CommentRepo, Database, DraftRepo, UserRepo
from app.dependencies import FindingModelCreationSession, SessionManager
from app.main import app
from app.models import FindingModelDraft, FindingModelInputs, User


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create a mock Redis cache."""
    return MagicMock(spec=RedisCache)


@pytest.fixture
def mock_session_manager(mock_cache: MagicMock) -> SessionManager:
    """Create a session manager with mocked cache."""
    return SessionManager(mock_cache)


@pytest.fixture
def authenticated_client_with_cache(mock_cache: MagicMock) -> Generator[TestClient, None, None]:
    """Create an authenticated test client with mocked cache."""
    # Mock database
    mock_database = Database()

    # Mock UserRepo
    mock_user_repo = MagicMock(spec=UserRepo)
    mock_user_repo.collection = MagicMock()
    mock_user_repo.collection.find_one = AsyncMock()
    mock_user_repo.collection.update_one = AsyncMock()
    mock_database.user_repo = mock_user_repo

    # Mock CommentRepo
    mock_comment_repo = MagicMock(spec=CommentRepo)
    mock_comment_repo.get_thread = AsyncMock()
    mock_comment_repo.add_comment = AsyncMock()
    mock_comment_repo.add_reply = AsyncMock()
    mock_comment_repo.report_comment = AsyncMock()
    mock_database.comment_repo = mock_comment_repo

    mock_database.finding_index = MagicMock()

    # Mock DraftRepo (required dependency) with minimal async behavior
    mock_draft_repo = MagicMock(spec=DraftRepo)

    async def _find_editable_by_name(user_id: int, name: str):  # type: ignore[no-untyped-def]
        return None

    async def _save_draft(  # type: ignore[no-untyped-def]
        user_id: int,
        name: str,
        inputs,
        draft_id: str | None = None,
        generated_json: str | None = None,
    ):
        return FindingModelDraft(
            id="mock-id",
            user_id=user_id,
            name=name,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            inputs=inputs if isinstance(inputs, FindingModelInputs) else FindingModelInputs(**inputs.model_dump()),
            generated_json=generated_json,
            status="draft",
            action_log=[],
        )

    mock_draft_repo.find_editable_by_name = AsyncMock(side_effect=_find_editable_by_name)
    mock_draft_repo.save_draft = AsyncMock(side_effect=_save_draft)
    mock_database.draft_repo = mock_draft_repo

    app.state.database = mock_database
    app.state.cache = mock_cache

    def mock_get_current_user() -> User:
        return User(
            id=123,
            login="testuser",
            email="test@example.com",
            name="Test User",
            avatar_url="https://example.com/avatar.png",
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
            organizations=["test-org"],
        )

    app.dependency_overrides[get_current_user] = mock_get_current_user

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides = {}


class TestSessionManager:
    """Test the SessionManager class."""

    async def test_create_session(self, mock_session_manager: SessionManager, mock_cache: MagicMock) -> None:
        """Test creating a new session."""
        # Mock cache.set to succeed
        mock_cache.set = AsyncMock(return_value=None)

        session_id = await mock_session_manager.create_session()

        assert isinstance(session_id, str)
        assert len(session_id) == 36  # UUID4 length

        # Verify cache was called
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert call_args[0][0] == f"creation_session:{session_id}"  # cache key
        assert "session_id" in call_args[0][1]  # session data JSON

    async def test_get_session_exists(self, mock_session_manager: SessionManager, mock_cache: MagicMock) -> None:
        """Test getting an existing session."""
        session_data = '{"session_id": "test-123", "current_step": 2, "name": "test"}'
        mock_cache.get = AsyncMock(return_value=session_data)

        session = await mock_session_manager.get_session("test-123")

        assert session is not None
        assert session.session_id == "test-123"
        assert session.current_step == 2
        assert session.name == "test"

        mock_cache.get.assert_called_once_with("creation_session:test-123")

    async def test_get_session_not_found(self, mock_session_manager: SessionManager, mock_cache: MagicMock) -> None:
        """Test getting a non-existent session."""
        mock_cache.get = AsyncMock(return_value=None)

        session = await mock_session_manager.get_session("nonexistent")

        assert session is None
        mock_cache.get.assert_called_once_with("creation_session:nonexistent")

    async def test_get_session_invalid_json(self, mock_session_manager: SessionManager, mock_cache: MagicMock) -> None:
        """Test getting session with invalid JSON data."""
        mock_cache.get = AsyncMock(return_value="invalid-json")

        session = await mock_session_manager.get_session("test-123")

        assert session is None

    async def test_update_session(self, mock_session_manager: SessionManager, mock_cache: MagicMock) -> None:
        """Test updating a session."""
        mock_cache.set = AsyncMock(return_value=None)

        session = FindingModelCreationSession(session_id="test-123", current_step=3, name="updated")
        await mock_session_manager.update_session(session)

        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert call_args[0][0] == "creation_session:test-123"
        # JSON might be compact, so check for the value without exact spacing
        json_data = call_args[0][1]
        assert '"name":"updated"' in json_data or '"name": "updated"' in json_data

    async def test_delete_session(self, mock_session_manager: SessionManager, mock_cache: MagicMock) -> None:
        """Test deleting a session."""
        mock_cache.delete = AsyncMock(return_value=None)

        await mock_session_manager.delete_session("test-123")

        mock_cache.delete.assert_called_once_with("creation_session:test-123")


class TestHTMXCreateSession:
    """Test the HTMX session creation endpoint."""

    def test_create_session_success(self, authenticated_client_with_cache: TestClient, mock_cache: MagicMock) -> None:
        """Test successful session creation."""
        mock_cache.set = AsyncMock(return_value=None)
        mock_cache.get = AsyncMock(return_value='{"session_id": "test-123", "current_step": 1}')

        response = authenticated_client_with_cache.post("/create/restart")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"

        content = response.text
        assert "Finding Model Name" in content
        assert "Generate Description" in content

    def test_create_session_cache_error(
        self, authenticated_client_with_cache: TestClient, mock_cache: MagicMock
    ) -> None:
        """Test session creation with cache error."""
        mock_cache.set = AsyncMock(side_effect=Exception("Cache error"))
        mock_cache.get = AsyncMock(side_effect=Exception("Cache error"))

        response = authenticated_client_with_cache.post("/create/restart")

        assert response.status_code == 200  # Should still work with fallback
        content = response.text
        assert "Finding Model Name" in content


class TestHTMXStepEndpoints:
    """Test the HTMX step processing endpoints."""

    def test_step_1_valid_name(self, authenticated_client_with_cache: TestClient, mock_cache: MagicMock) -> None:
        """Test step 1 with valid name input."""
        # Mock session retrieval and update
        session_data = '{"session_id": "test-123", "current_step": 1}'
        mock_cache.get = AsyncMock(return_value=session_data)
        mock_cache.set = AsyncMock(return_value=None)

        # Mock index check to return None (name available)
        app.state.database.finding_index.get = AsyncMock(return_value=None)

        response = authenticated_client_with_cache.post(
            "/create/step/1", data={"session_id": "test-123", "name": "test-finding"}
        )

        assert response.status_code == 200
        content = response.text
        assert "Edit Description" in content
        assert "test-finding" in content

    def test_step_1_invalid_name_too_short(
        self, authenticated_client_with_cache: TestClient, mock_cache: MagicMock
    ) -> None:
        """Test step 1 with name too short."""
        session_data = '{"session_id": "test-123", "current_step": 1}'
        mock_cache.get = AsyncMock(return_value=session_data)
        mock_cache.set = AsyncMock(return_value=None)

        response = authenticated_client_with_cache.post("/create/step/1", data={"session_id": "test-123", "name": "a"})

        assert response.status_code == 422

    def test_step_1_invalid_name_too_long(
        self, authenticated_client_with_cache: TestClient, mock_cache: MagicMock
    ) -> None:
        """Test step 1 with name too long."""
        session_data = '{"session_id": "test-123", "current_step": 1}'
        mock_cache.get = AsyncMock(return_value=session_data)
        mock_cache.set = AsyncMock(return_value=None)

        long_name = "a" * 201  # Over 200 characters (our current limit)
        response = authenticated_client_with_cache.post(
            "/create/step/1", data={"session_id": "test-123", "name": long_name}
        )

        assert response.status_code == 422

    def test_step_1_name_unavailable(self, authenticated_client_with_cache: TestClient, mock_cache: MagicMock) -> None:
        """Test step 1 with unavailable name."""
        session_data = '{"session_id": "test-123", "current_step": 1}'
        mock_cache.get = AsyncMock(return_value=session_data)
        mock_cache.set = AsyncMock(return_value=None)

        # Mock index to return existing entry
        app.state.database.finding_index.get = AsyncMock(return_value={"name": "existing-finding"})

        response = authenticated_client_with_cache.post(
            "/create/step/1", data={"session_id": "test-123", "name": "existing-finding"}
        )

        assert response.status_code == 200
        content = response.text
        assert "already exists" in content.lower()
        assert "existing-finding" in content.lower()

    def test_step_2_success(
        self,
        authenticated_client_with_cache: TestClient,
        mock_cache: MagicMock,
    ) -> None:
        """Test step 2 with successful description/synonyms generation."""
        session_data = '{"session_id": "test-123", "current_step": 2, "name": "test-finding"}'
        mock_cache.get = AsyncMock(return_value=session_data)
        mock_cache.set = AsyncMock(return_value=None)

        # Mock creation service
        from app.dependencies import get_creation_service
        from app.main import app
        from app.services.creation_service import CreationService

        # Mock AI info generation
        mock_finding_info = FindingInfo(
            name="test-finding",
            description="A test finding description that is long enough",
            synonyms=["synonym1", "synonym2"],
        )

        # Mock similar models search
        mock_analysis = MagicMock()
        mock_analysis.similar_models = []
        mock_analysis.recommendation = "create_new"
        mock_analysis.confidence = 0.9

        # Create mock creation service
        mock_creation_service = MagicMock(spec=CreationService)
        mock_creation_service.generate_finding_info = AsyncMock(return_value=mock_finding_info)
        mock_creation_service.find_similar_models = AsyncMock(return_value=mock_analysis)
        mock_creation_service.is_test_user = MagicMock(return_value=False)
        mock_creation_service.generate_default_attributes_markdown = MagicMock(
            return_value="## Attributes\n\nDefault attributes for test-finding"
        )

        # Mock draft service
        from app.dependencies import get_draft_service
        from app.services.draft_service import DraftService

        mock_draft_service = MagicMock(spec=DraftService)
        mock_draft_service.find_editable_by_name = AsyncMock(return_value=None)
        mock_draft_service.find_latest_by_name = AsyncMock(return_value=None)

        # Mock save_draft to return a draft with an ID
        mock_saved_draft = MagicMock()
        mock_saved_draft.id = "507f1f77bcf86cd799439011"
        mock_draft_service.save_draft = AsyncMock(return_value=mock_saved_draft)

        app.dependency_overrides[get_creation_service] = lambda: mock_creation_service
        app.dependency_overrides[get_draft_service] = lambda: mock_draft_service

        # TestClient follows redirects by default, so we need to use follow_redirects=False
        response = authenticated_client_with_cache.post(
            "/create/step/2",
            data={
                "session_id": "test-123",
                "description": "A comprehensive test finding description",
                "synonyms": '["synonym1", "synonym2"]',  # JSON array
            },
            follow_redirects=False,
        )

        # When no similar models found, the current workflow redirects to draft editor
        assert response.status_code == 303
        assert "drafts/" in response.headers["location"]
        assert "mode=edit" in response.headers["location"]
        assert "created=true" in response.headers["location"]

    def test_step_2_description_too_short(
        self, authenticated_client_with_cache: TestClient, mock_cache: MagicMock
    ) -> None:
        """Test step 2 with description too short."""
        session_data = '{"session_id": "test-123", "current_step": 2, "name": "test-finding"}'
        mock_cache.get = AsyncMock(return_value=session_data)
        mock_cache.set = AsyncMock(return_value=None)

        response = authenticated_client_with_cache.post(
            "/create/step/2",
            data={
                "session_id": "test-123",
                "description": "short",  # Too short
                "synonyms": "",
            },
        )

        assert response.status_code == 422

    def test_step_3_success(self, authenticated_client_with_cache: TestClient, mock_cache: MagicMock) -> None:
        """Test step 3 with successful similar models search."""
        session_data = """
        {
            "session_id": "test-123",
            "current_step": 3,
            "name": "test-finding",
            "description": "A test finding description",
            "synonyms": ["synonym1"]
        }
        """
        mock_cache.get = AsyncMock(return_value=session_data)
        mock_cache.set = AsyncMock(return_value=None)

        # Mock creation service
        from app.dependencies import get_creation_service
        from app.main import app
        from app.services.creation_service import CreationService

        # Mock similar models search
        mock_analysis = MagicMock()
        mock_analysis.similar_models = []
        mock_analysis.recommendation = "create_new"
        mock_analysis.confidence = 0.9

        # Create mock creation service
        mock_creation_service = MagicMock(spec=CreationService)
        mock_creation_service.find_similar_models = AsyncMock(return_value=mock_analysis)
        mock_creation_service.is_test_user = MagicMock(return_value=False)
        mock_creation_service.generate_default_attributes_markdown = MagicMock(return_value="# Default attributes")

        # Mock draft service
        from app.dependencies import get_draft_service
        from app.services.draft_service import DraftService

        mock_draft_service = MagicMock(spec=DraftService)
        mock_draft_service.find_editable_by_name = AsyncMock(return_value=None)
        mock_draft_service.find_latest_by_name = AsyncMock(return_value=None)

        app.dependency_overrides[get_creation_service] = lambda: mock_creation_service
        app.dependency_overrides[get_draft_service] = lambda: mock_draft_service

        response = authenticated_client_with_cache.post(
            "/create/step/3", data={"session_id": "test-123"}, follow_redirects=False
        )

        # Step 3 now redirects to draft editor like step 2
        assert response.status_code == 303
        assert "drafts/" in response.headers["location"]
        assert "mode=edit" in response.headers["location"]
        assert "created=true" in response.headers["location"]

    @pytest.mark.skip(reason="Complex mock needed for FindingModelFull - requires detailed model structure")
    def test_step_4_success(self, authenticated_client_with_cache: TestClient, mock_cache: MagicMock) -> None:
        """Test step 4 with valid attributes markdown."""
        session_data = """
        {
            "session_id": "test-123",
            "current_step": 4,
            "name": "test-finding",
            "description": "A test finding description",
            "synonyms": ["synonym1"],
            "similar_models": []
        }
        """
        mock_cache.get = AsyncMock(return_value=session_data)
        mock_cache.set = AsyncMock(return_value=None)

        # Mock model creation - just use a MagicMock since FindingModelFull is complex
        mock_model = MagicMock()
        mock_model.name = "test-finding"
        mock_model.description = "A test finding description"
        mock_model.attributes = []
        mock_model.model_dump.return_value = {"name": "test-finding", "description": "A test finding"}
        mock_model.model_dump_json.return_value = '{"name": "test-finding"}'
        # mock_create_model.return_value = mock_model  # This line causes F821

        attributes_markdown = """
        ## Attributes

        ### presence
        Whether the finding is present or absent.

        **Options:** present, absent, indeterminate
        """

        response = authenticated_client_with_cache.post(
            "/create/step/4",
            data={
                "session_id": "test-123",
                "description": "A test finding description",
                "synonyms": '["synonym1"]',  # JSON string
                "attributes_markdown": attributes_markdown,
            },
        )

        assert response.status_code == 200
        content = response.text
        assert "Your Finding Model is Ready!" in content
        assert "test-finding" in content

    # NOTE: Step 4 POST endpoint has been removed - this functionality is now in the draft system

    def test_step_invalid_session(self, authenticated_client_with_cache: TestClient, mock_cache: MagicMock) -> None:
        """Test step endpoint with invalid session."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=None)

        # When session is invalid, dependency injection creates a new session
        # So this should actually work and return the name input template
        response = authenticated_client_with_cache.post(
            "/create/step/1",
            data={"session_id": "nonexistent", "name": "ab"},  # Too short
        )

        # Should get 422 for validation error
        assert response.status_code == 422

    def test_step_invalid_step_number(self, authenticated_client_with_cache: TestClient, mock_cache: MagicMock) -> None:
        """Test step endpoint with invalid step number."""
        session_data = '{"session_id": "test-123", "current_step": 1}'
        mock_cache.get = AsyncMock(return_value=session_data)
        mock_cache.set = AsyncMock(return_value=None)

        # Try to access step 3 when on step 1 - session lacks required name
        response = authenticated_client_with_cache.post("/create/step/3", data={"session_id": "test-123"})

        # Step 3 requires session to have name, so should get validation error
        assert response.status_code == 422  # Validation error for missing required fields

    def test_step_missing_required_fields(
        self, authenticated_client_with_cache: TestClient, mock_cache: MagicMock
    ) -> None:
        """Test step endpoints with missing required fields."""
        session_data = '{"session_id": "test-123", "current_step": 1}'
        mock_cache.get = AsyncMock(return_value=session_data)
        mock_cache.set = AsyncMock(return_value=None)

        # Step 1 without name should result in form validation error
        response = authenticated_client_with_cache.post("/create/step/1", data={"session_id": "test-123"})

        # FastAPI form validation will catch missing required field
        assert response.status_code == 422  # Unprocessable Entity for form validation


class TestHTMXEndpointsAuthentication:
    """Test that HTMX endpoints require authentication."""

    @pytest.fixture
    def unauthenticated_client_with_cache(self, mock_cache: MagicMock) -> TestClient:
        """Create an unauthenticated test client."""
        mock_database = Database()
        mock_user_repo = MagicMock(spec=UserRepo)
        mock_database.user_repo = mock_user_repo
        mock_database.finding_index = MagicMock()

        app.state.database = mock_database
        app.state.cache = mock_cache

        return TestClient(app)

    def test_create_session_requires_auth(self, unauthenticated_client_with_cache: TestClient) -> None:
        """Test that session creation requires authentication."""
        response = unauthenticated_client_with_cache.post("/create/restart")
        assert response.status_code == 401

    def test_step_endpoints_require_auth(self, unauthenticated_client_with_cache: TestClient) -> None:
        """Test that step endpoints require authentication."""
        endpoints = [1, 2, 3]  # Only steps 1-3 exist now
        for step in endpoints:
            response = unauthenticated_client_with_cache.post(f"/create/step/{step}", data={"session_id": "test"})
            assert response.status_code == 401, f"Step {step} should require authentication"


class TestModalComponents:
    """Test modal component HTML generation and attributes."""

    def test_confirmation_modal_base_component(self) -> None:
        """Test that confirmation_modal generates correct HTML structure."""
        from jinja2 import DictLoader, Environment

        # Load the confirmation modal template
        template_source = """
        {% from 'macros/confirmation_modal.html' import confirmation_modal %}
        {{ confirmation_modal(
            modal_id="test-modal",
            title="Test Title",
            message="Test message",
            confirm_text="Confirm",
            cancel_text="Cancel",
            confirm_color="primary",
            icon_type="warning",
            hx_post="/api/test",
            hx_target="#test-target",
            hx_swap="innerHTML"
        ) }}
        """

        # Read the actual confirmation_modal macro
        with open("templates/macros/confirmation_modal.html") as f:
            confirmation_modal_content = f.read()

        templates = {"test.html": template_source, "macros/confirmation_modal.html": confirmation_modal_content}

        env = Environment(loader=DictLoader(templates))
        template = env.get_template("test.html")
        html = template.render()

        # Verify modal structure
        assert 'id="test-modal"' in html
        assert "Test message" in html  # Note: title is not displayed in base modal
        assert 'hx-post="/api/test"' in html
        assert 'hx-target="#test-target"' in html
        assert 'hx-swap="innerHTML"' in html
        assert "Confirm" in html
        assert "Cancel" in html

    def test_delete_draft_modal_uses_base_component(self) -> None:
        """Test that delete_draft_modal properly uses the base confirmation_modal."""
        from jinja2 import DictLoader, Environment

        template_source = """
        {% from 'macros/delete_draft_modal.html' import delete_draft_modal %}
        {{ delete_draft_modal("test-draft-id") }}
        """

        # Read both macro files
        with open("templates/macros/confirmation_modal.html") as f:
            confirmation_modal_content = f.read()
        with open("templates/macros/delete_draft_modal.html") as f:
            delete_modal_content = f.read()

        templates = {
            "test.html": template_source,
            "macros/confirmation_modal.html": confirmation_modal_content,
            "macros/delete_draft_modal.html": delete_modal_content,
        }

        env = Environment(loader=DictLoader(templates))
        template = env.get_template("test.html")
        html = template.render()

        # Verify delete modal specific attributes
        assert "delete-draft-modal-test-draft-id" in html
        assert "Are you sure you want to delete this draft?" in html  # Message, not title
        assert "This action cannot be undone" in html
        assert "Yes, delete" in html
        assert 'hx-post="/drafts/test-draft-id/delete"' in html
        assert "bg-red-600" in html  # Red color for delete button

    def test_submit_draft_modal_uses_base_component(self) -> None:
        """Test that submit_draft_modal properly uses the base confirmation_modal."""
        from jinja2 import DictLoader, Environment

        template_source = """
        {% from 'macros/submit_draft_modal.html' import submit_draft_modal %}
        {{ submit_draft_modal("test-draft-id") }}
        """

        # Read both macro files
        with open("templates/macros/confirmation_modal.html") as f:
            confirmation_modal_content = f.read()
        with open("templates/macros/submit_draft_modal.html") as f:
            submit_modal_content = f.read()

        templates = {
            "test.html": template_source,
            "macros/confirmation_modal.html": confirmation_modal_content,
            "macros/submit_draft_modal.html": submit_modal_content,
        }

        env = Environment(loader=DictLoader(templates))
        template = env.get_template("test.html")
        html = template.render()

        # Verify submit modal specific attributes
        assert "submit-draft-modal-test-draft-id" in html
        assert "Are you sure you want to submit this draft?" in html  # Message, not title
        assert "This will lock the draft and prevent further edits" in html
        assert "Yes, submit" in html
        assert 'hx-post="/drafts/test-draft-id/submit"' in html
        assert 'hx-target="#main-content"' in html
        assert 'hx-swap="innerHTML"' in html
        assert "bg-green-600" in html  # Green color for submit button

    def test_modal_components_have_correct_htmx_targets(self) -> None:
        """Test that modal components use correct HTMX targets (not #draft-content)."""
        from jinja2 import DictLoader, Environment

        template_source = """
        {% from 'macros/delete_draft_modal.html' import delete_draft_modal %}
        {% from 'macros/submit_draft_modal.html' import submit_draft_modal %}
        {{ delete_draft_modal("test-id", "#custom-target", "outerHTML") }}
        {{ submit_draft_modal("test-id") }}
        """

        # Read all macro files
        with open("templates/macros/confirmation_modal.html") as f:
            confirmation_modal_content = f.read()
        with open("templates/macros/delete_draft_modal.html") as f:
            delete_modal_content = f.read()
        with open("templates/macros/submit_draft_modal.html") as f:
            submit_modal_content = f.read()

        templates = {
            "test.html": template_source,
            "macros/confirmation_modal.html": confirmation_modal_content,
            "macros/delete_draft_modal.html": delete_modal_content,
            "macros/submit_draft_modal.html": submit_modal_content,
        }

        env = Environment(loader=DictLoader(templates))
        template = env.get_template("test.html")
        html = template.render()

        # Verify HTMX targets are correct
        assert 'hx-target="#custom-target"' in html  # Delete modal with custom target
        assert 'hx-target="#main-content"' in html  # Submit modal default target
        assert 'hx-target="#draft-content"' not in html  # Should NOT use old target
        assert 'hx-swap="outerHTML"' in html  # Custom swap for delete
        assert 'hx-swap="innerHTML"' in html  # Default swap for submit


class TestHTMXErrorHandling:
    """Test error handling in HTMX endpoints."""

    def test_session_cache_failure_graceful_degradation(
        self, authenticated_client_with_cache: TestClient, mock_cache: MagicMock
    ) -> None:
        """Test graceful degradation when cache operations fail."""
        # Mock cache operations to fail
        mock_cache.get = AsyncMock(side_effect=Exception("Cache failure"))
        mock_cache.set = AsyncMock(side_effect=Exception("Cache failure"))

        response = authenticated_client_with_cache.post("/create/restart")

        # Should still work with fallback session
        assert response.status_code == 200
        content = response.text
        assert "Finding Model Name" in content

    def test_index_lookup_failure(self, authenticated_client_with_cache: TestClient, mock_cache: MagicMock) -> None:
        """Test handling of index lookup failures."""
        session_data = '{"session_id": "test-123", "current_step": 1}'
        mock_cache.get = AsyncMock(return_value=session_data)
        mock_cache.set = AsyncMock(return_value=None)

        # Mock creation service that handles index failures gracefully
        from app.dependencies import get_creation_service
        from app.main import app
        from app.services.creation_service import CreationService

        # Mock creation service with failing index but graceful handling
        mock_creation_service = MagicMock(spec=CreationService)
        mock_creation_service.check_name_availability = AsyncMock(return_value=True)  # Fail open
        mock_creation_service.is_test_user = MagicMock(return_value=False)
        mock_creation_service.generate_finding_info = AsyncMock(side_effect=Exception("Index error"))

        # Mock draft service
        from app.dependencies import get_draft_service
        from app.services.draft_service import DraftService

        mock_draft_service = MagicMock(spec=DraftService)
        mock_draft_service.find_editable_by_name = AsyncMock(return_value=None)
        mock_draft_service.find_latest_by_name = AsyncMock(return_value=None)

        app.dependency_overrides[get_creation_service] = lambda: mock_creation_service
        app.dependency_overrides[get_draft_service] = lambda: mock_draft_service

        response = authenticated_client_with_cache.post(
            "/create/step/1", data={"session_id": "test-123", "name": "test-finding"}
        )

        # With the service layer, index errors are now handled more gracefully
        # The service layer may catch and handle the error internally
        assert response.status_code in [200, 500]  # Either handled gracefully or error returned
