"""Integration tests for database layer."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError

from app.database import Database, UserRepo
from app.models import User, UserCreate, UserUpdate

pytestmark = pytest.mark.integration


class AsyncIteratorMock:
    """Helper class to mock async iterators for MongoDB cursors."""

    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


class TestDatabaseLifecycle:
    """Test Database class initialization and lifecycle management."""

    @pytest.mark.asyncio
    async def test_successful_database_connection(self):
        """Test successful MongoDB connection and initialization."""
        # Mock AsyncIOMotorClient
        mock_client = AsyncMock()
        mock_db = AsyncMock()
        mock_client.__getitem__.return_value = mock_db

        # Mock Index (findingmodel library)
        mock_index = AsyncMock()

        # Mock collections for people and organizations loading
        mock_people_collection = AsyncMock()
        mock_orgs_collection = AsyncMock()

        # Create async iterators for empty data - need to make find() return the iterator directly
        def mock_people_find(*args, **kwargs):
            return AsyncIteratorMock([])

        def mock_orgs_find(*args, **kwargs):
            return AsyncIteratorMock([])

        mock_people_collection.find = mock_people_find
        mock_orgs_collection.find = mock_orgs_find

        mock_index.people_collection = mock_people_collection
        mock_index.organizations_collection = mock_orgs_collection

        with (
            patch("app.database.AsyncIOMotorClient", return_value=mock_client),
            patch("app.database.Index", return_value=mock_index),
        ):
            database = Database()
            await database.connect()

            # Verify connection setup
            assert database.client is mock_client
            assert database.db is mock_db
            assert database.user_repo is not None
            assert database.finding_index is not None
            assert isinstance(database.user_repo, UserRepo)
            assert len(database.people) == 0
            assert len(database.organizations) == 0

    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """Test handling of MongoDB connection failures."""
        with patch("app.database.AsyncIOMotorClient", side_effect=ServerSelectionTimeoutError("Connection timeout")):
            database = Database()

            with pytest.raises(ServerSelectionTimeoutError):
                await database.connect()

    @pytest.mark.asyncio
    async def test_load_people_and_organizations_success(self):
        """Test successful loading of people and organizations into memory."""
        mock_client = AsyncMock()
        mock_db = AsyncMock()
        mock_client.__getitem__.return_value = mock_db

        # Mock finding index with test data
        mock_index = AsyncMock()
        mock_people_collection = AsyncMock()
        mock_orgs_collection = AsyncMock()

        # Sample test data
        people_data = [
            {"github_username": "user1", "name": "User One", "affiliation": "Test Org"},
            {"github_username": "user2", "name": "User Two", "affiliation": "Another Org"},
            {"no_github": "user3", "name": "User Three"},  # User without GitHub username
        ]

        orgs_data = [
            {"code": "ACR", "name": "American College of Radiology"},
            {"code": "RSNA", "name": "Radiological Society of North America"},
            {"code": "SIIM", "name": "Society for Imaging Informatics in Medicine"},
        ]

        # Create async iterators with test data
        def mock_people_find(*args, **kwargs):
            return AsyncIteratorMock(people_data)

        def mock_orgs_find(*args, **kwargs):
            return AsyncIteratorMock(orgs_data)

        mock_people_collection.find = mock_people_find
        mock_orgs_collection.find = mock_orgs_find

        mock_index.people_collection = mock_people_collection
        mock_index.organizations_collection = mock_orgs_collection

        with (
            patch("app.database.AsyncIOMotorClient", return_value=mock_client),
            patch("app.database.Index", return_value=mock_index),
            patch("app.database.Person") as mock_person_class,
            patch("app.database.Organization") as mock_org_class,
        ):
            # Mock Person and Organization model validation
            mock_person_class.model_validate.side_effect = lambda x: MagicMock(github_username=x.get("github_username"))
            mock_org_class.model_validate.side_effect = lambda x: MagicMock(code=x["code"])

            database = Database()
            await database.connect()

            # Verify people loaded (only those with github_username)
            assert len(database.people) == 2
            assert "user1" in database.people
            assert "user2" in database.people
            assert "user3" not in database.people  # No github_username

            # Verify organizations loaded
            assert len(database.organizations) == 3
            assert "ACR" in database.organizations
            assert "RSNA" in database.organizations
            assert "SIIM" in database.organizations

    @pytest.mark.asyncio
    async def test_load_people_organizations_with_database_error(self):
        """Test handling of database errors during people/orgs loading."""
        mock_client = AsyncMock()
        mock_db = AsyncMock()
        mock_client.__getitem__.return_value = mock_db

        mock_index = AsyncMock()
        mock_people_collection = AsyncMock()
        mock_orgs_collection = AsyncMock()

        # Mock database error during people loading - need to make find() method raise exception
        def mock_people_find_error(*args, **kwargs):
            raise Exception("Database connection lost")

        mock_people_collection.find = mock_people_find_error
        mock_index.people_collection = mock_people_collection
        mock_index.organizations_collection = mock_orgs_collection

        with (
            patch("app.database.AsyncIOMotorClient", return_value=mock_client),
            patch("app.database.Index", return_value=mock_index),
        ):
            database = Database()

            with pytest.raises(Exception, match="Database connection lost"):
                await database.connect()

    @pytest.mark.asyncio
    async def test_graceful_database_disconnection(self):
        """Test clean database disconnection."""
        mock_client = AsyncMock()
        # Make close() a regular mock method, not async
        mock_client.close = MagicMock()
        database = Database()
        database.client = mock_client

        await database.disconnect()

        mock_client.close.assert_called_once()
        assert database.user_repo is None
        assert database.finding_index is None


class TestUserRepoOperations:
    """Test UserRepo CRUD operations with comprehensive scenarios."""

    @pytest.fixture
    def mock_collection(self):
        """Mock MongoDB collection."""
        return AsyncMock()

    @pytest.fixture
    def user_repo(self, mock_collection):
        """UserRepo instance with mocked collection."""
        mock_db = MagicMock()
        mock_db.users = mock_collection
        return UserRepo(mock_db)

    @pytest.fixture
    def sample_user_create(self):
        """Sample user creation data."""
        return UserCreate(
            id=12345,
            login="testuser",
            name="Test User",
            email="test@example.com",
            avatar_url="https://avatars.githubusercontent.com/u/12345",
            html_url="https://github.com/testuser",
        )

    @pytest.fixture
    def sample_user(self):
        """Sample User model."""
        return User(
            id=12345,
            login="testuser",
            name="Test User",
            email="test@example.com",
            avatar_url="https://avatars.githubusercontent.com/u/12345",
            html_url="https://github.com/testuser",
            is_active=True,
            organizations=["ACR", "RSNA"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_repo, mock_collection, sample_user_create, sample_user):
        """Test successful user creation."""
        # Mock successful insertion
        mock_result = MagicMock()
        mock_result.inserted_id = "mock_object_id"
        mock_collection.insert_one.return_value = mock_result

        # Mock get_user to return the created user
        with patch.object(user_repo, "get_user", return_value=sample_user):
            result = await user_repo.create_user(sample_user_create)

            assert result.login == "testuser"
            assert result.email == "test@example.com"
            assert result.is_active is True

            # Verify insert_one was called with proper data structure
            mock_collection.insert_one.assert_called_once()
            call_args = mock_collection.insert_one.call_args[0][0]
            assert call_args["id"] == 12345
            assert call_args["login"] == "testuser"
            assert call_args["is_active"] is True
            assert "created_at" in call_args
            assert "updated_at" in call_args

    @pytest.mark.asyncio
    async def test_create_user_duplicate_key_error(self, user_repo, mock_collection, sample_user_create, sample_user):
        """Test creating user when duplicate exists (GitHub ID collision)."""
        # Mock duplicate key error on insertion
        mock_collection.insert_one.side_effect = DuplicateKeyError("E11000 duplicate key error")

        # Mock get_user to return existing user
        with patch.object(user_repo, "get_user", return_value=sample_user):
            result = await user_repo.create_user(sample_user_create)

            # Should return the existing user without error
            assert result.login == "testuser"
            assert result.id == 12345

            # Verify it attempted to insert and then retrieved existing user
            mock_collection.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_insertion_failure(self, user_repo, mock_collection, sample_user_create):
        """Test user creation when insertion fails and user doesn't exist."""
        # Mock insertion returning None (no inserted_id)
        mock_result = MagicMock()
        mock_result.inserted_id = None
        mock_collection.insert_one.return_value = mock_result

        # Mock get_user to return None (user doesn't exist)
        with (
            patch.object(user_repo, "get_user", return_value=None),
            pytest.raises(ValueError, match="Failed to create user"),
        ):
            await user_repo.create_user(sample_user_create)

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, user_repo, mock_collection, sample_user):
        """Test successful user retrieval by GitHub ID."""
        user_dict = sample_user.model_dump()
        user_dict["_id"] = "mock_mongodb_object_id"

        mock_collection.find_one.return_value = user_dict

        result = await user_repo.get_user(12345)

        assert result is not None
        assert result.id == 12345
        assert result.login == "testuser"
        assert result.email == "test@example.com"

        mock_collection.find_one.assert_called_once_with({"id": 12345})

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_repo, mock_collection):
        """Test user retrieval when user doesn't exist."""
        mock_collection.find_one.return_value = None

        result = await user_repo.get_user(99999)

        assert result is None
        mock_collection.find_one.assert_called_once_with({"id": 99999})

    @pytest.mark.asyncio
    async def test_get_user_by_login_success(self, user_repo, mock_collection, sample_user):
        """Test successful user retrieval by GitHub login."""
        user_dict = sample_user.model_dump()
        user_dict["_id"] = "mock_mongodb_object_id"

        mock_collection.find_one.return_value = user_dict

        result = await user_repo.get_user_by_login("testuser")

        assert result is not None
        assert result.login == "testuser"
        assert result.id == 12345

        mock_collection.find_one.assert_called_once_with({"login": "testuser"})

    @pytest.mark.asyncio
    async def test_get_user_by_login_not_found(self, user_repo, mock_collection):
        """Test user retrieval by login when user doesn't exist."""
        mock_collection.find_one.return_value = None

        result = await user_repo.get_user_by_login("nonexistent")

        assert result is None
        mock_collection.find_one.assert_called_once_with({"login": "nonexistent"})

    @pytest.mark.asyncio
    async def test_update_user_success(self, user_repo, mock_collection, sample_user):
        """Test successful user profile update."""
        update_data = UserUpdate(
            name="Updated Name", email="updated@example.com", organizations=["ACR", "RSNA", "SIIM"]
        )

        # Mock successful update
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result

        # Mock get_user to return updated user
        updated_user = User(
            id=12345,
            login="testuser",
            name="Updated Name",
            email="updated@example.com",
            avatar_url="https://avatars.githubusercontent.com/u/12345",
            html_url="https://github.com/testuser",
            is_active=True,
            organizations=["ACR", "RSNA", "SIIM"],
            created_at=sample_user.created_at,
            updated_at=datetime.now(UTC),
        )

        with patch.object(user_repo, "get_user", return_value=updated_user):
            result = await user_repo.update_user(12345, update_data)

            assert result is not None
            assert result.name == "Updated Name"
            assert result.email == "updated@example.com"
            assert result.organizations == ["ACR", "RSNA", "SIIM"]

            # Verify update_one was called with proper filter and update
            mock_collection.update_one.assert_called_once()
            call_args = mock_collection.update_one.call_args
            assert call_args[0][0] == {"id": 12345}  # Filter
            assert "$set" in call_args[0][1]  # Update operation
            assert "updated_at" in call_args[0][1]["$set"]  # Updated timestamp

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_repo, mock_collection):
        """Test updating user that doesn't exist."""
        update_data = UserUpdate(name="Updated Name")

        # Mock no documents modified (user doesn't exist)
        mock_result = MagicMock()
        mock_result.modified_count = 0
        mock_collection.update_one.return_value = mock_result

        result = await user_repo.update_user(99999, update_data)

        assert result is None
        mock_collection.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_partial_update(self, user_repo, mock_collection, sample_user):
        """Test partial user update (only some fields)."""
        update_data = UserUpdate(organizations=["ACR", "SIIM"])  # Only update organizations

        # Mock successful update
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result

        updated_user = User(
            id=sample_user.id,
            login=sample_user.login,
            name=sample_user.name,  # Unchanged
            email=sample_user.email,  # Unchanged
            avatar_url=sample_user.avatar_url,
            html_url=sample_user.html_url,
            is_active=sample_user.is_active,
            organizations=["ACR", "SIIM"],  # Changed
            created_at=sample_user.created_at,
            updated_at=datetime.now(UTC),
        )

        with patch.object(user_repo, "get_user", return_value=updated_user):
            result = await user_repo.update_user(12345, update_data)

            assert result is not None
            assert result.organizations == ["ACR", "SIIM"]
            # Other fields should remain unchanged
            assert result.name == sample_user.name
            assert result.email == sample_user.email


