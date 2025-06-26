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
