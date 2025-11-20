from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from findingmodel import settings as fm_settings

from .cache import CacheConfig, RedisCache
from .config import logger, settings
from .database import Database
from .health import router as health_router
from .routers import (
    auth,
    auth_pages,
    creation,
    drafts,
    finding_models_browse,
    home,
    pages,
    profile,
    static,
    test_auth,
    users,
)
from .utils.startup import validate_duckdb_file


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize Redis cache (required for session management)
    cache_config = CacheConfig(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
    )
    cache = RedisCache(config=cache_config)
    await cache.connect()

    if not await cache.is_healthy():
        raise RuntimeError(
            "Redis connection required but unavailable. "
            "Session management will not work. "
            f"Check REDIS_HOST={settings.redis_host} and REDIS_PORT={settings.redis_port} settings."
        )

    logger.info("Redis cache initialized and healthy")
    app.state.cache = cache

    # Validate DuckDB files if paths are configured in findingmodel
    if fm_settings.duckdb_index_path or fm_settings.duckdb_anatomic_path:
        logger.info("Validating FindingModel DuckDB files...")
        validate_duckdb_file(fm_settings.duckdb_index_path, "DUCKDB_INDEX_PATH", "Index DB")
        validate_duckdb_file(fm_settings.duckdb_anatomic_path, "DUCKDB_ANATOMIC_PATH", "Anatomic DB")
        logger.info("DuckDB files validated successfully")
    else:
        logger.warning("DuckDB paths not configured - findingmodel will use default locations")

    # Create and connect to MongoDB
    database = Database()
    try:
        await database.connect()
        logger.info("Connected to MongoDB")
        logger.info("FindingModel Index initialized")
        logger.info("Initialized contributor repositories (people_repo, org_repo)")

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

    # Disconnect Redis cache
    await cache.disconnect()
    logger.info("Disconnected from Redis cache")


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

    # Finding models creation router (Task 6) - URLs simplified as per original plan
    app.include_router(creation.router, prefix="/create", tags=["finding-models-creation"])

    # Finding models drafts router (Task 7) - URLs simplified as per original plan
    app.include_router(drafts.router, prefix="/drafts", tags=["finding-models-drafts"])

    # Remaining routers
    app.include_router(pages.router, tags=["pages"])

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
