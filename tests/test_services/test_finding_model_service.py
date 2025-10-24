"""Test the FindingModelService class."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from findingmodel import FindingModelFull

from app.cache import RedisCache
from app.database import CommentRepo, UserRepo
from app.models import Comment, CommentThread, User
from app.services import NotFoundError
from app.services.comment_service import CommentService
from app.services.finding_model_service import FindingModelService


class TestFindingModelService:
    """Test the FindingModelService class."""

    @pytest.fixture
    def mock_index(self) -> MagicMock:
        """Mock FindingModel index with DuckDB connection."""
        index = MagicMock()
        index.get = AsyncMock()

        # Mock DuckDB connection
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = [3]  # Default count
        mock_result.fetchall.return_value = [
            ("OIDM.1001", "Abdominal Abscess", "abdominal_abscess"),
            ("OIDM.1002", "Acute Appendicitis", "acute_appendicitis"),
            ("OIDM.1003", "Brain Tumor", "brain_tumor"),
        ]
        mock_conn.execute.return_value = mock_result

        # Mock _ensure_connection to return the connection
        index._ensure_connection = MagicMock(return_value=mock_conn)
        index.conn = mock_conn

        return index

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Mock Redis cache."""
        cache = MagicMock(spec=RedisCache)
        cache.get_finding_models = AsyncMock()
        cache.set_finding_models = AsyncMock()
        cache.get_finding_model = AsyncMock()
        cache.set_finding_model = AsyncMock()
        return cache

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
        mock_cache: MagicMock,
        mock_comment_repo: MagicMock,
        mock_user_repo: MagicMock,
        mock_comment_service: MagicMock,
    ) -> FindingModelService:
        """FindingModelService instance with mocked dependencies."""
        return FindingModelService(
            index=mock_index,
            cache=mock_cache,
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
    def sample_finding_model_full(self) -> MagicMock:
        """Sample complete finding model (mocked to avoid validation issues)."""
        mock_model = MagicMock(spec=FindingModelFull)
        mock_model.name = "Abdominal Abscess"
        mock_model.description = "A collection of pus in the abdominal cavity"
        mock_model.synonyms = ["abdominal infection", "intra-abdominal abscess"]
        mock_model.oifm_id = "OIFM_OIDM_000001"
        return mock_model

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
        # Test - should query DuckDB directly
        models, total = await service.list_models()

        # Assertions
        assert len(models) == 3
        assert total == 3
        assert models[0]["name"] == "Abdominal Abscess"
        assert models[0]["slug"] == "abdominal-abscess"
        assert models[1]["name"] == "Acute Appendicitis"
        assert models[2]["name"] == "Brain Tumor"

        # Verify DuckDB was queried (no cache layer)
        assert mock_index.conn.execute.called

    async def test_list_models_with_pagination(
        self,
        service: FindingModelService,
        mock_index: MagicMock,
    ):
        """Test listing models with pagination."""
        # Mock pagination results (page 2, 1 per page)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = [3]  # Total count
        mock_result.fetchall.return_value = [
            ("OIDM.1002", "Acute Appendicitis", "acute_appendicitis"),  # Second item
        ]
        mock_index.conn.execute.return_value = mock_result

        # Test with page 2, 1 per page
        models, total = await service.list_models(page=2, per_page=1)

        # Should have total count and only 1 item
        assert total == 3
        assert len(models) == 1
        assert models[0]["name"] == "Acute Appendicitis"

        # Verify DuckDB was queried with LIMIT/OFFSET
        assert mock_index.conn.execute.called

    async def test_list_models_with_search(self, service: FindingModelService, mock_index: MagicMock):
        """Test listing models with search filter."""
        # Setup: Mock DuckDB to return filtered results for search
        mock_result = MagicMock()
        mock_result.fetchone.return_value = [1]  # One match
        mock_result.fetchall.return_value = [
            ("OIDM.1001", "Abdominal Abscess", "abdominal_abscess"),
        ]
        mock_index.conn.execute.return_value = mock_result

        # Test with search (should query DuckDB with normalized search term)
        models, total = await service.list_models(search="abscess")

        # Assertions
        assert len(models) == 1
        assert total == 1
        assert models[0]["name"] == "Abdominal Abscess"

        # Verify DuckDB was queried with search pattern
        assert mock_index.conn.execute.called

    async def test_get_model_by_slug_cached(
        self,
        service: FindingModelService,
        mock_cache: MagicMock,
        mock_index: MagicMock,
        sample_finding_model_full: MagicMock,
    ):
        """Test getting model by slug with cache hit."""
        # Setup
        slug = "abdominal-abscess"
        index_entry = SimpleNamespace(filename="abdominal_abscess.fm.json", name="Abdominal Abscess")
        mock_index.get.return_value = index_entry
        mock_cache.get_finding_model.return_value = sample_finding_model_full

        # Test
        model, entry = await service.get_model_by_slug(slug)

        # Assertions
        assert model == sample_finding_model_full
        assert entry == index_entry
        # Cache is called with the slug as-is (no normalization)
        mock_cache.get_finding_model.assert_called_once_with(slug)

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

    async def test_get_finding_model_github_404(
        self, service: FindingModelService, mock_cache: MagicMock, mock_index: MagicMock
    ):
        """Test getting model when GitHub returns 404."""
        # Setup
        slug = "test-model"
        index_entry = SimpleNamespace(filename="test_model.fm.json", name="Test Model")
        mock_index.get.return_value = index_entry
        mock_cache.get_finding_model.return_value = None

        # Mock httpx 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("app.services.finding_model_service.httpx.AsyncClient") as mock_client:
            from httpx import HTTPStatusError

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=HTTPStatusError("Not found", request=MagicMock(), response=mock_response)
            )

            # Test
            with pytest.raises(NotFoundError, match="Finding model file not found on GitHub"):
                await service.get_model_by_slug(slug)

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
