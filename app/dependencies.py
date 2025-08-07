"""Dependency injection for the application."""

import uuid
from typing import Annotated, Any

from fastapi import Depends, Request
from findingmodel.contributor import Organization
from findingmodel.index import Index
from pydantic import BaseModel

from .cache import RedisCache
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


def get_cache(request: Request) -> RedisCache:
    """Get cache dependency."""
    return request.app.state.cache  # type: ignore[no-any-return]


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


# ===== SESSION MANAGEMENT FOR FINDING MODEL CREATION =====


class FindingModelCreationSession(BaseModel):
    """Session data for finding model creation workflow."""

    session_id: str
    current_step: int = 1
    name: str | None = None
    description: str | None = None
    synonyms: list[str] = []
    similar_models: list[dict[str, Any]] = []
    attributes_markdown: str | None = None
    final_model: dict[str, Any] | None = None
    error_message: str | None = None


class SessionManager:
    """Manages creation sessions using Redis cache."""

    def __init__(self, cache: RedisCache):
        self.cache = cache
        self.session_prefix = "creation_session:"
        self.session_ttl = 3600 * 4  # 4 hours

    async def create_session(self) -> str:
        """Create a new session and return session ID."""
        session_id = str(uuid.uuid4())
        session = FindingModelCreationSession(session_id=session_id)
        await self._save_session(session)
        return session_id

    async def get_session(self, session_id: str) -> FindingModelCreationSession | None:
        """Get session data by ID."""
        cache_key = f"{self.session_prefix}{session_id}"
        session_data = await self.cache.get(cache_key)
        if session_data is None:
            return None

        if isinstance(session_data, str):
            # Parse JSON string if needed
            import json

            try:
                session_dict = json.loads(session_data)
                return FindingModelCreationSession.model_validate(session_dict)
            except (json.JSONDecodeError, ValueError):
                return None
        elif isinstance(session_data, dict):
            # Direct dict
            return FindingModelCreationSession.model_validate(session_data)
        else:
            return None

    async def update_session(self, session: FindingModelCreationSession) -> None:
        """Update session data."""
        await self._save_session(session)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        cache_key = f"{self.session_prefix}{session_id}"
        await self.cache.delete(cache_key)

    async def _save_session(self, session: FindingModelCreationSession) -> None:
        """Save session to cache."""
        from datetime import timedelta

        cache_key = f"{self.session_prefix}{session.session_id}"
        session_data = session.model_dump_json()  # Convert to JSON string for cache
        await self.cache.set(cache_key, session_data, expires_in=timedelta(seconds=self.session_ttl))


def get_session_manager(cache: CacheDep) -> SessionManager:
    """Get SessionManager instance."""
    return SessionManager(cache)


SessionManagerDep = Annotated[SessionManager, Depends(get_session_manager)]


async def get_creation_session(request: Request, session_manager: SessionManagerDep) -> FindingModelCreationSession:
    """Get or create a finding model creation session."""
    # Try to get session ID from request (could be from cookie, header, or query param)
    session_id = None

    # Check query parameter first (for HTMX requests)
    session_id = request.query_params.get("session_id")

    # Check form data for POST requests
    if not session_id and request.method == "POST":
        try:
            form = await request.form()
            session_id = form.get("session_id")
        except Exception:
            pass

    # Check cookies as fallback
    if not session_id:
        session_id = request.cookies.get("creation_session_id")

    # Get existing session or create new one
    if session_id:
        session = await session_manager.get_session(session_id)
        if session is not None:
            return session

    # Create new session if none found or invalid
    new_session_id = await session_manager.create_session()
    session = await session_manager.get_session(new_session_id)
    if session is None:
        # Fallback if cache fails
        session = FindingModelCreationSession(session_id=new_session_id)

    return session


CreationSessionDep = Annotated[FindingModelCreationSession, Depends(get_creation_session)]
