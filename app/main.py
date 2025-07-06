from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import logger, settings
from .database import Database
from .health import router as health_router
from .routers import auth, pages, users


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Create and connect to MongoDB
    database = Database()
    try:
        await database.connect()
        logger.info("Connected to MongoDB")

        # Store database in app state for dependency injection
        app.state.database = database

        # Initialize FindingModel Index with the same database connection
        from findingmodel.index import Index

        index = Index(client=database.client, db_name=settings.mongodb_db)
        await index.setup_indexes()
        app.state.finding_index = index
        logger.info("FindingModel Index initialized")

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
    app.include_router(pages.router, tags=["pages"])

    # Import and include finding models router
    from .routers import finding_models

    app.include_router(finding_models.router, prefix="/api/finding-models", tags=["finding-models"])

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
