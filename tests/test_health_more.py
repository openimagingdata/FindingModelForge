"""Extra health endpoint coverage tests."""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.main import app


def _with_cache(healthy: bool = True) -> TestClient:
    from app.cache import RedisCache

    cache = MagicMock(spec=RedisCache)
    cache.is_healthy = AsyncMock(return_value=healthy)
    cache.get_stats = AsyncMock(return_value={"status": "connected"})
    app.state.cache = cache
    return TestClient(app)


def test_readiness_healthy_cache() -> None:
    client = _with_cache(healthy=True)
    resp = client.get("/api/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["checks"]["cache"] == "healthy"


def test_readiness_unhealthy_cache() -> None:
    client = _with_cache(healthy=False)
    resp = client.get("/api/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["cache"] == "unhealthy"


def test_cache_health_connected_stats() -> None:
    client = _with_cache(healthy=True)
    resp = client.get("/api/health/cache")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "connected"
