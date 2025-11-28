"""Finding Model service with browsing and slug operations."""

from typing import Any, cast

from findingmodel import FindingModelFull
from findingmodel.index import IndexEntry

from app.config import logger
from app.database import CommentRepo, UserRepo
from app.models import Comment, CommentThread, User
from app.services.comment_service import CommentService

from . import NotFoundError


class FindingModelService:
    """Service for finding model operations including browsing."""

    def __init__(
        self,
        index: Any,
        comment_repo: CommentRepo,
        user_repo: UserRepo,
        comment_service: CommentService,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            index: FindingModel DuckDB index for queries
            comment_repo: Repository for comment operations
            user_repo: Repository for user operations
            comment_service: Service for comment business logic
        """
        self.index = index
        self.comment_repo = comment_repo
        self.user_repo = user_repo
        self.comment_service = comment_service

    async def list_models(
        self, search: str | None = None, page: int = 1, per_page: int = 20
    ) -> tuple[list[dict[str, Any]], int]:
        """Get paginated list of finding models with optional search.

        Args:
            search: Optional search term for filtering by slug
            page: Page number (1-indexed)
            per_page: Results per page

        Returns:
            Tuple of (list of model dicts, total count)
        """
        offset = (page - 1) * per_page

        if search:
            # Server-side pagination with tuple return (models, total)
            paginated_models, total_count = await self.index.search_by_slug(search, limit=per_page, offset=offset)
        else:
            # List all models with pagination, tuple return (models, total)
            paginated_models, total_count = await self.index.all(offset=offset, limit=per_page)

        # Convert IndexEntry objects to dicts for template rendering
        model_list = []
        for entry in paginated_models:
            # Use slug_name field directly (verified in Phase 1.5)
            model_list.append(
                {
                    "id": entry.oifm_id,
                    "name": entry.name,
                    "slug": entry.slug_name,
                }
            )

        return model_list, total_count

    async def get_model_by_slug(self, slug: str) -> FindingModelFull:
        """Get finding model by slug.

        Args:
            slug: URL slug for the finding model

        Returns:
            Complete FindingModelFull object

        Raises:
            NotFoundError: If model not found
        """
        # Step 1: Get IndexEntry to obtain oifm_id
        index_entry = await self.index.get(slug)
        if not index_entry:
            raise NotFoundError(f"Finding model '{slug}' not found")

        # Step 2: Use oifm_id with get_full() (requires OIFM ID, not slug)
        try:
            finding_model = cast(FindingModelFull, await self.index.get_full(index_entry.oifm_id))
        except KeyError as e:
            # get_full() raises KeyError if model not found (doesn't return None)
            raise NotFoundError(f"Full model data for '{slug}' not found") from e

        logger.debug(f"Retrieved finding model '{slug}' from Index")
        return finding_model

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
            if result:
                logger.debug(f"Found base model by OIFM ID {oifm_id}: slug={result.slug_name}, name={result.name}")
            else:
                logger.warning(f"No result found for OIFM ID: {oifm_id}")
            return cast(IndexEntry | None, result)
        except Exception as e:
            logger.error(f"Error looking up OIFM ID {oifm_id}: {e}")
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
