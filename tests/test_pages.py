"""Test page routes."""

from fastapi.testclient import TestClient


def test_index_page(client: TestClient) -> None:
    """Test index page loads correctly."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Finding Model Forge" in response.text


def test_login_page(client: TestClient) -> None:
    """Test login page loads correctly."""
    response = client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Sign in to your account" in response.text


def test_profile_page_requires_auth(client: TestClient) -> None:
    """Test profile page requires authentication."""
    response = client.get("/profile")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # Should show login form when not authenticated
    assert "Please log in" in response.text


def test_dashboard_redirect(client: TestClient) -> None:
    """Test dashboard redirects to profile."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["location"] == "/profile"


def test_create_finding_model_requires_auth(client: TestClient) -> None:
    """Test create finding model page requires authentication."""
    response = client.get("/create-finding-model")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # Should show login form when not authenticated
    assert "Please log in to create finding models" in response.text