class TestDatabaseErrorScenarios:
    """Test database operations under various error conditions."""

    @pytest.fixture
    def user_repo(self):
        """UserRepo with mock collection for error testing."""
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.users = mock_collection
        return UserRepo(mock_db), mock_collection

    @pytest.mark.asyncio
    async def test_database_timeout_during_user_creation(self, user_repo):
        """Test handling of database timeouts during user creation."""
        repo, mock_collection = user_repo

        # Mock timeout error
        mock_collection.insert_one.side_effect = ServerSelectionTimeoutError("Connection timeout")

        user_create = UserCreate(id=12345, login="testuser", name="Test User", email="test@example.com")

        with pytest.raises(ServerSelectionTimeoutError):
            await repo.create_user(user_create)

    @pytest.mark.asyncio
    async def test_database_timeout_during_user_retrieval(self, user_repo):
        """Test handling of database timeouts during user retrieval."""
        repo, mock_collection = user_repo

        # Mock timeout error
        mock_collection.find_one.side_effect = ServerSelectionTimeoutError("Connection timeout")

        with pytest.raises(ServerSelectionTimeoutError):
            await repo.get_user(12345)

    @pytest.mark.asyncio
    async def test_database_timeout_during_user_update(self, user_repo):
        """Test handling of database timeouts during user updates."""
        repo, mock_collection = user_repo

        # Mock timeout error
        mock_collection.update_one.side_effect = ServerSelectionTimeoutError("Connection timeout")

        update_data = UserUpdate(name="Updated Name")

        with pytest.raises(ServerSelectionTimeoutError):
            await repo.update_user(12345, update_data)

    @pytest.mark.asyncio
    async def test_corrupted_data_handling(self, user_repo):
        """Test handling of corrupted data from database."""
        repo, mock_collection = user_repo

        # Mock corrupted data (missing required fields)
        corrupted_data = {
            "_id": "mock_id",
            "id": 12345,
            "login": "testuser",
            # Missing required fields like created_at, updated_at
        }

        mock_collection.find_one.return_value = corrupted_data

        # Should handle Pydantic validation errors gracefully
        with pytest.raises((ValueError, TypeError)):  # ValidationError is a subclass of ValueError
            await repo.get_user(12345)

    @pytest.mark.asyncio
    async def test_network_partition_scenario(self, user_repo):
        """Test behavior during network partitions (MongoDB unavailable)."""
        repo, mock_collection = user_repo

        # Mock network partition - all operations fail
        network_error = Exception("Network is unreachable")
        mock_collection.find_one.side_effect = network_error
        mock_collection.insert_one.side_effect = network_error
        mock_collection.update_one.side_effect = network_error

        # All operations should propagate the network error
        with pytest.raises(Exception, match="Network is unreachable"):
            await repo.get_user(12345)

        with pytest.raises(Exception, match="Network is unreachable"):
            await repo.create_user(UserCreate(id=123, login="test", email="test@example.com"))

        with pytest.raises(Exception, match="Network is unreachable"):
            await repo.update_user(12345, UserUpdate(name="Test"))


