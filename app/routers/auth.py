# mypy: disable-error-code="prop-decorator"
# mypy: disable-error-code="arg-type"
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_github_access_token,
    get_github_user,
    get_or_create_user,
    verify_token,
)
from app.config import logger, settings
from app.database import UserRepo
from app.dependencies import get_user_repo
from app.models import Token, User

router = APIRouter()

COOKIE_CONFIG = {
    "path": "/",
    "httponly": True,
    "secure": settings.environment == "production",
    "samesite": "lax",
}


@router.get("/login")
async def login() -> RedirectResponse:
    """Redirect to GitHub OAuth login."""
    if not settings.github_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub OAuth not configured",
        )

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "user:email",
    }

    auth_url = f"{settings.github_authorize_url}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def auth_callback(code: str, user_repo: Annotated[UserRepo, Depends(get_user_repo)]) -> RedirectResponse:
    """Handle GitHub OAuth callback."""
    try:
        # Exchange code for access token
        github_token = await get_github_access_token(code)

        # Get user information from GitHub
        github_user = await get_github_user(github_token)

        logger.info(f"GitHub user info: {github_user}")
        # Get or create user in our database
        user, is_new_user = await get_or_create_user(github_user, user_repo)
        logger.info(f"User info: {user}, is_new_user: {is_new_user}")

        # Create JWT tokens
        access_token = create_access_token(data={"sub": str(user.id), "username": user.login})
        refresh_token = create_refresh_token(data={"sub": str(user.id), "username": user.login})
        logger.info(f"Access token: {access_token}")
        logger.info(f"Refresh token: {refresh_token}")

        # Determine redirect URL based on whether user is new
        redirect_url = "/profile?welcome=true" if is_new_user else "/profile"

        response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
        # Set secure HTTP-only cookies
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=settings.access_token_expire_minutes * 60,
            **COOKIE_CONFIG,
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
            **COOKIE_CONFIG,
        )

        # Redirect to dashboard
        return response

    except HTTPException:
        # Redirect to login page on error
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    """Logout user by clearing tokens."""
    response.delete_cookie(key="access_token", **COOKIE_CONFIG)
    response.delete_cookie(key="refresh_token", **COOKIE_CONFIG)
    return {"message": "Successfully logged out"}


@router.get("/logout")
async def logout_get() -> RedirectResponse:
    """Logout user via GET request (for browser navigation)."""
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token", **COOKIE_CONFIG)
    response.delete_cookie(key="refresh_token", **COOKIE_CONFIG)
    return response


@router.post("/refresh", response_model=Token)
async def refresh_token(request: Request) -> Token:
    """Refresh access token using refresh token."""
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found")

    # Verify refresh token
    token_data = verify_token(refresh_token, token_type="refresh")

    if token_data is None or token_data.user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Create new access token
    access_token = create_access_token(data={"sub": str(token_data.user_id), "username": token_data.username})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


# Dependency wrapper for get_current_user
async def get_current_user_dependency(request: Request, user_repo: Annotated[UserRepo, Depends(get_user_repo)]) -> User:
    """Dependency wrapper for get_current_user."""
    return await get_current_user(request, user_repo)


@router.get("/me", response_model=User)
async def get_me(current_user: Annotated[User, Depends(get_current_user_dependency)]) -> User:
    """Get current user information."""
    return current_user
