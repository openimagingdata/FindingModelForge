# Model Iteration Feature - Implementation Plan

**Status**: Sprint 1 Complete **Created**: 2025-10-29 **Last Updated**: 2025-11-27 **Branch**: `feature/model-editing`

---

## Feature Overview

Add capability for users to create **iterations** of existing published finding models through AI-assisted editing.

### Iteration Methods

1. **Natural Language Iteration** (Sprint 1 - MVP): User submits text prompts describing desired changes ✅ COMPLETE
2. **Markdown Edit Iteration** (Sprint 2): AI exports model to markdown, user edits, AI applies changes back

**Key Distinction**: Iterations are AI-assisted ONLY. Users cannot manually edit iteration drafts.

### Requirements

- Name remains the same as base model
- One iteration draft per user per published model
- Full audit trail via existing `action_log`
- Multiple refinement rounds (iterative)
- Same submission workflow as regular drafts
- NO manual editing of iteration drafts

---

## findingmodel 0.6.0 API (Verified)

```python
from findingmodel.tools.model_editor import (
    edit_model_natural_language,  # async
    edit_model_markdown,          # async
    export_model_for_editing,     # SYNC (not async!)
    EditResult,
)

class EditResult(BaseModel):
    model: FindingModelFull
    rejections: list[str]
    changes: list[str]
```

**Built-in Guardrails**: Preserves OIFM IDs, validates schema, rejects unsafe changes.

---

## Sprint Overview

| Sprint       | Focus                  | Status      |
| ------------ | ---------------------- | ----------- |
| **Sprint 1** | MVP - Natural Language | ✅ Complete |
| **Sprint 2** | Markdown Edit          | Not Started |
| **Sprint 3** | Enhanced History       | Not Started |

---

# Sprint 1: MVP - Natural Language Iteration ✅ COMPLETE

**Goal**: Working iteration feature for test users with natural language editing only.

**Scope**:

- Create iteration from published model ✅
- Natural language change requests ✅
- Display changes/rejections ✅
- Use existing draft submission workflow ✅
- Simple UI (no tabs) ✅

---

## Sprint 1 Architecture Decisions

### Simplified Data Model

Added two fields to `FindingModelDraft`:

```python
# In app/models.py
class FindingModelDraft(BaseModel):
    # ... existing fields ...

    # Iteration tracking
    is_iteration: bool = False
    base_model_id: str | None = None  # oifm_id of model being iterated
```

**MVP Decision**: Use existing `action_log` for iteration history. Log entries with action types `iteration.applied` or
`iteration.failed` store user input, changes, rejections.

### Service Layer Approach

Extended `DraftService` with iteration methods (follows existing patterns in `app/services/draft_service.py`).

---

## Sprint 1, Phase 1: Data Model ✅ COMPLETE

### Tasks

- [x] Add `is_iteration: bool = False` to `FindingModelDraft`
- [x] Add `base_model_id: str | None = None` to `FindingModelDraft`
- [x] **Unit test**: Verify serialization with new fields
- [x] **Unit test**: Verify defaults for existing drafts

---

## Sprint 1, Phase 2: Backend ✅ COMPLETE

### Tasks

#### DraftRepo (app/database.py)

- [x] Add `get_iteration_draft(user_id: int, base_model_id: str) -> FindingModelDraft | None`
- [x] Modify `save_draft()` to accept `is_iteration` and `base_model_id` parameters
- [x] Add `update_generated_json(draft_id: str, json: str)` helper method
- [x] **Unit test**: `test_get_iteration_draft_returns_existing`
- [x] **Unit test**: `test_get_iteration_draft_returns_none_when_not_found`

#### DraftService (app/services/draft_service.py)

- [x] Add `start_iteration(user_id, user, base_model) -> FindingModelDraft`
- [x] Add `apply_natural_language_iteration(draft_id, user_id, command) -> dict`
- [x] **Unit test**: `test_start_iteration_creates_new_draft`
- [x] **Unit test**: `test_start_iteration_returns_existing`
- [x] **Unit test**: `test_apply_iteration_success` (mock AI)
- [x] **Unit test**: `test_apply_iteration_with_rejections` (mock AI)
- [x] **Unit test**: `test_apply_iteration_logs_to_action_log`

---

## Sprint 1, Phase 3: Endpoints ✅ COMPLETE

### Tasks

#### Entry Point (app/routers/finding_models_browse.py)

- [x] Add `POST /{slug}/iterate` endpoint
- [x] **Integration test**: `test_start_iteration_creates_draft`
- [x] **Integration test**: `test_start_iteration_redirects_to_draft`

#### Iteration Endpoint (app/routers/drafts/workflows.py)

- [x] Add `POST /{draft_id}/iterate` endpoint
- [x] **Integration test**: `test_iterate_endpoint_applies_changes`
- [x] **Integration test**: `test_iterate_endpoint_requires_auth`
- [x] **Integration test**: `test_iterate_non_iteration_draft_fails`

#### View Modification (app/routers/drafts/views.py)

- [x] Modify `get_draft_page` to fetch `base_model_slug` for iterations
- [x] Pass `base_model_slug` to template context
- [x] Store iteration results in Redis for one-time display after redirect

---

## Sprint 1, Phase 4: UI ✅ COMPLETE

### Tasks

#### Entry Button (templates/components/finding_model_display.html)

