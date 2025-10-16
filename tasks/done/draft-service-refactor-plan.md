# DraftService Refactor Plan

**Last Updated**: October 5, 2025
**Status**: ✅ **COMPLETE** - All steps implemented and verified
**Time Taken**: ~45 minutes

## Current State (as of October 4, 2025)

✅ **Completed Prerequisites:**
- `app/utils/draft_formatting.py` exists with all formatting functions
- `format_draft_for_display()`, `extract_attribute_names()`, `humanize_timestamp()`, `format_date_short()`
- `DraftService.get_drafts_for_user()` already delegates to formatting utilities
- 22 formatting tests passing in `tests/test_utils_draft_formatting.py`
- Service already focused on business logic for most operations

❌ **Remaining Issues:**
- 3 service methods duplicate `DraftRepo` functionality with Python-side filtering:
  - `list_for_user_by_name()` - fetches ALL drafts, filters in Python
  - `find_editable_by_name()` - fetches ALL drafts, filters in Python
  - `find_latest_by_name()` - fetches ALL drafts, filters in Python
- 2 router call sites use these inefficient methods (`creation.py:128, 147`)
- 1 test file references `list_for_user_by_name()` (no production usage)

## Context

The formatting extraction work (originally planned as "Phase 0") has been **completed**. This refactor is now a simple cleanup task to:
1. Remove duplicate filtering methods from `DraftService`
2. Update 2 router calls to use `DraftRepo` directly
3. Delete associated tests

This is **not** an architectural change—the architecture is already correct per FastAPI 2025 best practices.

## Objectives

- Remove Python-side filtering that duplicates database-level queries
- Ensure routers call `DraftRepo` directly for simple queries
- Keep `DraftService` focused on orchestration and business logic:
  - Ownership/permission checks
  - Workflow transitions (make public, submit)
  - Service coordination (comment tracking, contributor creation)
  - Formatting delegation (already done)

## Constraints & Principles

- `DraftRepo` already has all needed query methods
- Maintain async patterns and type hints per project standards
- Target: 100% test success rate maintained throughout
- No breaking changes to public APIs
- Follow existing FastAPI service layer patterns from `app/CLAUDE.md`

## Deliverables

1. Slimmed `DraftService` with duplicate methods removed (~60 lines deleted)
2. Updated router calls using `DraftRepo` directly (2 lines changed)
3. Updated/removed tests (3 test methods)
4. Documentation update in `RECENT_UPDATES_SUMMARY.md`

## Implementation Plan

This is a **single-phase cleanup task**, not a multi-phase refactor.

### Step 1: Update Router Call Sites (5 minutes) ✅ COMPLETE
**File**: `app/routers/creation.py`

- [x] Line 128: Change to call `draft_repo.find_editable_by_name()` directly
  ```python
  # OLD:
  draft = await draft_service.find_editable_by_name(user_id=current_user.id, name=name)

  # NEW:
  draft = await draft_repo.find_editable_by_name(user_id=current_user.id, name=name)
  ```

- [x] Line 147: Change to call `draft_repo.find_latest_by_name()` directly
  ```python
  # OLD:
  latest = await draft_service.find_latest_by_name(user_id=current_user.id, name=name)

  # NEW:
  latest = await draft_repo.find_latest_by_name(user_id=current_user.id, name=name)
  ```

- [x] Verify `draft_repo` is available via dependency injection in the route handler

### Step 2: Remove Duplicate Methods from DraftService (10 minutes) ✅ COMPLETE
**File**: `app/services/draft_service.py`

- [x] Delete `list_for_user_by_name()` method (lines ~181-197)
  - Duplicates `draft_repo.list_for_user()` + Python filter
  - Currently only called in tests, not production code

- [x] Delete `find_editable_by_name()` method (lines ~199-218)
  - Duplicates `draft_repo.find_editable_by_name()`
  - Now called directly from router

- [x] Delete `find_latest_by_name()` method (lines ~220-240)
  - Duplicates `draft_repo.find_latest_by_name()`
  - Now called directly from router

- [x] Remove unused imports if any (e.g., list comprehension utils)

