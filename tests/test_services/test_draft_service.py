"""Test the DraftService class."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database import DraftRepo, UserRepo
from app.models import Comment, DraftStatus, FindingModelDraft, FindingModelInputs, User
from app.services import NotFoundError
from app.services.comment_service import CommentService
from app.services.draft_service import DraftService


class TestDraftService:
    """Test the DraftService class."""

    @pytest.fixture
    def mock_draft_repo(self) -> MagicMock:
        """Mock draft repository."""
        repo = MagicMock(spec=DraftRepo)
        repo.list_for_user = AsyncMock()
        repo.get_draft = AsyncMock()
        repo.delete_draft = AsyncMock()
        repo.submit = AsyncMock()
        return repo

    @pytest.fixture
    def mock_user_repo(self) -> MagicMock:
        """Mock user repository."""
        repo = MagicMock(spec=UserRepo)
        repo.collection = MagicMock()
        repo.collection.find_one = AsyncMock()
        repo.collection.update_one = AsyncMock()
        return repo

    @pytest.fixture
    def mock_database(self) -> MagicMock:
        """Mock database for DraftService."""
        from app.database import Database

        db = MagicMock(spec=Database)
        db.ensure_person_for_user = AsyncMock(return_value=None)
        db.people = {}
        return db

    @pytest.fixture
    def mock_comment_service(self) -> MagicMock:
        """Mock comment service."""
        service = MagicMock(spec=CommentService)
        service.get_thread = AsyncMock()
        service.add_comment = AsyncMock()
        service.report_comment = AsyncMock()
        return service

    @pytest.fixture
    def service(
        self,
        mock_draft_repo: MagicMock,
        mock_user_repo: MagicMock,
        mock_database: MagicMock,
        mock_comment_service: MagicMock,
    ) -> DraftService:
        """DraftService instance with mocked dependencies."""
        return DraftService(
            draft_repo=mock_draft_repo,
            user_repo=mock_user_repo,
            database=mock_database,
            comment_service=mock_comment_service,
        )

    @pytest.fixture
    def sample_user(self) -> User:
        now = datetime.now(UTC)
        return User(
            id=111,
            login="tester",
            name="Tester",
            email="tester@example.com",
            avatar_url="https://example.com/avatar.png",
            html_url=None,
            organizations=[],
            created_at=now,
            updated_at=now,
            comment_index=[],
        )

    @pytest.fixture
    def sample_draft(self) -> FindingModelDraft:
        """Sample draft for testing."""
        now = datetime.now(UTC)
        return FindingModelDraft(
            id="507f1f77bcf86cd799439011",
            user_id=12345,
            name="Test Finding",
            created_at=now,
            updated_at=now,
            inputs=FindingModelInputs(
                description="Test description",
                synonyms=["synonym1", "synonym2"],
                attributes_markdown="### presence\n\n- absent\n- present",
            ),
            status=DraftStatus.DRAFT,
            action_log=[],
            generated_json=None,
        )

    async def test_get_drafts_for_user_success(
        self, service: DraftService, mock_draft_repo: MagicMock, sample_draft: FindingModelDraft
    ):
        """Test getting drafts for user successfully."""
        # Setup
        user_id = 12345
        mock_draft_repo.list_for_user.return_value = [sample_draft]

        # Test
        result = await service.get_drafts_for_user(user_id)

        # Assertions
        assert len(result) == 1
        draft_dict = result[0]
        assert draft_dict["id"] == "507f1f77bcf86cd799439011"
        assert draft_dict["name"] == "Test Finding"
        assert draft_dict["status"] == "draft"
        assert draft_dict["slug"] == "test-finding"
        assert draft_dict["has_generated"] is False
        assert "ago" in draft_dict["updated_display"] or "now" in draft_dict["updated_display"]
        mock_draft_repo.list_for_user.assert_called_once_with(user_id)

    async def test_get_drafts_for_user_error_handling(self, service: DraftService, mock_draft_repo: MagicMock):
        """Test getting drafts for user with error handling."""
        # Setup: Repository throws exception
        user_id = 12345
        mock_draft_repo.list_for_user.side_effect = Exception("Database error")

        # Test
        result = await service.get_drafts_for_user(user_id)

        # Assertions
        assert result == []

    async def test_get_draft_by_id_success(
        self, service: DraftService, mock_draft_repo: MagicMock, sample_draft: FindingModelDraft
    ):
        """Test getting draft by ID successfully."""
        # Setup
        draft_id = "507f1f77bcf86cd799439011"
        user_id = 12345
        mock_draft_repo.get_draft.return_value = sample_draft

        # Test
        result = await service.get_draft_by_id(draft_id, user_id)

        # Assertions
        assert result == sample_draft
        mock_draft_repo.get_draft.assert_called_once_with(draft_id, user_id)

    async def test_get_draft_by_id_not_found(self, service: DraftService, mock_draft_repo: MagicMock):
        """Test getting draft by ID when not found."""
        # Setup
        draft_id = "507f1f77bcf86cd799439011"
        user_id = 12345
        mock_draft_repo.get_draft.return_value = None

        # Test
        with pytest.raises(NotFoundError, match="Draft 507f1f77bcf86cd799439011 not found"):
            await service.get_draft_by_id(draft_id, user_id)

    async def test_get_draft_by_id_authorization_error(
        self, service: DraftService, mock_draft_repo: MagicMock, sample_draft: FindingModelDraft
    ):
        """Test getting draft by ID with wrong user."""
        # Setup
        draft_id = "507f1f77bcf86cd799439011"
        wrong_user_id = 99999
        # Repository returns None when user doesn't own the draft
        mock_draft_repo.get_draft.return_value = None

        # Test
        with pytest.raises(NotFoundError, match="Draft 507f1f77bcf86cd799439011 not found"):
            await service.get_draft_by_id(draft_id, wrong_user_id)

    async def test_get_draft_by_id_repository_error(self, service: DraftService, mock_draft_repo: MagicMock):
        """Test getting draft by ID with repository error."""
        # Setup
        draft_id = "507f1f77bcf86cd799439011"
        user_id = 12345
        mock_draft_repo.get_draft.side_effect = Exception("Database error")

        # Test
        with pytest.raises(NotFoundError, match="Error retrieving draft"):
            await service.get_draft_by_id(draft_id, user_id)

    async def test_delete_draft_success(
        self, service: DraftService, mock_draft_repo: MagicMock, sample_draft: FindingModelDraft
    ):
        """Test deleting draft successfully."""
        # Setup
        draft_id = "507f1f77bcf86cd799439011"
        user_id = 12345
        mock_draft_repo.get_draft.return_value = sample_draft
        mock_draft_repo.delete_draft.return_value = True

        # Test
        result = await service.delete_draft(draft_id, user_id)

        # Assertions
        assert result is True
        mock_draft_repo.get_draft.assert_called_once_with(draft_id, user_id)
        mock_draft_repo.delete_draft.assert_called_once_with(draft_id, user_id)

    async def test_delete_draft_not_found(self, service: DraftService, mock_draft_repo: MagicMock):
        """Test deleting draft that doesn't exist."""
        # Setup
        draft_id = "507f1f77bcf86cd799439011"
        user_id = 12345
        mock_draft_repo.get_draft.return_value = None

        # Test
        with pytest.raises(NotFoundError, match="Draft 507f1f77bcf86cd799439011 not found"):
            await service.delete_draft(draft_id, user_id)

    async def test_delete_draft_authorization_error(
        self, service: DraftService, mock_draft_repo: MagicMock, sample_draft: FindingModelDraft
    ):
        """Test deleting draft with wrong user."""
        # Setup
        draft_id = "507f1f77bcf86cd799439011"
        wrong_user_id = 99999
        # Repository returns None when user doesn't own the draft
        mock_draft_repo.get_draft.return_value = None

        # Test
        with pytest.raises(NotFoundError, match="Draft 507f1f77bcf86cd799439011 not found"):
            await service.delete_draft(draft_id, wrong_user_id)

    async def test_delete_draft_repository_error(
        self, service: DraftService, mock_draft_repo: MagicMock, sample_draft: FindingModelDraft
    ):
        """Test deleting draft with repository error."""
        # Setup
        draft_id = "507f1f77bcf86cd799439011"
        user_id = 12345
        mock_draft_repo.get_draft.return_value = sample_draft
        mock_draft_repo.delete_draft.side_effect = Exception("Database error")

        # Test
        with pytest.raises(NotFoundError, match="Failed to delete draft"):
            await service.delete_draft(draft_id, user_id)

    async def test_submit_draft_success(
        self, service: DraftService, mock_draft_repo: MagicMock, sample_draft: FindingModelDraft
    ):
        """Test submitting draft successfully."""
        # Setup
        draft_id = "507f1f77bcf86cd799439011"
        user_id = 12345
        # Create a submitted version of the draft
        submitted_draft = sample_draft.model_copy(update={"status": DraftStatus.SUBMITTED})

        mock_draft_repo.get_draft.return_value = sample_draft
        mock_draft_repo.submit.return_value = submitted_draft

        # Test
        result = await service.submit_draft(draft_id, user_id)

        # Assertions
        assert result == submitted_draft
        mock_draft_repo.get_draft.assert_called_once_with(draft_id, user_id)
        mock_draft_repo.submit.assert_called_once_with(draft_id, user_id)

    async def test_submit_draft_not_found(self, service: DraftService, mock_draft_repo: MagicMock):
        """Test submitting draft that doesn't exist."""
        # Setup
        draft_id = "507f1f77bcf86cd799439011"
        user_id = 12345
        mock_draft_repo.get_draft.return_value = None

        # Test
        with pytest.raises(NotFoundError, match="Draft 507f1f77bcf86cd799439011 not found"):
            await service.submit_draft(draft_id, user_id)

    async def test_submit_draft_repository_error(
        self, service: DraftService, mock_draft_repo: MagicMock, sample_draft: FindingModelDraft
    ):
        """Test submitting draft with repository error."""
        # Setup
        draft_id = "507f1f77bcf86cd799439011"
        user_id = 12345
        mock_draft_repo.get_draft.return_value = sample_draft
        mock_draft_repo.submit.side_effect = Exception("Database error")

        # Test
        with pytest.raises(NotFoundError, match="Failed to submit draft"):
            await service.submit_draft(draft_id, user_id)

    async def test_list_for_user_by_name_success(
        self, service: DraftService, mock_draft_repo: MagicMock, sample_draft: FindingModelDraft
    ):
        """Test listing drafts for user by name successfully."""
        # Setup
        user_id = 12345
        name = "Test Finding"
        # Service calls list_for_user and filters by name
        mock_draft_repo.list_for_user.return_value = [sample_draft]

        # Test
        result = await service.list_for_user_by_name(user_id, name)

        # Assertions
        assert result == [sample_draft]
        mock_draft_repo.list_for_user.assert_called_once_with(user_id)

    async def test_list_for_user_by_name_error(self, service: DraftService, mock_draft_repo: MagicMock):
        """Test listing drafts for user by name with error."""
        # Setup
        user_id = 12345
        name = "Test Finding"
        mock_draft_repo.list_for_user.side_effect = Exception("Database error")

        # Test
        result = await service.list_for_user_by_name(user_id, name)

        # Assertions
        assert result == []

    @pytest.mark.asyncio
    async def test_get_comments_for_draft_delegates(
        self, service: DraftService, mock_comment_service: MagicMock
    ) -> None:
        thread = MagicMock()
        mock_comment_service.get_thread.return_value = thread

        result = await service.get_comments_for_draft("draft-1")

        mock_comment_service.get_thread.assert_awaited_once_with("draft", "draft-1")
        assert result is thread

    @pytest.mark.asyncio
    async def test_add_comment_to_draft_delegates(
        self,
        service: DraftService,
        mock_comment_service: MagicMock,
        sample_user: User,
    ) -> None:
        comment = Comment(
            user_id=sample_user.id,
            user_name=sample_user.login,
            content="test",
            created_at=datetime.now(UTC),
        )
        mock_comment_service.add_comment.return_value = comment

        result = await service.add_comment_to_draft("draft-1", sample_user, "hello", parent_id="parent")

        mock_comment_service.add_comment.assert_awaited_once_with(
            "draft", "draft-1", sample_user, "hello", parent_id="parent"
        )
        assert result is comment

    @pytest.mark.asyncio
    async def test_report_draft_comment_delegates(self, service: DraftService, mock_comment_service: MagicMock) -> None:
        await service.report_draft_comment("draft-1", "comment-1", 123)

        mock_comment_service.report_comment.assert_awaited_once_with("draft", "draft-1", "comment-1", 123)
