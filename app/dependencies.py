"""Dependency injection for the application."""

from __future__ import annotations

import contextlib
import json
import uuid
from typing import TYPE_CHECKING, Annotated, Any

if TYPE_CHECKING:
    from .services.comment_service import CommentService
    from .services.creation_service import CreationService
    from .services.draft_service import DraftService
    from .services.finding_model_service import FindingModelService

from fastapi import Depends, Request
from findingmodel.contributor import Organization
from findingmodel.index import Index
from pydantic import BaseModel

from .cache import RedisCache
from .database import CommentRepo, Database, DraftRepo, UserRepo
from .services.comment_service import CommentService


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


def get_draft_repo(database: DatabaseDep) -> DraftRepo:
    """Get DraftRepo instance from the database."""
    if database.draft_repo is None:
        raise RuntimeError("Database not initialized or DraftRepo not available")
    return database.draft_repo


DraftRepoDep = Annotated[DraftRepo, Depends(get_draft_repo)]


def get_comment_repo(database: DatabaseDep) -> CommentRepo:
    """Get CommentRepo instance from the database."""
    if database.comment_repo is None:
        raise RuntimeError("Database not initialized or CommentRepo not available")
    return database.comment_repo


CommentRepoDep = Annotated[CommentRepo, Depends(get_comment_repo)]


def get_comment_service(
    comment_repo: CommentRepoDep,
    user_repo: UserRepoDep,
    draft_repo: DraftRepoDep,
) -> CommentService:
    """Provide CommentService with required repositories."""
    return CommentService(comment_repo=comment_repo, user_repo=user_repo, draft_repo=draft_repo)


CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]


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
    draft_id: str | None = None
    draft_status: str | None = None
    submitted_display_time: str | None = None
    error_message: str | None = None
    success_message: str | None = None


class SessionManager:
    """Manages creation sessions using Redis cache."""

    def __init__(self, cache: RedisCache) -> None:
        self.cache = cache
        self.session_prefix = "creation_session:"
        self.session_ttl = 3600 * 4  # 4 hours

    async def create_session(self) -> str:
        """Create a new session and return session ID."""
        session_id = str(uuid.uuid4())
        session = FindingModelCreationSession(session_id=session_id)
        with contextlib.suppress(Exception):
            await self._save_session(session)
        return session_id

    async def get_session(self, session_id: str) -> FindingModelCreationSession | None:
        """Get session data by ID."""
        try:
            cache_key = f"{self.session_prefix}{session_id}"
            session_data = await self.cache.get(cache_key)
            if session_data is None:
                return None

            # Cache stores JSON strings, so we always expect strings
            try:
                session_dict = json.loads(str(session_data))
                return FindingModelCreationSession.model_validate(session_dict)
            except (json.JSONDecodeError, ValueError, TypeError):
                return None
        except Exception:
            # Handle cache connection/operation errors gracefully
            return None

    async def update_session(self, session: FindingModelCreationSession) -> None:
        """Update session data."""
        with contextlib.suppress(Exception):
            await self._save_session(session)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        try:
            cache_key = f"{self.session_prefix}{session_id}"
            await self.cache.delete(cache_key)
        except Exception:
            # Handle cache errors gracefully - deletion failures are not critical
            pass

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
    from app.config import logger

    # Try to get session ID from request (could be from cookie, header, or query param)
    session_id = None

    # Check query parameter first (for HTMX requests)
    session_id = request.query_params.get("session_id")
    if session_id:
        logger.debug(f"Found session_id in query params: {session_id}")

    # Check form data for POST requests
    if not session_id and request.method == "POST":
        try:
            form = await request.form()
            form_session_id = form.get("session_id")
            if isinstance(form_session_id, str):
                session_id = form_session_id
                logger.debug(f"Found session_id in form data: {session_id}")
        except Exception:
            pass

    # Check cookies as fallback
    if not session_id:
        session_id = request.cookies.get("creation_session_id")
        if session_id:
            logger.debug(f"Found session_id in cookies: {session_id}")
        else:
            logger.debug("No session_id found in request")

    # Get existing session or create new one
    if session_id:
        session = await session_manager.get_session(session_id)
        if session is not None:
            logger.debug(f"Retrieved existing session: {session.session_id}")
            return session
        else:
            logger.debug(f"Session {session_id} not found in cache")

    # Create new session if none found or invalid
    logger.debug("Creating new session")
    new_session_id = await session_manager.create_session()
    session = await session_manager.get_session(new_session_id)
    if session is None:
        # Fallback if cache fails
        session = FindingModelCreationSession(session_id=new_session_id)

    logger.debug(f"Created new session: {new_session_id}")
    return session


CreationSessionDep = Annotated[FindingModelCreationSession, Depends(get_creation_session)]


# ===== SERVICE LAYER DEPENDENCIES =====


def get_finding_model_service(
    index: FindingIndexDep,
    cache: CacheDep,
    comment_repo: CommentRepoDep,
    user_repo: UserRepoDep,
    comment_service: CommentServiceDep,
) -> FindingModelService:
    """Get FindingModelService instance."""
    from .services.finding_model_service import FindingModelService

    return FindingModelService(index, cache, comment_repo, user_repo, comment_service)


FindingModelServiceDep = Annotated["FindingModelService", Depends(get_finding_model_service)]


def get_creation_service(index: FindingIndexDep, database: DatabaseDep) -> CreationService:
    """Get CreationService instance."""
    from .services.creation_service import CreationService

    return CreationService(index, database)


CreationServiceDep = Annotated["CreationService", Depends(get_creation_service)]


def get_draft_service(
    draft_repo: DraftRepoDep,
    user_repo: UserRepoDep,
    database: DatabaseDep,
    comment_service: CommentServiceDep,
) -> DraftService:
    """Get DraftService instance."""
    from .services.draft_service import DraftService

    return DraftService(draft_repo, user_repo, database, comment_service)


DraftServiceDep = Annotated["DraftService", Depends(get_draft_service)]
