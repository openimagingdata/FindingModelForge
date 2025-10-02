# Draft Formatting Utilities Plan

**Last Updated**: October 2, 2025
**Status**: ✅ Ready to implement
**Prerequisite for**: DraftService Refactor (see `draft-service-refactor-plan.md`)

## Context & Analysis (October 2, 2025)

After examining the actual code, the "presenter layer" concept is **over-engineered**. The real issue is simpler:

**Current State:**
- `DraftService` has 515 lines and mixes business logic with formatting
- Formatting functions like `format_draft_for_display()` (82 lines) and `extract_attribute_names_from_generated_json()` (25 lines) are **pure functions** with no I/O
- These functions only depend on `humanize` and `slugify` - they don't need services, DI, or repositories
- The project already has `app/utils/slug.py` for pure utility functions

**The Real Problem:**
1. Service bloat - formatting logic doesn't belong in orchestration layer
2. Code duplication - `get_drafts_for_user()` reimplements parts of `format_draft_for_display()`
3. No clear home for pure formatting functions

**Better Solution:**
Follow the existing `app/utils/` pattern instead of inventing a new "presenter layer" architecture.

## Revised Objectives

- Extract pure formatting functions from `DraftService` into `app/utils/draft_formatting.py`
- Keep functions simple: input data + optional context → formatted output
- No new architectural patterns - just move code to where it belongs
- Make functions testable with deterministic timestamp injection
- Services call utils for formatting, stay focused on business logic
- **Enable DraftService refactor**: Once formatting is extracted, service can be cleaned up to focus on business logic only (removes Python-side filtering, keeps orchestration)

## Constraints & Principles

- **Follow existing patterns**: Use `app/utils/` like `slug.py`, not new packages
- **Pure functions only**: No I/O, no async, no database calls
- **Minimal dependencies**: stdlib + `humanize` + existing utils
- **Testable design**: Accept `now` parameter for deterministic time formatting
- **No breaking changes**: Maintain exact same output format for backward compatibility

## Deliverables

1. **New module**: `app/utils/draft_formatting.py` with pure formatting functions
2. **Slim services**: `DraftService` methods delegate to utils instead of implementing formatting
3. **Comprehensive tests**: `tests/test_utils/test_draft_formatting.py` covering all edge cases
4. **Clean separation**: Business logic in services, formatting in utils, no mixing

## Implementation Plan

### Phase 1 – Create Formatting Utilities
**Status**: Not started

- [ ] Create `app/utils/draft_formatting.py` with functions:
  ```python
  def format_draft_for_display(
      draft: dict[str, Any] | FindingModelDraft,
      *,
      comment_count: int = 0,
      now: datetime | None = None
  ) -> dict[str, Any]:
      """Format a draft for template display.

      Pure function - no I/O, no database calls.
      Accepts both dict (from cache/aggregation) and Pydantic model.

      Args:
          draft: Draft data from repo or cache
          comment_count: Number of comments (default 0)
          now: Current time for relative timestamps (default: datetime.now(UTC))

      Returns:
          Dict with all display fields (updated_display, slug, attribute_names, etc.)
      """
      pass

  def extract_attribute_names(generated_json: str | None) -> list[str]:
      """Extract attribute names from FindingModelFull JSON.

      Returns empty list on any error (conservative parsing).
      """
      pass

  def humanize_timestamp(
      dt: datetime | str | None,
      *,
      now: datetime | None = None
  ) -> str:
      """Convert datetime to human-friendly relative time.

      Handles timezone-naive datetimes, ISO strings, and None.
      Returns "Unknown" for invalid inputs.
      """
      pass

  def format_date_short(dt: datetime | str | None) -> str:
      """Format datetime as 'Mon DD, YYYY'.

      Returns "N/A" for invalid inputs.
      """
      pass
  ```

- [ ] Copy implementation from `DraftService` methods:
  - Port `format_draft_for_display()` body → utils version
  - Port `extract_attribute_names_from_generated_json()` → `extract_attribute_names()`
  - Port timestamp logic → `humanize_timestamp()` and `format_date_short()`

- [ ] Add `now` parameter to all time-dependent functions:
  ```python
  # Enables deterministic testing
  if now is None:
      now = datetime.now(UTC)
  updated_display = humanize.naturaltime(now - updated_dt)
  ```

  **Note**: Timestamp helpers (`humanize_timestamp`, `format_date_short`) are separated for:
  - Independent testing of edge cases (timezone-naive, strings, None)
  - Reusability across other entities (finding models, comments)
  - Single-responsibility principle (each function does one thing well)

- [ ] Handle both dict and model inputs gracefully (copy existing pattern)

### Phase 2 – Create Comprehensive Tests
**Status**: Not started
**Depends on**: Phase 1 complete

