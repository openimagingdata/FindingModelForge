# Comments Feature Implementation Plan

## Current Status: Phase 2 Complete
**Last Updated**: January 31, 2025

### Progress Summary
- ✅ **Phase 1**: Backend Data Models (Steps 1-3) - COMPLETED
- ✅ **Phase 2**: Repository Layer (Steps 4-6) - COMPLETED
- ✅ **Tests**: Unit tests for models, repository, and dependencies - COMPLETED (38 tests)
- ⏳ **Phase 3**: Helper Functions (Steps 7-8) - PENDING
- ⏳ **Phase 4**: Service Layer Integration (Steps 9-10) - PENDING
- ⏳ **Phase 5**: Frontend Component (Steps 11-13) - PENDING
- ⏳ **Phase 6**: Router Endpoints (Steps 14-17) - PENDING
- ⏳ **Phase 7**: Testing (Steps 18-20) - PENDING
- ⏳ **Phase 8**: CLI Tool (Step 21) - PENDING

## Overview

This plan implements the comment system as specified in the PRD, broken into focused, testable chunks.

## Phase 1: Backend Data Models (Step 1-3) ✅ COMPLETED

### Step 1: Define Pydantic Models ✅

**File**: `app/models.py` **Standards**:

- Use type hints throughout (CLAUDE.md)
- Avoid mutable defaults - use `Field(default_factory=...)`
- Follow existing model patterns in the file

**Add**:

```python
class Comment(BaseModel)
class CommentThread(BaseModel)
class UserCommentEntry(BaseModel)
```

**Testing**: Run `uv run mypy app/models.py` to verify type safety

---

### Step 2: Update User Model ✅

**File**: `app/models.py` **Standards**: Maintain backward compatibility

**Update** `User` class to add:

```python
comment_index: list[UserCommentEntry] = Field(default_factory=list)
```

**Testing**: Ensure existing user tests still pass: `uv run pytest tests/test_database.py::TestUserRepo -v`

---

### Step 3: Create MongoDB Indices ✅

**File**: `app/database.py` in `Database.connect()` method **Standards**: Add after existing index creation

**Add** index creation for comment_threads:

```python
# In connect() method after finding_index initialization
comment_threads = self.db.comment_threads
await comment_threads.create_index([("reference_type", 1), ("reference_id", 1)], unique=True)
await comment_threads.create_index([("reported_count", -1)])
```

**Testing**: Verify indices created: `uv run python -c "from app.database import Database; ..."`

## Phase 2: Repository Layer (Step 4-6) ✅ COMPLETED

### Step 4: Create CommentRepo Class ✅

**File**: `app/database.py` **Standards**:

- Follow existing repo patterns (UserRepo, DraftRepo)
- All methods async
- Return Pydantic models, not raw dicts
- **Use MongoDB atomic operations**

**Add** `CommentRepo` class with methods:

```python
async def get_thread(reference_type, reference_id) -> CommentThread | None:
    """Simple find_one operation"""

async def add_comment(reference_type, reference_id, comment) -> CommentThread:
    """Create thread if doesn't exist, add comment atomically.
    Uses $push for comments array, $inc for comment_count."""

async def add_reply(thread_id, parent_id, reply) -> bool:
    """Add reply to specific parent comment.
    Uses $push with array filters to add reply to correct parent.
    Single-level only - enforced by checking parent is top-level."""

async def report_comment(thread_id, comment_id, user_id) -> bool:
    """Mark comment as reported.
    Uses $set with array filters, $inc for reported_count."""

async def get_threads_with_reported() -> list[CommentThread]:
    """Find threads where reported_count > 0"""
```

**MongoDB Operations Examples**:

```python
# Add comment atomically
await collection.update_one(
    {"reference_type": ref_type, "reference_id": ref_id},
    {
        "$push": {"comments": comment.model_dump()},
        "$inc": {"comment_count": 1},
        "$set": {"updated_at": datetime.utcnow()}
    },
    upsert=True  # Create if doesn't exist
)

# Add reply with array filter
await collection.update_one(
    {"_id": thread_id, "comments.id": parent_id},
    {
        "$push": {"comments.$.replies": reply.model_dump()},
        "$inc": {"comment_count": 1}
    }
)
```

