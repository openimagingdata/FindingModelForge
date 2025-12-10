"""Test the CreationService class."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from findingmodel import FindingInfo
from findingmodel.tools.similar_finding_models import SimilarModelAnalysis

from app.database import Database
from app.models import FindingModelInputs, User
from app.services.creation_service import TEST_USER_ID, CreationService


class TestCreationService:
    """Test the CreationService class."""

    @pytest.fixture
    def mock_index(self) -> MagicMock:
        """Mock FindingModel index."""
        index = MagicMock()
        index.get = AsyncMock()
        return index

    @pytest.fixture
    def mock_database(self) -> MagicMock:
        """Mock database."""
        db = MagicMock(spec=Database)
        db.finding_index = MagicMock()

        # Mock people_repo with async method
        mock_person = MagicMock()
        mock_person.organization_code = "OIDM"
        mock_people_repo = AsyncMock()
        mock_people_repo.get_by_username = AsyncMock(return_value=mock_person)
        db.people_repo = mock_people_repo

        return db

    @pytest.fixture
    def mock_draft_repo(self) -> MagicMock:
        """Mock DraftRepo."""
        repo = MagicMock()
        repo.find_editable_by_name = AsyncMock(return_value=None)
        repo.find_latest_by_name = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def service(self, mock_index: MagicMock, mock_database: MagicMock, mock_draft_repo: MagicMock) -> CreationService:
        """CreationService instance with mocked dependencies."""
        return CreationService(index=mock_index, database=mock_database, draft_repo=mock_draft_repo)

    @pytest.fixture
    def sample_user(self) -> User:
        """Sample user for testing."""
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        return User(
            id=12345,
            login="testuser",
            name="Test User",
            email="test@example.com",
            avatar_url="https://avatar.example.com/testuser.jpg",
            html_url="https://github.com/testuser",
            is_active=True,
            created_at=now,
            updated_at=now,
            last_login=now,
            organizations=["OIDM"],
        )

    @pytest.fixture
    def sample_inputs(self) -> FindingModelInputs:
        """Sample finding model inputs."""
        return FindingModelInputs(
            description="A test finding for medical imaging",
            synonyms=["test finding", "example finding"],
            attributes_markdown=(
                "### presence\n\nPresence of test finding\n\n- absent: Not visible\n- present: Clearly visible"
            ),
        )

    async def test_check_name_availability_available(self, service: CreationService, mock_index: MagicMock):
        """Test checking name availability when name is available."""
        # Setup: Index returns None (name doesn't exist)
        mock_index.get.return_value = None

        # Test
        result = await service.check_name_availability("New Finding")

        # Assertions
        assert result is True
        mock_index.get.assert_called_once_with("New Finding")

    async def test_check_name_availability_taken(self, service: CreationService, mock_index: MagicMock):
        """Test checking name availability when name is taken."""
        # Setup: Index returns entry (name exists)
        mock_index.get.return_value = SimpleNamespace(name="Existing Finding")

        # Test
        result = await service.check_name_availability("Existing Finding", user_id=12345)

        # Assertions
        assert result is False
        mock_index.get.assert_called_once_with("Existing Finding")

    async def test_check_name_availability_error_fail_open(self, service: CreationService, mock_index: MagicMock):
        """Test checking name availability when index throws error (fail open)."""
        # Setup: Index throws exception
        mock_index.get.side_effect = Exception("Database error")

        # Test
        result = await service.check_name_availability("Any Finding")

        # Assertions
        assert result is True  # Fail open

    async def test_generate_finding_info_normal_mode(self, service: CreationService):
        """Test generating finding info in normal mode."""
        with patch("app.services.creation_service.create_info_from_name", new=AsyncMock()) as mock_create:
            expected_info = FindingInfo(
                name="Test Finding", description="AI generated description", synonyms=["synonym1", "synonym2"]
            )
            mock_create.return_value = expected_info

            # Test
            result = await service.generate_finding_info("Test Finding", test_mode=False)

            # Assertions
            assert result == expected_info
            mock_create.assert_called_once_with("Test Finding")

    async def test_generate_finding_info_test_mode(self, service: CreationService):
        """Test generating finding info in test mode."""
        # Test
        result = await service.generate_finding_info("Test Finding", test_mode=True)

        # Assertions
        assert result.name == "Test Finding"
        assert "Test description for Test Finding" in result.description
        assert "This is a mock response" in result.description
        assert result.synonyms == ["Test Finding_synonym1", "Test Finding_synonym2"]

    async def test_find_similar_models_normal_mode(self, service: CreationService, mock_index: MagicMock):
        """Test finding similar models in normal mode."""
        with patch("app.services.creation_service.find_similar_models", new=AsyncMock()) as mock_find:
            expected_analysis = SimilarModelAnalysis(similar_models=[], recommendation="create_new", confidence=0.8)
            mock_find.return_value = expected_analysis

            # Test
            result = await service.find_similar_models(
                name="Test Finding", description="Test description", synonyms=["synonym"], test_mode=False
            )

            # Assertions
            assert result == expected_analysis
            mock_find.assert_called_once_with(
                finding_name="Test Finding", description="Test description", synonyms=["synonym"], index=mock_index
            )

    async def test_find_similar_models_test_mode(self, service: CreationService):
        """Test finding similar models in test mode."""
        # Test
        result = await service.find_similar_models(
            name="Test Finding", description="Test description", synonyms=["synonym"], test_mode=True
        )

        # Assertions
        assert result.similar_models == []
        assert result.recommendation == "create_new"
        assert result.confidence == 1.0

    async def test_generate_from_inputs_normal_mode(
        self, service: CreationService, sample_user: User, sample_inputs: FindingModelInputs, mock_database: MagicMock
    ):
        """Test generating finding model from inputs in normal mode."""
        with (
            patch("app.services.creation_service.create_model_from_markdown", new=AsyncMock()) as mock_create,
            patch("app.services.creation_service.add_ids_to_model") as mock_add_ids,
            patch("app.services.creation_service.add_standard_codes_to_model") as mock_add_codes,
        ):
            # Setup mocks
            from findingmodel import FindingModelBase

            mock_model = FindingModelBase(
                name="Test Finding",
                description="Test description",
                synonyms=["synonym"],
                tags=None,
                contributors=None,
                attributes=[
                    {
                        "name": "presence",
                        "description": "Test attribute",
                        "type": "choice",
                        "values": [
                            {"name": "absent", "description": "Not visible"},
                            {"name": "present", "description": "Visible"},
                        ],
                        "required": False,
                        "max_selected": 1,
                    }
                ],
            )
            mock_create.return_value = mock_model
            mock_add_ids.return_value = mock_model

            # Test
            result = await service.generate_from_inputs(
                name="Test Finding", inputs=sample_inputs, user=sample_user, test_mode=False
            )

            # Assertions
            assert isinstance(result, str)
            result_dict = json.loads(result)
            assert result_dict["name"] == "Test Finding"
            mock_create.assert_called_once()
            mock_add_ids.assert_called_once()
            mock_add_codes.assert_called_once()

    async def test_generate_from_inputs_test_mode(
        self, service: CreationService, sample_user: User, sample_inputs: FindingModelInputs
    ):
        """Test generating finding model from inputs in test mode."""
        with (
            patch("app.services.creation_service.add_ids_to_model") as mock_add_ids,
            patch("app.services.creation_service.add_standard_codes_to_model"),
        ):
            # Setup mocks
            from findingmodel import FindingModelBase

            mock_model = FindingModelBase(
                name="Test Finding Test",  # Test mode adds "Test" suffix for short names
                description="Test description",
                synonyms=["synonym"],
                tags=None,
                contributors=None,
                attributes=[
                    {
                        "name": "presence",
                        "description": "Test attribute",
                        "type": "choice",
                        "values": [
                            {"name": "absent", "description": "Not visible"},
                            {"name": "present", "description": "Visible"},
                        ],
                        "required": False,
                        "max_selected": 1,
                    }
                ],
            )
            mock_add_ids.return_value = mock_model

            # Test
            result = await service.generate_from_inputs(
                name="Test",  # Short name to trigger suffix
                inputs=sample_inputs,
                user=sample_user,
                test_mode=True,
            )

            # Assertions
            assert isinstance(result, str)
            result_dict = json.loads(result)
            assert "Test" in result_dict["name"]
            assert result_dict["attributes"][0]["name"] == "presence"

    async def test_generate_from_inputs_no_finding_index(
        self, service: CreationService, sample_user: User, sample_inputs: FindingModelInputs, mock_database: MagicMock
    ):
        """Test generating finding model when finding_index is not initialized.

        Note: We must mock create_model_from_markdown to avoid calling real OpenAI API.
        The finding_index check happens AFTER the AI call in the real code.
        """
        # Setup: No finding index
        mock_database.finding_index = None

        # Mock the AI call to prevent real OpenAI API calls
        with patch("app.services.creation_service.create_model_from_markdown", new=AsyncMock()) as mock_create:
            from findingmodel import FindingModelBase

            mock_model = FindingModelBase(
                name="Test Finding",
                description="Test description",
                synonyms=["synonym"],
                tags=None,
                contributors=None,
                attributes=[
                    {
                        "name": "presence",
                        "description": "Test attribute",
                        "type": "choice",
                        "values": [
                            {"name": "absent", "description": "Not visible"},
                            {"name": "present", "description": "Visible"},
                        ],
                        "required": False,
                        "max_selected": 1,
                    }
                ],
            )
            mock_create.return_value = mock_model

            # Test
            with pytest.raises(RuntimeError, match="FindingIndex must be initialized"):
                await service.generate_from_inputs(
                    name="Test Finding", inputs=sample_inputs, user=sample_user, test_mode=False
                )

    def test_generate_default_attributes_markdown(self, service: CreationService):
        """Test generating default attributes markdown."""
        # Test
        result = service.generate_default_attributes_markdown("test finding")

        # Assertions
        assert "### presence" in result
        assert "### change from prior" in result
        assert "Presence of test finding" in result
        assert "Test finding is not visible" in result
        assert "How the test finding has changed compared to prior imaging" in result

    def test_is_test_user_true(self, service: CreationService):
        """Test checking if user is test user (true case)."""
        # Test
        result = service.is_test_user(TEST_USER_ID)

        # Assertions
        assert result is True

    def test_is_test_user_false(self, service: CreationService):
        """Test checking if user is test user (false case)."""
        # Test
        result = service.is_test_user(12345)

        # Assertions
        assert result is False

    def test_test_user_id_constant(self):
        """Test that TEST_USER_ID constant is set correctly."""
        assert TEST_USER_ID == 999999
