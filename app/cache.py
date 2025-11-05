"""Redis cache implementation for FindingModelForge."""

import asyncio
from datetime import timedelta
from typing import Any

import redis.asyncio as redis_client
from findingmodel.contributor import Organization
from loguru import logger
from pydantic import BaseModel, TypeAdapter

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


OrganizationList = TypeAdapter(list[Organization])


class RedisCache:
    """Redis cache manager for user data and other cacheable items.

    Redis is required for session management - the application will not start without it.
    """

    def __init__(self, config: CacheConfig | None = None) -> None:
        """Initialize Redis cache with configuration."""
        self.config = config or CacheConfig()
        self.client: Any = None  # Redis client instance
        self.connection_pool: Any = None  # Connection pool instance

    async def connect(self) -> None:
        """Connect to Redis server.

        Raises:
            Exception: If connection to Redis fails. This is intentional - Redis is required.
        """
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

        # Test connection - will raise exception if Redis is unavailable
        await self.client.ping()
        logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")

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
        try:
            result = await self.client.delete(key)
            logger.debug(f"Cache delete for key: {key}, result: {result}")
            return bool(result)
        except Exception:
            return True  # Still return True - cache failure shouldn't break the app

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            result = await self.client.exists(key)
            return bool(result)
        except Exception:
            return False

    # User-specific cache methods using Pydantic serialization
    async def set_user(self, user_id: str, user: User, expires: int = 3600) -> bool:
        """Cache a user object with expiration time in seconds."""
        try:
            user_json = user.model_dump_json()
            await self.client.setex(f"user:{user_id}", expires, user_json)
            logger.debug(f"Cached user {user_id} for {expires} seconds")
            return True
        except Exception:
            return True  # Still return True - cache failure shouldn't break the app

    async def get_user(self, user_id: str) -> User | None:
        """Retrieve a user from cache and return as User object."""
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

    async def get_organizations(self) -> list[Organization] | None:
        """Get all organizations from cache."""
        key = self._make_key("organizations", "all")
        cached_data = await self.get(key)

        if cached_data:
            try:
                return OrganizationList.validate_json(cached_data)
            except ValueError:
                logger.warning(f"Cached organizations data is not valid: {cached_data}")
                await self.delete(key)
            except TypeError:
                logger.warning(f"Cached organizations data is not a valid JSON: {cached_data}")
                await self.delete(key)
            except Exception as e:
                logger.warning(f"Failed to deserialize cached organizations: {e}")
                await self.delete(key)

        return None

    async def set_organizations(
        self,
        organizations: list[Organization],
        expires_in: timedelta | None = None,
    ) -> bool:
        """Set all organizations in cache."""
        key = self._make_key("organizations", "all")
        orgs_json = "[" + ",".join(org.model_dump_json(exclude_none=True) for org in organizations) + "]"

        # Organizations can be cached longer as they don't change frequently
        if expires_in is None:
            expires_in = timedelta(seconds=settings.cache_finding_models_expires_in)

        return await self.set(key, orgs_json, expires_in)

    async def invalidate_organizations_cache(self) -> None:
        """Invalidate cached organizations list."""
        key = self._make_key("organizations", "all")
        await self.delete(key)
        logger.info("Invalidated cache for organizations list")