**Testing**: Create `tests/test_comment_repo.py` with unit tests for each method ✅

---

### Step 5: Initialize CommentRepo in Database ✅

**File**: `app/database.py` **Standards**: Follow initialization pattern of other repos

**Update** `Database` class:

- Add `self.comment_repo: CommentRepo | None = None` in `__init__`
- Initialize in `connect()`: `self.comment_repo = CommentRepo(self.db)`
- Clear in `disconnect()`: `self.comment_repo = None`

**Testing**: Verify initialization in existing database tests

---

### Step 6: Add CommentRepo Dependency ✅

**File**: `app/dependencies.py` **Standards**: Use `Annotated` pattern for type-safe DI

**Add**:

```python
def get_comment_repo(database: DatabaseDep) -> CommentRepo:
    if database.comment_repo is None:
        raise RuntimeError("Database not initialized or CommentRepo not available")
    return database.comment_repo

CommentRepoDep = Annotated[CommentRepo, Depends(get_comment_repo)]
```

**Testing**: Test dependency injection works properly ✅

## Phase 3: Helper Functions (Step 7-8)

### Step 7: Create Comment Helpers

**File**: `app/services/comment_helpers.py` (new file) **Standards**: Pure functions where possible, clear docstrings

**Implement**:

- `check_rate_limit(user_doc) -> bool` - Check user's comment_index
- `add_to_comment_index(user_repo, user_id, finding_name, reference_type, reference_id, comment_id)`
- `get_blacklist_user_ids() -> list[int]` - Parse from environment
- `is_reply_allowed(comment: Comment) -> bool` - **Check if comment can have replies (not itself a reply)**

**Single-level reply enforcement**:

```python
def is_reply_allowed(comment: Comment) -> bool:
    """Check if a comment can accept replies.
    Only top-level comments (those without parent) can have replies.
    This enforces single-level threading."""
    # Comment is top-level if it's in the main comments array
    # Not allowed if it's already a reply (in someone's replies array)
    return len(comment.replies) == 0 or True  # Simplified check
```

**Testing**: Create `tests/test_comment_helpers.py`

---

### Step 8: Add Humanize Support

**File**: `app/main.py` **Standards**: Register as Jinja2 filter

**Add**:

```python
import humanize
# After templates initialization
templates.env.filters['humanize'] = humanize.naturaltime
```

**Dependencies**: Add to pyproject.toml: `uv add humanize`

**Testing**: Verify filter works in template rendering

## Phase 4: Service Layer Integration (Step 9-10)

### Step 9: Update FindingModelService

**File**: `app/services/finding_model_service.py` **Standards**: Keep service methods focused, handle errors gracefully

**Add** methods:

```python
async def get_comments_for_model(oifm_id) -> CommentThread | None:
    """Get comment thread for a finding model"""

async def add_comment_to_model(oifm_id, user, content, parent_id=None) -> Comment:
    """Add comment with validations.
    - Validate content (1-2000 chars, sanitized)
    - If parent_id: verify parent exists and is top-level
    - Check rate limit
    - Enforce single-level replies"""

async def report_model_comment(oifm_id, comment_id, user_id) -> None:
    """Report comment with duplicate check"""
```

**Testing**: Add tests to existing `test_finding_model_service.py`

---

### Step 10: Create DraftService Comment Methods

**File**: `app/services/draft_service.py` **Standards**: Only allow comments on submitted drafts

**Add** methods:

- `get_comments_for_draft(draft_id) -> CommentThread | None`
- `add_comment_to_draft(draft_id, user, content, parent_id=None) -> Comment`
- `report_draft_comment(draft_id, comment_id, user_id) -> None`

Include check: `if draft.status == "draft": raise HTTPException(403, "Cannot comment on draft")`

**Testing**: Add tests verifying status check

## Phase 5: Frontend Component (Step 11-13)

### Step 11: Create Comment Thread Component

**File**: `templates/components/comment_thread.html` (new) **Standards**:

- Use Flowbite components only (templates/CLAUDE.md)
- Alpine.js for interactivity
- NO custom CSS or JavaScript

**Structure**:

