"""Draft service for draft management and display formatting."""

from datetime import UTC, datetime
from typing import Any

import humanize
from fastapi import HTTPException
from findingmodel import FindingModelFull

from app.config import logger
from app.database import CommentRepo, DraftRepo, UserRepo
from app.models import Comment, CommentThread, User
from app.utils.slug import slugify

from . import AuthorizationError, NotFoundError
from .comment_helpers import (
    add_to_comment_index,
    check_rate_limit,
    get_blacklist_user_ids,
    validate_comment_content,
    validate_parent_comment,
)


class DraftService:
    """Service for draft operations and display formatting."""

    def __init__(self, draft_repo: DraftRepo, comment_repo: CommentRepo, user_repo: UserRepo) -> None:
        """Initialize with required dependencies.

        Args:
            draft_repo: Repository for draft data access
            comment_repo: Repository for comment operations
            user_repo: Repository for user operations
        """
        self.draft_repo = draft_repo
        self.comment_repo = comment_repo
        self.user_repo = user_repo

    async def get_drafts_for_user(self, user_id: int) -> list[dict[str, Any]]:
        """Get formatted drafts list for a user.

        Args:
            user_id: User ID to get drafts for

        Returns:
            List of formatted draft dictionaries for display
        """
        user_drafts: list[dict[str, Any]] = []
        try:
            drafts = await self.draft_repo.list_for_user(user_id)
            for d in drafts:
                # Humanized timestamp
                try:
                    updated_dt = d.updated_at
                    if updated_dt.tzinfo is None:
                        updated_dt = updated_dt.replace(tzinfo=UTC)
                    updated_display = humanize.naturaltime(datetime.now(UTC) - updated_dt)
                except Exception:
                    updated_display = d.updated_at.isoformat()

                # Slug for view links
                name_slug = slugify(d.name or "")
                has_generated = bool(getattr(d, "generated_json", None))
                user_drafts.append(
                    {
                        "id": d.id,
                        "name": d.name,
                        "status": d.status,
                        "updated_at": d.updated_at.isoformat(),
                        "updated_display": updated_display,
                        "slug": name_slug,
                        "has_generated": has_generated,
                        "attribute_names": self.extract_attribute_names_from_generated_json(
                            getattr(d, "generated_json", None)
                        ),
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to load drafts for user {user_id}: {e}")
            user_drafts = []

        return user_drafts

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

    async def list_for_user_by_name(self, user_id: int, name: str) -> list[Any]:
        """List drafts for a user filtered by name.

        Args:
            user_id: User ID to filter by
            name: Name to filter by

        Returns:
            List of draft objects matching the name
        """
        try:
            # Get all drafts for user and filter by name in Python
            all_drafts = await self.draft_repo.list_for_user(user_id)
            return [draft for draft in all_drafts if draft.name and draft.name.lower() == name.lower()]
        except Exception as e:
            logger.warning(f"Error listing drafts for user {user_id} with name '{name}': {e}")
            return []

    def extract_attribute_names_from_generated_json(self, generated_json: str | None) -> list[str]:
        """Extract attribute names from a FindingModelFull JSON payload.

        Conservative parser that looks for an 'attributes' list and returns readable names.

        Args:
            generated_json: JSON string containing FindingModelFull data

        Returns:
            List of attribute names
        """
        if not generated_json:
            return []
        try:
            data = FindingModelFull.model_validate_json(generated_json).model_dump(mode="json", exclude_none=True)
            attrs: list[str] = []
            for item in data.get("attributes", []) or []:
                if isinstance(item, dict):
                    # Try common name fields
                    name = item.get("name") or item.get("title") or item.get("id")
                    if isinstance(name, str) and name:
                        attrs.append(name)
            return attrs
        except Exception:
            return []

    async def find_editable_by_name(self, user_id: int, name: str) -> Any | None:
        """Find editable draft by name for a user.

        Args:
            user_id: User ID to search for
            name: Name to search for (case insensitive)

        Returns:
            Editable draft if found, None otherwise
        """
        try:
            # Get all drafts for user and find editable one with matching name
            all_drafts = await self.draft_repo.list_for_user(user_id)
            for draft in all_drafts:
                if draft.name and draft.name.lower() == name.lower() and draft.status == "draft":
                    return draft
            return None
        except Exception as e:
            logger.warning(f"Error finding editable draft by name '{name}' for user {user_id}: {e}")
            return None

    async def find_latest_by_name(self, user_id: int, name: str) -> Any | None:
        """Find latest draft by name for a user.

        Args:
            user_id: User ID to search for
            name: Name to search for (case insensitive)

        Returns:
            Latest draft if found, None otherwise
        """
        try:
            # Get all drafts for user and find latest one with matching name
            all_drafts = await self.draft_repo.list_for_user(user_id)
            matching_drafts = [draft for draft in all_drafts if draft.name and draft.name.lower() == name.lower()]
            if not matching_drafts:
                return None
            # Sort by updated_at descending and return first
            return sorted(matching_drafts, key=lambda x: x.updated_at, reverse=True)[0]
        except Exception as e:
            logger.warning(f"Error finding latest draft by name '{name}' for user {user_id}: {e}")
            return None

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

    async def save_draft(
        self, user_id: int, name: str, inputs: Any, draft_id: str | None = None, generated_json: str | None = None
    ) -> Any:
        """Save draft inputs.

        Args:
            user_id: User ID creating/updating the draft
            name: Name of the finding model
            inputs: FindingModelInputs with description, synonyms, attributes
            draft_id: Optional existing draft ID to update
            generated_json: Optional generated JSON for the finding model

        Returns:
            Saved draft object
        """
        try:
            return await self.draft_repo.save_draft(user_id, name, inputs, draft_id, generated_json)
        except Exception as e:
            logger.error(f"Error saving draft for user {user_id}: {e}")
            raise

    def format_submitted_time(self, updated_at: datetime) -> str:
        """Format submitted time in human-friendly format.

        Args:
            updated_at: Datetime when draft was submitted

        Returns:
            Human-friendly time string
        """
        try:
            submitted_time = updated_at
            # Ensure timezone-aware
            if submitted_time.tzinfo is None:
                submitted_time = submitted_time.replace(tzinfo=UTC)
            return humanize.naturaltime(datetime.now(UTC) - submitted_time)
        except Exception:
            return updated_at.isoformat()

    def format_draft_for_display(self, draft: Any) -> dict[str, Any]:
        """Format a single draft for display purposes.

        Args:
            draft: Raw draft object from repository

        Returns:
            Dictionary formatted for template display
        """
        try:
            updated_dt = draft.updated_at
            if updated_dt.tzinfo is None:
                updated_dt = updated_dt.replace(tzinfo=UTC)
            updated_display = humanize.naturaltime(datetime.now(UTC) - updated_dt)
        except Exception:
            updated_display = draft.updated_at.isoformat()

        name_slug = slugify(draft.name or "")
        has_generated = bool(getattr(draft, "generated_json", None))

        return {
            "id": draft.id,
            "name": draft.name,
            "status": draft.status,
            "updated_at": draft.updated_at.isoformat(),
            "updated_display": updated_display,
            "slug": name_slug,
            "has_generated": has_generated,
            "attribute_names": self.extract_attribute_names_from_generated_json(getattr(draft, "generated_json", None)),
        }

    async def get_comments_for_draft(self, draft_id: str) -> CommentThread | None:
        """Get comment thread for a draft.

        Args:
            draft_id: The draft ObjectId

        Returns:
            CommentThread if exists, None otherwise
        """
        return await self.comment_repo.get_thread("draft", draft_id)

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
        # 1. CRITICAL: Check draft status (no ownership check for comments)
        draft = await self.get_draft(draft_id)  # No user_id - anyone can comment on submitted drafts
        if not draft:
            raise HTTPException(404, "Draft not found")
        if draft.status == "draft":
            raise HTTPException(403, "Cannot comment on draft models")

        # 2. Check if user is blacklisted
        blacklist = get_blacklist_user_ids()
        if user.id in blacklist:
            raise HTTPException(403, "User is not allowed to comment")

        # 3. Validate content
        content = validate_comment_content(content)

        # 4. Check rate limit
        user_doc = await self.user_repo.collection.find_one({"id": user.id})
        if not user_doc or not check_rate_limit(user_doc):
            raise HTTPException(429, "Rate limit exceeded. Please wait before commenting again.")

        # 5. If parent_id provided, validate it's a top-level comment
        if parent_id:
            thread = await self.comment_repo.get_thread("draft", draft_id)
            if thread:
                validate_parent_comment(thread, parent_id)

        # 6. Create comment
        comment = Comment(
            user_id=user.id,
            user_name=user.login,
            user_avatar_url=user.avatar_url,
            content=content,
            created_at=datetime.now(UTC),
        )

        # 7. Add to thread
        if parent_id:
            # thread is guaranteed to exist because validate_parent_comment would have raised if not
            thread = await self.comment_repo.get_thread("draft", draft_id)
            if thread:
                await self.comment_repo.add_reply(thread.id, parent_id, comment)
        else:
            await self.comment_repo.add_comment("draft", draft_id, comment)

        # 8. Track in user's comment index
        finding_name = draft.name if draft else draft_id
        await add_to_comment_index(self.user_repo, user.id, finding_name, "draft", draft_id, comment.id)

        return comment

    async def report_draft_comment(self, draft_id: str, comment_id: str, user_id: int) -> None:
        """Report a comment on a draft.

        Args:
            draft_id: The draft ObjectId
            comment_id: The comment to report
            user_id: The user reporting

        Raises:
            HTTPException: If comment not found or already reported by user
        """
        thread = await self.comment_repo.get_thread("draft", draft_id)
        if not thread:
            raise HTTPException(404, "Comment thread not found")

        # Check if already reported by this user
        for comment in thread.comments:
            if comment.id == comment_id and comment.reported_by == user_id:
                raise HTTPException(400, "You have already reported this comment")
            for reply in comment.replies:
                if reply.id == comment_id and reply.reported_by == user_id:
                    raise HTTPException(400, "You have already reported this comment")

        success = await self.comment_repo.report_comment(thread.id, comment_id, user_id)
        if not success:
            raise HTTPException(404, "Comment not found")
