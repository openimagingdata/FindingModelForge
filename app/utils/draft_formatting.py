"""Draft formatting utilities for display.

Pure functions for formatting draft data for template display.
No I/O operations, no database calls - just data transformation.

Used by DraftService and routers for consistent draft display formatting.

Example:
    >>> draft_dict = {"id": "123", "name": "Test Draft", "updated_at": datetime.now(UTC), ...}
    >>> formatted = format_draft_for_display(draft_dict)
    >>> formatted["updated_display"]
    '2 hours ago'
    >>> formatted["slug"]
    'test-draft'
"""

from datetime import UTC, datetime
from typing import Any

import humanize
from findingmodel import FindingModelFull

from app.utils.slug import slugify


def format_draft_for_display(
    draft: dict[str, Any] | Any,
    *,
    comment_count: int = 0,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Format a draft for template display.

    Pure function - no I/O, no database calls. Accepts both dict (from cache/aggregation)
    and Pydantic model instances.

    Args:
        draft: Draft data from repository or cache (dict or model)
        comment_count: Number of comments on this draft (default: 0)
        now: Current time for relative timestamps (default: datetime.now(UTC))

    Returns:
        Dictionary with all display fields including:
        - updated_display: Human-friendly relative time
        - created_at_display: Short date format
        - slug: URL-friendly name
        - attribute_names: List of attribute names from generated JSON
        - author_name: Author's display name
        - comment_count: Number of comments

    Examples:
        >>> from datetime import datetime, UTC
        >>> draft = {
        ...     "id": "123",
        ...     "name": "Test Draft",
        ...     "status": "draft",
        ...     "updated_at": datetime.now(UTC),
        ...     "created_at": datetime.now(UTC),
        ...     "generated_json": None
        ... }
        >>> result = format_draft_for_display(draft)
        >>> result["slug"]
        'test-draft'
        >>> "updated_display" in result
        True
    """
    if now is None:
        now = datetime.now(UTC)

    # Handle both dict and model objects
    if isinstance(draft, dict):
        draft_dict = draft
        updated_at = draft_dict.get("updated_at")
        created_at = draft_dict.get("created_at")
        draft_id = draft_dict.get("id")
        draft_name = draft_dict.get("name")
        draft_status = draft_dict.get("status")
        generated_json = draft_dict.get("generated_json")
        author_info = draft_dict.get("author_info")
    else:
        # Pydantic model or similar object
        updated_at = draft.updated_at
        created_at = getattr(draft, "created_at", None)
        draft_id = draft.id
        draft_name = draft.name
        draft_status = draft.status
        generated_json = getattr(draft, "generated_json", None)
        author_info = getattr(draft, "author_info", None)

    # Format updated timestamp
    updated_display = humanize_timestamp(updated_at, now=now)

    # Format created timestamp
    created_at_display = format_date_short(created_at)

    # Generate slug
    name_slug = slugify(draft_name or "")

    # Check if generated JSON exists
    has_generated = bool(generated_json)

    # Build result dict
    result = {
        "id": draft_id,
        "name": draft_name,
        "status": draft_status,
        "updated_at": updated_at.isoformat() if updated_at and hasattr(updated_at, "isoformat") else updated_at,
        "updated_display": updated_display,
        "created_at": created_at.isoformat() if created_at and hasattr(created_at, "isoformat") else created_at,
        "created_at_display": created_at_display,
        "slug": name_slug,
        "has_generated": has_generated,
        "comment_count": comment_count,
        "attribute_names": extract_attribute_names(generated_json),
    }

    # Add author information if available
    if author_info:
        result["author_name"] = author_info.get("name", author_info.get("github_username", "Unknown"))
        result["github_username"] = author_info.get("github_username")
    else:
        result["author_name"] = "Unknown"
        result["github_username"] = None

    return result


def extract_attribute_names(generated_json: str | None) -> list[str]:
    """Extract attribute names from FindingModelFull JSON.

    Conservative parser that returns empty list on any error.
    Looks for 'attributes' list and extracts readable names.

    Args:
        generated_json: JSON string containing FindingModelFull data

    Returns:
        List of attribute names, or empty list if parsing fails

    Examples:
        >>> json_str = '{"attributes": [{"name": "Size"}, {"name": "Location"}]}'
        >>> extract_attribute_names(json_str)
        ['Size', 'Location']
        >>> extract_attribute_names(None)
        []
        >>> extract_attribute_names("invalid json")
        []
    """
    if not generated_json:
        return []

    try:
        # Parse and validate as FindingModelFull
        data = FindingModelFull.model_validate_json(generated_json).model_dump(mode="json", exclude_none=True)

        attrs: list[str] = []
        for item in data.get("attributes", []) or []:
            if isinstance(item, dict):
                # Try common name fields in order of preference
                name = item.get("name") or item.get("title") or item.get("id")
                if isinstance(name, str) and name:
                    attrs.append(name)

        return attrs
    except Exception:
        # Conservative: return empty list on any parsing error
        return []


def humanize_timestamp(
    dt: datetime | str | None,
    *,
    now: datetime | None = None,
) -> str:
    """Convert datetime to human-friendly relative time.

    Handles timezone-naive datetimes (assumes UTC), ISO strings, and None values.
    Returns "Unknown" for invalid inputs.

    Args:
        dt: Datetime to format (datetime object, ISO string, or None)
        now: Current time for relative calculation (default: datetime.now(UTC))

    Returns:
        Human-friendly relative time string (e.g., "2 hours ago") or "Unknown"

    Examples:
        >>> from datetime import datetime, UTC, timedelta
        >>> now = datetime(2024, 10, 3, 12, 0, 0, tzinfo=UTC)
        >>> past = datetime(2024, 10, 3, 10, 0, 0, tzinfo=UTC)
        >>> humanize_timestamp(past, now=now)
        '2 hours ago'
        >>> humanize_timestamp(None)
        'Unknown'
        >>> humanize_timestamp("invalid")
        'Unknown'
    """
    if now is None:
        now = datetime.now(UTC)

    if dt is None:
        return "Unknown"

    try:
        # Handle string inputs (e.g., from cache)
        if isinstance(dt, str):
            # Parse ISO format, handle 'Z' timezone indicator
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))

        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)

        return humanize.naturaltime(now - dt)
    except Exception:
        # Fallback to ISO format if datetime-like, otherwise "Unknown"
        if isinstance(dt, datetime):
            return dt.isoformat()
        return "Unknown"


def format_date_short(dt: datetime | str | None) -> str:
    """Format datetime as short date string 'Mon DD, YYYY'.

    Handles timezone-naive datetimes, ISO strings, and None values.
    Returns "N/A" for invalid inputs.

    Args:
        dt: Datetime to format (datetime object, ISO string, or None)

    Returns:
        Short date string (e.g., "Oct 03, 2024") or "N/A"

    Examples:
        >>> from datetime import datetime, UTC
        >>> dt = datetime(2024, 10, 3, 12, 0, 0, tzinfo=UTC)
        >>> format_date_short(dt)
        'Oct 03, 2024'
        >>> format_date_short(None)
        'N/A'
        >>> format_date_short("2024-10-03T12:00:00Z")
        'Oct 03, 2024'
    """
    if dt is None:
        return "N/A"

    try:
        # Handle string inputs (e.g., from cache)
        if isinstance(dt, str):
            # Parse ISO format, handle 'Z' timezone indicator
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))

        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)

        return dt.strftime("%b %d, %Y")
    except Exception:
        return "N/A"
