"""Test-only authentication endpoints for Playwright integration tests."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

from app.auth import create_access_token, create_refresh_token
from app.config import settings
from app.dependencies import UserRepoDep
from app.models import UserCreate

if settings.environment in ("development", "test"):
    router = APIRouter(prefix="/test-auth", tags=["test-auth"])

    @router.get("/login")
    async def test_login(request: Request, response: Response, user_repo: UserRepoDep) -> RedirectResponse:
        """Test-only endpoint to create an authenticated session."""

        # Define test user data
        test_user_id = 999999  # Use a high ID to avoid conflicts

        # Ensure the test user exists in the database
        existing_user = await user_repo.get_user(test_user_id)
        if existing_user is None:
            # Create the user in the database using UserCreate model
            user_create = UserCreate(
                id=test_user_id,
                login="playwright-test-user",
                name="Playwright Test User",
                email="playwright@test.example.com",
                avatar_url="https://github.com/playwright.png",
                html_url=None,
                organizations=["test-org"],
            )
            await user_repo.create_user(user_create)

        # Create JWT tokens
        access_token = create_access_token(data={"sub": str(test_user_id)})
        refresh_token = create_refresh_token(data={"sub": str(test_user_id)})

        # Set HTTP-only cookies
        response = RedirectResponse(url="/create-finding-model", status_code=302)

        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=settings.access_token_expire_minutes * 60,
            httponly=True,
            samesite="lax",
            secure=False,  # False for localhost
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
            httponly=True,
            samesite="lax",
            secure=False,
        )

        return response

    @router.get("/logout")
    async def test_logout() -> RedirectResponse:
        """Test-only endpoint to clear authentication."""
        response = RedirectResponse(url="/", status_code=302)

        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response

else:
    # Create empty router for production
    router = APIRouter()
