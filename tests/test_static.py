"""Test static asset routes."""

from fastapi.testclient import TestClient


def test_favicon_ico(client: TestClient) -> None:
    """Test favicon.ico is served correctly."""
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert "image" in response.headers["content-type"]


def test_apple_touch_icon(client: TestClient) -> None:
    """Test Apple touch icon is served correctly."""
    response = client.get("/apple-touch-icon.png")
    assert response.status_code == 200
    assert "image" in response.headers["content-type"]


def test_site_webmanifest(client: TestClient) -> None:
    """Test site.webmanifest is served correctly."""
    response = client.get("/site.webmanifest")
    assert response.status_code == 200
    assert "application/manifest+json" in response.headers["content-type"]


def test_android_chrome_icons(client: TestClient) -> None:
    """Test Android Chrome icons are served correctly."""
    for size in ["192x192", "512x512"]:
        response = client.get(f"/android-chrome-{size}.png")
        assert response.status_code == 200
        assert "image" in response.headers["content-type"]


def test_favicon_png_icons(client: TestClient) -> None:
    """Test PNG favicon icons are served correctly."""
    for size in ["16x16", "32x32"]:
        response = client.get(f"/favicon-{size}.png")
        assert response.status_code == 200
        assert "image" in response.headers["content-type"]