- [ ] Create `tests/test_utils/` directory (if doesn't exist)
- [ ] Create `tests/test_utils/test_draft_formatting.py` with test cases:

  **Test `format_draft_for_display()`:**
  - [ ] Dict input with all fields
  - [ ] Pydantic model input with all fields
  - [ ] Missing optional fields (created_at, generated_json, author_info)
  - [ ] Timezone-naive vs timezone-aware datetimes
  - [ ] String datetime from cache (ISO format with 'Z')
  - [ ] Comment count integration
  - [ ] Deterministic time formatting with `now` parameter

  **Test `extract_attribute_names()`:**
  - [ ] Valid FindingModelFull JSON with attributes
  - [ ] Empty JSON / missing attributes key
  - [ ] Invalid JSON (returns empty list)
  - [ ] Attributes with missing name fields (fallback to title/id)
  - [ ] None input (returns empty list)

  **Test `humanize_timestamp()`:**
  - [ ] Timezone-aware datetime
  - [ ] Timezone-naive datetime (adds UTC)
  - [ ] ISO string with 'Z'
  - [ ] ISO string without timezone
  - [ ] None input (returns "Unknown")
  - [ ] Invalid input (returns "Unknown")
  - [ ] Deterministic output with `now` parameter

  **Test `format_date_short()`:**
  - [ ] Valid datetime → "Mon DD, YYYY"
  - [ ] Timezone-aware vs naive
  - [ ] ISO string input
  - [ ] None input → "N/A"
  - [ ] Invalid input → "N/A"

- [ ] Target: 100% code coverage for utils module

### Phase 3 – Update DraftService
**Status**: Not started
**Depends on**: Phase 2 complete (tests passing)

- [ ] Import formatting utilities in `DraftService`:
  ```python
  from app.utils.draft_formatting import (
      format_draft_for_display,
      extract_attribute_names,
  )
  ```

- [ ] Replace `get_drafts_for_user()` formatting loop:
  ```python
  # OLD: Inline formatting (40+ lines)
  for d in drafts:
      updated_display = humanize.naturaltime(...)
      name_slug = slugify(...)
      # ... more formatting

  # NEW: Delegate to utils
  for d in drafts:
      user_drafts.append(format_draft_for_display(d))
  ```

- [ ] Replace `get_public_drafts()` formatting:
  ```python
  # OLD: Calls self.format_draft_for_display()
  result.append(self.format_draft_for_display(draft, comment_count))

  # NEW: Calls utils directly
  result.append(format_draft_for_display(draft, comment_count=comment_count))
  ```

- [ ] Remove methods from `DraftService`:
  - [ ] Delete `format_draft_for_display()` (now in utils)
  - [ ] Delete `extract_attribute_names_from_generated_json()` (now in utils)
  - [ ] Delete `format_submitted_time()` (replaced by `humanize_timestamp()`)

- [ ] Update docstrings in service methods to reflect delegation

### Phase 4 – Update Service Tests
**Status**: Not started
**Depends on**: Phase 3 complete

- [ ] Update `tests/test_services/test_draft_service.py`:
  - [ ] Remove formatting assertion tests (now in test_draft_formatting.py):
    - Delete `test_format_draft_for_display`
    - Delete `test_format_draft_for_display_no_generated`
    - Delete `test_format_draft_for_display_timestamp_error`
    - Delete `test_extract_attribute_names_*` tests
    - Delete `test_format_submitted_time` (if exists)

  - [ ] Keep orchestration tests:
    - `test_get_drafts_for_user_success` - verify repo call + formatting delegation
    - `test_get_public_drafts` - verify comment integration + formatting delegation
    - All ownership/permission tests (delete, make_public, submit)

  - [ ] Verify tests still pass (should, since output format unchanged)

### Phase 5 – Verify Integration
**Status**: Not started
**Depends on**: Phase 4 complete

- [ ] Run full test suite - must remain at 100% pass rate:
  ```bash
  task test
  ```

- [ ] Check integration tests don't break:
  - [ ] `tests/test_public_draft_feature.py` - public draft listings
  - [ ] `tests/test_resume_logic.py` - draft workflow
  - [ ] `tests/test_profile.py` - profile draft display (if exists)

- [ ] Manual verification:
  - [ ] Start dev server: `task dev`
  - [ ] Visit profile page - verify draft list renders correctly
  - [ ] Visit public drafts page - verify formatting matches old behavior
  - [ ] Check timestamps show relative times ("2 hours ago")
  - [ ] Verify author names display correctly

- [ ] Performance check (should be unchanged):
  - Formatting is still in-memory, just moved to different module
  - No new database queries added

### Phase 6 – Documentation & Cleanup
**Status**: Not started
**Depends on**: Phase 5 complete

- [ ] Update `app/utils/__init__.py` to export formatting functions (if following that pattern)

- [ ] Add docstring examples to `draft_formatting.py`:
  ```python
  """Draft formatting utilities.

  Pure functions for formatting draft data for display.
  Used by DraftService and routers for consistent output.

  Example:
      >>> draft_dict = {"id": "123", "name": "Test", ...}
      >>> formatted = format_draft_for_display(draft_dict)
      >>> formatted["updated_display"]
      '2 hours ago'
  """
  ```

- [ ] Update `app/CLAUDE.md` with utils pattern guidance (if not already present):
  - Section on when to use utils vs services
  - Example of pure formatting functions

- [ ] Update `docs/RECENT_UPDATES_SUMMARY.md`:
  - Add entry about formatting utilities extraction
  - Note service cleanup (reduced from 515 lines)

- [ ] Optional: Update `CHANGELOG.md` if visible to users

## Success Criteria

- [ ] All formatting logic moved out of `DraftService`
- [ ] `DraftService` reduced from 515 to ~350 lines (removing ~165 lines of formatting)
- [ ] New `app/utils/draft_formatting.py` with ~150 lines of pure functions
- [ ] Tests at 100% pass rate (144+ tests remain green)
- [ ] Test coverage for utils at 100%
- [ ] Formatting output **identical** to current behavior (backward compatible)
- [ ] No new dependencies added
- [ ] Services can be imported without circular dependencies
- [ ] **Enables next step**: DraftService refactor can proceed (Phase 0 prerequisite satisfied per `draft-service-refactor-plan.md`)

## Risk Assessment

**Risk: LOW** ✅

- Pure code movement, not architectural change
- Comprehensive test coverage catches regressions
- Output format unchanged (backward compatible)
- Can be done incrementally (one function at a time if needed)
- Easy to rollback (just one commit)

**Validation Strategy:**
- Tests must pass at each phase
- Manual verification before merge
- Integration tests ensure HTMX fragments still work

## Why This Approach is Better

**Original "presenter layer" plan issues:**
- ❌ Created new `app/presenters/` package (unfamiliar pattern)
- ❌ Talked about "DI integration" for simple functions
- ❌ Over-engineered with phases about "presenter adoption patterns"
- ❌ Suggested 2-3 days of work for moving simple functions

**This approach:**
- ✅ Uses existing `app/utils/` pattern (like `slug.py`)
- ✅ Pure functions - no DI, no complexity
- ✅ Simple phases - create, test, integrate, done
- ✅ Clear separation: utils for formatting, services for business logic

**Aligns with project principles:**
- Type safety: Functions have full type hints
- Testability: Pure functions with deterministic testing
- Simplicity: No new architectural patterns
- Maintainability: Clear responsibility boundaries

## How This Enables the Draft Service Refactor

The **DraftService Refactor depends on this work** (see `draft-service-refactor-plan.md` Phase 0).

**Why the dependency matters:**

1. **Clean separation of concerns**: Once formatting is in utils, DraftService can focus purely on business logic:
   - Remove Python-side filtering methods (they duplicate `DraftRepo`)
   - Keep only orchestration (ownership checks, workflow transitions, service coordination)
   - No mixed responsibilities

2. **Single migration wave**: Routers and services change ONCE:
   ```python
   # After this refactor:
   from app.utils.draft_formatting import format_draft_for_display
   drafts = await draft_repo.list_for_user(user_id)
   formatted = [format_draft_for_display(d) for d in drafts]

   # Then DraftService refactor removes inefficient Python filtering:
   # DELETE: DraftService.list_for_user_by_name() - just call repo directly
   # DELETE: DraftService.find_editable_by_name() - just call repo directly
   # KEEP: DraftService.delete_draft() - has ownership checks (business logic)
   ```

3. **Test stability**: Formatting tests move to `test_utils/` now. When we clean up `DraftService` later:
   - Service tests only check business logic delegation
   - No need to rewrite formatting assertions (already tested in utils)
   - Integration tests remain stable (formatting output unchanged)

4. **Clear completion criteria**:
   - ✅ This plan complete = formatting extracted, services slimmed
   - ✅ Service refactor complete = Python filtering removed, only orchestration remains
   - Both have objective success criteria

**What the service looks like after both refactors:**
```python
class DraftService:
    """Orchestrates draft business logic - no formatting, no filtering."""

    # Orchestration with ownership checks
    async def delete_draft(self, draft_id, user_id) -> bool:
        draft = await self.draft_repo.get_draft(draft_id, user_id)
        if not draft:
            raise NotFoundError()
        return await self.draft_repo.delete_draft(draft_id, user_id)

    # Workflow transitions
    async def make_public_draft(self, draft_id, user_id):
        # Verify ownership, transition status
        ...

    # Service coordination
    async def save_draft(self, user_id, name, inputs, user=None):
        if user:
            await self.database.ensure_person_for_user(user)
        return await self.draft_repo.save_draft(...)

    # Comment integration
    async def add_comment_to_draft(self, draft_id, user, content):
        return await self.comment_service.add_comment("draft", draft_id, user, content)
```

**Services become thin orchestration layers** with:
- Formatting in `app/utils/`
- Queries in `app/database.py` (repositories)
- Business logic in services (ownership, transitions, coordination)

## Open Questions

None - approach is clear and actionable.
