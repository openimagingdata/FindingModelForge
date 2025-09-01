"""Helper functions for comment system business logic."""

import re
from datetime import UTC, datetime, timedelta
from os import environ
from typing import Any, Literal

from fastapi import HTTPException

from app.database import UserRepo
from app.models import Comment, CommentThread, UserCommentEntry


def check_rate_limit(user_doc: dict[str, Any]) -> bool:
    """Check if user is under rate limit (3 comments per minute).

    Args:
        user_doc: User document from database containing comment_index

    Returns:
        True if user can comment, False if rate limited.
    """
    comment_index = user_doc.get("comment_index", [])
    cutoff_time = datetime.now(UTC) - timedelta(seconds=60)

    # Count recent comments
    recent_count = 0
    for entry in comment_index:
        if not isinstance(entry, dict):
            continue
        entry_created_at = entry.get("created_at")
        if entry_created_at and entry_created_at > cutoff_time:
            recent_count += 1

    return recent_count < 3


async def add_to_comment_index(
    user_repo: UserRepo,
    user_id: int,
    finding_name: str,
    reference_type: Literal["finding_model", "draft"],
    reference_id: str,
    comment_id: str,
) -> None:
    """Add comment entry to user's comment index for rate limiting.

    Args:
        user_repo: User repository instance
        user_id: GitHub user ID
        finding_name: Human-readable name for display
        reference_type: Type of reference ("finding_model" or "draft")
        reference_id: ID of the referenced object
        comment_id: Unique comment ID
    """
    entry = UserCommentEntry(
        reference_type=reference_type,
        reference_id=reference_id,
        finding_name=finding_name,
        comment_id=comment_id,
        created_at=datetime.now(UTC),
    )

    # Add the new entry to comment_index using MongoDB $push operation
    await user_repo.collection.update_one({"id": user_id}, {"$push": {"comment_index": entry.model_dump(mode="json")}})


def get_blacklist_user_ids() -> list[int]:
    """Get list of blacklisted user IDs from environment.

    Reads the COMMENT_BLACKLIST_USER_IDS environment variable as a
    comma-separated list of GitHub user IDs.

    Returns:
        List of blacklisted user IDs as integers. Empty list if not configured.
    """
    blacklist_str = environ.get("COMMENT_BLACKLIST_USER_IDS", "")
    if not blacklist_str:
        return []

    try:
        return [int(uid.strip()) for uid in blacklist_str.split(",") if uid.strip()]
    except ValueError:
        # Log warning about invalid format - for now just return empty list
        return []


def is_reply_allowed(comment: Comment) -> bool:
    """Check if a comment can accept replies.

    For single-level threading, only top-level comments can have replies.
    This is a simplified check - actual enforcement will be at UI level.

    Args:
        comment: Comment to check

    Returns:
        True if the comment can accept replies, False otherwise.
    """
    # Simplified for now - will be enforced at UI level
    # In the future, we'll need to know if this comment is already nested
    # within another comment's replies array
    return True


def validate_comment_content(content: str) -> str:
    """Validate and sanitize comment content.

    Args:
        content: Raw comment content

    Returns:
        Cleaned content

    Raises:
        ValueError: If content is invalid
    """
    if not content or not content.strip():
        raise ValueError("Comment content cannot be empty")

    content = content.strip()

    if len(content) < 1:
        raise ValueError("Comment must be at least 1 character")
    if len(content) > 2000:
        raise ValueError("Comment cannot exceed 2000 characters")

    # Basic XSS prevention - remove script tags and event handlers
    # This is a simple sanitization. In production, use a library like bleach
    content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', "", content, flags=re.IGNORECASE)

    return content


def validate_parent_comment(thread: CommentThread, parent_id: str) -> bool:
    """Verify parent comment exists and is top-level.

    Args:
        thread: The comment thread
        parent_id: ID of the parent comment

    Returns:
        True if valid

    Raises:
        HTTPException: If parent not found or is not top-level
    """
    # Find parent in top-level comments
    parent_found = False
    for comment in thread.comments:
        if comment.id == parent_id:
            parent_found = True
            break

    if not parent_found:
        # Check if parent is a reply (not allowed)
        for comment in thread.comments:
            for reply in comment.replies:
                if reply.id == parent_id:
                    raise HTTPException(400, "Cannot reply to a reply. Only single-level threading is allowed.")
        # Parent not found at all
        raise HTTPException(404, "Parent comment not found")

    return True
