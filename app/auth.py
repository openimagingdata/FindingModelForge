"""Authentication utilities for FindingModelForge with transparent caching support."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer

from app.cache import RedisCache

from .config import logger, settings
from .database import UserRepo
from .dependencies import CacheDep, UserRepoDep
from .models import GitHubTokenResponse, GitHubUser, TokenData, User, UserCreate

# Security setup
security = HTTPBearer()


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.get_secret_key(), algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.get_secret_key(), algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> TokenData | None:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.get_secret_key(), algorithms=[settings.algorithm])

        # Check token type
        if payload.get("type") != token_type:
            return None

        user_id: int | None = payload.get("sub")
        username: str | None = payload.get("username")

        if user_id is None:
            return None

        return TokenData(user_id=int(user_id), username=username)
    except jwt.InvalidTokenError:
        return None


async def get_github_access_token(code: str) -> str:
    """Exchange GitHub authorization code for access token."""
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub OAuth not configured",
        )

    data = {
        "client_id": settings.github_client_id,
        "client_secret": settings.github_client_secret.get_secret_value(),
        "code": code,
    }

    headers = {"Accept": "application/json"}

    async with httpx.AsyncClient() as client:
        response = await client.post(settings.github_token_url, data=data, headers=headers)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange code for token",
        )

    token_data = GitHubTokenResponse(**response.json())
    return token_data.access_token


async def get_github_user(access_token: str) -> GitHubUser:
    """Get GitHub user information using access token."""
    headers = {"Authorization": f"token {access_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(settings.github_user_url, headers=headers)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch user information",
        )

    return GitHubUser(**response.json())


async def get_or_create_user(github_user: GitHubUser, user_repo: UserRepo, cache: RedisCache) -> tuple[User, bool]:
    """Get or create user from GitHub user data with optional caching.

    Returns:
        tuple[User, bool]: (user, is_new_user)
    """
    # Check cache first (transparently handles Redis availability)
    logger.info(f"Checking cache for user {github_user.id}")
    cached_user = await cache.get_user(str(github_user.id))
    if cached_user:
        logger.info(f"Found user {cached_user.login} in cache")
        return cached_user, False

    # Check if user exists in database
    logger.info(f"Checking database for user {github_user.id}")
    existing_user = await user_repo.get_user(github_user.id)

    if existing_user:
        # Cache the user for future requests (transparently handles Redis availability)
        await cache.set_user(str(existing_user.id), existing_user)
        await cache.set_user_by_login(existing_user)
        logger.info(f"Found user {existing_user.login} in database, cached for future requests")
        return existing_user, False

    # Create new user
    logger.info(f"Creating new user for GitHub user {github_user.login}")
    user_create = UserCreate(
        id=github_user.id,
        login=github_user.login,
        name=github_user.name,
        email=github_user.email,
        avatar_url=github_user.avatar_url,
        html_url=github_user.html_url,
    )

    user = await user_repo.create_user(user_create)

    # Cache the new user (transparently handles Redis availability)
    await cache.set_user(str(user.id), user)
    await cache.set_user_by_login(user)
    logger.info(f"Created and cached new user {user.login}")

    return user, True


async def get_current_user(request: Request, user_repo: UserRepoDep, cache: CacheDep) -> User:
    """Get current authenticated user from JWT token with transparent caching."""
    # Try to get token from cookie first
    token = request.cookies.get("access_token")

    # If not in cookie, try Authorization header
    if not token:
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = verify_token(token)
    if token_data is None or token_data.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check cache first (transparently handles no Redis)
    user = await cache.get_user(str(token_data.user_id))
    if user:
        logger.debug(f"Cache hit for user {user.login} (ID: {user.id})")
        return user

    # Fall back to database
    logger.debug(f"Cache miss for user ID {token_data.user_id}, checking database")
    user = await user_repo.get_user(token_data.user_id)

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Cache the user for future requests (transparently handles no Redis)
    await cache.set_user(str(user.id), user)
    await cache.set_user_by_login(user)
    logger.debug(f"Database hit for user {user.login}, cached for future requests")

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_optional_user(request: Request, user_repo: UserRepoDep, cache: CacheDep) -> User | None:
    """Get current user if authenticated with transparent caching, otherwise return None."""
    try:
        return await get_current_user(request, user_repo, cache)
    except HTTPException as e:
        logger.debug(f"No authenticated user found, returning None ({e})")
        return None


OptionalUserDep = Annotated[User | None, Depends(get_optional_user)]
