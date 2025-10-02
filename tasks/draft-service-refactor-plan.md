# DraftService Refactor Plan

**Last Updated**: October 1, 2025
**Status**: ⚠️ **BLOCKED - DO NOT PROCEED YET**
**Blocker**: Presenter layer must be implemented first (see Phase 0)

## Context
- `DraftService` currently performs repository-like queries (filtering and sorting draft lists) and embeds logic duplicated with `DraftRepo`.
- It also contains helpers for formatting data for UI consumption, which **MUST** move to a dedicated presenter module FIRST.
- Objective is to focus `DraftService` on business rules that truly require orchestration while deferring raw persistence to `DraftRepo`.

## Code Analysis Summary (October 1, 2025)

**Critical Findings:**
1. **DraftRepo is already comprehensive** - has `find_editable_by_name()`, `find_latest_by_name()`, etc. using MongoDB queries
2. **DraftService has inefficient duplicates** - `list_for_user_by_name()`, `find_editable_by_name()`, `find_latest_by_name()` fetch ALL drafts then filter in Python! 😱
3. **Presentation logic is mixed in** - `format_draft_for_display()`, `extract_attribute_names_from_generated_json()` belong in presenter
4. **25+ router call sites** expect current return shapes - changing this twice (now + presenter) creates unnecessary churn

**Why Wait:**
- Moving presentation logic now means modifying the same code twice when presenter layer arrives
- Test suite would need rewriting twice (once now, once for presenter integration)
- Router updates would happen in two waves instead of one clean migration
- Clear dependency: Can't "update routers to use presenter outputs" (Phase 4) if presenters don't exist!

## Objectives
- Delegate all direct data retrieval/manipulation to `DraftRepo` methods (which already exist!)
- Remove Python-side filtering that duplicates database-level queries
- Ensure `DraftService` is responsible for:
  - Ownership/permission checks
  - Workflow transitions (make public, submit)
  - Integrations with other services (comment tracking, contributor creation)
  - Coordination with caching or session management when needed
- **Presentation logic moves to DraftPresenter** (Phase 0 prerequisite)

## Constraints & Assumptions
- `DraftRepo` **already has all needed queries** - Phase 2 is verification only, no new methods required!
- Avoid breaking API contracts used by routers—but accept we'll change them ONCE after presenter is ready
- **Presenter layer MUST be completed before this refactor** (not in parallel!)
- Maintain async patterns and type hints per project standards
- Target is 100% test success rate maintained throughout

## Deliverables
1. **Phase 0**: Working `DraftPresenter` with all formatting logic, routers updated, tests passing
2. **Phase 1+**: Slimmed `DraftService` with only orchestration/business logic, no presentation or Python filtering
3. Updated unit tests focusing on business logic, not formatting
4. Documentation reflecting new architecture

## Plan

### Phase 0 – Formatting Utilities (PREREQUISITE - DO THIS FIRST!)
**Status**: 🚫 Not started - REQUIRED before proceeding
**See**: `presenter-module-plan.md` for detailed implementation steps

**Summary**: Extract formatting logic from `DraftService` into `app/utils/draft_formatting.py`:
- [ ] Create `app/utils/draft_formatting.py` with pure formatting functions:
  - `format_draft_for_display(draft, comment_count, now)` - move from DraftService
  - `extract_attribute_names(json_str)` - move from DraftService
  - `humanize_timestamp(dt, now)` - for consistent time formatting
  - `format_date_short(dt)` - for date display
- [ ] Create comprehensive test suite in `tests/test_utils/test_draft_formatting.py`
  - Test all timestamp formatting edge cases (timezone-aware/naive, strings, None)
  - Test JSON attribute extraction with various schemas
  - Test display formatting with/without generated JSON
  - Deterministic testing with `now` parameter injection
- [ ] Update `DraftService` to delegate to utils:
  - `get_drafts_for_user()` calls formatting utils
  - `get_public_drafts()` calls formatting utils
  - Remove formatting methods from service (165 lines reduced)
- [ ] Update service tests - remove formatting assertions, test delegation only
- [ ] Run full test suite - must remain at 100% pass rate
- [ ] **GATE**: All tests passing? Formatting in utils? Service slimmed? → Proceed to Phase 1

**Only proceed past this point once Phase 0 is COMPLETE and MERGED!**

---

### Phase 1 – Audit & Gap Analysis
**Status**: Not started
**Depends on**: Phase 0 complete

- [ ] Verify `DraftRepo` has all needed methods (SPOILER: it does!)
  - ✅ `find_editable_by_name()` - already exists with MongoDB regex
  - ✅ `find_latest_by_name()` - already exists with MongoDB sort
  - ✅ `list_for_user()` - already exists
  - ✅ `get_public_drafts()` - already exists with author aggregation
