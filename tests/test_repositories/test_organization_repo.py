"""Unit tests for OrganizationRepo.

Tests dual-source lookup, cache behavior, and lazy loading.
"""

from unittest.mock import AsyncMock

import pytest
from findingmodel import Index
from findingmodel.contributor import Organization

from app.repositories.organization_repo import OrganizationRepo


@pytest.fixture
def mock_index() -> AsyncMock:
    """Create mock Index with organizations."""
    index = AsyncMock(spec=Index)
    # Mock get_organizations() to return list
    index.get_organizations = AsyncMock(return_value=[])
    return index


@pytest.fixture
def mock_draft_collection() -> AsyncMock:
    """Create mock MongoDB collection."""
    collection = AsyncMock()
    collection.find_one = AsyncMock(return_value=None)
    return collection


@pytest.fixture
def organization_repo(mock_index: AsyncMock, mock_draft_collection: AsyncMock) -> OrganizationRepo:
    """Create OrganizationRepo with mocked sources."""
    return OrganizationRepo(index=mock_index, draft_collection=mock_draft_collection)


@pytest.fixture
def mock_org() -> Organization:
    """Create realistic test organization."""
    return Organization(
        code="TEST",
        name="Test Organization",
        url="https://example.com",
    )


class TestOrganizationRepoLookup:
    """Test dual-source lookup for OrganizationRepo."""

    @pytest.mark.asyncio
    async def test_get_by_code_from_cache(self, organization_repo: OrganizationRepo, mock_org: Organization) -> None:
        """Test cache hit returns immediately without Index/MongoDB access."""
        # Pre-populate cache
        organization_repo._cache["TEST"] = mock_org

        # Act
        result = await organization_repo.get_by_code("TEST")

        # Assert
        assert result == mock_org
        # Verify no Index access (cache hit)
        organization_repo.index.get_organizations.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_code_from_index(
        self,
        organization_repo: OrganizationRepo,
        mock_index: AsyncMock,
        mock_org: Organization,
    ) -> None:
        """Test Index lookup works and caches result."""
        # Setup Index to return organization
        mock_index.get_organizations = AsyncMock(return_value=[mock_org])

        # Act
        result = await organization_repo.get_by_code("TEST")

        # Assert
        assert result == mock_org
        # Verify Index was called
        mock_index.get_organizations.assert_called_once()
        # Verify result cached
        assert "TEST" in organization_repo._cache
        assert organization_repo._cache["TEST"] == mock_org
        # Verify index loaded flag set
        assert organization_repo._index_loaded is True

    @pytest.mark.asyncio
    async def test_get_by_code_from_mongodb(
        self,
        organization_repo: OrganizationRepo,
        mock_index: AsyncMock,
        mock_draft_collection: AsyncMock,
    ) -> None:
        """Test MongoDB lookup works when not in Index, caches result."""
        # Setup Index to return empty list
        mock_index.get_organizations = AsyncMock(return_value=[])

        # Setup MongoDB to return organization
        org_doc = {
            "code": "DRF",  # Valid 3-letter code
            "name": "Draft Organization",
            "url": "https://draft.example.com",
        }
        mock_draft_collection.find_one = AsyncMock(return_value=org_doc)

        # Act
        result = await organization_repo.get_by_code("DRF")

        # Assert
        assert result is not None
        assert result.code == "DRF"
        assert result.name == "Draft Organization"
        # Verify MongoDB was called
        mock_draft_collection.find_one.assert_called_once_with({"code": "DRF"})
        # Verify result cached
        assert "DRF" in organization_repo._cache
        assert organization_repo._cache["DRF"].code == "DRF"

    @pytest.mark.asyncio
    async def test_get_by_code_precedence(
        self,
        mock_index: AsyncMock,
        mock_draft_collection: AsyncMock,
    ) -> None:
        """Test Index beats MongoDB when both have data."""
        # Setup Index to return organization
        index_org = Organization(
            code="TEST",
            name="Index Organization",
            url="https://index.example.com",
        )
        mock_index.get_organizations = AsyncMock(return_value=[index_org])

        # Setup MongoDB to return different organization (should not be used)
        mongo_org_doc = {
            "code": "TEST",
            "name": "Mongo Organization",
            "url": "https://mongo.example.com",
        }
        mock_draft_collection.find_one = AsyncMock(return_value=mongo_org_doc)

        # Create repo
        repo = OrganizationRepo(index=mock_index, draft_collection=mock_draft_collection)

        # Act
        result = await repo.get_by_code("TEST")

        # Assert
        assert result == index_org
        assert result.name == "Index Organization"
        # Verify Index was called
        mock_index.get_organizations.assert_called_once()
        # Verify MongoDB was NOT called (Index took precedence)
        mock_draft_collection.find_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_code_not_found(
        self,
        organization_repo: OrganizationRepo,
        mock_index: AsyncMock,
        mock_draft_collection: AsyncMock,
    ) -> None:
        """Test returns None when not in any source."""
        # Setup Index to return empty list
        mock_index.get_organizations = AsyncMock(return_value=[])

        # Setup MongoDB to return None
        mock_draft_collection.find_one = AsyncMock(return_value=None)

        # Act
        result = await organization_repo.get_by_code("NONEXISTENT")

        # Assert
        assert result is None
        # Verify both sources were checked
        mock_index.get_organizations.assert_called_once()
        mock_draft_collection.find_one.assert_called_once_with({"code": "NONEXISTENT"})


class TestOrganizationRepoCache:
    """Test cache behavior."""

    @pytest.mark.asyncio
    async def test_clear_cache(
        self,
        organization_repo: OrganizationRepo,
        mock_org: Organization,
    ) -> None:
        """Test cache clearing works."""
        # Pre-populate cache
        organization_repo._cache["TEST"] = mock_org
        organization_repo._index_loaded = True

        # Act
        await organization_repo.clear_cache()

        # Assert
        assert len(organization_repo._cache) == 0
        assert organization_repo._index_loaded is False

    @pytest.mark.asyncio
    async def test_lazy_loading_index(
        self,
        organization_repo: OrganizationRepo,
        mock_index: AsyncMock,
        mock_org: Organization,
    ) -> None:
        """Test Index loaded only on first access."""
        # Setup Index to return organization
        mock_index.get_organizations = AsyncMock(return_value=[mock_org])

        # Verify Index not loaded initially
        assert organization_repo._index_loaded is False

        # Act - First access triggers load
        result = await organization_repo.get_by_code("TEST")

        # Assert
        assert result == mock_org
        assert organization_repo._index_loaded is True
        mock_index.get_organizations.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_calls_load_index_once(
        self,
        organization_repo: OrganizationRepo,
        mock_index: AsyncMock,
        mock_org: Organization,
    ) -> None:
        """Test Index loaded once even with multiple lookups."""
        # Setup Index to return organization
        mock_index.get_organizations = AsyncMock(return_value=[mock_org])

        # Act - Multiple lookups
        await organization_repo.get_by_code("TEST")
        await organization_repo.get_by_code("TEST")
        await organization_repo.get_by_code("OTHER")

        # Assert
        # Index should only be loaded once
        mock_index.get_organizations.assert_called_once()
        assert organization_repo._index_loaded is True
