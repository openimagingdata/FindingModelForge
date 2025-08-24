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
