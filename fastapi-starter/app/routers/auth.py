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
from app.config import settings
from app.models import Token, User

router = APIRouter()


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
async def auth_callback(code: str, response: Response) -> RedirectResponse:
    """Handle GitHub OAuth callback."""
    try:
        # Exchange code for access token
        github_token = await get_github_access_token(code)

        # Get user information from GitHub
        github_user = await get_github_user(github_token)

        # Get or create user in our database
        user = get_or_create_user(github_user)

        # Create JWT tokens
        access_token = create_access_token(
            data={"sub": str(user.id), "username": user.login}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "username": user.login}
        )

        # Set secure HTTP-only cookies
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=settings.access_token_expire_minutes * 60,
            httponly=True,
            secure=settings.environment == "production",
            samesite="lax",
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
            httponly=True,
            secure=settings.environment == "production",
            samesite="lax",
        )

        # Redirect to dashboard
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    except HTTPException:
        # Redirect to login page on error
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    """Logout user by clearing tokens."""
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    return {"message": "Successfully logged out"}


@router.get("/logout")
async def logout_get(response: Response) -> RedirectResponse:
    """Logout user via GET request (for browser navigation)."""
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/refresh", response_model=Token)
async def refresh_token(request: Request) -> Token:
    """Refresh access token using refresh token."""
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found"
        )

    # Verify refresh token
    token_data = verify_token(refresh_token, token_type="refresh")

    if token_data is None or token_data.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Create new access token
    access_token = create_access_token(
        data={"sub": str(token_data.user_id), "username": token_data.username}
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Get current user information."""
    return current_user
