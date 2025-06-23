"""Test authentication functionality."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.auth import create_access_token, verify_token


def test_create_and_verify_token() -> None:
    """Test JWT token creation and verification."""
    token_data = {"sub": "123", "username": "testuser"}
    token = create_access_token(token_data)

    assert isinstance(token, str)
    assert len(token) > 0

    # Verify the token
    decoded = verify_token(token)
    assert decoded is not None
    assert decoded.user_id == 123
    assert decoded.username == "testuser"


def test_verify_invalid_token() -> None:
    """Test verification of invalid token."""
    invalid_token = "invalid.token.here"
    decoded = verify_token(invalid_token)
    assert decoded is None


def test_auth_login_redirect(client: TestClient) -> None:
    """Test auth login redirects to GitHub."""
    with patch("app.config.settings.github_client_id", "test_client_id"):
        response = client.get("/auth/login", follow_redirects=False)
        assert response.status_code == 307
        assert "github.com" in response.headers["location"]


def test_auth_me_endpoint_requires_auth(client: TestClient) -> None:
    """Test /auth/me endpoint requires authentication."""
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_logout_clears_cookies(client: TestClient) -> None:
    """Test logout clears authentication cookies."""
    response = client.get("/auth/logout", follow_redirects=False)
    assert response.status_code == 303

    # Check redirect location
    assert response.headers["location"] == "/"
