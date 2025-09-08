# Technical Debt Tracker

This document tracks deferred features, technical debt, and improvement opportunities that should be addressed in future
development cycles.

## Deferred Features

### 1. Humanize Filter for Date Display

**Priority**: Medium
**Effort**: Small (2-3 hours)
**Date Added**: February 1, 2025

**Issue**: Frontend templates use `| humanize` filter that doesn't exist in our codebase yet. This filter should convert
timestamps to human-readable format like "2 hours ago" or "3 days ago".

**Current State**:

- Templates reference the filter but it will cause errors when rendered
- Filter is used in `comment_thread.html` and `comment_display.html`

**Proposed Solution**:

1. Install `humanize` package: `uv add humanize`
2. Create the filter in `app/templates.py`
3. Apply consistently across all date displays in the application
4. Consider using for draft timestamps, finding model dates, etc.

**Files to Update**:

- `app/templates.py` - Add filter implementation
- All templates showing dates - Apply filter consistently

---

### 2. Comment Report Functionality

**Priority**: Low
**Effort**: Medium (4-6 hours)
**Date Added**: February 1, 2025

**Issue**: Report functionality for inappropriate comments was deferred to focus on core comment functionality.

**Current State**:

- Frontend has placeholder onclick handlers with TODO comments
- Backend has `report_comment()` method in repository but no service/router integration
- No admin interface for reviewing reported comments

**Proposed Solution** (Phase 8):

1. Add report endpoints to routers
2. Update templates with working report buttons
3. Create admin interface for reviewing reports
4. Add tests for reporting flow

---

## Code Quality Issues

### 3. Duplicate Comment Implementation in Frontend

**Priority**: High
**Effort**: Small (1-2 hours)
**Date Added**: February 1, 2025

**Issue**: Two different comment display implementations exist:

- `comment_thread.html` - Self-contained component with inline forms
- `comment_display.html` - Macro-based reusable approach

**Current State**: Both files exist with different approaches and endpoint patterns

**Proposed Solution**:

1. Keep simpler `comment_thread.html` approach
2. Remove `comment_display.html` macros
3. Standardize on consistent HTMX endpoints

---

### 4. Duplicate Comment Logic in Services

**Priority**: Medium
**Effort**: Medium (3-4 hours)
**Date Added**: February 1, 2025

**Issue**: `FindingModelService` and `DraftService` have duplicated comment validation and creation logic.

**Current State**: Both services implement similar methods with repeated code for:

- Blacklist checking
- Content validation
- Rate limit checking
- Parent comment validation
- Comment creation and thread addition
- User comment index tracking

**Proposed Solution** (Step 18 in Phase 7):

1. Create a `BaseCommentService` or `CommentMixin`
2. Extract shared logic to common methods
3. Have both services inherit/use the shared implementation
4. Add tests to ensure refactoring doesn't break functionality

---

## Architecture Improvements

### 5. Repository Pattern Violation

**Priority**: Low
**Effort**: Small (1 hour)
**Date Added**: January 31, 2025

**Issue**: `add_to_comment_index()` directly accesses `user_repo.collection.update_one()` instead of using a repository
method.

**Current State**: Works but bypasses repository abstraction layer

**Proposed Solution**:

1. Add `add_comment_index_entry()` method to UserRepo
2. Update `add_to_comment_index()` to use the new method

---

## Future Enhancements

### 6. Comment System Features

**Priority**: Low
**Effort**: Large

**Potential Features**:

- Pagination for threads with > 100 comments
- Rich text editor for markdown formatting
- Email notifications for replies
- Flippable sort order (newest/oldest first)
- User profile comment history page
- Comment editing (with edit history)
- Voting/reactions on comments

---

## Notes

- Items marked **High Priority** should be addressed before the next major feature
- **Medium Priority** items should be scheduled in the next sprint/cycle
- **Low Priority** items can be addressed opportunistically or bundled with related work
- Effort estimates are rough and may vary based on testing requirements

## Adding New Technical Debt

When deferring work or identifying technical debt:

1. Add an entry to this file with clear description
2. Include priority, effort estimate, and date added
3. Document current state and proposed solution
4. Reference this file in relevant code comments when appropriate
