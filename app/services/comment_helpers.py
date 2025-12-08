"""Helper functions for comment system business logic."""

import re
from datetime import UTC, datetime, timedelta
from os import environ

from fastapi import HTTPException

from app.models import CommentThread, User


def check_rate_limit(user: User) -> tuple[bool, str]:
    """Check if user has exceeded rate limit (3 comments per minute).

    This is a pure function that only needs the User object,
    which already contains the comment_index with timestamps.

    Returns:
        Tuple of (allowed, error_message).
        If allowed is True, error_message will be empty string.
        If allowed is False, error_message contains the rate limit message.
    """
    if not user.comment_index:
        return True, ""  # No comments yet, allow

    # Count comments in last 60 seconds
    cutoff = datetime.now(UTC) - timedelta(seconds=60)
    recent_comments = [c for c in user.comment_index if c.created_at > cutoff]

    if len(recent_comments) >= 3:
        return False, "Rate limit exceeded. Maximum 3 comments per minute."
    return True, ""


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


def sanitize_comment_content(content: str) -> str:
    """Sanitize comment content (XSS prevention).

    Note: Length validation is handled by FastAPI Form() constraints.

    Args:
        content: Raw comment content (already validated for length)

    Returns:
        Sanitized content with XSS patterns removed
    """
    content = content.strip()

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
