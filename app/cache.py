"""Redis cache implementation for FindingModelForge."""

import asyncio
from datetime import timedelta
from typing import Any

import redis.asyncio as redis_client
from findingmodel import FindingModelFull
from loguru import logger
from pydantic import BaseModel

from .config import settings
from .models import GitHubUser, User


class CacheConfig(BaseModel):
    """Cache configuration settings."""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    decode_responses: bool = True
    socket_connect_timeout: int = 5
    socket_keepalive: bool = True
    socket_keepalive_options: dict[str, int] = {}
    health_check_interval: int = 30
    max_connections: int = 20


class RedisCache:
    """Redis cache manager for user data and other cacheable items."""

    def __init__(self, config: CacheConfig | None = None) -> None:
        """Initialize Redis cache with configuration."""
        self.config = config or CacheConfig()
        self.client: Any = None  # Redis client instance
        self.connection_pool: Any = None  # Connection pool instance
        self.enabled = False  # Will be set to True if Redis connection succeeds

    async def connect(self) -> None:
        """Connect to Redis server."""
        try:
            # Create connection pool for better performance
            self.connection_pool = redis_client.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                decode_responses=self.config.decode_responses,
                socket_connect_timeout=self.config.socket_connect_timeout,
                socket_keepalive=self.config.socket_keepalive,
                socket_keepalive_options=self.config.socket_keepalive_options,
                health_check_interval=self.config.health_check_interval,
                max_connections=self.config.max_connections,
            )

            # Create Redis client using the connection pool
            self.client = redis_client.Redis(connection_pool=self.connection_pool)

            # Test connection
            await self.client.ping()
            logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")
            self.enabled = True

        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e} - cache will be disabled")
            # Don't raise exception - fall back to no caching
            self.client = None
            self.connection_pool = None
            self.enabled = False

    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        if self.client:
            await self.client.aclose()
            self.client = None

        if self.connection_pool:
            await self.connection_pool.aclose()
            self.connection_pool = None

        logger.info("Disconnected from Redis")

    async def is_healthy(self) -> bool:
        """Check if Redis connection is healthy."""
        if not self.client:
            return False

        try:
            await self.client.ping()
            return True
        except Exception:
            return False

    def _make_key(self, prefix: str, identifier: str) -> str:
        """Create a cache key with prefix and identifier."""
        return f"{settings.app_name.lower().replace(' ', '_')}:{prefix}:{identifier}"

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        if not self.client:
            return None

        try:
            value = await self.client.get(key)
            if value:
                logger.debug(f"Cache hit for key: {key}")
                return str(value)
            else:
                logger.debug(f"Cache miss for key: {key}")
                return None
        except Exception:
            return None

    async def set(
        self,
        key: str,
        value: str,
        expires_in: timedelta | None = None,
    ) -> bool:
        """Set value in cache with optional expiration."""
        if not self.client:
            return True  # Return True to indicate "success" (no-op)

        try:
            if expires_in:
                await self.client.setex(key, expires_in, value)
            else:
                await self.client.set(key, value)

            logger.debug(f"Cache set for key: {key}")
            return True
        except Exception:
            return True  # Still return True - cache failure shouldn't break the app

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.client:
            return True  # Return True to indicate "success" (no-op)

        try:
            result = await self.client.delete(key)
            logger.debug(f"Cache delete for key: {key}, result: {result}")
            return bool(result)
        except Exception:
            return True  # Still return True - cache failure shouldn't break the app

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.client:
            return False

        try:
            result = await self.client.exists(key)
            return bool(result)
        except Exception:
            return False

    # User-specific cache methods using Pydantic serialization
    async def set_user(self, user_id: str, user: User, expires: int = 3600) -> bool:
        """Cache a user object with expiration time in seconds."""
        if not self.client:
            return True  # Return True to indicate "success" (no-op)

        try:
            user_json = user.model_dump_json()
            await self.client.setex(f"user:{user_id}", expires, user_json)
            logger.debug(f"Cached user {user_id} for {expires} seconds")
            return True
        except Exception:
            return True  # Still return True - cache failure shouldn't break the app

    async def get_user(self, user_id: str) -> User | None:
        """Retrieve a user from cache and return as User object."""
        if not self.client:
            return None

        try:
            user_json = await self.client.get(f"user:{user_id}")
            if user_json:
                user = User.model_validate_json(user_json)
                logger.debug(f"Retrieved user {user_id} from cache")
                return user
            return None
        except Exception:
            return None

    async def delete_user(self, user_id: str) -> bool:
        """Delete user from cache."""
        if not self.client:
            return True  # Return True to indicate "success" (no-op)

        try:
            result = await self.client.delete(f"user:{user_id}")
            logger.debug(f"Deleted user {user_id} from cache")
            return bool(result)
        except Exception:
            return True  # Still return True - cache failure shouldn't break the app

    async def get_user_by_login(self, login: str) -> User | None:
        """Get user by login from cache."""
        key = self._make_key("user_by_login", login.lower())
        cached_data = await self.get(key)

        if cached_data:
            try:
                return User.model_validate_json(cached_data)
            except Exception as e:
                logger.warning(f"Failed to deserialize cached user by login {login}: {e}")
                await self.delete(key)

        return None

    async def set_user_by_login(
        self,
        user: User,
        expires_in: timedelta | None = None,
    ) -> bool:
        """Set user by login in cache."""
        key = self._make_key("user_by_login", user.login.lower())
        user_json = user.model_dump_json()

        if expires_in is None:
            expires_in = timedelta(minutes=30)

        return await self.set(key, user_json, expires_in)

    async def delete_user_by_login(self, login: str) -> bool:
        """Delete user by login from cache."""
        key = self._make_key("user_by_login", login.lower())
        return await self.delete(key)

    # GitHub user data caching (for OAuth flow)
    async def get_github_user_data(self, github_user_id: int) -> GitHubUser | None:
        """Get GitHub user data from cache."""
        key = self._make_key("github_user", str(github_user_id))
        cached_data = await self.get(key)

        if cached_data:
            try:
                return GitHubUser.model_validate_json(cached_data)
            except Exception as e:
                logger.warning(f"Failed to deserialize cached GitHub user {github_user_id}: {e}")
                await self.delete(key)

        return None

    async def set_github_user_data(
        self,
        github_user_id: int,
        user_data: GitHubUser,
        expires_in: timedelta | None = None,
    ) -> bool:
        """Set GitHub user data in cache."""
        key = self._make_key("github_user", str(github_user_id))
        user_json = user_data.model_dump_json()

        # GitHub user data has shorter expiration
        if expires_in is None:
            expires_in = timedelta(minutes=15)

        return await self.set(key, user_json, expires_in)

    # Finding models cache methods
    async def get_finding_model(self, slug: str) -> FindingModelFull | None:
        """Get finding model data from cache."""
        key = self._make_key("finding_model", slug.lower())
        cached_data = await self.get(key)

        if cached_data:
            try:
                return FindingModelFull.model_validate_json(cached_data)
            except Exception as e:
                logger.warning(f"Failed to deserialize cached finding model {slug}: {e}")
                await self.delete(key)

        return None

    async def set_finding_model(
        self,
        slug: str,
        model_data: FindingModelFull,
        expires_in: timedelta | None = None,
    ) -> bool:
        """Set finding model data in cache."""
        key = self._make_key("finding_model", slug.lower())
        model_json = model_data.model_dump_json()

        # Finding models can be cached longer as they don't change frequently
        if expires_in is None:
            expires_in = timedelta(hours=1)

        return await self.set(key, model_json, expires_in)

    async def invalidate_user_cache(self, user: User) -> None:
        """Invalidate all cached data for a user."""
        tasks = [
            self.delete_user(str(user.id)),
            self.delete_user_by_login(user.login),
        ]

        # Execute all deletions concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to invalidate cache task {i}: {result}")

        logger.info(f"Invalidated cache for user {user.login} (ID: {user.id})")

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        if not self.client:
            return {"status": "disconnected"}

        try:
            info = await self.client.info()
            keyspace_hits = info.get("keyspace_hits", 0)
            keyspace_misses = info.get("keyspace_misses", 0)
            total_keyspace = keyspace_hits + keyspace_misses

            return {
                "status": "connected",
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": keyspace_hits,
                "keyspace_misses": keyspace_misses,
                "hit_rate": (keyspace_hits / max(total_keyspace, 1)) * 100,
            }
        except Exception:
            return {"status": "error"}


# Global cache instance
cache = RedisCache()
