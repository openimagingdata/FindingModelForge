# Recent Updates Summary - September 2025

## 🔧 Refactor: Draft Formatting Utilities Extraction (October 3, 2025)

### Overview

Extracted draft formatting logic from `DraftService` into pure utility functions (`app/utils/draft_formatting.py`), reducing service bloat and improving code organization. This follows the existing `app/utils/` pattern and enables upcoming DraftService business logic refactor.

### Changes Made

- **Created `app/utils/draft_formatting.py`** - 259 lines of pure formatting functions with comprehensive type hints
  - `format_draft_for_display()` - Main orchestrator for template display data
  - `extract_attribute_names()` - Parse FindingModelFull JSON for attribute names
  - `humanize_timestamp()` - Convert datetimes to relative time ("2 hours ago")
  - `format_date_short()` - Format datetimes as "Mon DD, YYYY"
- **Reduced DraftService** - From 515 to 356 lines (-31%), removed 3 formatting methods
- **Added comprehensive tests** - 22 new tests in `tests/test_utils_draft_formatting.py` with 100% coverage
- **Zero breaking changes** - All 86 UI tests pass, output format identical to before

### Architecture Pattern

```
Service Layer (Business Logic)
    ↓ delegates formatting to
Utils Layer (Pure Functions) - No I/O, fully testable
```

### Developer Impact

- Import formatting utilities from `app/utils/draft_formatting` for draft display needs
- Services remain focused on business logic and orchestration only
- Formatting functions accept `now` parameter for deterministic testing

### Why This Matters

This refactoring is **Phase 0 prerequisite** for the DraftService cleanup (removing Python-side filtering). Clean separation of concerns enables safe service layer simplification.

---

## 🔧 Refactor: Comment System - Service Layer Centralization (September 30, 2025)

### Overview

Refactored comment system to eliminate code duplication by centralizing all comment business logic into a shared `CommentService`. This establishes proper service layer separation with routers as thin HTTP handlers.

### Changes Made

- **Created CommentService** (`app/services/comment_service.py`) - Single source of truth for comment operations
- **Eliminated duplication** - Removed duplicate rate limiting from routers
- **Service delegation** - DraftService and FindingModelService delegate to CommentService
- **Router cleanup** - Removed manual user index updates and business logic from routers
- **Maintained quality** - All 491 tests passing, 79.50% coverage

### Architecture Pattern

```
Router (HTTP) → Service (Business Logic) → Repository (Data)
                      ↓
              CommentService (shared)
```

### Developer Impact

When adding comments to new features, inject CommentService and delegate comment operations. See `.serena/memories/comment_service_refactor.md` for usage patterns.

---

## 🎉 Major Feature: Comment System Implementation

### What's New

The FindingModelForge now has a complete comment system enabling collaborative feedback on finding models and drafts.
This feature went live in September 2025 with comprehensive backend, frontend, and testing infrastructure.

### Key Features

1. **Commenting on Finding Models and Drafts**
   - Users can comment on public finding models at `/finding-models/{slug}`
   - Comments enabled for submitted drafts (not editable drafts)
   - Single-level threading (comments can have replies, but not nested replies)

2. **Rate Limiting & Moderation**
   - 3 comments per minute per user (429 status enforcement)
   - Report inappropriate content functionality
   - Double-report prevention
   - User comment index for tracking history

3. **UI/UX Features**
   - Real-time character counting (1-2000 chars)
   - HTMX-powered dynamic updates without page reload
   - GitHub avatar integration
   - Chronological ordering (oldest first)
   - Authentication-aware UI (different for logged-in vs anonymous)

### Technical Implementation

#### Architecture Decisions

- **Separate MongoDB collection** (`comment_threads`) for clean separation from content
- **Polymorphic references** using `reference_type` and `reference_id`
- **Atomic operations** for thread creation and comment addition
- **Lazy thread creation** (threads created on first comment)

#### New Components

- `CommentRepo` in `app/database.py` - All comment CRUD operations
- `comment_helpers.py` - Rate limiting and validation logic
- `comment_thread.html` - Reusable UI component
- Comprehensive test coverage: 68 tests (17 UI + 8 rate limiting + 43 repository)

#### Endpoints Added

- `POST /finding-models/{slug}/comments` - Add comment to model
- `POST /finding-models/{slug}/comments/{id}/report` - Report comment
- `POST /drafts/{id}/comments` - Add comment to draft
- `POST /drafts/{id}/comments/{id}/report` - Report draft comment

### What's Still Pending

1. **Blacklist Enforcement** - Helper exists but not yet enforced in routers
2. **Markdown Rendering** - Plain text only currently
3. **Time Humanization** - Raw UTC timestamps shown
4. **CLI Moderation Tool** - Admin interface not yet built

### Migration Notes

No breaking changes. The comment system is additive and doesn't affect existing functionality.

### Testing

All tests passing:

- ✅ 17 UI tests (Playwright)
- ✅ 8 rate limiting tests
- ✅ 43 repository tests
- ✅ Total: 144 tests passing

### Documentation Updates

- **CHANGELOG.md** - Complete feature documentation
- **CLAUDE.md** - Added comment system section
- **app/CLAUDE.md** - Updated with CommentRepo patterns
- **UI_COMPONENT_MACROS.md** - Added comment component documentation
- **Serena Memory** - Stored architectural decisions in `comment_system_architecture`

### How to Use

For developers integrating comments into new pages:

```jinja
{% include 'components/comment_thread.html' with
    thread=comment_thread,
    reference_type="finding_model",
    reference_id=model.oifm_id,
    slug_or_id=model.slug,
    current_user=current_user
%}
```

### Performance Considerations

- Indexed lookups on `(reference_type, reference_id)`
- Separate collection prevents document bloat
- Comments can be cached independently
- Atomic operations prevent race conditions

### Security

- Authentication required for commenting
- Rate limiting prevents spam
- Report system for community moderation
- No edit/delete to maintain accountability

## Lessons Learned

1. **Test Implementation, Not Just Mocks** - Initial tests passed with mocks but rate limiting wasn't actually
   implemented
2. **Use Shared Fixtures** - DRY principle for test data prevents duplication
3. **Document First** - PRD before implementation saves time and prevents scope creep
4. **Atomic Operations Critical** - MongoDB atomic updates prevent race conditions
5. **UI Component Reusability** - Single comment_thread.html serves both models and drafts

## Next Steps

1. Enable blacklist checking (< 1 hour of work)
2. Add markdown rendering (2-4 hours)
3. Implement time humanization (1-2 hours)
4. Build CLI moderation tool (4+ hours)

## Questions or Issues?

- Check the PRD: `tasks/comments-feature-prd.md`
- Review implementation plan: `tasks/comments-implementation-plan.md`
- See architectural decisions: `.serena/memories/comment_system_architecture.md`

---

_Last Updated: September 7, 2025_
