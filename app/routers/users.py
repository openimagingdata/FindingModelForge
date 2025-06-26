# ruff: noqa: B008
"""User management API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth import get_current_user
from app.database import UserRepo
from app.dependencies import get_user_repo
from app.models import User, UserUpdate

router = APIRouter()


# Dependency wrapper for get_current_user
async def get_current_user_dependency(request: Request, user_repo: UserRepo = Depends(get_user_repo)) -> User:
    """Dependency wrapper for get_current_user."""
    return await get_current_user(request, user_repo)


@router.get("/profile", response_model=User)
async def get_user_profile(current_user: Annotated[User, Depends(get_current_user_dependency)]) -> User:
    """Get current user's profile."""
    return current_user


@router.patch("/profile", response_model=User)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user_dependency)],
    user_repo: UserRepo = Depends(get_user_repo),
) -> User:
    """Update current user's profile."""
    updated_user = await user_repo.update_user(current_user.id, user_update)
    if updated_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated_user


@router.get("/organizations/{org_code}/members", response_model=list[User])
async def get_organization_members(
    org_code: str,
    current_user: Annotated[User, Depends(get_current_user_dependency)],
    user_repo: UserRepo = Depends(get_user_repo),
) -> list[User]:
    """Get all users in an organization (only if current user is member)."""
    if org_code not in (current_user.organizations or []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this organization")

    return await user_repo.list_users_by_organization(org_code)
