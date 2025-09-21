# DraftService Refactor Plan

**Last Updated**: December 8, 2025

## Context
- `DraftService` currently performs repository-like queries (filtering and sorting draft lists) and embeds logic duplicated with `DraftRepo`.
- It also contains helpers for formatting data for UI consumption, which will move to a dedicated presenter module (see separate plan).
- Objective is to focus `DraftService` on business rules that truly require orchestration while deferring raw persistence to `DraftRepo`.

## Objectives
- Delegate all direct data retrieval/manipulation to `DraftRepo` methods, requiring repository additions only where gaps exist.
- Ensure `DraftService` is responsible for:
  - Ownership/permission checks
  - Workflow transitions (make public, submit)
  - Integrations with other services (comment tracking, contributor creation)
  - Coordination with caching or session management when needed
- Remove redundant Python-side filtering and keep surfaces small and testable.

## Constraints & Assumptions
- `DraftRepo` already offers many queries (`list_for_user`, `find_editable_by_name`, etc.); add new repository-level operations in `app/database.py` only if absolutely necessary.
- Avoid breaking API contracts used by routers (`app/routers/drafts.py`, `app/routers/profile.py`)—refactor should be transparent to callers except for import path adjustments.
- Presenter refactor happens in parallel; this plan assumes formatting helpers will migrate out, reducing scope here.
- Maintain async patterns and type hints per project standards.

## Deliverables
1. Slimmed `DraftService` with methods mapped to well-defined responsibilities (no presentation logic).
2. Updated `DraftRepo` (if needed) with richer queries to support the service without Python-side filtering.
3. Adjusted unit tests verifying new responsibilities and ensuring regressions are caught.
4. Documentation updates (if API surface changes) indicating new responsibilities and any new repo methods.

## Plan

### Phase 1 – Audit & Gap Analysis
- [ ] Catalogue each `DraftService` method, identify responsibilities to keep vs. move to repo or presenter.
- [ ] Confirm repository coverage; for missing queries (e.g., list-by-name with status filter) outline necessary repo changes.

### Phase 2 – Enhance Repository (if needed)
- [ ] Implement any new repository methods inside `DraftRepo` (e.g., `list_for_user_by_name`, `find_latest_by_name` using Mongo queries) ensuring indexes support queries.
- [ ] Add unit tests around new repository methods.

### Phase 3 – Refactor Service Responsibilities
- [ ] Update `DraftService.get_drafts_for_user` to call repo directly and leave formatting for presenter module.
- [ ] Replace Python-side filtering in `find_editable_by_name`, `find_latest_by_name`, `list_for_user_by_name` with repo queries or remove if redundant.
- [ ] Ensure `save_draft`, `make_public`, `submit_draft`, `delete_draft` continue to orchestrate workflow/permission checks only.
- [ ] Maintain contributor creation call (`ensure_person_for_user`) where necessary.

### Phase 4 – Integration Adjustments
- [ ] Review routers (`drafts.py`, `profile.py`) for expectations about return shapes; update them to use the upcoming presenter outputs.
- [ ] Verify creation workflow dependencies continue to function (step 1/4 resume logic).

### Phase 5 – Testing & Verification
- [ ] Rework `tests/test_services/test_draft_service.py` to focus on orchestration concerns:
  - Keep coverage for ownership/permission checks (`delete_draft`, `make_public`, `submit_draft`).
  - Replace presentation assertions with mocks/stubs that verify delegation to the presenter layer
    (once Phase 2 presenter work lands).
- [ ] Ensure repository query behaviour remains covered—if new `DraftRepo` helpers are introduced,
  mirror them with unit tests similar to `tests/test_draftrepo_queries.py`.
- [ ] Update integration suites that currently inspect formatted payloads (`tests/test_public_draft_feature.py`,
  `tests/test_resume_logic.py`, `tests/test_profile`-related flows) to consume presenter output instead of
  service-produced dicts once the refactor is complete.
- [ ] Run regression tests for draft workflows (HTMX autosave, submission, profile listing).

### Phase 6 – Cleanup & Documentation
- [ ] Remove dead code from `DraftService` once presenter migration is complete.
- [ ] Update `docs/RECENT_UPDATES_SUMMARY.md` or `technical_debt.md` to reflect the change.

## Open Questions
- None currently. Add `[NEEDS CLARIFICATION]` items here if repository responsibilities require specification changes during implementation.