**Result**: ~60 lines deleted from service

### Step 3: Update Tests (15 minutes) ✅ COMPLETE
**File**: `tests/test_services/test_draft_service.py`

- [x] Remove or update tests for deleted methods:
  - `test_list_for_user_by_name_success`
  - `test_list_for_user_by_name_error`
  - Tests for `find_editable_by_name()` (if any service-level tests exist)
  - Tests for `find_latest_by_name()` (if any service-level tests exist)

- [x] Keep all orchestration and business logic tests:
  - `test_get_drafts_for_user_success` (delegates to repo + formatting)
  - `test_delete_draft` (ownership checks)
  - `test_make_public_draft` (workflow transition)
  - `test_submit_draft` (workflow transition)
  - Comment delegation tests

**Note**: Repository-level tests in `tests/test_draftrepo_queries.py` remain unchanged

**Additional work**: Fixed test mocks in `tests/test_finding_models_comprehensive.py`:
- Updated 8 tests to mock `app.database.DraftRepo` methods instead of removed service methods
- Fixed `test_process_step_1_resume_existing_draft` to mock repository instance directly
- Fixed `test_step1_resumes_submitted_draft_to_draft_view` mock setup

### Step 4: Verify & Test (10 minutes) ✅ COMPLETE

- [x] Run service tests:
  ```bash
  uv run pytest tests/test_services/test_draft_service.py -v
  ```
  **Result**: 16 tests passed (down from 18 as expected)

- [x] Run router tests:
  ```bash
  uv run pytest tests/test_drafts_router.py tests/test_resume_logic.py -v
  ```
  **Result**: All tests passed

- [x] Run full test suite:
  ```bash
  task test-unit
  ```
  **Result**: ✅ All unit tests passing! (6 skipped tests with "Complex session handling" markers)

### Step 5: Documentation (5 minutes) ✅ COMPLETE

- [x] Update `docs/RECENT_UPDATES_SUMMARY.md`:
  ```markdown
  ## Service Layer Cleanup (October 4, 2025)

  - Removed duplicate filtering methods from `DraftService`
  - Routers now call `DraftRepo` directly for simple queries
  - Service focused on business logic only (ownership, workflows, coordination)
  - Formatting utilities already in `app/utils/draft_formatting.py`
  ```

- [ ] Optional: Update `CHANGELOG.md` if user-visible

## Success Criteria ✅ ALL COMPLETE

- [x] 3 duplicate methods removed from `DraftService` (~60 lines)
- [x] 2 router calls updated to use `DraftRepo` directly
- [x] Test suite passes (all unit tests passing with 6 skipped)
- [x] No Python-side filtering for simple queries
- [x] Service remains focused on business logic:
  - ✅ Ownership checks (`delete_draft`, `get_draft_by_id`)
  - ✅ Workflow transitions (`submit_draft`, `make_public_draft`)
  - ✅ Service coordination (`save_draft` with `ensure_person_for_user`)
  - ✅ Formatting delegation (`get_drafts_for_user` calls utils)
- [x] Documentation updated

## Risk Assessment

**Risk: VERY LOW** ✅

- Simple code deletion, no architectural changes
- Only 2 router call sites affected
- Comprehensive test coverage catches issues
- Can be completed and verified in under 1 hour
- Easy to rollback (single commit)
- Repository methods already tested and working

## Verification Strategy

1. **Before changes**: Run `task test-unit` (baseline)
2. **After Step 2**: Check service tests pass
3. **After Step 3**: Check all tests pass
4. **Manual check**: Test creation workflow in browser (resume draft functionality)

## Why This Approach

**Simplified from original plan because:**
- ✅ Formatting extraction already complete (was "Phase 0")
- ✅ Only 2 call sites need updating (not "25+")
- ✅ Only 3 methods to delete (straightforward)
- ✅ No architectural changes needed (already follows best practices)
- ✅ 1-hour task, not multi-phase project

**Aligns with FastAPI 2025 best practices:**
- Thin routers → call repos directly for simple queries ✓
- Services → business logic and orchestration only ✓
- Utilities → formatting and presentation ✓
- Repository pattern → data access layer ✓
