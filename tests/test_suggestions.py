"""Integration tests for suggestion submission endpoint.

NOTE: These tests mock the template response since the suggestion_alert.html template
is created in the frontend implementation phase. We're testing the backend logic here.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.responses import HTMLResponse

from app.auth import get_optional_user
from app.config import settings
from app.database import SuggestionRepo
from app.dependencies import get_suggestion_repo
from app.main import app
from app.models import User


class TestSuggestionEndpoint:
    """Test suggestion submission endpoint."""

    @pytest.fixture(autouse=True)
    def mock_template_response(self):
        """Mock template rendering to avoid template not found errors."""
        with patch("app.routers.home.templates.TemplateResponse") as mock:
            # Return a simple HTML response that includes the context data
            def make_response(request, name, context):
                # Create response that includes context info for verification
                success = context.get("success", False)
                message = context.get("message", "")
                html = f"<div>{'success' if success else 'error'}: {message}</div>"
                return HTMLResponse(content=html)

            mock.side_effect = make_response
            yield mock

    @pytest.fixture
    def mock_suggestion_repo(self) -> SuggestionRepo:
        """Mock SuggestionRepo."""
        repo = MagicMock(spec=SuggestionRepo)
        repo.create = AsyncMock(return_value="507f1f77bcf86cd799439011")
        return repo

    @pytest.fixture
    def authenticated_user(self) -> User:
        """Mock authenticated user."""
        return User(
            id=12345,
            login="testuser",
            name="Test User",
            email="test@example.com",
            avatar_url="https://github.com/images/error/testuser_happy.gif",
            html_url="https://github.com/testuser",
            is_active=True,
            organizations=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.fixture
    def authenticated_client(self, mock_suggestion_repo: SuggestionRepo, authenticated_user: User) -> TestClient:
        """Create authenticated test client."""
        # Override dependencies
        app.dependency_overrides[get_suggestion_repo] = lambda: mock_suggestion_repo
        app.dependency_overrides[get_optional_user] = lambda: authenticated_user

        client = TestClient(app)
        yield client

        # Cleanup
        app.dependency_overrides.clear()

    @pytest.fixture
    def anonymous_client(self, mock_suggestion_repo: SuggestionRepo) -> TestClient:
        """Create anonymous test client."""
        # Override dependencies
        app.dependency_overrides[get_suggestion_repo] = lambda: mock_suggestion_repo
        app.dependency_overrides[get_optional_user] = lambda: None

        client = TestClient(app)
        yield client

        # Cleanup
        app.dependency_overrides.clear()

    def test_submit_as_authenticated_user(
        self, authenticated_client: TestClient, mock_suggestion_repo: SuggestionRepo, authenticated_user: User
    ) -> None:
        """Test POST as authenticated user (user_id + email populated from session)."""
        response = authenticated_client.post(
            "/suggestions", data={"content": "This is a suggestion from authenticated user"}
        )

        # Should return success (200 OK for HTML response)
        assert response.status_code == 200

        # Verify repo.create was called with correct parameters
        mock_suggestion_repo.create.assert_called_once_with(
            content="This is a suggestion from authenticated user",
            user_id=authenticated_user.id,
            submitter_email=authenticated_user.email,
        )

        # Verify success message in HTML
        html_content = response.text
        assert "success" in html_content.lower() or "thanks" in html_content.lower()
        assert "notify you" in html_content.lower()  # Has email, so should mention notification

    def test_submit_as_anonymous_with_email(
        self, anonymous_client: TestClient, mock_suggestion_repo: SuggestionRepo
    ) -> None:
        """Test POST as anonymous with email (user_id=None, email from form)."""
        response = anonymous_client.post(
            "/suggestions",
            data={"content": "Anonymous suggestion with email", "submitter_email": "anon@example.com"},
        )

        # Should return success
        assert response.status_code == 200

        # Verify repo.create was called with correct parameters
        mock_suggestion_repo.create.assert_called_once_with(
            content="Anonymous suggestion with email", user_id=None, submitter_email="anon@example.com"
        )

        # Verify success message mentions notification (has email)
        html_content = response.text
        assert "success" in html_content.lower() or "thanks" in html_content.lower()
        assert "notify you" in html_content.lower()

    def test_submit_as_anonymous_without_email(
        self, anonymous_client: TestClient, mock_suggestion_repo: SuggestionRepo
    ) -> None:
        """Test POST as anonymous without email (both None)."""
        response = anonymous_client.post("/suggestions", data={"content": "Completely anonymous suggestion"})

        # Should return success
        assert response.status_code == 200

        # Verify repo.create was called with correct parameters
        mock_suggestion_repo.create.assert_called_once_with(
            content="Completely anonymous suggestion", user_id=None, submitter_email=None
        )

        # Verify success message does NOT mention notification (no email)
        html_content = response.text
        assert "success" in html_content.lower() or "thanks" in html_content.lower()
        assert "review it soon" in html_content.lower()  # Generic message, no notification

    def test_invalid_email_format(self, anonymous_client: TestClient, mock_suggestion_repo: SuggestionRepo) -> None:
        """Test invalid email format returns error alert HTML."""
        response = anonymous_client.post(
            "/suggestions", data={"content": "Test suggestion", "submitter_email": "not-an-email"}
        )

        # Should return 200 with error HTML (not raising exception)
        assert response.status_code == 200

        # Verify repo.create was NOT called
        mock_suggestion_repo.create.assert_not_called()

        # Verify error message in HTML
        html_content = response.text
        assert "invalid" in html_content.lower() or "error" in html_content.lower()
        assert "email" in html_content.lower()

    def test_content_empty_validation(self, anonymous_client: TestClient) -> None:
        """Test empty content returns error."""
        response = anonymous_client.post("/suggestions", data={"content": ""})

        # FastAPI validation should catch this with 422
        assert response.status_code == 422

    def test_content_too_long_validation(self, anonymous_client: TestClient) -> None:
        """Test content >300 chars returns error."""
        long_content = "x" * 301  # 301 characters
        response = anonymous_client.post("/suggestions", data={"content": long_content})

        # FastAPI validation should catch this with 422
        assert response.status_code == 422

    def test_content_valid_length(self, anonymous_client: TestClient, mock_suggestion_repo: SuggestionRepo) -> None:
        """Test valid content length (1-300 chars) succeeds."""
        # Test minimum length
        response = anonymous_client.post("/suggestions", data={"content": "a"})
        assert response.status_code == 200
        mock_suggestion_repo.create.assert_called()

        # Reset mock
        mock_suggestion_repo.create.reset_mock()

        # Test maximum length
        max_content = "x" * 300
        response = anonymous_client.post("/suggestions", data={"content": max_content})
        assert response.status_code == 200
        mock_suggestion_repo.create.assert_called()

    def test_alert_html_structure_success(
        self, authenticated_client: TestClient, mock_suggestion_repo: SuggestionRepo
    ) -> None:
        """Test alert HTML structure for success case."""
        response = authenticated_client.post("/suggestions", data={"content": "Test suggestion"})

        assert response.status_code == 200
        html_content = response.text

        # Verify it's rendering the suggestion_alert.html template
        # The template should have context with success=True and a message
        assert len(html_content) > 0  # Non-empty response

    def test_alert_html_structure_error(
        self, anonymous_client: TestClient, mock_suggestion_repo: SuggestionRepo
    ) -> None:
        """Test alert HTML structure for error case."""
        response = anonymous_client.post("/suggestions", data={"content": "Test", "submitter_email": "invalid-email"})

        assert response.status_code == 200
        html_content = response.text

        # Verify error context is passed
        assert len(html_content) > 0
        assert "invalid" in html_content.lower() or "error" in html_content.lower()

    def test_email_validation_accepts_valid_formats(
        self, anonymous_client: TestClient, mock_suggestion_repo: SuggestionRepo
    ) -> None:
        """Test various valid email formats are accepted."""
        valid_emails = [
            "user@example.com",
            "test.user@example.co.uk",
            "user+tag@example.com",
            "123@example.com",
        ]

        for email in valid_emails:
            mock_suggestion_repo.create.reset_mock()
            response = anonymous_client.post("/suggestions", data={"content": "Test", "submitter_email": email})

            assert response.status_code == 200, f"Failed for email: {email}"
            mock_suggestion_repo.create.assert_called_once()
            # Verify email was passed correctly
            call_kwargs = mock_suggestion_repo.create.call_args[1]
            assert call_kwargs["submitter_email"] == email

    def test_email_validation_rejects_invalid_formats(
        self, anonymous_client: TestClient, mock_suggestion_repo: SuggestionRepo
    ) -> None:
        """Test various invalid email formats are rejected."""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user @example.com",
            "user@example",
        ]

        for email in invalid_emails:
            mock_suggestion_repo.create.reset_mock()
            response = anonymous_client.post("/suggestions", data={"content": "Test", "submitter_email": email})

            # Should return error HTML (200 with error message)
            assert response.status_code == 200, f"Should return 200 for email: {email}"
            # Verify create was NOT called
            mock_suggestion_repo.create.assert_not_called(), f"create() should not be called for email: {email}"


class TestSuggestionRepo:
    """Unit tests for SuggestionRepo class."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Mock database."""
        db = MagicMock()
        db.suggestions = MagicMock()
        db.suggestions.insert_one = AsyncMock()
        return db

    @pytest.fixture
    def suggestion_repo(self, mock_db: MagicMock) -> SuggestionRepo:
        """SuggestionRepo instance with mocked database."""
        return SuggestionRepo(mock_db)

    async def test_create_authenticated_user(self, suggestion_repo: SuggestionRepo, mock_db: MagicMock) -> None:
        """Test creating suggestion with authenticated user (user_id populated, email from session)."""
        # Mock insert result
        mock_result = MagicMock()
        mock_result.inserted_id = "507f1f77bcf86cd799439011"
        mock_db.suggestions.insert_one.return_value = mock_result

        # Create suggestion as authenticated user
        suggestion_id = await suggestion_repo.create(
            content="This is a suggestion from authenticated user",
            user_id=12345,
            submitter_email="user@example.com",
        )

        # Verify result
        assert suggestion_id == "507f1f77bcf86cd799439011"

        # Verify insert was called with correct structure
        mock_db.suggestions.insert_one.assert_called_once()
        call_args = mock_db.suggestions.insert_one.call_args[0][0]

        # Verify exactly 4 fields: content, user_id, submitter_email, created_at
        assert len(call_args) == 4
        assert "content" in call_args
        assert "user_id" in call_args
        assert "submitter_email" in call_args
        assert "created_at" in call_args

        # Verify field values
        assert call_args["content"] == "This is a suggestion from authenticated user"
        assert call_args["user_id"] == 12345
        assert call_args["submitter_email"] == "user@example.com"
        assert isinstance(call_args["created_at"], datetime)

        # Verify no extra fields (no status, notes, etc.)
        assert "status" not in call_args
        assert "notes" not in call_args
        assert "updated_at" not in call_args

    async def test_create_anonymous_with_email(self, suggestion_repo: SuggestionRepo, mock_db: MagicMock) -> None:
        """Test creating suggestion with anonymous user + email (user_id=None, email from form)."""
        mock_result = MagicMock()
        mock_result.inserted_id = "507f1f77bcf86cd799439012"
        mock_db.suggestions.insert_one.return_value = mock_result

        # Create suggestion as anonymous with email
        suggestion_id = await suggestion_repo.create(
            content="Anonymous suggestion with email", user_id=None, submitter_email="anon@example.com"
        )

        # Verify result
        assert suggestion_id == "507f1f77bcf86cd799439012"

        # Verify insert structure
        mock_db.suggestions.insert_one.assert_called_once()
        call_args = mock_db.suggestions.insert_one.call_args[0][0]

        # Verify exactly 4 fields
        assert len(call_args) == 4
        assert call_args["content"] == "Anonymous suggestion with email"
        assert call_args["user_id"] is None
        assert call_args["submitter_email"] == "anon@example.com"
        assert isinstance(call_args["created_at"], datetime)

    async def test_create_anonymous_without_email(self, suggestion_repo: SuggestionRepo, mock_db: MagicMock) -> None:
        """Test creating suggestion with anonymous user without email (both None)."""
        mock_result = MagicMock()
        mock_result.inserted_id = "507f1f77bcf86cd799439013"
        mock_db.suggestions.insert_one.return_value = mock_result

        # Create suggestion as anonymous without email
        suggestion_id = await suggestion_repo.create(
            content="Completely anonymous suggestion", user_id=None, submitter_email=None
        )

        # Verify result
        assert suggestion_id == "507f1f77bcf86cd799439013"

        # Verify insert structure
        mock_db.suggestions.insert_one.assert_called_once()
        call_args = mock_db.suggestions.insert_one.call_args[0][0]

        # Verify exactly 4 fields with both user_id and email as None
        assert len(call_args) == 4
        assert call_args["content"] == "Completely anonymous suggestion"
        assert call_args["user_id"] is None
        assert call_args["submitter_email"] is None
        assert isinstance(call_args["created_at"], datetime)

    async def test_create_field_count_validation(self, suggestion_repo: SuggestionRepo, mock_db: MagicMock) -> None:
        """Test that created document has exactly 4 fields, no more, no less."""
        mock_result = MagicMock()
        mock_result.inserted_id = "507f1f77bcf86cd799439014"
        mock_db.suggestions.insert_one.return_value = mock_result

        await suggestion_repo.create(content="Field count test", user_id=99, submitter_email="test@example.com")

        call_args = mock_db.suggestions.insert_one.call_args[0][0]

        # Strict field count check
        expected_fields = {"content", "user_id", "submitter_email", "created_at"}
        actual_fields = set(call_args.keys())

        assert actual_fields == expected_fields, f"Expected exactly {expected_fields}, got {actual_fields}"

    async def test_created_at_timestamp(self, suggestion_repo: SuggestionRepo, mock_db: MagicMock) -> None:
        """Test that created_at is a UTC datetime."""
        mock_result = MagicMock()
        mock_result.inserted_id = "507f1f77bcf86cd799439015"
        mock_db.suggestions.insert_one.return_value = mock_result

        before = datetime.now(UTC)
        await suggestion_repo.create(content="Timestamp test", user_id=1, submitter_email="test@example.com")
        after = datetime.now(UTC)

        call_args = mock_db.suggestions.insert_one.call_args[0][0]
        created_at = call_args["created_at"]

        # Verify it's a datetime with UTC timezone
        assert isinstance(created_at, datetime)
        assert created_at.tzinfo == UTC
        # Verify it's between before and after (reasonable timestamp)
        assert before <= created_at <= after


