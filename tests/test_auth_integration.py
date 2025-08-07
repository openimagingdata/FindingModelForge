"""Integration tests for authentication flow."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.auth import get_github_access_token, get_github_user, get_or_create_user, verify_token
from app.models import GitHubUser, User

pytestmark = pytest.mark.integration


class TestGitHubAPIIntegration:
    """Test integration with GitHub OAuth API."""

    @pytest.mark.asyncio
    async def test_get_github_access_token_success(self):
        """Test successful GitHub token exchange."""
        # Mock httpx.AsyncClient to return successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "gho_test123456789",
            "token_type": "bearer",
            "scope": "user:email",
        }

        with patch("httpx.AsyncClient") as mock_client:
            # Setup the async context manager
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            token = await get_github_access_token("test_auth_code")

            assert token == "gho_test123456789"

    @pytest.mark.asyncio
    async def test_get_github_access_token_api_error(self):
        """Test GitHub API error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "bad_verification_code",
            "error_description": "The code passed is incorrect or expired.",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(HTTPException) as exc_info:
                await get_github_access_token("invalid_code")

            assert exc_info.value.status_code == 400
            assert "Failed to exchange code for token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_github_access_token_network_timeout(self):
        """Test handling network timeouts."""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock timeout exception
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Request timed out")
            )

            with pytest.raises(httpx.TimeoutException):
                await get_github_access_token("test_code")

    @pytest.mark.asyncio
    async def test_get_github_user_success(self):
        """Test successful GitHub user data retrieval."""
        github_user_data = {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
            "html_url": "https://github.com/testuser",
            "type": "User",
            "site_admin": False,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = github_user_data

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            user = await get_github_user("gho_test123456789")

            assert isinstance(user, GitHubUser)
            assert user.id == 12345
            assert user.login == "testuser"
            assert user.name == "Test User"
            assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_github_user_invalid_token(self):
        """Test GitHub user API with invalid token."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "message": "Bad credentials",
            "documentation_url": "https://docs.github.com/rest",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            with pytest.raises(HTTPException) as exc_info:
                await get_github_user("invalid_token")

            assert exc_info.value.status_code == 400
            assert "Failed to fetch user information" in str(exc_info.value.detail)


class TestUserCreationFlow:
    """Test user creation and retrieval with caching."""

    @pytest.fixture
    def sample_github_user(self):
        """Sample GitHub user for testing."""
        return GitHubUser(
            id=12345,
            login="testuser",
            name="Test User",
            email="test@example.com",
            avatar_url="https://avatars.githubusercontent.com/u/12345",
            html_url="https://github.com/testuser",
            type="User",
            site_admin=False,
        )

    @pytest.fixture
    def sample_user(self):
        """Sample User model for testing."""
        return User(
            id=12345,
            login="testuser",
            name="Test User",
            email="test@example.com",
            avatar_url="https://avatars.githubusercontent.com/u/12345",
            html_url="https://github.com/testuser",
            is_active=True,
            organizations=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_get_or_create_user_cache_hit(self, sample_github_user, sample_user):
        """Test cache hit scenario."""
        mock_cache = AsyncMock()
        mock_user_repo = AsyncMock()

        # Mock cache hit
        mock_cache.get_user.return_value = sample_user

        user, is_new = await get_or_create_user(sample_github_user, mock_user_repo, mock_cache)

        assert user.login == "testuser"
        assert is_new is False

        # Should only check cache, not database
        mock_cache.get_user.assert_called_once_with("12345")
        mock_user_repo.get_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_user_cache_miss_database_hit(self, sample_github_user, sample_user):
        """Test cache miss but database has user."""
        mock_cache = AsyncMock()
        mock_user_repo = AsyncMock()

        # Mock cache miss, database hit
        mock_cache.get_user.return_value = None
        mock_user_repo.get_user.return_value = sample_user

        user, is_new = await get_or_create_user(sample_github_user, mock_user_repo, mock_cache)

        assert user.login == "testuser"
        assert is_new is False

        # Should check both cache and database, then update cache
        mock_cache.get_user.assert_called_once_with("12345")
        mock_user_repo.get_user.assert_called_once_with(12345)
        mock_cache.set_user.assert_called_once_with("12345", sample_user)
        mock_cache.set_user_by_login.assert_called_once_with(sample_user)

    @pytest.mark.asyncio
    async def test_get_or_create_user_new_user_creation(self, sample_github_user, sample_user):
        """Test creating completely new user."""
        mock_cache = AsyncMock()
        mock_user_repo = AsyncMock()

        # Mock cache and database miss, user creation
        mock_cache.get_user.return_value = None
        mock_user_repo.get_user.return_value = None
        mock_user_repo.create_user.return_value = sample_user

        user, is_new = await get_or_create_user(sample_github_user, mock_user_repo, mock_cache)

        assert user.login == "testuser"
        assert is_new is True

        # Should check cache, check database, create user, then cache
        mock_cache.get_user.assert_called_once_with("12345")
        mock_user_repo.get_user.assert_called_once_with(12345)
        mock_user_repo.create_user.assert_called_once()
        mock_cache.set_user.assert_called_once_with("12345", sample_user)
        mock_cache.set_user_by_login.assert_called_once_with(sample_user)


class TestCompleteOAuthFlow:
    """Test the complete OAuth authentication flow end-to-end."""

    @pytest.mark.asyncio
    async def test_oauth_callback_new_user_flow(self, client):
        """Test complete OAuth callback flow for new user."""

        # Mock GitHub token exchange response
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"access_token": "gho_test123", "token_type": "bearer"}

        # Mock GitHub user API response
        github_user_data = {
            "id": 12345,
            "login": "newuser",
            "name": "New User",
            "email": "new@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
            "html_url": "https://github.com/newuser",
            "type": "User",
            "site_admin": False,
        }

        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = github_user_data

        # Setup httpx mocking
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_token_response)
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_user_response)

            # Mock the get_or_create_user function to simulate new user creation
            new_user = User(
                id=12345,
                login="newuser",
                name="New User",
                email="new@example.com",
                avatar_url="https://avatars.githubusercontent.com/u/12345",
                html_url="https://github.com/newuser",
                is_active=True,
                organizations=[],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

            with patch("app.routers.auth.get_or_create_user") as mock_get_or_create:
                mock_get_or_create.return_value = (new_user, True)  # is_new_user=True

                # Make the OAuth callback request
                response = client.get("/auth/callback?code=test_auth_code", follow_redirects=False)

                # Verify the response
                assert response.status_code == 303  # Redirect
                assert response.headers["location"] == "/profile?welcome=true"  # New user gets welcome

                # Verify JWT cookies are set
                cookies = response.cookies
                assert "access_token" in cookies
                assert "refresh_token" in cookies

                # Verify JWT token is valid
                access_token = cookies["access_token"]
                decoded = verify_token(access_token)
                assert decoded is not None
                assert decoded.user_id == 12345
                assert decoded.username == "newuser"

    @pytest.mark.asyncio
    async def test_oauth_callback_existing_user_flow(self, client):
        """Test OAuth callback flow for existing user."""

        # Mock GitHub token exchange response
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"access_token": "gho_test123", "token_type": "bearer"}

        # Mock GitHub user API response
        github_user_data = {
            "id": 54321,
            "login": "existinguser",
            "name": "Existing User",
            "email": "existing@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/54321",
            "html_url": "https://github.com/existinguser",
            "type": "User",
            "site_admin": False,
        }

        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = github_user_data

        # Setup httpx mocking and create existing user
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_token_response)
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_user_response)

            existing_user = User(
                id=54321,
                login="existinguser",
                name="Existing User",
                email="existing@example.com",
                avatar_url="https://avatars.githubusercontent.com/u/54321",
                html_url="https://github.com/existinguser",
                is_active=True,
                organizations=["ACR"],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

            with patch("app.routers.auth.get_or_create_user") as mock_get_or_create:
                mock_get_or_create.return_value = (existing_user, False)  # is_new_user=False

                response = client.get("/auth/callback?code=test_auth_code", follow_redirects=False)

                assert response.status_code == 303
                assert response.headers["location"] == "/profile"  # Existing user, no welcome

                # Verify JWT token
                access_token = response.cookies["access_token"]
                decoded = verify_token(access_token)
                assert decoded.user_id == 54321
                assert decoded.username == "existinguser"

    @pytest.mark.asyncio
    async def test_oauth_callback_github_error(self, client):
        """Test OAuth callback handles GitHub API errors."""

        # Mock GitHub token endpoint failure
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "bad_verification_code"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            response = client.get("/auth/callback?code=invalid_code", follow_redirects=False)

            # Should redirect to login page on error
            assert response.status_code == 303
            assert response.headers["location"] == "/login"

            # Should not set any authentication cookies
            assert "access_token" not in response.cookies
            assert "refresh_token" not in response.cookies


class TestAuthenticationMiddleware:
    """Test authentication in protected endpoints."""

    def test_protected_endpoint_requires_auth(self, client):
        """Test that protected endpoints require authentication."""
        # Try accessing protected endpoint without authentication
        response = client.get("/auth/me")
        assert response.status_code == 401

        response = client.get("/api/users/profile")
        assert response.status_code == 401