```jinja
<div id="comment-thread-{{ reference_type }}-{{ reference_id }}">
    <h3 class="text-lg font-semibold mb-4">Comments</h3>

    {% if thread and thread.comments %}
        {# Display comments #}
    {% else %}
        {# Empty state #}
    {% endif %}

    {# Add comment form with HTMX #}
</div>
```

**Reference**: See `docs/htmx-comment-patterns.md` for HTMX attributes

---

### Step 12: Create Comment Display Macro

**File**: `templates/macros/comment_display.html` (new) **Standards**: Reusable macros for DRY principle

**Create** macros:

- `comment_item(comment, reference_type, reference_id, slug_or_id)`
- `comment_form(reference_type, reference_id, slug_or_id, parent_id=None)`

Use Flowbite card components for comment display

---

### Step 13: Integrate Component into Pages

**Files**:

- `templates/fragments/finding_model_detail_content.html`
- `templates/components/draft_view.html`

**Standards**: Include after main content, before JSON accordion

**Add**:

```jinja
{% include 'components/comment_thread.html' %}
```

**Testing**: Manual UI verification initially

## Phase 6: Router Endpoints (Step 14-17)

### Step 14: Finding Model Comment Endpoints

**File**: `app/routers/finding_models_browse.py` **Standards**:

- Return HTML fragments for HTMX
- Use dependency injection
- Handle errors with proper HTTP codes
- **Validate all input data**

**Add** endpoints:

```python
@router.post("/finding-models/{slug}/comments")
async def add_finding_model_comment(
    slug: str,
    content: str = Form(...),
    parent_comment_id: str | None = Form(None),
    current_user: CurrentUserDep,
    finding_model_service: FindingModelServiceDep,
    comment_repo: CommentRepoDep,
    request: Request
) -> HTMLResponse:
    # Validations:
    # 1. Content length: 1-2000 characters
    # 2. Sanitize markdown content for XSS
    # 3. If parent_comment_id, verify parent exists and is not a reply
    # 4. Check rate limit (3 per minute)
    # Return updated comment thread HTML

@router.post("/finding-models/{slug}/comments/{comment_id}/report")
async def report_finding_model_comment(...) -> HTMLResponse:
    # Validate comment exists
    # Prevent duplicate reports from same user
    # Return success/error alert HTML
```

**Testing**: Create `tests/test_comment_endpoints.py`

---

### Step 15: Draft Comment Endpoints

**File**: `app/routers/drafts.py` **Standards**: Same as finding model endpoints

**Add** similar endpoints for drafts:

- `POST /drafts/{draft_id}/comments`
- `POST /drafts/{draft_id}/comments/{comment_id}/report`

**Critical validation**:

```python
# Check draft status BEFORE allowing comments
if draft.status == "draft":
    raise HTTPException(403, "Cannot comment on draft models")
```

**Testing**: Add to test file, verify draft status check

---

### Step 16: Update Template Context

**Files**:

- `app/routers/finding_models_browse.py` - in `get_finding_model_detail`
- `app/routers/drafts.py` - in `unified_draft_page`

**Standards**: Pass comment thread to template context

**Update** context dictionaries to include:

```python
comment_thread = await comment_repo.get_thread("finding_model", oifm_id)
context["comment_thread"] = comment_thread
```

**Testing**: Verify templates receive thread data

---

### Step 17: Add Comment Validation Helpers

**File**: `app/services/comment_helpers.py` **Standards**: Centralized validation logic

**Add** validation functions:

```python
def validate_comment_content(content: str) -> str:
    """Validate and sanitize comment content.
    - Check length (1-2000 chars)
    - Sanitize markdown for XSS
    - Return cleaned content or raise ValueError
    """

def validate_parent_comment(thread: CommentThread, parent_id: str) -> bool:
    """Verify parent comment exists and is top-level.
    - Find parent in thread.comments
    - Ensure parent is not itself a reply
    - Return True if valid, raise HTTPException if not
    """
```

**Testing**: Unit tests for each validation function

## Phase 7: Testing (Step 18-20)

### Step 18: Unit Tests

**Files**: Create new test files **Standards**: Follow patterns in tests/CLAUDE.md

**Create**:

