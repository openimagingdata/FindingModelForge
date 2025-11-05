"""Test the FindingModelService class."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from findingmodel import FindingModelFull

from app.database import CommentRepo, UserRepo
from app.models import Comment, CommentThread, User
from app.services import NotFoundError
from app.services.comment_service import CommentService
from app.services.finding_model_service import FindingModelService


class TestFindingModelService:
    """Test the FindingModelService class."""

    @pytest.fixture
    def mock_index(self, mock_finding_model: FindingModelFull) -> MagicMock:
        """Mock FindingModel index with new Index API."""
        index = MagicMock()

        # Mock IndexEntry objects with slug_name field
        mock_entries = [
            type(
                "IndexEntry",
                (),
                {"oifm_id": "OIFM_TEST_000001", "name": "Abdominal Abscess", "slug_name": "abdominal-abscess"},
            )(),
            type(
                "IndexEntry",
                (),
                {"oifm_id": "OIFM_TEST_000002", "name": "Acute Appendicitis", "slug_name": "acute-appendicitis"},
            )(),
            type(
                "IndexEntry", (), {"oifm_id": "OIFM_TEST_000003", "name": "Brain Tumor", "slug_name": "brain-tumor"}
            )(),
        ]

        # all() returns tuple (list[IndexEntry], int)
        index.all = AsyncMock(return_value=(mock_entries, 3))

        # search_by_slug() returns tuple (list[IndexEntry], int)
        index.search_by_slug = AsyncMock(return_value=(mock_entries[:1], 1))

        # get() returns IndexEntry or None (for slug lookup)
        index.get = AsyncMock(return_value=mock_entries[0])

        # get_full() returns FindingModelFull - use the existing fixture
        index.get_full = AsyncMock(return_value=mock_finding_model)

        return index

    @pytest.fixture
    def mock_comment_repo(self) -> MagicMock:
        """Mock comment repository."""
        repo = MagicMock(spec=CommentRepo)
        repo.get_thread = AsyncMock()
        repo.add_comment = AsyncMock()
        repo.add_reply = AsyncMock()
        repo.report_comment = AsyncMock()
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
        mock_index: MagicMock,
        mock_comment_repo: MagicMock,
        mock_user_repo: MagicMock,
        mock_comment_service: MagicMock,
    ) -> FindingModelService:
        """FindingModelService instance with mocked dependencies."""
        return FindingModelService(
            index=mock_index,
            comment_repo=mock_comment_repo,
            user_repo=mock_user_repo,
            comment_service=mock_comment_service,
        )

    @pytest.fixture
    def sample_finding_models(self) -> list[dict[str, str]]:
        """Sample finding models data."""
        return [
            {"oifm_id": "OIDM.1001", "name": "Abdominal Abscess"},
            {"oifm_id": "OIDM.1002", "name": "Acute Appendicitis"},
            {"oifm_id": "OIDM.1003", "name": "Brain Tumor"},
        ]

    @pytest.fixture
    def sample_user(self) -> User:
        now = datetime.now(UTC)
        return User(
            id=777,
            login="finder",
            name="Finder",
            email="finder@example.com",
            avatar_url="https://example.com/avatar.png",
            html_url=None,
            organizations=[],
            created_at=now,
            updated_at=now,
            comment_index=[],
        )

    async def test_list_models_no_search(self, service: FindingModelService, mock_index: MagicMock):
        """Test listing all models without search."""
        # Test - should query Index.all() directly
        models, total = await service.list_models()

        # Assertions
        assert len(models) == 3
        assert total == 3
        assert models[0]["name"] == "Abdominal Abscess"
        assert models[0]["slug"] == "abdominal-abscess"
        assert models[1]["name"] == "Acute Appendicitis"
        assert models[2]["name"] == "Brain Tumor"

        # Verify Index.all() was called
        mock_index.all.assert_called_once()

    async def test_list_models_with_pagination(
        self,
        service: FindingModelService,
        mock_index: MagicMock,
    ):
        """Test listing models with pagination."""
        # Mock pagination results (page 2, 1 per page) - return second entry only
        second_entry = type(
            "IndexEntry", (), {"oifm_id": "OIFM.1002", "name": "Acute Appendicitis", "slug_name": "acute-appendicitis"}
        )()
        mock_index.all.return_value = ([second_entry], 3)

        # Test with page 2, 1 per page
        models, total = await service.list_models(page=2, per_page=1)

        # Should have total count and only 1 item
        assert total == 3
        assert len(models) == 1
        assert models[0]["name"] == "Acute Appendicitis"

        # Verify Index.all() was called with correct offset/limit
        mock_index.all.assert_called_once_with(offset=1, limit=1)

    async def test_list_models_with_search(self, service: FindingModelService, mock_index: MagicMock):
        """Test listing models with search filter."""
        # Setup: Mock Index.search_by_slug to return filtered results
        abscess_entry = type(
            "IndexEntry", (), {"oifm_id": "OIFM.1001", "name": "Abdominal Abscess", "slug_name": "abdominal-abscess"}
        )()
        mock_index.search_by_slug.return_value = ([abscess_entry], 1)

        # Test with search
        models, total = await service.list_models(search="abscess")

        # Assertions
        assert len(models) == 1
        assert total == 1
        assert models[0]["name"] == "Abdominal Abscess"

        # Verify Index.search_by_slug was called
        mock_index.search_by_slug.assert_called_once_with("abscess", limit=20, offset=0)

    async def test_get_model_by_slug_success(
        self,
        service: FindingModelService,
        mock_index: MagicMock,
    ):
        """Test getting model by slug successfully."""
        # Setup
        slug = "abdominal-abscess"
        index_entry = type(
            "IndexEntry",
            (),
            {"oifm_id": "OIFM_TEST_000001", "name": "Abdominal Abscess", "slug_name": "abdominal-abscess"},
        )()
        mock_index.get.return_value = index_entry

        # Use MagicMock for FindingModelFull to avoid validation
        finding_model_full = MagicMock(spec=FindingModelFull)
        finding_model_full.oifm_id = "OIFM_TEST_000001"
        finding_model_full.name = "Abdominal Abscess"
        finding_model_full.description = "Test description"
        mock_index.get_full.return_value = finding_model_full

        # Test - now returns FindingModelFull directly, not tuple
        model = await service.get_model_by_slug(slug)

        # Assertions
        assert model == finding_model_full
        assert model.name == "Abdominal Abscess"
        assert model.oifm_id == "OIFM_TEST_000001"

        # Verify calls
        mock_index.get.assert_called_once_with(slug)
        mock_index.get_full.assert_called_once_with("OIFM_TEST_000001")

    async def test_get_model_by_slug_not_found(self, service: FindingModelService, mock_index: MagicMock):
        """Test getting model by slug when not found."""
        # Setup: Index returns None (not found)
        mock_index.get.return_value = None

        # Test - should raise NotFoundError
        with pytest.raises(NotFoundError, match="Finding model 'nonexistent' not found"):
            await service.get_model_by_slug("nonexistent")

    async def test_search_in_index_found(self, service: FindingModelService, mock_index: MagicMock):
        """Test searching in index when entry is found."""
        # Setup
        slug = "abdominal-abscess"
        index_entry = SimpleNamespace(filename="abdominal_abscess.fm.json", name="Abdominal Abscess")
        mock_index.get.return_value = index_entry

        # Test
        result = await service.search_in_index(slug)

        # Assertions
        assert result == index_entry
        # The service tries multiple variants, starting with the exact slug
        mock_index.get.assert_called()

    async def test_search_in_index_not_found(self, service: FindingModelService, mock_index: MagicMock):
        """Test searching in index when entry is not found."""
        # Setup: Index throws exception for all variants
        mock_index.get.side_effect = Exception("Not found")

        # Test
        result = await service.search_in_index("nonexistent")

        # Assertions
        assert result is None

    @pytest.mark.asyncio
    async def test_get_comments_for_model_delegates(
        self, service: FindingModelService, mock_comment_service: MagicMock
    ) -> None:
        thread = CommentThread(
            id="thread",
            reference_type="finding_model",
            reference_id="fm-1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            comments=[],
        )
        mock_comment_service.get_thread.return_value = thread

        result = await service.get_comments_for_model("fm-1")

        mock_comment_service.get_thread.assert_awaited_once_with("finding_model", "fm-1")
        assert result is thread

    @pytest.mark.asyncio
    async def test_add_comment_to_model_delegates(
        self,
        service: FindingModelService,
        mock_comment_service: MagicMock,
        sample_user: User,
    ) -> None:
        comment = Comment(
            user_id=sample_user.id,
            user_name=sample_user.login,
            content="Comment",
            created_at=datetime.now(UTC),
        )
        mock_comment_service.add_comment.return_value = comment
        # Mock IndexEntry with name attribute
        mock_index_entry = SimpleNamespace(name="Model", oifm_id="OIFM_123")
        service.get_by_oifm_id = AsyncMock(return_value=mock_index_entry)  # type: ignore[attr-defined]

        result = await service.add_comment_to_model("fm-1", sample_user, "body", parent_id="parent")

        mock_comment_service.add_comment.assert_awaited_once_with(
            "finding_model",
            "fm-1",
            sample_user,
            "body",
            parent_id="parent",
            reference_name="Model",
        )
        assert result is comment

    @pytest.mark.asyncio
    async def test_add_comment_to_model_without_name_falls_back(
        self,
        service: FindingModelService,
        mock_comment_service: MagicMock,
        sample_user: User,
    ) -> None:
        mock_comment_service.add_comment.return_value = Comment(
            user_id=sample_user.id,
            user_name=sample_user.login,
            content="Comment",
            created_at=datetime.now(UTC),
        )
        # Mock IndexEntry without name attribute (None fallback)
        mock_index_entry = SimpleNamespace(oifm_id="OIFM_123")
        service.get_by_oifm_id = AsyncMock(return_value=mock_index_entry)  # type: ignore[attr-defined]

        await service.add_comment_to_model("fm-1", sample_user, "body")

        kwargs = mock_comment_service.add_comment.await_args.kwargs
        assert kwargs["reference_name"] is None

    @pytest.mark.asyncio
    async def test_report_model_comment_delegates(
        self, service: FindingModelService, mock_comment_service: MagicMock
    ) -> None:
        await service.report_model_comment("fm-1", "comment", 123)

        mock_comment_service.report_comment.assert_awaited_once_with("finding_model", "fm-1", "comment", 123)
