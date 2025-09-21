# Shared Comment Service Refactor Plan

**Last Updated**: December 8, 2025

## Context
- Comment creation/report/reporting logic is duplicated between `DraftService` and `FindingModelService`, both depending on `CommentRepo` and helper functions in `app/services/comment_helpers.py`.
- Goal is to centralize validation, rate limiting, repository coordination, and cache invalidation for comments while keeping routers thin and services cohesive.
- Must preserve existing behaviour (single-level replies, rate limiting via user comment index, blacklist, sanitisation) and maintain compatibility with current FastAPI dependency injection.

## Objectives
- Provide a dedicated `CommentService` (or similarly named module under `app/services/`) that encapsulates shared comment workflows for both drafts and finding models.
- Maintain explicit dependencies on `CommentRepo`, `UserRepo`, and `RedisCache` (if/when needed) via existing dependency wiring (`app/dependencies.py`).
- Ensure the service exposes clear methods used by routers/services (e.g., `add_comment`, `add_reply`, `report_comment`, `get_thread`) without forcing large-scale router rewrites.
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
- [ ] Create `CommentService` class in `app/services/comment_service.py` with constructor accepting `CommentRepo`, `UserRepo` (and optional `DraftRepo` if needed for status checks).
- [ ] Define public methods mirroring current use cases:
  - `get_thread(reference_type, reference_id)`
  - `add_comment(reference_type, reference_id, user, content, *, parent_id=None)`
  - `report_comment(reference_type, reference_id, comment_id, user_id)`
- [ ] Centralise validation/rate-limit/blacklist logic inside the service by reusing `comment_helpers`; if additional helpers are required, move them alongside or keep them imported.

### Phase 2 – Dependency Wiring
- [ ] Add FastAPI dependency provider in `app/dependencies.py` (e.g., `get_comment_service`).
- [ ] Expose `CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]` for router/service consumption.
- [ ] Update `app/services/__init__.py` to export the new service or errors if necessary.

### Phase 3 – Integrate with Existing Services
- [ ] Refactor `DraftService` methods (`get_comments_for_draft`, `add_comment_to_draft`, `report_draft_comment`) to delegate to `CommentService`.
- [ ] Refactor `FindingModelService` comment-related methods to delegate similarly.
- [ ] Remove now-redundant helper functions or imports from both services.

### Phase 4 – Clean Up Helpers
- [ ] Determine whether remaining functions in `app/services/comment_helpers.py` belong inside the service; migrate or keep as lightweight utility module.
- [ ] Ensure there are no unused functions after the migration; delete or mark for removal.

### Phase 5 – Testing & Verification
- [ ] Add a dedicated `tests/test_services/test_comment_service.py` suite that exercises:
  - Successful top-level and reply creation for both drafts and finding models (ensuring repo + user index interactions)
  - Status enforcement for drafts (public/submitted only)
  - Rate limit and blacklist failures propagating as `HTTPException`
  - Reporting workflows delegating to `CommentRepo`
  - Parent validation and sanitisation paths (including malformed content)
- [ ] Expand `tests/test_comment_helpers.py` (or a new helper-focused module) with explicit cases for
  `validate_comment_content` and `validate_parent_comment`, since these behaviours are currently untested.
- [ ] Adjust `tests/test_services/test_draft_service.py` and `tests/test_services/test_finding_model_service.py`
  to expect delegation into `CommentService` (mock the new dependency and assert it is called with the
  correct reference identifiers/name lookups).
- [ ] Migrate the draft comment permission assertions from `tests/test_public_draft_feature.py` into the
  new comment service suite (or update them to target `CommentService`) so they continue to verify the
  same business rules after the refactor.
- [ ] Run targeted manual/automated regression checks (HTMX comment flows) to confirm no behaviour changes.

### Phase 6 – Documentation & Rollout
- [ ] Update relevant documentation (e.g., `app/CLAUDE.md` if service architecture changes).
- [ ] Note migration details in `docs/RECENT_UPDATES_SUMMARY.md` or internal change log if required.

## Open Questions
- None at this time. Add sections flagged `[NEEDS CLARIFICATION]` if new requirements arise during implementation.
