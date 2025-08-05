"""Dependency injection for the application."""

from typing import Annotated, Any

from fastapi import Depends, Request
from findingmodel.contributor import Organization
from findingmodel.index import Index

from .cache import RedisCache, cache
from .database import Database, UserRepo


def get_database(request: Request) -> Database:
    """Get Database instance from FastAPI app state."""
    return request.app.state.database  # type: ignore[no-any-return]


DatabaseDep = Annotated[Database, Depends(get_database)]


def get_user_repo(database: DatabaseDep) -> UserRepo:
    """Get UserRepo instance from the database."""
    if database.user_repo is None:
        raise RuntimeError("Database not initialized or UserRepo not available")
    return database.user_repo


UserRepoDep = Annotated[UserRepo, Depends(get_user_repo)]


def get_finding_index(database: DatabaseDep) -> Index:
    """Get FindingModel Index instance from the database."""
    if database.finding_index is None:
        raise RuntimeError("Database not initialized or FindingModel Index not available")
    return database.finding_index


FindingIndexDep = Annotated[Index, Depends(get_finding_index)]


def get_cache() -> RedisCache:
    """Get cache dependency."""
    return cache


CacheDep = Annotated[RedisCache, Depends(get_cache)]


async def get_organization_list(index: FindingIndexDep, cache: CacheDep) -> list[Organization]:
    """Return the list of all organizations in the database (cached)."""
    organizations: list[Organization] | None = None
    if (organizations := await cache.get_organizations()) is not None:
        return organizations
    organizations_data: list[dict[str, Any]] = await index.organizations_collection.find().to_list(length=None)
    organizations = []
    for org_data in organizations_data:
        org_data.pop("_id")
        organizations.append(Organization.model_validate(org_data))

    await cache.set_organizations(organizations)
    return organizations


OrganizationListDep = Annotated[list[Organization], Depends(get_organization_list)]
