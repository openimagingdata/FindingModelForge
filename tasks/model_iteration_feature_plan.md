# Model Iteration Feature - Implementation Plan

**Status**: Planning - Under Review
**Created**: 2025-10-29
**Last Updated**: 2025-11-25
**Branch**: `feature/model-editing`

---

## Feature Overview

Add capability for users to create **iterations** of existing published finding models through AI-assisted editing.

### Iteration Methods

1. **Natural Language Iteration** (Sprint 1 - MVP): User submits text prompts describing desired changes
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

| Sprint | Focus | Scope |
|--------|-------|-------|
| **Sprint 1** | MVP - Natural Language | Core iteration with NL editing |
| **Sprint 2** | Markdown Edit | Export/edit/apply markdown workflow |
| **Sprint 3** | Enhanced History | Timeline UI, structured history model |

---

# Sprint 1: MVP - Natural Language Iteration

**Goal**: Working iteration feature for test users with natural language editing only.

**Scope**:
- Create iteration from published model
- Natural language change requests
- Display changes/rejections
- Use existing draft submission workflow
- Simple UI (no tabs)

---

## Sprint 1 Architecture Decisions

### Simplified Data Model

Add only two fields to `FindingModelDraft`:

```python
# In app/models.py
class FindingModelDraft(BaseModel):
    # ... existing fields ...

    # Iteration tracking
    is_iteration: bool = False
    base_model_id: str | None = None  # oifm_id of model being iterated
```

**MVP Decision**: Use existing `action_log` for iteration history. Log entries with action types `iteration.applied` or `iteration.failed` store user input, changes, rejections.

### Service Layer Approach

Extend `DraftService` with iteration methods (follows existing patterns in `app/services/draft_service.py`).

---

## Sprint 1, Phase 1: Data Model

### Tasks

- [ ] Add `is_iteration: bool = False` to `FindingModelDraft`
- [ ] Add `base_model_id: str | None = None` to `FindingModelDraft`
- [ ] **Unit test**: Verify serialization with new fields
- [ ] **Unit test**: Verify defaults for existing drafts

---

## Sprint 1, Phase 2: Backend

### Tasks

#### DraftRepo (app/database.py)

- [ ] Add `get_iteration_draft(user_id: int, base_model_id: str) -> FindingModelDraft | None`
- [ ] Modify `save_draft()` to accept `is_iteration` and `base_model_id` parameters
- [ ] Add `update_generated_json(draft_id: str, json: str)` helper method
- [ ] **Unit test**: `test_get_iteration_draft_returns_existing`
- [ ] **Unit test**: `test_get_iteration_draft_returns_none_when_not_found`

#### DraftService (app/services/draft_service.py)

- [ ] Add `start_iteration(user_id, user, base_model) -> FindingModelDraft`
- [ ] Add `apply_natural_language_iteration(draft_id, user_id, command) -> dict`
- [ ] **Unit test**: `test_start_iteration_creates_new_draft`
- [ ] **Unit test**: `test_start_iteration_returns_existing`
- [ ] **Unit test**: `test_apply_iteration_success` (mock AI)
- [ ] **Unit test**: `test_apply_iteration_with_rejections` (mock AI)
- [ ] **Unit test**: `test_apply_iteration_logs_to_action_log`

#### Implementation Notes

The service methods follow existing patterns in `DraftService`:
- Use `self.draft_repo` for database operations
- Log errors with `logger.error()`
- Return dict with `success`, `changes`, `rejections`, `error` keys

---

## Sprint 1, Phase 3: Endpoints

### Tasks

#### Entry Point (app/routers/finding_models_browse.py)

- [ ] Add `POST /{slug}/iterate` endpoint
- [ ] **Integration test**: `test_start_iteration_creates_draft`
- [ ] **Integration test**: `test_start_iteration_redirects_to_draft`

#### Iteration Endpoint (app/routers/drafts/workflows.py)

- [ ] Add `POST /{draft_id}/iterate` endpoint
- [ ] **Integration test**: `test_iterate_endpoint_applies_changes`
- [ ] **Integration test**: `test_iterate_endpoint_requires_auth`
- [ ] **Integration test**: `test_iterate_non_iteration_draft_fails`

#### View Modification (app/routers/drafts/views.py)

- [ ] Modify `get_draft_page` to fetch `base_model_slug` for iterations
- [ ] Pass `base_model_slug` to template context

### Implementation Notes

Follow existing patterns in `workflows.py`:
- Use `CurrentUserDep`, `DraftServiceDep` from `app.dependencies`
- Return `templates.TemplateResponse()` for HTMX partials
- Use `Form(...)` for form field extraction

---

## Sprint 1, Phase 4: UI

### Tasks

#### Entry Button (templates/finding_models/detail.html)

- [ ] Add "Create Iteration" form/button for authenticated users
- [ ] **Playwright test**: `test_iterate_button_visible_for_authenticated_user`
- [ ] **Playwright test**: `test_iterate_button_creates_draft_and_redirects`

#### New Macros (templates/macros/iteration_components.html)

- [ ] Create `iteration_banner(model_name, base_model_slug)` macro
- [ ] Create `htmx_spinner(id, text)` macro (or reuse existing if available)

#### Draft Page Modification (templates/drafts/edit.html or unified template)

- [ ] Add conditional for `draft.is_iteration`
- [ ] Include iteration banner for iteration drafts
- [ ] Include iteration form component

#### Iteration Form (templates/components/iteration_form.html)

- [ ] Natural language textarea with HTMX submission
- [ ] Result container for changes/rejections
- [ ] JSON preview accordion (reuse `json_accordion` macro)
- [ ] **Playwright test**: `test_iteration_form_submission`
- [ ] **Playwright test**: `test_changes_and_rejections_display`

#### Result Component (templates/components/iteration_result.html)

- [ ] Success state with changes list
- [ ] Rejections in warning style
- [ ] Error state
- [ ] Reuse `error_alert` from `macros/creation_components.html`

### Implementation Notes

All UI must follow project standards:
- Use Flowbite component patterns (see templates/CLAUDE.md)
- Use Alpine.js for any client-side state
- Use existing macros from `templates/macros/`
- Include dark mode classes

---

## Sprint 1 Success Criteria

- [ ] User can click "Create Iteration" on any published model
- [ ] Iteration draft created with `is_iteration=True` and `base_model_id`
- [ ] User can enter natural language request and see changes/rejections
- [ ] Multiple iteration rounds work
- [ ] Iteration drafts can be submitted via existing workflow
- [ ] All existing tests pass
- [ ] New tests pass

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

Iteration drafts cannot be manually edited. The draft editor detects `is_iteration=True` and shows iteration UI instead of the standard form.

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

_Last Updated: 2025-11-25_