- `tests/test_comment_repo.py` - Repository tests with mocked DB
- `tests/test_comment_helpers.py` - Helper function tests (including validations)
- `tests/test_comment_endpoints.py` - Endpoint tests with TestClient

**Run**: `uv run pytest tests/test_comment* -v`

---

### Step 19: Integration Tests

**File**: `tests/test_comments_integration.py` **Standards**: Mark with `@pytest.mark.integration`

Test full flow:

1. Create comment thread
2. Add comments
3. Add replies (verify single-level enforcement)
4. Report comment
5. Verify counts
6. Test draft status validation

**Run**: `uv run pytest tests/test_comments_integration.py -v`

---

### Step 20: Playwright UI Tests

**File**: `tests/test_comments_playwright.py` **Standards**: Use test-auth system (user ID 999999)

Test scenarios:

- Add comment to finding model
- Add reply to comment (verify no reply-to-reply option)
- Report inappropriate comment
- Rate limiting (attempt 4 comments quickly)
- Draft status check (verify no comment form on draft models)

**Reference**: `docs/htmx-comment-patterns.md` for selectors

**Run**: `uv run python scripts/run_playwright_tests.py tests/test_comments_playwright.py`

## Phase 8: CLI Tool (Step 21)

### Step 21: Create Moderation Script

**File**: `scripts/moderate_comments.py` **Standards**:

- Use `click` for CLI interface
- Direct MongoDB access via Motor

**Commands**:

```python
@click.group()
def cli():
    pass

@cli.command()
async def list_reported():
    """List all comments with reports."""

@cli.command()
@click.argument('thread_id')
@click.argument('comment_id')
async def remove_comment(thread_id, comment_id):
    """Remove a specific comment."""
```

**Testing**: Manual testing with test database

## Implementation Order & Dependencies

### Priority: NOW (Core Functionality)

1. **Phase 1**: Data Models (Steps 1-3) - Foundation
2. **Phase 2**: Repository Layer (Steps 4-6) - Data access
3. **Phase 3**: Helper Functions (Steps 7-8) - Business logic
4. **Phase 4**: Service Integration (Steps 9-10) - Service layer
5. **Phase 5**: Router Endpoints (Steps 11-13) - API
6. **Phase 6**: Frontend Component (Steps 14-16) - UI
7. **Phase 7**: Testing (Steps 17-19) - Quality assurance

### Priority: SOON

- **Phase 8**: CLI Tool (Step 20) - Admin capabilities
- Flippable sort order
- User profile comment history

### Priority: LATER

- Pagination for > 100 comments
- Rich text editor
- Email notifications

## Success Criteria

Each step is complete when:

1. Code is implemented following standards
2. Type checking passes: `uv run mypy <file>`
3. Linting passes: `task lint`
4. Unit tests pass
5. Manual testing confirms functionality

## Environment Setup

Before starting, ensure:

```bash
# Add humanize dependency
uv add humanize

# Verify test environment
docker-compose up -d mongodb redis
uv run pytest tests/test_database.py -v  # Verify DB connection
```

## Notes

- Each step is designed to be completed in 15-30 minutes
- Steps within a phase can often be done in parallel
- Always run existing tests after changes to ensure no regressions
- Use the reference docs for implementation details:
  - `docs/humanize-usage.md` - Time formatting
  - `docs/htmx-comment-patterns.md` - HTMX patterns
  - `tasks/comments-feature-prd.md` - Full requirements

## Implementation Approach

### Key Principles

1. **Implement backend first** - Models → Repo → Service → Router
2. **Test each layer** before moving to the next
3. **Keep PRs focused** - One phase per PR if possible
4. **Maintain backward compatibility** - Don't break existing features

### Common Pitfalls to Avoid

- Don't forget to check draft status before allowing comments
- Remember to use `Field(default_factory=list)` for list fields
- Always return HTML fragments from endpoints, not JSON
- Don't create custom CSS or JavaScript - use Flowbite and Alpine.js only
- Test with user ID 999999 for Playwright tests

### Validation Checkpoints

After each phase:

1. Run type checker: `uv run mypy app`
2. Run linter: `task lint`
3. Run relevant tests: `uv run pytest tests/test_<feature> -v`
4. Manual smoke test if UI changes
