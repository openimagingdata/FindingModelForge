# Shared Comment Service Refactor Plan

**Last Updated**: December 8, 2025

## Context

- Comment creation/report/reporting logic is duplicated between `DraftService` and `FindingModelService`, both depending
  on `CommentRepo` and helper functions in `app/services/comment_helpers.py`.
- Goal is to centralize validation, rate limiting, repository coordination, and cache invalidation for comments while
  keeping routers thin and services cohesive.
- Must preserve existing behaviour (single-level replies, rate limiting via user comment index, blacklist, sanitisation)
  and maintain compatibility with current FastAPI dependency injection.

## Objectives

- Provide a dedicated `CommentService` (or similarly named module under `app/services/`) that encapsulates shared
  comment workflows for both drafts and finding models.
- Maintain explicit dependencies on `CommentRepo`, `UserRepo`, and `RedisCache` (if/when needed) via existing dependency
  wiring (`app/dependencies.py`).
- Ensure the service exposes clear methods used by routers/services (e.g., `add_comment`, `add_reply`, `report_comment`,
  `get_thread`) without forcing large-scale router rewrites.
- Retire duplicated logic from `DraftService` and `FindingModelService` once the new service is adopted.
- Preserve existing unit/integration test coverage; add targeted tests for the new service.

## Constraints & Assumptions

- FastAPI dependency graph should still source dependencies from `app.dependencies`; avoid circular imports.
- `CommentRepo` remains the single point for persistence; do not move DB access into the new service.
- Rate limiting will continue using the `User.comment_index` approach until a future redesign.
- No behavioural changes to HTMX fragments or templates should be required.
- The refactor must remain incremental: introduce the new service, integrate it, then remove duplication.

## Deliverables

1. `app/services/comment_service.py` (new) containing:
   - High-level orchestration methods for creating/replying/reporting comments.
   - Shared validation hooks (calls to helpers) plus any new helper consolidation needed.
   - Error handling consistent with current implementation (raises `HTTPException` where applicable).
2. Updated dependencies wiring (likely `CommentServiceDep` in `app/dependencies.py`).
3. Refactored `DraftService` and `FindingModelService` using the new service, removing duplicated code.
4. Updated or new tests covering comment flows (unit tests for service, regression tests for routers if needed).

## Plan

### Phase 1 – Service Skeleton

- [x] **Task 1:** Draft `app/services/comment_service.py` module with `CommentService` class, dependency fields
      (`CommentRepo`, `UserRepo`, optional `DraftRepo`) and method stubs.
  - Implementation note (cycle 1): initial stub introduced an unused `extra_context` parameter; removed in the second
    pass leaving clean stubs.
- [x] **Task 2:** Implement `get_thread(reference_type, reference_id)` ensuring it delegates to `CommentRepo` and
      returns `CommentThread | None` consistently.
- [x] **Task 3:** Implement `add_comment(...)` orchestration:
  - Pull in validation helpers (`check_rate_limit`, `get_blacklist_user_ids`, `validate_comment_content`,
    `validate_parent_comment`).
  - Support both draft and finding-model flows, including draft-status guard via `DraftRepo` when needed.
  - Persist via `CommentRepo`, update `UserRepo.add_comment_to_index`, and return created `Comment`.
- [x] **Task 4:** Implement `report_comment(...)` orchestration covering thread lookup, duplicate-report detection, and
      delegation to `CommentRepo`.
- [x] **Task 5:** Add any shared internal helpers/constants required by Tasks 2–4 while keeping logic lean (no router
      changes yet).
  - Current implementation only required `_ALLOWED_REFERENCE_TYPES`; no additional helpers needed.

### Phase 2 – Dependency Wiring

- [x] **Task 6:** Add FastAPI dependency provider in `app/dependencies.py` (e.g., `get_comment_service`).
- [x] **Task 7:** Expose `CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]` for
      router/service consumption.
- [x] **Task 8:** Update `app/services/__init__.py` to export the new service class for downstream imports.

### Phase 3 – Integrate with Existing Services

- [x] **Task 9:** Refactor `DraftService` comment methods (`get_comments_for_draft`, `add_comment_to_draft`,
      `report_draft_comment`) to delegate to `CommentService`.
- [x] **Task 10:** Refactor `FindingModelService` comment-related methods to delegate similarly.
- [x] **Task 11:** Remove now-redundant helper functions or imports from both services.

### Phase 4 – Clean Up Helpers

- [x] **Task 12:** Audit `app/services/comment_helpers.py` usage and relocate logic that now fits better inside
      `CommentService`.
- [x] **Task 13:** Remove or flag any unused helper functions/imports left over after the refactor.
- [x] **Task 4a:** Remove redundant `CommentRepo` dependency from `DraftService` (constructor, DI wiring, tests) now
      that comment flows use `CommentService`.

### Phase 5 – Testing & Verification

- [x] **Task 14:** Create `tests/test_services/test_comment_service.py` validating
  - top-level and reply creation (draft + finding model paths)
  - draft status enforcement
  - rate limit and blacklist failures
  - reporting workflows via `CommentRepo`
  - malformed content / parent validation behaviour.
- [x] **Task 15:** Expand helper tests to cover `validate_comment_content` and `validate_parent_comment` edge cases.
- [x] **Task 16:** Update `tests/test_services/test_draft_service.py` and
      `tests/test_services/test_finding_model_service.py` to assert delegation into `CommentService` with appropriate
      reference identifiers.
- [x] **Task 17:** Move draft comment permission checks from `tests/test_public_draft_feature.py` into the new comment
      service suite (or equivalent tests targeting `CommentService`).
- [x] **Task 18:** Run targeted regression tests (HTMX comment flows / related suites) to confirm behaviour unchanged.

### Phase 6 – Documentation & Rollout

- [x] **Task 19:** Update `app/CLAUDE.md` with CommentService patterns and usage guidelines.
- [x] **Task 20:** Document refactor in `CHANGELOG.md`, `docs/RECENT_UPDATES_SUMMARY.md`, and Serena memory.

## Completion Summary

**Status**: ✅ **COMPLETE** (September 30, 2025)

All phases completed successfully:

- CommentService created and fully tested
- DraftService and FindingModelService refactored to delegate
- Routers cleaned up (no duplicate business logic)
- All 491 tests passing (79.50% coverage)
- Documentation updated across CHANGELOG, RECENT_UPDATES, app/CLAUDE.md, and Serena memories

**Key Achievement**: Eliminated code duplication, established proper service layer separation, maintained test coverage.

## Open Questions

- None remaining. Refactor complete and production-ready.
