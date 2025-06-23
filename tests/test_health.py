"""Test health check endpoints."""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Test basic health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
    assert "environment" in data


def test_readiness_check(client: TestClient) -> None:
    """Test readiness check endpoint."""
    response = client.get("/api/health/ready")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ready"
    assert "timestamp" in data
    assert "checks" in data


def test_liveness_check(client: TestClient) -> None:
    """Test liveness check endpoint."""
    response = client.get("/api/health/live")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data
