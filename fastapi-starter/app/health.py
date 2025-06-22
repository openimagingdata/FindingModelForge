from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .config import settings
from .models import HealthCheck

router = APIRouter()


@router.get("/health", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    """Basic health check endpoint."""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(),
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/health/ready")
async def readiness_check() -> JSONResponse:
    """Readiness check for Kubernetes deployments."""
    # Add checks for database connectivity, external services, etc.
    return JSONResponse(
        content={
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "checks": {
                "database": "ok",  # Replace with actual database check
                "github_oauth": "ok" if settings.github_client_id else "disabled",
            },
        }
    )


@router.get("/health/live")
async def liveness_check() -> JSONResponse:
    """Liveness check for Kubernetes deployments."""
    return JSONResponse(
        content={"status": "alive", "timestamp": datetime.now().isoformat()}
    )