@pytest.mark.integration
class TestSuggestionRepoIntegration:
    """Integration tests with real MongoDB database."""

    async def test_create_suggestion_in_database(self) -> None:
        """Verify suggestion is stored in database with correct field structure."""
        # Connect to real database
        client = AsyncIOMotorClient(settings.mongodb_uri)
        db = client[settings.mongodb_db]
        col = db.suggestions

        # Clean up any existing test data
        await col.delete_many({"content": "Integration test suggestion"})

        try:
            # Create real repository
            repo = SuggestionRepo(db)

            # Create suggestion
            suggestion_id = await repo.create(content="Integration test suggestion", user_id=None, submitter_email=None)

            assert suggestion_id is not None

            # Verify document in database
            await db.command("ping")  # Ensure write is committed
            doc = await col.find_one({"content": "Integration test suggestion"})

            assert doc is not None, "Suggestion document should exist in database"

            # Verify exactly 4 fields (plus _id from MongoDB)
            # MongoDB adds _id, so we expect 5 total
            assert len(doc) == 5, f"Expected 5 fields (including _id), got {len(doc)}: {list(doc.keys())}"

            # Verify required fields
            assert "content" in doc
            assert "user_id" in doc
            assert "submitter_email" in doc
            assert "created_at" in doc
            assert "_id" in doc

            # Verify field values for anonymous submission
            assert doc["content"] == "Integration test suggestion"
            assert doc["user_id"] is None
            assert doc["submitter_email"] is None
            assert isinstance(doc["created_at"], datetime)
            # MongoDB may strip timezone info, but the timestamp should be recent
            from datetime import timedelta

            assert datetime.now(UTC) - doc["created_at"].replace(tzinfo=UTC) < timedelta(seconds=5)

            # Verify no extra fields
            assert "status" not in doc
            assert "notes" not in doc
            assert "updated_at" not in doc

        finally:
            # Cleanup
            await col.delete_many({"content": "Integration test suggestion"})
            client.close()

    async def test_create_authenticated_suggestion(self) -> None:
        """Verify authenticated user's ID and email are stored correctly."""
        client = AsyncIOMotorClient(settings.mongodb_uri)
        db = client[settings.mongodb_db]
        col = db.suggestions

        # Clean up
        await col.delete_many({"content": "Authenticated integration test"})

        try:
            repo = SuggestionRepo(db)

            # Create suggestion with user info
            suggestion_id = await repo.create(
                content="Authenticated integration test", user_id=99999, submitter_email="integration@example.com"
            )

            assert suggestion_id is not None

            # Verify document
            await db.command("ping")
            doc = await col.find_one({"content": "Authenticated integration test"})

            assert doc is not None
            assert doc["user_id"] == 99999
            assert doc["submitter_email"] == "integration@example.com"
            assert doc["content"] == "Authenticated integration test"
            assert isinstance(doc["created_at"], datetime)

            # Verify field count
            assert len(doc) == 5  # 4 fields + _id

        finally:
            # Cleanup
            await col.delete_many({"content": "Authenticated integration test"})
            client.close()

    async def test_create_anonymous_with_email(self) -> None:
        """Verify anonymous user with email is stored correctly."""
        client = AsyncIOMotorClient(settings.mongodb_uri)
        db = client[settings.mongodb_db]
        col = db.suggestions

        # Clean up
        await col.delete_many({"content": "Anonymous with email test"})

        try:
            repo = SuggestionRepo(db)

            # Create suggestion with email but no user_id
            suggestion_id = await repo.create(
                content="Anonymous with email test", user_id=None, submitter_email="anon@example.com"
            )

            assert suggestion_id is not None

            # Verify document
            await db.command("ping")
            doc = await col.find_one({"content": "Anonymous with email test"})

            assert doc is not None
            assert doc["user_id"] is None
            assert doc["submitter_email"] == "anon@example.com"
            assert doc["content"] == "Anonymous with email test"
            assert isinstance(doc["created_at"], datetime)

            # Verify field count
            assert len(doc) == 5

        finally:
            # Cleanup
            await col.delete_many({"content": "Anonymous with email test"})
            client.close()
