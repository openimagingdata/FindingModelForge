"""Test the FindingModelService class."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from findingmodel import FindingModelFull

from app.cache import RedisCache
from app.services import NotFoundError
from app.services.finding_model_service import FindingModelService


class TestFindingModelService:
    """Test the FindingModelService class."""

    @pytest.fixture
    def mock_index(self) -> MagicMock:
        """Mock FindingModel index."""
        index = MagicMock()
        index.get = AsyncMock()
        index.index_collection = AsyncMock()
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
    def service(self, mock_index: MagicMock, mock_cache: MagicMock) -> FindingModelService:
        """FindingModelService instance with mocked dependencies."""
        return FindingModelService(index=mock_index, cache=mock_cache)

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

    async def test_list_models_cached(
        self, service: FindingModelService, mock_cache: MagicMock, sample_finding_models: list[dict[str, str]]
    ):
        """Test listing models with cache hit."""
        # Setup: Cache returns models
        expected_models = [
            {"id": "OIDM.1001", "name": "Abdominal Abscess", "slug": "abdominal-abscess"},
            {"id": "OIDM.1002", "name": "Acute Appendicitis", "slug": "acute-appendicitis"},
            {"id": "OIDM.1003", "name": "Brain Tumor", "slug": "brain-tumor"},
        ]
        mock_cache.get_finding_models.return_value = expected_models

        # Test
        models, total = await service.list_models()

        # Assertions
        assert len(models) == 3
        assert total == 3
        assert models == expected_models
        mock_cache.get_finding_models.assert_called_once()

    async def test_list_models_cache_miss(
        self,
        service: FindingModelService,
        mock_cache: MagicMock,
        mock_index: MagicMock,
        sample_finding_models: list[dict[str, str]],
    ):
        """Test listing models with cache miss."""
        # Setup: Cache miss, index returns data
        mock_cache.get_finding_models.return_value = None

        # Mock the aggregate pipeline - need to return the cursor directly
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=sample_finding_models)
        mock_index.index_collection.aggregate = MagicMock(return_value=mock_cursor)

        # Test
        models, total = await service.list_models()

        # Assertions
        assert len(models) == 3
        assert total == 3
        assert models[0]["name"] == "Abdominal Abscess"
        assert models[0]["slug"] == "abdominal-abscess"
        mock_cache.set_finding_models.assert_called_once()

    async def test_list_models_with_search(self, service: FindingModelService, mock_cache: MagicMock):
        """Test listing models with search filter."""
        # Setup: Cache returns models
        all_models = [
            {"id": "OIDM.1001", "name": "Abdominal Abscess", "slug": "abdominal-abscess"},
            {"id": "OIDM.1002", "name": "Acute Appendicitis", "slug": "acute-appendicitis"},
            {"id": "OIDM.1003", "name": "Brain Tumor", "slug": "brain-tumor"},
        ]
        mock_cache.get_finding_models.return_value = all_models

        # Test
        models, total = await service.list_models(search="abscess")

        # Assertions
        assert len(models) == 1
        assert total == 1
        assert models[0]["name"] == "Abdominal Abscess"

    async def test_list_models_pagination(self, service: FindingModelService, mock_cache: MagicMock):
        """Test listing models with pagination."""
        # Setup: Cache returns models
        all_models = [
            {"id": f"OIDM.100{i}", "name": f"Model {i}", "slug": f"model-{i}"}
            for i in range(1, 26)  # 25 models
        ]
        mock_cache.get_finding_models.return_value = all_models

        # Test page 2 with 10 per page
        models, total = await service.list_models(page=2, per_page=10)

        # Assertions
        assert len(models) == 10
        assert total == 25
        assert models[0]["name"] == "Model 11"  # Second page starts at index 10

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
        mock_cache.get_finding_model.assert_called_once_with("abdominal abscess")

    async def test_get_model_by_slug_not_found(self, service: FindingModelService, mock_index: MagicMock):
        """Test getting model by slug when not found."""
        # Setup: Index returns None
        mock_index.get.return_value = None

        # Mock collection search to also fail
        mock_index.index_collection.find_one = AsyncMock(return_value=None)

        # Test
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

    async def test_get_finding_models_list_empty(
        self, service: FindingModelService, mock_cache: MagicMock, mock_index: MagicMock
    ):
        """Test getting finding models list when index is empty."""
        # Setup: Cache miss, empty index
        mock_cache.get_finding_models.return_value = None
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_index.index_collection.aggregate = MagicMock(return_value=mock_cursor)

        # Test
        models = await service._get_finding_models_list()

        # Assertions
        assert models == []
        # Should not cache empty results
        mock_cache.set_finding_models.assert_not_called()

    async def test_get_finding_model_with_cache_fallback_regex(
        self,
        service: FindingModelService,
        mock_cache: MagicMock,
        mock_index: MagicMock,
        sample_finding_model_full: MagicMock,
    ):
        """Test getting model with cache using regex fallback."""
        # Setup: Index get fails, but regex search succeeds
        slug = "bow-tie"
        mock_index.get.return_value = None
        mock_index.index_collection.find_one = AsyncMock(
            return_value={"filename": "bow_tie.fm.json", "name": "Bow Tie", "description": "Test"}
        )
        mock_cache.get_finding_model.return_value = None

        # Mock httpx response
        mock_response = MagicMock()
        mock_response.text = '{"name": "test_model"}'  # Simple JSON response
        mock_response.raise_for_status = MagicMock()

        with (
            patch("app.services.finding_model_service.httpx.AsyncClient") as mock_client,
            patch("app.services.finding_model_service.FindingModelFull") as mock_model_class,
        ):
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_model_class.model_validate_json.return_value = sample_finding_model_full

            # Test
            model, entry = await service._get_finding_model_with_cache(slug)

            # Assertions
            assert model == sample_finding_model_full
            assert entry.filename == "bow_tie.fm.json"
            mock_cache.set_finding_model.assert_called_once()

    async def test_get_finding_model_with_cache_filename_fallback(
        self,
        service: FindingModelService,
        mock_cache: MagicMock,
        mock_index: MagicMock,
        sample_finding_model_full: MagicMock,
    ):
        """Test getting model with cache using filename fallback."""
        # Setup: Index get and name regex fail, but filename search succeeds
        slug = "test-model"
        mock_index.get.return_value = None
        # First find_one (name regex) returns None, second (filename) returns result
        mock_index.index_collection.find_one = AsyncMock(
            side_effect=[
                None,  # name regex search fails
                {
                    "filename": "test_model.fm.json",
                    "name": "Test Model",
                    "description": "Test",
                },  # filename search succeeds
            ]
        )
        mock_cache.get_finding_model.return_value = None

        # Mock httpx response
        mock_response = MagicMock()
        mock_response.text = '{"name": "test_model"}'  # Simple JSON response
        mock_response.raise_for_status = MagicMock()

        with (
            patch("app.services.finding_model_service.httpx.AsyncClient") as mock_client,
            patch("app.services.finding_model_service.FindingModelFull") as mock_model_class,
        ):
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_model_class.model_validate_json.return_value = sample_finding_model_full

            # Test
            model, entry = await service._get_finding_model_with_cache(slug)

            # Assertions
            assert model == sample_finding_model_full
            assert entry.filename == "test_model.fm.json"

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
                await service._get_finding_model_with_cache(slug)
