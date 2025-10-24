"""Finding Model service with browsing and slug operations."""

from typing import Any, cast

import httpx
from findingmodel import FindingModelFull
from findingmodel.common import normalize_name
from findingmodel.index import IndexEntry

from app.cache import RedisCache
from app.config import logger, settings
from app.database import CommentRepo, UserRepo
from app.models import Comment, CommentThread, User
from app.services.comment_service import CommentService
from app.utils.slug import slugify

from . import NotFoundError


class FindingModelService:
    """Service for finding model operations including browsing."""

    def __init__(
        self,
        index: Any,
        cache: RedisCache,
        comment_repo: CommentRepo,
        user_repo: UserRepo,
        comment_service: CommentService,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            index: FindingModel DuckDB index for queries
            cache: Redis cache for GitHub JSON caching
            comment_repo: Repository for comment operations
            user_repo: Repository for user operations
            comment_service: Service for comment business logic
        """
        self.index = index
        self.cache = cache
        self.comment_repo = comment_repo
        self.user_repo = user_repo
        self.comment_service = comment_service

    async def list_models(
        self, search: str | None = None, page: int = 1, per_page: int = 20
    ) -> tuple[list[dict[str, Any]], int]:
        """Get paginated list of finding models with optional search.

        Args:
            search: Optional search query (searches slug_name)
            page: Page number (1-based)
            per_page: Items per page

        Returns:
            Tuple of (models_list, total_count)
        """
        # Ensure DuckDB connection is established
        conn = self.index._ensure_connection()
        offset = (page - 1) * per_page

        # Normalize search term the same way Index does (if searching)
        if search and search.strip():
            normalized_search = normalize_name(search.strip())
            # Query with LIKE on slug_name for efficient searching
            models_query = """
                SELECT oifm_id, name, slug_name
                FROM finding_models
                WHERE slug_name LIKE ?
                ORDER BY LOWER(name)
                LIMIT ? OFFSET ?
            """
            count_query = """
                SELECT COUNT(*) as count
                FROM finding_models
                WHERE slug_name LIKE ?
            """
            search_pattern = f"%{normalized_search}%"

            # Get total count
            total_count = conn.execute(count_query, [search_pattern]).fetchone()[0]

            # Get paginated results
            rows = conn.execute(models_query, [search_pattern, per_page, offset]).fetchall()
        else:
            # No search - just paginate all models
            models_query = """
                SELECT oifm_id, name, slug_name
                FROM finding_models
                ORDER BY LOWER(name)
                LIMIT ? OFFSET ?
            """
            count_query = "SELECT COUNT(*) as count FROM finding_models"

            # Get total count
            total_count = conn.execute(count_query).fetchone()[0]

            # Get paginated results
            rows = conn.execute(models_query, [per_page, offset]).fetchall()

        # Convert to list of dicts
        finding_models = [{"id": row[0], "name": row[1], "slug": slugify(row[1])} for row in rows]

        return finding_models, total_count

    async def get_model_by_slug(self, slug: str) -> tuple[FindingModelFull, IndexEntry]:
        """Get finding model by slug.

        Args:
            slug: URL slug for the finding model

        Returns:
            Tuple of (finding_model, index_entry)

        Raises:
            NotFoundError: If model not found
        """
        # Get from Index (handles normalization internally)
        index_entry = await self.index.get(slug)
        if not index_entry:
            raise NotFoundError(f"Finding model '{slug}' not found in index")

        # Check cache for GitHub JSON
        finding_model = await self.cache.get_finding_model(slug)
        if finding_model:
            logger.debug(f"Cache hit for finding model '{slug}'")
            return finding_model, index_entry

        logger.debug(f"Cache miss for finding model '{slug}', fetching from GitHub")

        # Extract filename from index entry
        if not index_entry.filename:
            raise NotFoundError("Finding model entry missing filename")

        # Fetch from GitHub
        github_url = f"{settings.finding_models_github_base_url}{index_entry.filename}"
        logger.debug(f"Fetching finding model from: {github_url}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(github_url)
                response.raise_for_status()
                finding_model = FindingModelFull.model_validate_json(response.text)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise NotFoundError(f"Finding model file not found on GitHub: {github_url}") from e
                raise
            except Exception as e:
                raise NotFoundError(f"Failed to fetch finding model from GitHub: {str(e)}") from e

        # Cache the GitHub JSON
        await self.cache.set_finding_model(slug, finding_model)
        logger.debug(f"Cached finding model '{slug}' for future requests")

        return finding_model, index_entry

    async def search_in_index(self, slug: str) -> IndexEntry | None:
        """Search for a model in the index by slug.

        Args:
            slug: URL slug to search for

        Returns:
            IndexEntry object if found, None otherwise
        """
        try:
            result = await self.index.get(slug)
            return cast(IndexEntry | None, result)
        except Exception:
            return None

    async def get_by_oifm_id(self, oifm_id: str) -> IndexEntry | None:
        """Get finding model by OIFM ID.

        Args:
            oifm_id: The finding model ID

        Returns:
            IndexEntry object if found, None otherwise
        """
        try:
            result = await self.index.get(oifm_id)
            return cast(IndexEntry | None, result)
        except Exception:
            return None

    async def get_comments_for_model(self, oifm_id: str) -> CommentThread | None:
        """Get comment thread for a finding model.

        Args:
            oifm_id: The finding model ID

        Returns:
            CommentThread if exists, None otherwise
        """
        return await self.comment_service.get_thread("finding_model", oifm_id)

    async def add_comment_to_model(
        self, oifm_id: str, user: User, content: str, parent_id: str | None = None
    ) -> Comment:
        """Add comment to finding model with validations.

        Args:
            oifm_id: The finding model ID
            user: Current user object
            content: Comment content (1-2000 chars)
            parent_id: Optional parent comment ID for replies

        Returns:
            The created Comment

        Raises:
            ValueError: If content invalid
            HTTPException: If rate limited, blacklisted, or parent invalid
        """
        # Log user details for debugging
        logger.info(f"Adding comment for user: id={user.id}, login={user.login}")

        model_doc = await self.get_by_oifm_id(oifm_id)
        finding_name = getattr(model_doc, "name", None) if model_doc else None

        return await self.comment_service.add_comment(
            "finding_model",
            oifm_id,
            user,
            content,
            parent_id=parent_id,
            reference_name=finding_name,
        )

    async def report_model_comment(self, oifm_id: str, comment_id: str, user_id: int) -> None:
        """Report a comment on a finding model.

        Args:
            oifm_id: The finding model ID
            comment_id: The comment to report
            user_id: The user reporting

        Raises:
            HTTPException: If comment not found or already reported by user
        """
        await self.comment_service.report_comment("finding_model", oifm_id, comment_id, user_id)