class TestDatabaseCacheIntegration:
    """Test database operations integrated with caching layer."""

    @pytest.mark.asyncio
    async def test_database_operations_with_cache_available(self):
        """Test that database operations work normally when cache is available."""
        from app.auth import get_or_create_user
        from app.models import GitHubUser

        # Mock database
        mock_user_repo = AsyncMock()

        # Mock cache
        mock_cache = AsyncMock()
        mock_cache.get_user.return_value = None  # Cache miss

        # Mock user creation
        created_user = User(
            id=12345,
            login="integrationuser",
            name="Integration User",
            email="integration@example.com",
            is_active=True,
            organizations=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_user_repo.get_user.return_value = None  # User doesn't exist
        mock_user_repo.create_user.return_value = created_user

        github_user = GitHubUser(
            id=12345,
            login="integrationuser",
            name="Integration User",
            email="integration@example.com",
            avatar_url="https://avatar.example.com",
            html_url="https://github.com/integrationuser",
            type="User",
        )

        # Test the integration
        user, is_new = await get_or_create_user(github_user, mock_user_repo, mock_cache)

        assert user.login == "integrationuser"
        assert is_new is True

        # Verify database was called
        mock_user_repo.get_user.assert_called_once_with(12345)
        mock_user_repo.create_user.assert_called_once()

        # Verify cache was attempted to be populated
        mock_cache.set_user.assert_called_once()
        mock_cache.set_user_by_login.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_fallback_when_cache_fails(self):
        """Test that database operations continue when cache operations fail."""
        from app.auth import get_or_create_user
        from app.models import GitHubUser

        # Mock database
        mock_user_repo = AsyncMock()
        existing_user = User(
            id=12345,
            login="fallbackuser",
            name="Fallback User",
            email="fallback@example.com",
            is_active=True,
            organizations=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_user_repo.get_user.return_value = existing_user

        # Mock cache that fails gracefully (returns None, doesn't raise) - this is how RedisCache actually behaves
        mock_cache = AsyncMock()
        mock_cache.get_user.return_value = None  # Cache miss due to internal failure
        mock_cache.set_user.return_value = None  # Set operations silently fail
        mock_cache.set_user_by_login.return_value = None  # Set operations silently fail

        github_user = GitHubUser(
            id=12345,
            login="fallbackuser",
            name="Fallback User",
            email="fallback@example.com",
            avatar_url="https://avatar.example.com",
            html_url="https://github.com/fallbackuser",
            type="User",
        )

        # Should still work despite cache failures
        user, is_new = await get_or_create_user(github_user, mock_user_repo, mock_cache)

        assert user.login == "fallbackuser"
        assert is_new is False

        # Database should have been called as fallback
        mock_user_repo.get_user.assert_called_once_with(12345)
