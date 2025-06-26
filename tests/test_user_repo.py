"""Test the new user management functionality."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database import UserRepo
from app.models import User, UserCreate, UserUpdate


class TestUserRepo:
    """Test the UserRepo class."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Mock database."""
        db = MagicMock()
        db.users = AsyncMock()
        return db

    @pytest.fixture
    def user_repo(self, mock_db: MagicMock) -> UserRepo:
        """UserRepo instance with mocked database."""
        return UserRepo(mock_db)

    @pytest.fixture
    def sample_user_create(self) -> UserCreate:
        """Sample user creation data."""
        return UserCreate(
            id=12345,
            login="testuser",
            name="Test User",
            email="test@example.com",
            avatar_url="https://avatar.example.com/testuser.jpg",
            html_url="https://github.com/testuser",
        )

    @pytest.fixture
    def sample_user(self) -> User:
        """Sample user data."""
        now = datetime.now(UTC)
        return User(
            id=12345,
            login="testuser",
            name="Test User",
            email="test@example.com",
            avatar_url="https://avatar.example.com/testuser.jpg",
            html_url="https://github.com/testuser",
            is_active=True,
            organizations=["ACR", "RSNA"],
            created_at=now,
            updated_at=now,
        )

    async def test_create_user(self, user_repo: UserRepo, sample_user_create: UserCreate, sample_user: User) -> None:
        """Test creating a new user."""
        # Mock the collection methods
        user_repo.collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="mock_id"))  # type: ignore[method-assign]
        user_repo.get_user = AsyncMock(return_value=sample_user)  # type: ignore[method-assign]

        result = await user_repo.create_user(sample_user_create)

        assert result.id == sample_user.id
        assert result.login == sample_user.login
        assert result.email == sample_user.email

    async def test_get_user(self, user_repo: UserRepo, sample_user: User) -> None:
        """Test getting a user by ID."""
        user_dict = sample_user.model_dump()
        user_dict["_id"] = "mock_object_id"

        user_repo.collection.find_one = AsyncMock(return_value=user_dict)  # type: ignore[method-assign]

        result = await user_repo.get_user(12345)

        assert result is not None
        assert result.id == sample_user.id
        assert result.login == sample_user.login

    async def test_get_user_not_found(self, user_repo: UserRepo) -> None:
        """Test getting a user that doesn't exist."""
        user_repo.collection.find_one = AsyncMock(return_value=None)  # type: ignore[method-assign]

        result = await user_repo.get_user(99999)

        assert result is None

    async def test_update_user(self, user_repo: UserRepo, sample_user: User) -> None:
        """Test updating user information."""
        update_data = UserUpdate(name="Updated Name", email="updated@example.com")

        user_repo.collection.update_one = AsyncMock(return_value=MagicMock(modified_count=1))  # type: ignore[method-assign]
        user_repo.get_user = AsyncMock(return_value=sample_user)  # type: ignore[method-assign]

        result = await user_repo.update_user(12345, update_data)

        assert result is not None
        assert result.id == sample_user.id

    async def test_update_user_organizations(self, user_repo: UserRepo, sample_user: User) -> None:
        """Test updating user organizations."""
        # Update user with new organizations list
        update_data = UserUpdate(organizations=["ACR", "RSNA", "SIIM"])

        user_repo.collection.update_one = AsyncMock(return_value=MagicMock(modified_count=1))  # type: ignore[method-assign]
        user_repo.get_user = AsyncMock(return_value=sample_user)  # type: ignore[method-assign]

        result = await user_repo.update_user(12345, update_data)

        assert result is not None
        assert result.id == sample_user.id
