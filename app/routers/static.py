"""Static asset routes for favicon and app icons."""

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/favicon.ico")
async def favicon() -> FileResponse:
    """Serve favicon."""
    return FileResponse("static/images/favicon.ico")


@router.get("/apple-touch-icon.png")
async def apple_touch_icon() -> FileResponse:
    """Serve Apple touch icon."""
    return FileResponse("static/images/apple-touch-icon.png")


@router.get("/apple-touch-icon-precomposed.png")
async def apple_touch_icon_precomposed() -> FileResponse:
    """Serve Apple touch icon precomposed."""
    return FileResponse("static/images/apple-touch-icon-precomposed.png")


@router.get("/android-chrome-192x192.png")
async def android_chrome_192() -> FileResponse:
    """Serve Android Chrome 192x192 icon."""
    return FileResponse("static/images/android-chrome-192x192.png")


@router.get("/android-chrome-512x512.png")
async def android_chrome_512() -> FileResponse:
    """Serve Android Chrome 512x512 icon."""
    return FileResponse("static/images/android-chrome-512x512.png")


@router.get("/favicon-16x16.png")
async def favicon_16() -> FileResponse:
    """Serve 16x16 favicon."""
    return FileResponse("static/images/favicon-16x16.png")


@router.get("/favicon-32x32.png")
async def favicon_32() -> FileResponse:
    """Serve 32x32 favicon."""
    return FileResponse("static/images/favicon-32x32.png")


@router.get("/site.webmanifest")
async def site_webmanifest() -> FileResponse:
    """Serve site web manifest."""
    return FileResponse("static/images/site.webmanifest", media_type="application/manifest+json")
