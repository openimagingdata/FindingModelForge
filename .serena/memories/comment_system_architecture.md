# Comment System Architecture Decisions

## Implementation Date

September 2025

## Core Design Decisions

### 1. Separate Collection Architecture

**Decision**: Store comments in a separate `comment_threads` collection rather than embedding in finding models or
drafts.

**Rationale**:

- Clean separation of concerns between content and discussions
- Prevents document size bloat as comments accumulate
- Enables independent caching strategies
- Simplifies comment-specific queries and moderation
- Allows for future scaling without affecting core data

**Implementation**:

- One document per finding model or draft (created lazily on first comment)
- Polymorphic references using `reference_type` and `reference_id`
- Compound index on (reference_type, reference_id) for fast lookups

### 2. Single-Level Threading

**Decision**: Allow replies to comments, but not replies to replies.

**Rationale**:

- Keeps discussions focused and readable
- Avoids deep nesting complexity in UI
- Simplifies data model and queries
- Matches successful patterns from GitHub, Slack
- Easier moderation and management

**Implementation**:

- Comments array at thread level
- Each comment has a replies array
- Validation prevents adding replies to replies
- UI shows replies indented under parent

### 3. Rate Limiting Strategy

**Decision**: 3 comments per minute per user, tracked via user document.

**Rationale**:

- Prevents spam without being restrictive
- User document already loaded for auth
- Simple sliding window algorithm
- No additional collections needed
- Clear user feedback with 429 status

**Implementation**:

- `user.comment_index` tracks recent comments
- Check last 60 seconds on each submission
- Populate index after successful comment
- Return helpful error messages

### 4. Authentication Requirement

**Decision**: Only authenticated users can comment.

**Rationale**:

- Accountability for content
- Prevents anonymous spam
- Enables user attribution and avatars
- Supports moderation actions
- Aligns with GitHub OAuth integration

**Implementation**:

- Check `current_user` dependency in endpoints
- Different UI for anonymous vs authenticated
- "Sign in with GitHub" prompts for anonymous

### 5. Draft Status Restriction

**Decision**: Comments only allowed on submitted drafts, not draft status.

**Rationale**:

- Draft status indicates work in progress
- Submitted drafts are ready for feedback
- Prevents confusion about incomplete work
- Maintains clear workflow stages

**Implementation**:

- Check `draft.status != "draft"` before showing comments
- Endpoints validate status before accepting comments
- UI conditionally renders comment section

## Technical Patterns

### MongoDB Atomic Operations

All comment operations use atomic updates:

```python
# Thread creation with upsert
await collection.update_one(
    {"reference_type": ref_type, "reference_id": ref_id},
    {
        "$push": {"comments": comment.model_dump()},
        "$inc": {"comment_count": 1},
        "$set": {"updated_at": datetime.utcnow()}
    },
    upsert=True
)
```

### HTMX Response Pattern

Comments return HTML fragments for seamless updates:

- Success: Complete thread HTML with `hx-swap="outerHTML"`
- Error: Alert HTML with appropriate styling
- Rate limit: 429 status with user-friendly message

### Repository Layer Abstraction

`CommentRepo` encapsulates all operations:

- `get_thread()` - Simple retrieval
- `add_comment()` - Atomic addition with thread creation
- `add_reply()` - Validated reply addition
- `report_comment()` - Double-report prevention

## Testing Strategy

### Comprehensive Coverage

- 43 repository unit tests
- 17 UI Playwright tests
- 8 rate limiting tests
- Mock user ID 999999 for testing

### Test Patterns

- Shared fixtures in conftest.py
- Realistic MongoDB ObjectIds
- Proper async mocking
- HTMX content swap detection

## Future Enhancements (Not Yet Implemented)

### High Priority

1. **Blacklist enforcement** - Helper exists, needs router integration
2. **Markdown rendering** - Sanitized HTML conversion

### Medium Priority

3. **Time humanization** - "2 hours ago" format
4. **Moderation CLI** - Admin tools for reported comments

### Low Priority

5. **Sort order toggle** - Newest first option
6. **Comment permalinks** - Direct links to comments
7. **Pagination** - For threads > 100 comments

## Lessons Learned

1. **Always implement features completely** - Tests with mocks aren't enough
2. **Use existing fixtures** - DRY principle for test data
3. **Verify with real server** - Mock tests can hide missing implementation
4. **Document decisions early** - PRD before implementation saves time
5. **Atomic operations crucial** - Prevent race conditions in concurrent updates