- [ ] Catalogue DraftService methods to remove:
  - `list_for_user_by_name()` - duplicates repo, filters in Python ❌
  - `find_editable_by_name()` - duplicates repo, filters in Python ❌
  - `find_latest_by_name()` - duplicates repo, filters/sorts in Python ❌
  - Presentation methods already moved to presenter ✅
- [ ] Document methods to KEEP:
  - `get_draft_by_id()` - orchestration with ownership checks ✅
  - `delete_draft()` - business logic with permission checks ✅
  - `make_public_draft()` - workflow transition ✅
  - `submit_draft()` - workflow transition ✅
  - `save_draft()` - orchestration with `ensure_person_for_user()` ✅
  - Comment delegation methods ✅

### Phase 2 – Repository Verification (NO NEW CODE NEEDED!)
**Status**: Not started
**Depends on**: Phase 1 complete

- [ ] **VERIFICATION ONLY** - confirm existing DraftRepo methods work correctly:
  - Test `find_editable_by_name()` case-insensitivity (test already exists)
  - Test `find_latest_by_name()` sorting (test already exists)
  - Confirm indexes support these queries efficiently
- [ ] **Result**: No new repository methods needed! 🎉

### Phase 3 – Remove Service Duplicates
**Status**: Not started
**Depends on**: Phase 2 complete

- [ ] Remove Python-filtering methods from DraftService:
  - Delete `list_for_user_by_name()` (lines 214-230) - callers should use repo directly
  - Delete `find_editable_by_name()` (lines 258-277) - callers should use repo directly
  - Delete `find_latest_by_name()` (lines 279-299) - callers should use repo directly
- [ ] Update `get_drafts_for_user()` to return raw drafts (presenter handles formatting now)
- [ ] Update `get_public_drafts()` to return raw drafts (presenter handles formatting now)
- [ ] Keep orchestration methods unchanged:
  - `save_draft()` with `ensure_person_for_user()` call
  - `delete_draft()` with ownership verification
  - `make_public_draft()` with ownership verification
  - `submit_draft()` with ownership verification
- [ ] Verify comment service delegation methods untouched

### Phase 4 – Update Router Call Sites
**Status**: Not started
**Depends on**: Phase 3 complete

- [ ] Update `app/routers/drafts.py`:
  - Review ~15 call sites currently using removed service methods
  - Change to call `draft_repo` directly or use presenter for formatting
  - Example: `drafts = await draft_repo.list_for_user(user_id)`
  - Example: `formatted = presenter.format_drafts_list(drafts)`
- [ ] Update `app/routers/profile.py`:
  - Similar review for profile-related draft queries
- [ ] Verify creation workflow still functions (step 1/4 resume logic)
- [ ] Test all updated endpoints manually via browser

### Phase 5 – Testing & Verification
**Status**: Not started
**Depends on**: Phase 4 complete

- [ ] Update `tests/test_services/test_draft_service.py`:
  - Remove tests for deleted methods (list_for_user_by_name, find_editable_by_name, find_latest_by_name)
  - Remove presentation formatting tests (now in test_draft_presenter.py from Phase 0)
  - Keep orchestration tests (delete, make_public, submit with ownership checks)
  - Verify comment delegation tests remain
- [ ] Update integration tests:
  - `tests/test_public_draft_feature.py` - should already work with presenter (from Phase 0)
  - `tests/test_resume_logic.py` - verify draft adoption still works
  - Profile-related tests - verify draft listing works
- [ ] Run full test suite - must remain at 100% pass rate
- [ ] Run Playwright browser tests for draft workflows
- [ ] Performance check: verify queries use database filtering, not Python

### Phase 6 – Cleanup & Documentation
**Status**: Not started
**Depends on**: Phase 5 complete

- [ ] Remove any dead code or unused imports
- [ ] Update docstrings to reflect new responsibilities
- [ ] Update `docs/RECENT_UPDATES_SUMMARY.md` with:
  - Presenter layer creation (Phase 0)
  - Service layer cleanup (Phases 1-5)
  - Performance improvements from database-level filtering
- [ ] Add entry to `CHANGELOG.md` about architectural improvement
- [ ] Consider updating `app/CLAUDE.md` with presenter pattern guidance

## Success Criteria
- [ ] Zero Python-side filtering of database results
- [ ] All presentation logic in DraftPresenter
- [ ] DraftService only does orchestration/business logic
- [ ] 100% test pass rate maintained throughout
- [ ] No router API changes between Phase 0 and Phase 6 completion
- [ ] Performance: draft queries use database indexes, not Python loops

## Risk Assessment
- **LOW risk once Phase 0 complete** - presenter provides stable interface
- **HIGH risk if we skip Phase 0** - would require two refactors instead of one
- **Test coverage is excellent** - 144 tests help catch regressions

## Open Questions
- None currently. Proceed with Phase 0 when ready to invest 2-3 days of focused work.
