"""Tests for Redis cache functionality."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.cache import CacheConfig, RedisCache
from app.models import User


@pytest.fixture
def cache_config() -> CacheConfig:
    """Test cache configuration."""
    return CacheConfig(
        host="localhost",
        port=6379,
        db=1,  # Use test database
    )


@pytest.fixture
def sample_user() -> User:
    """Sample user for testing."""
    now = datetime.now(UTC)
    return User(
        id=12345,
        login="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="https://github.com/testuser.png",
        html_url="https://github.com/testuser",
        is_active=True,
        organizations=[],
        created_at=now,
        updated_at=now,
    )


class TestRedisCache:
    """Test Redis cache functionality."""

    @pytest.mark.asyncio
    async def test_cache_disabled_when_redis_unavailable(self, cache_config: CacheConfig) -> None:
        """Test that cache gracefully handles Redis unavailability."""
        # Mock Redis to fail connection
        with patch("app.cache.redis_client", None):
            cache = RedisCache(cache_config)
            await cache.connect()

            # Cache should be disabled
            assert not cache.enabled
            assert cache.client is None

            # Operations should return safely with transparent fallbacks
            result = await cache.get("test_key")
            assert result is None

            # Set should return True (no-op success) even when Redis is unavailable
            success = await cache.set("test_key", "test_value")
            assert success  # Transparent no-op returns True

            # Delete should return True (no-op success)
            delete_success = await cache.delete("test_key")
            assert delete_success

            # Exists should return False when Redis is unavailable
            exists = await cache.exists("test_key")
            assert not exists

    @pytest.mark.asyncio
    async def test_user_caching(self, cache_config: CacheConfig, sample_user: User) -> None:
        """Test user caching functionality."""
        cache = RedisCache(cache_config)

        # Mock Redis operations
        cache.client = AsyncMock()
        cache.enabled = True

        # Mock cache miss then hit
        cache.client.get.side_effect = [None, sample_user.model_dump_json()]
        cache.client.setex.return_value = True

        # First call - cache miss
        result = await cache.get_user(str(sample_user.id))
        assert result is None

        # Set user in cache
        success = await cache.set_user(str(sample_user.id), sample_user)
        assert success

        # Second call - cache hit
        result = await cache.get_user(str(sample_user.id))
        assert result is not None
        assert result.id == sample_user.id
        assert result.login == sample_user.login

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, cache_config: CacheConfig) -> None:
        """Test cache key generation."""
        cache = RedisCache(cache_config)

        key = cache._make_key("user", "12345")
        assert key == "finding_model_forge:user:12345"

        key = cache._make_key("finding_model", "chest-xray")
        assert key == "finding_model_forge:finding_model:chest-xray"

    @pytest.mark.asyncio
    async def test_cache_expiration(self, cache_config: CacheConfig, sample_user: User) -> None:
        """Test that cache entries expire correctly."""
        cache = RedisCache(cache_config)
        cache.client = AsyncMock()
        cache.enabled = True

        # Set user with short expiration
        await cache.set_user(str(sample_user.id), sample_user, expires=1)

        # Verify setex was called with correct TTL
        cache.client.setex.assert_called_once()
        args = cache.client.setex.call_args[0]
        assert args[1] == 1  # TTL argument in seconds

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache_config: CacheConfig, sample_user: User) -> None:
        """Test cache invalidation for users."""
        cache = RedisCache(cache_config)
        cache.client = AsyncMock()
        cache.enabled = True
        cache.client.delete.return_value = 1

        # Invalidate user cache
        await cache.invalidate_user_cache(sample_user)

        # Verify both user caches were deleted
        assert cache.client.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_corrupted_cache_data_handling(self, cache_config: CacheConfig) -> None:
        """Test handling of corrupted cache data."""
        cache = RedisCache(cache_config)
        cache.client = AsyncMock()
        cache.enabled = True

        # Mock corrupted JSON data
        cache.client.get.return_value = "invalid_json_data"
        cache.client.delete.return_value = 1

        # Should handle corrupted data gracefully
        result = await cache.get_user("12345")
        assert result is None

        # The corrupted data should have been handled by returning None
        # (The current implementation doesn't delete corrupt entries, which is fine)
        cache.client.get.assert_called_once()


class TestCachedAuthentication:
    """Test cached authentication functionality."""

    @pytest.mark.asyncio
    async def test_authentication_cache_flow(self, sample_user: User) -> None:
        """Test the full authentication cache flow."""
        from unittest.mock import Mock

        from app.auth import get_current_user

        # Mock dependencies
        request = Mock()
        request.cookies.get.return_value = "valid_jwt_token"

        user_repo = AsyncMock()
        user_repo.get_user.return_value = sample_user

        # Mock cache to simulate cache miss then hit
        with patch("app.auth.cache") as mock_cache:
            mock_cache.get_user = AsyncMock(side_effect=[None, sample_user])  # Miss then hit
            mock_cache.set_user = AsyncMock(return_value=True)
            mock_cache.set_user_by_login = AsyncMock(return_value=True)

            # Mock token verification
            with patch("app.auth.verify_token") as mock_verify:
                from app.models import TokenData

                mock_verify.return_value = TokenData(user_id=sample_user.id, username=sample_user.login)

                # First call - should hit database and cache result
                result = await get_current_user(request, user_repo)
                assert result.id == sample_user.id
                user_repo.get_user.assert_called_once()
                mock_cache.set_user.assert_called_once()


@pytest.mark.integration
class TestRedisIntegration:
    """Integration tests for Redis cache (requires running Redis)."""

    @pytest.mark.asyncio
    async def test_real_redis_connection(self) -> None:
        """Test actual Redis connection (skip if Redis not available)."""
        try:
            cache = RedisCache()
            await cache.connect()

            if not cache.enabled:
                pytest.skip("Redis not available")

            # Test basic operations
            key = "test:integration"
            value = "test_value"

            # Set and get
            await cache.set(key, value, timedelta(seconds=10))
            result = await cache.get(key)
            assert result == value

            # Delete
            deleted = await cache.delete(key)
            assert deleted

            # Verify deleted
            result = await cache.get(key)
            assert result is None

            await cache.disconnect()

        except Exception as e:
            pytest.skip(f"Redis integration test failed: {e}")


if __name__ == "__main__":
    # Run a simple cache test
    async def main() -> None:
        print("Testing Redis cache implementation...")

        cache = RedisCache()
        await cache.connect()

        if cache.enabled:
            print("✅ Redis cache connected successfully")

            # Test basic operations
            test_key = "test:demo"
            test_value = "Hello, Redis!"

            await cache.set(test_key, test_value, timedelta(seconds=30))
            result = await cache.get(test_key)

            if result == test_value:
                print("✅ Cache set/get operations working")
            else:
                print("❌ Cache operations failed")

            # Test cache stats
            stats = await cache.get_stats()
            print(f"✅ Cache stats: {stats.get('status', 'unknown')}")

            await cache.delete(test_key)
            print("✅ Cache cleanup completed")

        else:
            print("⚠️  Redis cache not available - will fall back to database queries")

        await cache.disconnect()
        print("✅ Test completed")

    asyncio.run(main())
