"""Health check endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from .cache import RedisCache
from .config import settings
from .dependencies import get_cache
from .models import HealthCheck

router = APIRouter()


@router.get("/health")
async def health_check() -> HealthCheck:
    """Basic health check endpoint."""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(),
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/health/ready")
async def readiness_check(cache: Annotated[RedisCache, Depends(get_cache)]) -> JSONResponse:
    """Readiness check endpoint with cache status."""
    checks = {
        "database": "healthy",  # We assume MongoDB is healthy if we reach this point
        "cache": "disabled" if not cache.enabled else ("healthy" if await cache.is_healthy() else "unhealthy"),
    }

    overall_status = "ready" if all(status in ["healthy", "disabled"] for status in checks.values()) else "not_ready"

    return JSONResponse(
        content={
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": checks,
        }
    )


@router.get("/health/live")
async def liveness_check() -> JSONResponse:
    """Liveness check endpoint."""
    return JSONResponse(
        content={
            "status": "alive",
            "timestamp": datetime.now().isoformat(),
        }
    )


@router.get("/health/cache")
async def cache_health_check(cache: Annotated[RedisCache, Depends(get_cache)]) -> JSONResponse:
    """Cache-specific health check with statistics."""
    if not cache.enabled:
        return JSONResponse(
            content={
                "status": "disabled",
                "message": "Redis caching is disabled",
                "timestamp": datetime.now().isoformat(),
            }
        )

    cache_stats = await cache.get_stats()
    cache_stats["timestamp"] = datetime.now().isoformat()

    return JSONResponse(content=cache_stats)
