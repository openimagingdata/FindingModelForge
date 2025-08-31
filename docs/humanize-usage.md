# Humanize Library Usage Guide

## Installation

```bash
uv add humanize
```

## Common Usage Patterns

### Relative Time Display

```python
import humanize
from datetime import datetime, timedelta

# Convert datetime to relative time
now = datetime.utcnow()
past_time = now - timedelta(hours=2)
print(humanize.naturaltime(past_time))  # "2 hours ago"

# Examples
humanize.naturaltime(now - timedelta(seconds=30))  # "30 seconds ago"
humanize.naturaltime(now - timedelta(minutes=5))   # "5 minutes ago"
humanize.naturaltime(now - timedelta(days=1))      # "a day ago"
humanize.naturaltime(now - timedelta(days=7))      # "a week ago"
```

### In Jinja2 Templates

```python
# In app/main.py or dependencies
import humanize

# Register as Jinja2 filter
templates.env.filters['humanize'] = humanize.naturaltime

# Alternative: Pass as function to template
templates.env.globals['humanize_time'] = humanize.naturaltime
```

```jinja
{# In template #}
{{ comment.created_at | humanize }}
{# or #}
{{ humanize_time(comment.created_at) }}
```

### With Timezone Awareness

```python
import humanize
from datetime import datetime, timezone

# For UTC timestamps
utc_time = datetime.now(timezone.utc)
humanize.naturaltime(utc_time)

# Convert stored UTC to relative
from datetime import UTC
stored_time = datetime.fromisoformat("2024-01-01T12:00:00Z")
humanize.naturaltime(stored_time.replace(tzinfo=UTC))
```

## Integration Pattern for Comments

```python
# In template context
def prepare_comment_for_display(comment: Comment) -> dict:
    """Prepare comment with humanized timestamps."""
    return {
        **comment.model_dump(),
        'time_ago': humanize.naturaltime(comment.created_at)
    }

# In router
context = {
    'comment_thread': {
        **thread.model_dump(),
        'comments': [prepare_comment_for_display(c) for c in thread.comments]
    }
}
```

## Best Practices

1. **Always use UTC**: Store timestamps in UTC, display with humanize
2. **Refresh on load**: Don't cache humanized times, regenerate on each request
3. **Fallback**: Provide ISO timestamp as title attribute for exact time
4. **Localization**: humanize supports i18n if needed later

```jinja
<span title="{{ comment.created_at.isoformat() }}">
    {{ comment.created_at | humanize }}
</span>
```
