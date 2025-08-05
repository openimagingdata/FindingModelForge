# ruff: noqa: B008
"""User management API routes."""

from fastapi import APIRouter, HTTPException, status

from app.auth import CurrentUserDep
from app.dependencies import UserRepoDep
from app.models import User, UserUpdate

router = APIRouter()


@router.get("/profile", response_model=User)
async def get_user_profile(current_user: CurrentUserDep) -> User:
    """Get current user's profile."""
    return current_user


@router.patch("/profile", response_model=User)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: CurrentUserDep,
    user_repo: UserRepoDep,
) -> User:
    """Update current user's profile."""
    updated_user = await user_repo.update_user(current_user.id, user_update)
    if updated_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated_user


@router.get("/profile/organizations", response_model=list[str])
async def get_user_organizations(
    current_user: CurrentUserDep,
) -> list[str]:
    """Get organizations that the current user belongs to."""
    return current_user.organizations or []
