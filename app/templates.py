"""Centralized template configuration with custom filters."""

from datetime import UTC, datetime

import humanize
from fastapi.templating import Jinja2Templates

# Create the templates instance
templates = Jinja2Templates(directory="templates")


def humanize_time(dt: datetime | None) -> str:
    """Convert datetime to human-readable format like '2 hours ago'.

    Args:
        dt: Datetime object to humanize

    Returns:
        Human-readable time string or empty string if dt is None
    """
    if not dt:
        return ""
    # Ensure dt is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return humanize.naturaltime(dt, when=datetime.now(UTC))


# Add custom filters
templates.env.filters["humanize"] = humanize_time
