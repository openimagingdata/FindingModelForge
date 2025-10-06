"""Draft service for draft management and display formatting."""

from typing import TYPE_CHECKING, Any

from app.config import logger
from app.database import DraftRepo, UserRepo
from app.models import Comment, CommentThread, User
from app.services.comment_service import CommentService
from app.utils.draft_formatting import format_draft_for_display

if TYPE_CHECKING:
    from app.database import Database

from . import AuthorizationError, NotFoundError


class DraftService:
    """Service for draft operations and display formatting."""

    def __init__(
        self,
        draft_repo: DraftRepo,
        user_repo: UserRepo,
        database: "Database",
        comment_service: CommentService,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            draft_repo: Repository for draft data access
            user_repo: Repository for user operations
            database: Database instance for Person management
            comment_service: Shared comment orchestration service
        """
        self.draft_repo = draft_repo
        self.user_repo = user_repo
        self.database = database
        self.comment_service = comment_service

    async def get_drafts_for_user(self, user_id: int) -> list[dict[str, Any]]:
        """Get formatted drafts list for a user.

        Args:
            user_id: User ID to get drafts for

        Returns:
            List of formatted draft dictionaries for display
        """
        try:
            drafts = await self.draft_repo.list_for_user(user_id)
            return [format_draft_for_display(d) for d in drafts]
        except Exception as e:
            logger.warning(f"Failed to load drafts for user {user_id}: {e}")
            return []

    async def get_draft_by_id(self, draft_id: str, user_id: int | None = None) -> Any:
        """Get draft by ID with optional ownership check.

        Args:
            draft_id: Draft ID to retrieve
            user_id: Optional user ID for ownership verification

        Returns:
            Draft object

        Raises:
            NotFoundError: If draft not found
            AuthorizationError: If user doesn't own draft (when user_id provided)
        """
        try:
            draft = await self.draft_repo.get_draft(draft_id, user_id)
            if not draft:
                if user_id is not None:
                    # With user_id, not found means either doesn't exist or not owned
                    raise NotFoundError(f"Draft {draft_id} not found")
                else:
                    # Without user_id, not found means doesn't exist
                    raise NotFoundError(f"Draft {draft_id} not found")
            return draft
        except Exception as e:
            if isinstance(e, NotFoundError | AuthorizationError):
                raise
            raise NotFoundError(f"Error retrieving draft {draft_id}: {str(e)}") from e

    async def delete_draft(self, draft_id: str, user_id: int) -> bool:
        """Delete a draft with ownership check.

        Args:
            draft_id: Draft ID to delete
            user_id: User ID requesting deletion

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If draft not found
            AuthorizationError: If user doesn't own draft
        """
        # Verify ownership first
        await self.get_draft_by_id(draft_id, user_id)

        try:
            return await self.draft_repo.delete_draft(draft_id, user_id)
        except Exception as e:
            logger.error(f"Error deleting draft {draft_id}: {e}")
            raise NotFoundError(f"Failed to delete draft {draft_id}") from e

    async def make_public_draft(self, draft_id: str, user_id: int) -> Any:
        """Make a draft public with ownership check.

        Args:
            draft_id: Draft ID to make public
            user_id: User ID requesting the change

        Returns:
            Updated draft object

        Raises:
            NotFoundError: If draft not found
            AuthorizationError: If user doesn't own draft
        """
        # Verify ownership first
        await self.get_draft_by_id(draft_id, user_id)

        try:
            return await self.draft_repo.make_public(draft_id, user_id)
        except Exception as e:
            logger.error(f"Error making draft public {draft_id}: {e}")
            raise NotFoundError(f"Failed to make draft public {draft_id}") from e

    async def submit_draft(self, draft_id: str, user_id: int) -> Any:
        """Submit a draft with ownership check.

        Args:
            draft_id: Draft ID to submit
            user_id: User ID requesting submission

        Returns:
            Updated draft object

        Raises:
            NotFoundError: If draft not found
            AuthorizationError: If user doesn't own draft
        """
        # Verify ownership first
        await self.get_draft_by_id(draft_id, user_id)

        try:
            return await self.draft_repo.submit(draft_id, user_id)
        except Exception as e:
            logger.error(f"Error submitting draft {draft_id}: {e}")
            raise NotFoundError(f"Failed to submit draft {draft_id}") from e

    async def get_public_drafts(self) -> list[dict[str, Any]]:
        """Get all public drafts formatted for display.

        Returns:
            List of formatted public draft dictionaries
        """
        try:
            drafts = await self.draft_repo.get_public_drafts()
            result = []
            for draft in drafts:
                # Get comment count for each draft
                comment_count = 0
                try:
                    draft_id = draft.get("id") if isinstance(draft, dict) else str(draft.id)
                    if draft_id:
                        thread = await self.comment_service.get_thread("draft", draft_id)
                        if thread and thread.comments:
                            comment_count = len(thread.comments)
                except Exception:
                    # If we can't get comment count, default to 0
                    comment_count = 0

                result.append(format_draft_for_display(draft, comment_count=comment_count))
            return result
        except Exception as e:
            logger.warning(f"Failed to load public drafts: {e}")
            return []

    async def get_draft(self, draft_id: str, user_id: int | None = None) -> Any | None:
        """Get draft by ID, optionally checking ownership.

        Args:
            draft_id: Draft ID to retrieve
            user_id: User ID for ownership verification (optional)

        Returns:
            Draft if found (and owned by user if user_id provided), None otherwise
        """
        try:
            return await self.draft_repo.get_draft(draft_id, user_id)
        except Exception as e:
            logger.warning(f"Error getting draft {draft_id}: {e}")
            return None

    async def get_draft_with_author(self, draft_id: str, user_id: int | None = None) -> dict[str, Any] | None:
        """Get draft with author information by ID, optionally checking ownership.

        Args:
            draft_id: Draft ID to retrieve
            user_id: User ID for ownership verification (optional)

        Returns:
            Draft dictionary with author_info if found (and owned by user if user_id provided), None otherwise
        """
        try:
            return await self.draft_repo.get_draft_with_author(draft_id, user_id)
        except Exception as e:
            logger.warning(f"Error getting draft with author {draft_id}: {e}")
            return None

    async def save_draft(
        self,
        user_id: int,
        name: str,
        inputs: Any,
        draft_id: str | None = None,
        generated_json: str | None = None,
        user: User | None = None,
    ) -> Any:
        """Save draft inputs.

        Args:
            user_id: User ID creating/updating the draft
            name: Name of the finding model
            inputs: FindingModelInputs with description, synonyms, attributes
            draft_id: Optional existing draft ID to update
            generated_json: Optional generated JSON for the finding model
            user: Optional User object for Person creation

        Returns:
            Saved draft object
        """
        try:
            # Ensure Person exists for the user if User object is provided
            if user:
                await self.database.ensure_person_for_user(user)

            return await self.draft_repo.save_draft(user_id, name, inputs, draft_id, generated_json, user)
        except Exception as e:
            logger.error(f"Error saving draft for user {user_id}: {e}")
            raise

    async def get_comments_for_draft(self, draft_id: str) -> CommentThread | None:
        """Get comment thread for a draft.

        Args:
            draft_id: The draft ObjectId

        Returns:
            CommentThread if exists, None otherwise
        """
        return await self.comment_service.get_thread("draft", draft_id)

    async def add_comment_to_draft(
        self, draft_id: str, user: User, content: str, parent_id: str | None = None
    ) -> Comment:
        """Add comment to draft with validations.

        IMPORTANT: Only submitted drafts can have comments!

        Args:
            draft_id: The draft ObjectId
            user: Current user object
            content: Comment content (1-2000 chars)
            parent_id: Optional parent comment ID for replies

        Returns:
            The created Comment

        Raises:
            HTTPException: If draft is not submitted, rate limited, etc.
        """
        return await self.comment_service.add_comment(
            "draft",
            draft_id,
            user,
            content,
            parent_id=parent_id,
        )

    async def report_draft_comment(self, draft_id: str, comment_id: str, user_id: int) -> None:
        """Report a comment on a draft.

        Args:
            draft_id: The draft ObjectId
            comment_id: The comment to report
            user_id: The user reporting

        Raises:
            HTTPException: If comment not found or already reported by user
        """
        await self.comment_service.report_comment("draft", draft_id, comment_id, user_id)
