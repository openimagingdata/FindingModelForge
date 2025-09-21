# Presenter Module Consolidation Plan

**Last Updated**: December 8, 2025

## Context
- Formatting logic (humanised timestamps, attribute extraction, author display info) is currently embedded within `DraftService` and, to a lesser extent, router layers.
- Similar presentation requirements appear across profile pages, public draft listings, and creation workflow views.
- To keep services and repositories focused, we will introduce lightweight presenter utilities dedicated to shaping data for templates and HTMX fragments.

## Objectives
- Create a reusable presenter module (initially `app/presenters/drafts.py`) that encapsulates draft-specific formatting concerns.
- Ensure presenters operate on domain models or plain dicts returned from services without performing I/O.
- Provide helper functions used across routers (`drafts.py`, `profile.py`, `creation.py`) and templates to minimise duplication.
- Keep presenter layer thin: pure functions with minimal dependencies (prefer standard lib + existing utilities like `humanize`).

## Constraints & Assumptions
- Presenters should not depend on FastAPI request objects or repositories; they should accept data plus optional context (e.g., `now` overrides for testing).
- Continue using `humanize` for time display to preserve existing output; consider injecting current time for deterministic tests.
- Avoid broad architectural changes—presenters are helper modules imported where needed, not a new framework.
- Initial scope focuses on draft-related views; future expansion (finding models, comments) can follow once patterns are proven.

## Deliverables
1. New package directory `app/presenters/` with `__init__.py` and `drafts.py` module.
2. Functions covering existing formatting needs, e.g.:
   - `format_draft(draft, *, comment_count=0, now=None)`
   - `format_draft_list(drafts, *, now=None)`
   - `extract_attribute_names(generated_json)` (if not already elsewhere)
3. Updated routers/services to call presenter functions instead of embedding formatting logic.
4. Unit tests for presenter functions ensuring consistent output and handling of edge cases (missing timestamps, strings vs `datetime`).

## Plan

### Phase 1 – Module Setup
- [ ] Create `app/presenters/__init__.py` with exports for draft presenters.
- [ ] Implement core presenter functions porting logic from `DraftService.format_draft_for_display` and related helpers.
- [ ] Ensure helper handles both Pydantic models and dicts, matching current behaviour.

### Phase 2 – Service & Router Integration
- [ ] Update `DraftService.get_drafts_for_user`, `DraftService.get_public_drafts`, and creation workflow pathways to call presenter functions.
- [ ] Adjust routers (`profile.py`, `drafts.py`) to use presenter outputs where they previously formatted data inline.
- [ ] Confirm dependency injection remains unaffected (presenters should not require DI).

### Phase 3 – Attribute Extraction Consolidation
- [ ] Move `extract_attribute_names_from_generated_json` logic into presenter (or related helper) and update callers.
- [ ] Provide backward-compatible wrapper in service if needed during transition.

### Phase 4 – Testing
- [ ] Introduce a `tests/test_presenters/test_draft_presenter.py` (or similar) covering:
  - Time formatting with timezone-naïve and aware datetimes (injecting `now` for determinism)
  - Handling of dict vs model inputs
  - Attribute extraction error resilience and fallbacks for missing author metadata.
- [ ] Remove/relocate the existing formatting assertions living in `tests/test_services/test_draft_service.py`
  so that presentation behaviour is validated only via the new presenter tests.
- [ ] Update service tests to stub presenter calls and assert delegation rather than inspecting
  the formatted payload inline.
- [ ] Adjust router/integration tests that assert rendered strings (`tests/test_public_draft_feature.py`,
  `tests/test_drafts_router.py`, etc.) to consume presenter output where appropriate, ensuring
  HTMX fragments still render the expected fields.

### Phase 5 – Cleanup & Documentation
- [ ] Remove redundant formatting code from `DraftService` after presenter adoption.
- [ ] Update documentation (`app/CLAUDE.md` or internal docs) describing presenter usage patterns.

## Open Questions
- None currently. Use `[NEEDS CLARIFICATION]` markers if additional presenter responsibilities emerge during implementation.
