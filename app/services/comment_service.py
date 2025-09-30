"""Shared comment service coordinating validation and persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import HTTPException

from app.database import CommentRepo, DraftRepo, UserRepo
from app.models import Comment, CommentThread, DraftStatus, User, UserCommentEntry
from app.services.comment_helpers import (
    check_rate_limit,
    get_blacklist_user_ids,
    validate_comment_content,
    validate_parent_comment,
)

_ALLOWED_REFERENCE_TYPES = {"draft", "finding_model"}
ReferenceType = Literal["draft", "finding_model"]


class CommentService:
    """Coordinate comment workflows across drafts and finding models."""

    def __init__(
        self,
        comment_repo: CommentRepo,
        user_repo: UserRepo,
        draft_repo: DraftRepo | None = None,
    ) -> None:
        self._comment_repo = comment_repo
        self._user_repo = user_repo
        self._draft_repo = draft_repo

    async def get_thread(self, reference_type: str, reference_id: str) -> CommentThread | None:
        """Fetch comment thread for the reference if it exists."""
        return await self._comment_repo.get_thread(reference_type, reference_id)

    async def add_comment(
        self,
        reference_type: ReferenceType,
        reference_id: str,
        user: User,
        content: str,
        *,
        parent_id: str | None = None,
        reference_name: str | None = None,
    ) -> Comment:
        """Add comment or reply for a reference."""
        if reference_type not in _ALLOWED_REFERENCE_TYPES:
            raise HTTPException(status_code=400, detail="Unsupported reference type for comments")

        # Check blacklist first to short-circuit early.
        if user.id in get_blacklist_user_ids():
            raise HTTPException(status_code=403, detail="User is not allowed to comment")

        allowed, error_msg = check_rate_limit(user)
        if not allowed:
            raise HTTPException(status_code=429, detail=error_msg)

        try:
            cleaned_content = validate_comment_content(content)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        draft_name: str | None = None
        if reference_type == "draft":
            if self._draft_repo is None:
                raise HTTPException(status_code=500, detail="Draft repository not configured")
            draft = await self._draft_repo.get_draft(reference_id)
            if draft is None:
                raise HTTPException(status_code=404, detail="Draft not found")
            if draft.status not in {DraftStatus.PUBLIC, DraftStatus.SUBMITTED}:
                raise HTTPException(status_code=403, detail="Comments are only allowed on public and submitted drafts")
            draft_name = draft.name

        reference_display_name = reference_name or draft_name or reference_id

        thread: CommentThread | None = None
        if parent_id is not None:
            thread = await self._comment_repo.get_thread(reference_type, reference_id)
            if thread is None:
                raise HTTPException(status_code=404, detail="Parent comment not found")
            validate_parent_comment(thread, parent_id)

        comment = Comment(
            user_id=user.id,
            user_name=user.login,
            user_avatar_url=user.avatar_url,
            content=cleaned_content,
            created_at=datetime.now(UTC),
        )

        if parent_id is not None:
            assert thread is not None  # mypy guard; already handled above
            saved = await self._comment_repo.add_reply(thread.id, parent_id, comment)
            if not saved:
                raise HTTPException(status_code=404, detail="Unable to add reply to the specified comment")
        else:
            thread = await self._comment_repo.add_comment(reference_type, reference_id, comment)
            if thread is None:
                raise HTTPException(status_code=500, detail="Failed to persist comment")

        await self._record_comment_index(
            user_id=user.id,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_name=reference_display_name,
            comment_id=comment.id,
        )

        return comment

    async def report_comment(
        self,
        reference_type: str,
        reference_id: str,
        comment_id: str,
        reporting_user_id: int,
    ) -> None:
        if reference_type not in _ALLOWED_REFERENCE_TYPES:
            raise HTTPException(status_code=400, detail="Unsupported reference type for comments")

        thread = await self._comment_repo.get_thread(reference_type, reference_id)
        if thread is None:
            raise HTTPException(status_code=404, detail="Comment thread not found")

        for top_level in thread.comments:
            if top_level.id == comment_id and top_level.reported_by == reporting_user_id:
                raise HTTPException(status_code=400, detail="You have already reported this comment")
            for reply in top_level.replies:
                if reply.id == comment_id and reply.reported_by == reporting_user_id:
                    raise HTTPException(status_code=400, detail="You have already reported this comment")

        success = await self._comment_repo.report_comment(thread.id, comment_id, reporting_user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Comment not found")

    async def _record_comment_index(
        self,
        *,
        user_id: int,
        reference_type: ReferenceType,
        reference_id: str,
        reference_name: str,
        comment_id: str,
    ) -> None:
        """Persist the comment reference for rate limiting and history."""
        entry = UserCommentEntry(
            reference_type=reference_type,
            reference_id=reference_id,
            finding_name=reference_name,
            comment_id=comment_id,
            created_at=datetime.now(UTC),
        )
        await self._user_repo.add_comment_to_index(user_id, entry)
