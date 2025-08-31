# Product Requirements Document: Comments Feature

## Overview

Add a commenting system to FindingModelForge to enable collaborative refinement of finding models through user
discussions and feedback.

## Goals

- Enable users to provide feedback on finding models
- Foster collaborative improvement of model definitions
- Build community knowledge around medical imaging terminology
- Allow domain experts to contribute insights

## Core Requirements

### 1. Scope of Comments

- Comments can be added to:
  - **Submitted drafts** (status = "submitted", "under-review", "added", "declined")
  - **Public finding models** (published models in the browse interface)
- Comments CANNOT be added to:
  - Draft models still being edited (status = "draft")
  - The creation workflow steps

### 2. Comment Threading

- **Single-level replies** only (comment → reply, no reply → reply)
- This keeps discussions focused while avoiding deep nesting complexity
- UI shows replies indented under parent comments

### 3. Comment Features

- **Text content**: 1-2000 characters, markdown support
- **Author attribution**: Display user name and avatar from GitHub profile
- **Timestamps**: Show relative time (e.g., "2 hours ago")
- **Report button**: Flag inappropriate content for moderation

### 4. User Capabilities

- Any authenticated user can comment
- Users can report inappropriate comments
- Users cannot edit or delete their own comments (immutability for accountability)
- Rate limiting: Maximum 3 comments per minute per user

### 5. Display Order

- **Oldest first** (chronological order)
- This allows readers to follow the discussion naturally
- New comments appear at the bottom

## Technical Decisions

### Data Model

#### Comment Structure

```python
class Comment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))  # Unique ID for references
    user_id: int  # GitHub user ID
    user_name: str  # Cached for display
    user_avatar_url: str | None
    content: str  # 1-2000 chars
    created_at: datetime
    replies: list[Comment] = Field(default_factory=list)  # Single-level only
    reported: bool = False
    reported_by: int | None  # User ID who reported
    reported_at: datetime | None
```

#### Comment Thread Structure

```python
class CommentThread(BaseModel):
    id: str  # MongoDB ObjectId
    reference_type: Literal["finding_model", "draft"]
    reference_id: str  # oifm_id for models, draft ObjectId for drafts
    created_at: datetime
    updated_at: datetime
    comment_count: int = 0
    reported_count: int = 0
    comments: list[Comment] = Field(default_factory=list)
```

#### Storage Architecture

- **Dedicated Collection**: `comment_threads`
- **One document per finding model or draft** (created lazily on first comment)
- **Clean separation** between content (models/drafts) and discussions (comments)

#### MongoDB Indices

```python
# Primary lookup index
comment_threads.create_index([
    ("reference_type", 1),
    ("reference_id", 1)
], unique=True)

# Moderation index for finding reported comments
comment_threads.create_index([
    ("reported_count", -1)
])

# Optional: Index for user's comment history (if needed for profiles)
comment_threads.create_index([
    ("comments.user_id", 1)
])
```

### Rate Limiting Implementation

Track recent comments in user document:

```python
class User(BaseModel):
    # ... existing fields ...
    comment_index: list[UserCommentEntry] = Field(default_factory=list)

class UserCommentEntry(BaseModel):
    reference_type: Literal["finding_model", "draft"]
    reference_id: str  # oifm_id for models, draft ObjectId for drafts
    finding_name: str  # Human-readable name for display
    comment_id: str  # Comment ID for direct access
    created_at: datetime
```

Rate limit check: Count entries in last 60 seconds, reject if >= 3

### Moderation Approach

1. **Reporting**: Any user can flag a comment
2. **Blacklist**: Environment variable `COMMENT_BLACKLIST_USER_IDS` with comma-separated GitHub user IDs (admin adjusts
   directly)
3. **CLI Script**: Offline moderation tool for admins
   ```bash
   uv run scripts/moderate_comments.py list-reported
   uv run scripts/moderate_comments.py remove-comment <thread_id> <comment_id>
   ```

## UI/UX Specifications

### Comment Thread Component

- **Single reusable Jinja template**: `templates/components/comment_thread.html`
- **Usage**: Included in both finding model and draft display templates
- **Location**: Below finding model/draft display, above JSON accordion
- **Parameters**: `thread` (CommentThread object), `reference_type`, `reference_id`

### Component Structure

```jinja
{# templates/components/comment_thread.html #}
<div id="comment-thread-{{ reference_type }}-{{ reference_id }}">
  <h3>Comments</h3>
  {% if thread and thread.comments %}
    {# Display existing comments #}
  {% else %}
    {# Empty state: "Feedback on this [finding model|draft]" with Comment button #}
  {% endif %}
  {# Add comment form with HTMX #}
</div>
```

### Comment Display

```
[Avatar] **User Name** • 2 hours ago [Report ⚑]
Comment text here with **markdown** support...
└─ [Reply button]
   └─ [Avatar] **Reply Author** • 1 hour ago [Report ⚑]
      Reply text here...
```

**Time Display**: Use `humanize` library for relative timestamps (e.g., "2 hours ago", "yesterday", "3 days ago")
instead of raw UTC timestamps

### Add Comment Form

