"""Draft service for draft management and display formatting."""

from datetime import UTC, datetime
from typing import Any

import humanize
from findingmodel import FindingModelFull

from app.config import logger
from app.database import DraftRepo
from app.utils.slug import slugify

from . import AuthorizationError, NotFoundError


class DraftService:
    """Service for draft operations and display formatting."""

    def __init__(self, draft_repo: DraftRepo) -> None:
        """Initialize with required dependencies.

        Args:
            draft_repo: Repository for draft data access
        """
        self.draft_repo = draft_repo

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
            AuthorizationError: If user doesn't own draft
        """
        try:
            if user_id is not None:
                draft = await self.draft_repo.get_draft(draft_id, user_id)
                if not draft:
                    raise NotFoundError(f"Draft {draft_id} not found")
            else:
                # For admin/system access without ownership check
                # We need a different method - for now just raise error
                raise AuthorizationError("User ID required for draft access")

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

    async def get_draft(self, draft_id: str, user_id: int) -> Any | None:
        """Get draft by ID for a user.

        Args:
            draft_id: Draft ID to retrieve
            user_id: User ID for ownership verification

        Returns:
            Draft if found and owned by user, None otherwise
        """
        try:
            return await self.draft_repo.get_draft(draft_id, user_id)
        except Exception as e:
            logger.warning(f"Error getting draft {draft_id} for user {user_id}: {e}")
            return None

    async def save_draft(self, user_id: int, name: str, inputs: Any, draft_id: str | None = None) -> Any:
        """Save draft inputs.

        Args:
            user_id: User ID creating/updating the draft
            name: Name of the finding model
            inputs: FindingModelInputs with description, synonyms, attributes
            draft_id: Optional existing draft ID to update

        Returns:
            Saved draft object
        """
        try:
            return await self.draft_repo.save_draft(user_id, name, inputs, draft_id)
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