- [x] Add "Create Iteration" form/button for authenticated users
- [x] **Playwright test**: `test_iterate_button_visible_for_authenticated_user`
- [x] **Playwright test**: `test_iterate_button_not_visible_for_unauthenticated_user`
- [x] **Playwright test**: `test_iterate_button_creates_draft_and_redirects`

#### Iteration UI Components

- [x] Iteration banner showing "Iteration Draft" status with link to base model
- [x] Natural language textarea form with HTMX submission
- [x] "Apply Changes" button with disabled state when empty
- [x] Loading spinner during AI processing
- [x] JSON preview accordion for current model

#### Draft Page Modification (templates/drafts/)

- [x] Add conditional for `draft.is_iteration` in edit mode
- [x] Show iteration form instead of standard edit form for iteration drafts
- [x] Include iteration banner for iteration drafts
- [x] Show iteration results in preview mode (changes/rejections)

#### Result Display (templates/components/draft_preview_content.html)

- [x] Green "Changes Applied:" section with list of changes
- [x] Yellow "Some changes were rejected:" section with list of rejections
- [x] Blue "Info:" section when no changes or rejections
- [x] **Playwright test**: `test_iteration_results_with_both_changes_and_rejections`
- [x] **Playwright test**: `test_iteration_results_with_only_changes`
- [x] **Playwright test**: `test_iteration_results_with_only_rejections`

#### Workflow Tests

- [x] **Playwright test**: `test_iteration_form_visible_on_iteration_draft`
- [x] **Playwright test**: `test_iteration_results_container_visible`
- [x] **Playwright test**: `test_iteration_json_preview_visible`
- [x] **Playwright test**: `test_iteration_form_submission_with_mocked_response`
- [x] **Playwright test**: `test_iteration_form_submit_button_disabled_when_empty`
- [x] **Playwright test**: `test_multiple_iteration_commands_on_same_draft`
- [x] **Playwright test**: `test_iteration_draft_persists_across_sessions`

---

## Sprint 1 Success Criteria ✅ ALL MET

- [x] User can click "Create Iteration" on any published model
- [x] Iteration draft created with `is_iteration=True` and `base_model_id`
- [x] User can enter natural language request and see changes/rejections
- [x] Multiple iteration rounds work
- [x] Iteration drafts can be submitted via existing workflow
- [x] All existing tests pass
- [x] New tests pass (13 iteration UI tests)

---

# Sprint 2: Markdown Edit Feature

**Goal**: Add export/edit/apply markdown workflow.

## Sprint 2, Phase 1: Backend

- [ ] Add `DraftService.export_for_editing(draft_id, user_id) -> str`
- [ ] Add `DraftService.apply_markdown_iteration(draft_id, user_id, markdown) -> dict`
- [ ] Unit tests for both methods

## Sprint 2, Phase 2: Endpoints

- [ ] Add `GET /{draft_id}/export-markdown`
- [ ] Add `POST /{draft_id}/iterate-markdown`
- [ ] Integration tests

## Sprint 2, Phase 3: UI

- [ ] Create tab interface (`drafts/iteration_tabs.html`)
- [ ] Create markdown form component
- [ ] Create markdown editor component
- [ ] Playwright tests for tab switching and markdown workflow

---

# Sprint 3: Enhanced History & Polish

**Goal**: Structured history with timeline UI.

## Sprint 3, Phase 1: Data Model

- [ ] Create `IterationInteraction` model
- [ ] Add `iteration_history` field to draft
- [ ] Add `DraftRepo.add_iteration_interaction()` method

## Sprint 3, Phase 2: History UI

- [ ] Create `iteration_history_timeline.html` with Flowbite timeline
- [ ] Add `GET /{draft_id}/iteration-history` endpoint (lazy-loaded)
- [ ] Add History tab to tabs interface

## Sprint 3, Phase 3: OOB JSON Refresh

- [ ] Create generic OOB helper in `helpers.py`
- [ ] Update iteration endpoints to refresh JSON preview via OOB swap

---

# Future Sprints (Out of Scope)

- Version restore/undo
- JSON diff visualization
- Batch iterations
- AI-suggested iterations

---

## Important Considerations

### Manual Editing Restriction

Iteration drafts cannot be manually edited. The draft editor detects `is_iteration=True` and shows iteration UI instead
of the standard form.

### Concurrent Iterations

Multiple users can iterate on the same published model independently. Each gets their own iteration draft.

### Summary vs JSON Diff

Display summary of changes from `EditResult.changes`, not line-by-line diff.

---

## Documentation Updates (After Sprint 1)

- [ ] Update `CLAUDE.md` with iteration feature overview
- [ ] Update `app/CLAUDE.md` with service layer changes
- [ ] Update `templates/CLAUDE.md` with new components
- [ ] Update Serena memory `current_development_status`

---

## Known Issues / Future Work

### AI Call Mocking for UI Tests

The current UI tests that submit iteration commands (`test_iteration_form_submission_with_mocked_response`,
`test_multiple_iteration_commands_on_same_draft`) make real AI API calls, which:

- Take 40-60 seconds per call
- Cost real money
- Are unreliable (rate limits, network issues)

**TODO**: Implement test-user detection in the iteration service to return mocked AI responses for user ID 999999,
similar to how other AI operations are mocked for testing. This would allow the UI tests to run quickly and
deterministically without real API calls.

The `seed_iteration_result()` helper in `tests/ui/utils.py` provides a workaround for testing the _display_ of iteration
results by seeding results directly into Redis, but doesn't help with testing the actual form submission flow.

---

_Last Updated: 2025-11-27_