- Textarea with character counter (X/2000)
- Submit button (disabled when empty or over limit)
- Rate limit message when triggered

### Template Integration

```jinja
{# In finding_model_detail.html #}
{% include 'components/comment_thread.html' with thread=comment_thread,
           reference_type="finding_model", reference_id=model.oifm_id %}

{# In draft_view.html #}
{% include 'components/comment_thread.html' with thread=comment_thread,
           reference_type="draft", reference_id=draft.id %}
```

### Technologies

- **Frontend**: HTMX for dynamic updates, Alpine.js for form state
- **Components**: Flowbite UI components
- **Time formatting**: `humanize` library for user-friendly timestamps
- **No custom JavaScript**: All interactivity via Alpine.js

## Implementation Architecture

### Backend Structure

```
app/
├── models.py              # Add Comment, CommentThread models
├── database.py            # Add CommentRepo class for comment operations
├── routers/
│   └── finding_models_browse.py  # Add comment endpoints
├── services/
│   ├── finding_model_service.py  # Integrate comment operations
│   └── comment_helpers.py        # Rate limiting, blacklist checks
└── dependencies.py        # Add CommentRepo dependency injection
```

### CommentRepo Operations

```python
class CommentRepo:
    async def get_thread(reference_type: str, reference_id: str) -> CommentThread | None
    async def add_comment(reference_type: str, reference_id: str, comment: Comment) -> CommentThread
        # Creates thread if doesn't exist, adds comment, updates counts atomically
    async def add_reply(thread_id: str, parent_id: str, reply: Comment) -> bool
        # Adds reply to parent comment, updates counts atomically
    async def report_comment(thread_id: str, comment_id: str, user_id: int) -> bool
        # Marks comment as reported, updates reported_count atomically
    async def get_threads_with_reported() -> list[CommentThread]
        # For moderation CLI tool
```

### HTMX Endpoints (Return HTML Fragments)

```
POST /finding-models/{slug}/comments
  - Add comment to finding model
  - Body: {content: str, parent_comment_id: str | None}
  - Returns: Updated comments section HTML (hx-swap="outerHTML")

POST /finding-models/{slug}/comments/{comment_id}/report
  - Report a comment on finding model
  - Returns: Success/error alert HTML (hx-swap="beforebegin")

POST /drafts/{draft_id}/comments
  - Add comment to submitted draft
  - Body: {content: str, parent_comment_id: str | None}
  - Returns: Updated comments section HTML (hx-swap="outerHTML")

POST /drafts/{draft_id}/comments/{comment_id}/report
  - Report a comment on draft
  - Returns: Success/error alert HTML (hx-swap="beforebegin")
```

### Service Layer Integration

The `FindingModelService` will:

1. Fetch the finding model/draft data
2. Query the `comment_threads` collection for associated comments
3. Return both to the template layer
4. Templates access comments as a separate object, not embedded in the model

## Security Considerations

- Rate limiting prevents spam
- Blacklist for bad actors
- Report system for community moderation
- No edit/delete to maintain accountability
- Sanitize markdown to prevent XSS

## Performance Considerations

- Separate collection with indexed lookups (minimal overhead)
- Primary compound index on `(reference_type, reference_id)` for fast queries
- Comments can be cached independently of models
- Additional index on `reported_count` for moderation queries
- Lazy thread creation avoids empty documents

## Feature Prioritization

### Now (Initial Implementation)

- Basic comment creation and display
- Single-level replies
- Rate limiting (3 per minute)
- Report button functionality
- Blacklist via environment variable
- Oldest-first display order
- HTMX dynamic updates

### Soon

- Flippable sort order (oldest/newest first)
- User profile showing comment history
- Moderation CLI tool improvements
- Comment permalinks

### Later

- Pagination for threads > 100 comments
- Rich text editor for markdown
- Comment search/filtering
- Email notifications for replies
- Voting/reactions on comments

## Open Questions Resolved

- ✅ Threading depth: Single-level only
- ✅ Edit/Delete: Not allowed for accountability
- ✅ Sort order: Oldest first (default), flippable to newest first (soon)
- ✅ Rate limiting: 3 per minute via user document
- ✅ Architecture: Separate `comment_threads` collection for clean separation
- ✅ Reference design: Polymorphic with `reference_type` and `reference_id` fields
- ✅ Template reuse: Single `comment_thread.html` component for both models and drafts
- ✅ Moderation script: Run with `uv run` command
- ✅ Time display: Use `humanize` library for relative timestamps
- ✅ Comment IDs: Each comment has unique ID for reply references

## Important Implementation Notes

### Process Lessons Learned

- **Always create PRD first** before implementation
- **Discuss architecture decisions** before coding
- **Clean separation of concerns** - Comments in separate collection, not embedded in content
- **Avoid mutable defaults** in Python - Use `Field(default_factory=list)`

### Technical Decisions Made

- **No CommentedIndex pattern needed** - Comments are separate from finding models
- **CommentRepo handles all DB operations** - Including thread creation on first comment
- **Atomic count updates** - Counts updated within add/report operations, not separately
- **HTMX returns HTML fragments** - Not JSON responses
- **Draft comment restriction** - Only submitted drafts can have comments (status != "draft")
