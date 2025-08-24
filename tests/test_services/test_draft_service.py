"""Test the DraftService class."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.database import DraftRepo
from app.models import FindingModelDraft, FindingModelInputs
from app.services import NotFoundError
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
    def service(self, mock_draft_repo: MagicMock) -> DraftService:
        """DraftService instance with mocked dependencies."""
        return DraftService(draft_repo=mock_draft_repo)

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
            status="draft",
            action_log=[],
            generated_json=None,
        )

    @pytest.fixture
    def sample_draft_with_json(self, sample_draft: FindingModelDraft) -> FindingModelDraft:
        """Sample draft with generated JSON."""
        # Simple JSON string that represents valid finding model data
        sample_draft.generated_json = '{"name": "Test Finding", "attributes": [{"name": "presence"}]}'
        return sample_draft

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

    async def test_get_drafts_for_user_with_generated_json(
        self, service: DraftService, mock_draft_repo: MagicMock, sample_draft_with_json: FindingModelDraft
    ):
        """Test getting drafts for user with generated JSON."""
        # Setup
        user_id = 12345
        mock_draft_repo.list_for_user.return_value = [sample_draft_with_json]

        # Mock the extract method to return expected attributes
        with patch.object(service, "extract_attribute_names_from_generated_json", return_value=["presence"]):
            # Test
            result = await service.get_drafts_for_user(user_id)

            # Assertions
            assert len(result) == 1
            draft_dict = result[0]
            assert draft_dict["has_generated"] is True
            assert draft_dict["attribute_names"] == ["presence"]

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
        submitted_draft = sample_draft
        submitted_draft.status = "submitted"

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

    def test_extract_attribute_names_from_generated_json_valid(self, service: DraftService):
        """Test extracting attribute names from valid JSON."""
        # Mock the FindingModelFull validation to avoid complex model setup
        with patch("app.services.draft_service.FindingModelFull") as mock_model:
            mock_instance = MagicMock()
            mock_instance.model_dump.return_value = {
                "name": "Test Finding",
                "attributes": [
                    {"name": "presence", "description": "Presence of finding"},
                    {"name": "size", "description": "Size of finding"},
                ],
            }
            mock_model.model_validate_json.return_value = mock_instance

            # Test
            result = service.extract_attribute_names_from_generated_json('{"test": "json"}')

            # Assertions
            assert result == ["presence", "size"]

    def test_extract_attribute_names_from_generated_json_empty(self, service: DraftService):
        """Test extracting attribute names from empty JSON."""
        # Test
        result = service.extract_attribute_names_from_generated_json(None)

        # Assertions
        assert result == []

    def test_extract_attribute_names_from_generated_json_invalid(self, service: DraftService):
        """Test extracting attribute names from invalid JSON."""
        # Test
        result = service.extract_attribute_names_from_generated_json("invalid json")

        # Assertions
        assert result == []

    def test_extract_attribute_names_from_generated_json_no_attributes(self, service: DraftService):
        """Test extracting attribute names when no attributes present."""
        # Mock the FindingModelFull validation
        with patch("app.services.draft_service.FindingModelFull") as mock_model:
            mock_instance = MagicMock()
            mock_instance.model_dump.return_value = {
                "name": "Test Finding",
                "attributes": [],
            }
            mock_model.model_validate_json.return_value = mock_instance

            # Test
            result = service.extract_attribute_names_from_generated_json('{"test": "json"}')

            # Assertions
            assert result == []

    def test_format_draft_for_display(self, service: DraftService, sample_draft_with_json: FindingModelDraft):
        """Test formatting draft for display."""
        # Mock the extract method to return expected attributes
        with patch.object(service, "extract_attribute_names_from_generated_json", return_value=["presence"]):
            # Test
            result = service.format_draft_for_display(sample_draft_with_json)

            # Assertions
            assert result["id"] == "507f1f77bcf86cd799439011"
            assert result["name"] == "Test Finding"
            assert result["status"] == "draft"
            assert result["slug"] == "test-finding"
            assert result["has_generated"] is True
            assert result["attribute_names"] == ["presence"]
            assert "updated_at" in result
            assert "updated_display" in result

    def test_format_draft_for_display_no_generated(self, service: DraftService, sample_draft: FindingModelDraft):
        """Test formatting draft for display without generated JSON."""
        # Test
        result = service.format_draft_for_display(sample_draft)

        # Assertions
        assert result["has_generated"] is False
        assert result["attribute_names"] == []

    def test_format_draft_for_display_timestamp_error(self, service: DraftService, sample_draft: FindingModelDraft):
        """Test formatting draft for display with timestamp error."""
        # Setup: Create draft with problematic timestamp
        bad_draft = MagicMock()
        mock_timestamp = MagicMock()
        mock_timestamp.isoformat.side_effect = AttributeError("Mock timestamp error")
        bad_draft.updated_at = mock_timestamp
        bad_draft.name = "Test"
        bad_draft.status = "draft"
        bad_draft.id = "test-id"
        bad_draft.generated_json = None

        # Mock the extract method
        with (
            patch.object(service, "extract_attribute_names_from_generated_json", return_value=[]),
            pytest.raises(AttributeError, match="Mock timestamp error"),
        ):
            service.format_draft_for_display(bad_draft)
