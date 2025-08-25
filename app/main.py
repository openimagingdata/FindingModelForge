from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .cache import CacheConfig, RedisCache
from .config import logger, settings
from .database import Database
from .health import router as health_router
from .routers import (
    auth,
    auth_pages,
    finding_models,
    finding_models_browse,
    home,
    pages,
    profile,
    static,
    test_auth,
    users,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize Redis cache if enabled
    cache = RedisCache()
    if settings.redis_enabled:
        cache_config = CacheConfig(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
        )
        cache = RedisCache(config=cache_config)
        await cache.connect()
        if await cache.is_healthy():
            logger.info("Redis cache initialized and healthy")
        else:
            logger.warning("Redis cache connection failed - continuing without cache")
    else:
        logger.info("Redis caching is disabled")
    app.state.cache = cache

    # Create and connect to MongoDB
    database = Database()
    try:
        await database.connect()
        logger.info("Connected to MongoDB")
        logger.info("FindingModel Index initialized")
        logger.info(f"Loaded {len(database.people)} people and {len(database.organizations)} organizations into memory")

        # Store database in app state for dependency injection
        app.state.database = database

    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

    if not settings.github_client_id:
        logger.warning("GitHub OAuth not configured - authentication will not work")

    yield

    # Shutdown
    logger.info("Shutting down application")
    await database.disconnect()
    logger.info("Disconnected from MongoDB")

    # Disconnect cache
    if cache:
        await cache.disconnect()
        logger.info("Disconnected from Redis cache")
    else:
        logger.info("No Redis cache to disconnect")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Modern FastAPI starter template with GitHub OAuth and JWT authentication",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Static files
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # Include routers
    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(auth.router, prefix="/auth", tags=["authentication"])
    app.include_router(users.router, prefix="/api/users", tags=["users"])
    app.include_router(static.router, tags=["static"])

    # Simple page routers (Task 4)
    app.include_router(home.router, tags=["home"])
    app.include_router(auth_pages.router, tags=["auth-pages"])
    app.include_router(profile.router, tags=["profile"])

    # Finding models browse router (Task 5)
    app.include_router(finding_models_browse.router, tags=["finding-models-browse"])

    # Remaining routers
    app.include_router(pages.router, tags=["pages"])
    app.include_router(finding_models.router, prefix="/api/finding-models", tags=["finding-models"])

    # Test-only authentication routes (development/test only)
    app.include_router(test_auth.router, tags=["test-auth"])

    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
        proxy_headers=True,
        forwarded_allow_ips=settings.forwarded_allow_ips,
    )
