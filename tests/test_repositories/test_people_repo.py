"""Unit tests for PeopleRepo.

Tests dual-source lookup, cache behavior, and write isolation.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from findingmodel import Index
from findingmodel.contributor import Person

from app.models import User
from app.repositories.people_repo import PeopleRepo


@pytest.fixture
def mock_index() -> AsyncMock:
    """Create mock Index with people."""
    index = AsyncMock(spec=Index)
    # Mock get_people() to return list
    index.get_people = AsyncMock(return_value=[])
    return index


@pytest.fixture
def mock_draft_collection() -> AsyncMock:
    """Create mock MongoDB collection."""
    collection = AsyncMock()
    collection.find_one = AsyncMock(return_value=None)
    collection.insert_one = AsyncMock()
    return collection


@pytest.fixture
def people_repo(mock_index: AsyncMock, mock_draft_collection: AsyncMock) -> PeopleRepo:
    """Create PeopleRepo with mocked sources."""
    return PeopleRepo(index=mock_index, draft_collection=mock_draft_collection)


@pytest.fixture
def mock_person() -> Person:
    """Create realistic test person."""
    return Person(
        github_username="testuser",
        email="test@example.com",
        name="Test User",
        organization_code="TEST",
        url="https://github.com/testuser",
    )


@pytest.fixture
def mock_user() -> User:
    """Create realistic test user."""
    now = datetime.now(UTC)
    return User(
        id=12345,
        login="newuser",
        name="New User",
        email="new@example.com",
        avatar_url="https://github.com/images/error/newuser_happy.gif",
        html_url="https://github.com/newuser",
        type="User",
        site_admin=False,
        organizations=[],
        is_active=True,
        created_at=now,
        updated_at=now,
    )


class TestPeopleRepoLookup:
    """Test dual-source lookup for PeopleRepo."""

    @pytest.mark.asyncio
    async def test_get_by_username_from_cache(self, people_repo: PeopleRepo, mock_person: Person) -> None:
        """Test cache hit returns immediately without Index/MongoDB access."""
        # Pre-populate cache
        people_repo._cache["testuser"] = mock_person

        # Act
        result = await people_repo.get_by_username("testuser")

        # Assert
        assert result == mock_person
        # Verify no Index access (cache hit)
        people_repo.index.get_people.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_username_from_index(
        self,
        people_repo: PeopleRepo,
        mock_index: AsyncMock,
        mock_person: Person,
    ) -> None:
        """Test Index lookup works and caches result."""
        # Setup Index to return person
        mock_index.get_people = AsyncMock(return_value=[mock_person])

        # Act
        result = await people_repo.get_by_username("testuser")

        # Assert
        assert result == mock_person
        # Verify Index was called
        mock_index.get_people.assert_called_once()
        # Verify result cached
        assert "testuser" in people_repo._cache
        assert people_repo._cache["testuser"] == mock_person
        # Verify index loaded flag set
        assert people_repo._index_loaded is True

    @pytest.mark.asyncio
    async def test_get_by_username_from_mongodb(
        self,
        people_repo: PeopleRepo,
        mock_index: AsyncMock,
        mock_draft_collection: AsyncMock,
    ) -> None:
        """Test MongoDB lookup works when not in Index, caches result."""
        # Setup Index to return empty list
        mock_index.get_people = AsyncMock(return_value=[])

        # Setup MongoDB to return person
        person_doc = {
            "github_username": "draftuser",
            "email": "draft@example.com",
            "name": "Draft User",
            "organization_code": "DRF",  # Valid 3-letter code
            "url": "https://github.com/draftuser",
        }
        mock_draft_collection.find_one = AsyncMock(return_value=person_doc)

        # Act
        result = await people_repo.get_by_username("draftuser")

        # Assert
        assert result is not None
        assert result.github_username == "draftuser"
        assert result.email == "draft@example.com"
        # Verify MongoDB was called
        mock_draft_collection.find_one.assert_called_once_with({"github_username": "draftuser"})
        # Verify result cached
        assert "draftuser" in people_repo._cache
        assert people_repo._cache["draftuser"].github_username == "draftuser"

    @pytest.mark.asyncio
    async def test_get_by_username_precedence(
        self,
        mock_index: AsyncMock,
        mock_draft_collection: AsyncMock,
        mock_person: Person,
    ) -> None:
        """Test Index beats MongoDB when both have data."""
        # Setup Index to return person
        index_person = Person(
            github_username="testuser",
            email="index@example.com",
            name="Index User",
            organization_code="IDX",  # Valid 3-letter code
            url="https://github.com/testuser",
        )
        mock_index.get_people = AsyncMock(return_value=[index_person])

        # Setup MongoDB to return different person (should not be used)
        mongo_person_doc = {
            "github_username": "testuser",
            "email": "mongo@example.com",
            "name": "Mongo User",
            "organization_code": "MNG",  # Valid 3-letter code
            "url": "https://github.com/testuser",
        }
        mock_draft_collection.find_one = AsyncMock(return_value=mongo_person_doc)

        # Create repo
        repo = PeopleRepo(index=mock_index, draft_collection=mock_draft_collection)

        # Act
        result = await repo.get_by_username("testuser")

        # Assert
        assert result == index_person
        assert result.email == "index@example.com"
        # Verify Index was called
        mock_index.get_people.assert_called_once()
        # Verify MongoDB was NOT called (Index took precedence)
        mock_draft_collection.find_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_username_not_found(
        self,
        people_repo: PeopleRepo,
        mock_index: AsyncMock,
        mock_draft_collection: AsyncMock,
    ) -> None:
        """Test returns None when not in any source."""
        # Setup Index to return empty list
        mock_index.get_people = AsyncMock(return_value=[])

        # Setup MongoDB to return None
        mock_draft_collection.find_one = AsyncMock(return_value=None)

        # Act
        result = await people_repo.get_by_username("nonexistent")

        # Assert
        assert result is None
        # Verify both sources were checked
        mock_index.get_people.assert_called_once()
        mock_draft_collection.find_one.assert_called_once_with({"github_username": "nonexistent"})


class TestPeopleRepoEnsureForUser:
    """Test ensure_for_user method."""

    @pytest.mark.asyncio
    async def test_ensure_for_user_existing(
        self,
        people_repo: PeopleRepo,
        mock_index: AsyncMock,
        mock_user: User,
        mock_person: Person,
    ) -> None:
        """Test returns existing person when found."""
        # Setup Index to return person with matching username
        existing_person = Person(
            github_username=mock_user.login,
            email=mock_user.email or f"{mock_user.login}@users.noreply.github.com",
            name=mock_user.name or mock_user.login,
            organization_code="EXST",  # Valid 4-letter code
            url=mock_user.html_url,
        )
        mock_index.get_people = AsyncMock(return_value=[existing_person])

        # Act
        result = await people_repo.ensure_for_user(mock_user)

        # Assert
        assert result == existing_person
        # Verify no MongoDB write
        people_repo.draft_people.insert_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_for_user_creates_new(
        self,
        people_repo: PeopleRepo,
        mock_index: AsyncMock,
        mock_draft_collection: AsyncMock,
        mock_user: User,
    ) -> None:
        """Test creates new person in MongoDB when not found, caches result."""
        # Setup Index to return empty list
        mock_index.get_people = AsyncMock(return_value=[])

        # Setup MongoDB to return None on lookup, succeed on insert
        mock_draft_collection.find_one = AsyncMock(return_value=None)
        mock_draft_collection.insert_one = AsyncMock()

        # Act
        result = await people_repo.ensure_for_user(mock_user)

        # Assert
        assert result is not None
        assert result.github_username == mock_user.login
        assert result.email == mock_user.email
        assert result.name == mock_user.name
        assert result.organization_code == "OIDM"
        assert str(result.url) == mock_user.html_url
        # Verify MongoDB insert was called
        mock_draft_collection.insert_one.assert_called_once()
        # Verify call args contain correct data
        call_args = mock_draft_collection.insert_one.call_args[0][0]
        assert call_args["github_username"] == mock_user.login
        assert call_args["organization_code"] == "OIDM"
        # Verify result cached
        assert mock_user.login in people_repo._cache
        assert people_repo._cache[mock_user.login].github_username == mock_user.login

    @pytest.mark.asyncio
    async def test_ensure_for_user_never_writes_index(
        self,
        people_repo: PeopleRepo,
        mock_index: AsyncMock,
        mock_draft_collection: AsyncMock,
        mock_user: User,
    ) -> None:
        """Test never writes to Index (read-only canonical source)."""
        # Setup Index to return empty list
        mock_index.get_people = AsyncMock(return_value=[])

        # Setup MongoDB
        mock_draft_collection.find_one = AsyncMock(return_value=None)
        mock_draft_collection.insert_one = AsyncMock()

        # Act
        await people_repo.ensure_for_user(mock_user)

        # Assert
        # Verify Index was only read from (get_people), never written to
        mock_index.get_people.assert_called_once()
        # Verify no other Index methods were called
        assert len(mock_index.method_calls) == 1  # Only get_people
        # Verify MongoDB was written to
        mock_draft_collection.insert_one.assert_called_once()


class TestPeopleRepoCache:
    """Test cache behavior."""

    @pytest.mark.asyncio
    async def test_clear_cache(
        self,
        people_repo: PeopleRepo,
        mock_person: Person,
    ) -> None:
        """Test cache clearing works."""
        # Pre-populate cache
        people_repo._cache["testuser"] = mock_person
        people_repo._index_loaded = True

        # Act
        await people_repo.clear_cache()

        # Assert
        assert len(people_repo._cache) == 0
        assert people_repo._index_loaded is False

    @pytest.mark.asyncio
    async def test_lazy_loading_index(
        self,
        people_repo: PeopleRepo,
        mock_index: AsyncMock,
        mock_person: Person,
    ) -> None:
        """Test Index loaded only on first access."""
        # Setup Index to return person
        mock_index.get_people = AsyncMock(return_value=[mock_person])

        # Verify Index not loaded initially
        assert people_repo._index_loaded is False

        # Act - First access triggers load
        result = await people_repo.get_by_username("testuser")

        # Assert
        assert result == mock_person
        assert people_repo._index_loaded is True
        mock_index.get_people.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_calls_load_index_once(
        self,
        people_repo: PeopleRepo,
        mock_index: AsyncMock,
        mock_person: Person,
    ) -> None:
        """Test Index loaded once even with multiple lookups."""
        # Setup Index to return person
        mock_index.get_people = AsyncMock(return_value=[mock_person])

        # Act - Multiple lookups
        await people_repo.get_by_username("testuser")
        await people_repo.get_by_username("testuser")
        await people_repo.get_by_username("otheruser")

        # Assert
        # Index should only be loaded once
        mock_index.get_people.assert_called_once()
        assert people_repo._index_loaded is True
