# Backend Complexity Assessment

> **Note**: This is an ASSESSMENT document identifying problems and their severity.
> For the detailed implementation plan, see [`service_layer_completion_plan.md`](service_layer_completion_plan.md).

## Executive Summary

After analyzing the backend router and service structure, I've identified several areas where complexity has accumulated. While the previous refactoring (router_cleanup.md) successfully broke up monolithic files, **business logic is still leaking into routers** and there's **significant code duplication** in HTMX response handling.

### Relationship to Previous Work

The `tasks/done/router_cleanup.md` effort (completed October 2025) achieved:
- ✅ Breaking up monolithic files (`pages.py` 539→49 lines, `finding_models.py` deleted)
- ✅ Creating service layer (`CreationService`, `DraftService`, `FindingModelService`)
- ✅ Clean file structure with focused routers

**What remained incomplete:**
- ❌ Business logic still in routers (this assessment addresses this)
- ❌ HTMX response patterns not standardized
- ❌ Services don't provide complete context objects for templates

---

## Current State

### Line Counts by Module

| Module | Lines | Purpose |
|--------|-------|---------|
| `app/routers/creation.py` | 407 | Creation workflow |
| `app/routers/drafts/helpers.py` | 448 | Draft helper functions |
| `app/routers/finding_models_browse.py` | 338 | Browse/detail views |
| `app/routers/drafts/views.py` | 261 | Draft view endpoints |
| `app/routers/drafts/mutations.py` | 248 | Draft CRUD operations |
| `app/services/draft_service.py` | 295 | Draft business logic |
| `app/services/creation_service.py` | 225 | Creation business logic |
| `app/services/finding_model_service.py` | 187 | Model browsing logic |
| **Total** | ~2,400+ | Core backend |

### Architecture Assessment

```
Current Flow (problematic):
┌─────────────────────────────────────────────────────────────┐
│ Routers (creation.py, drafts/*.py, finding_models_browse.py)│
│ • HTTP concerns ✓                                           │
│ • Business logic ✗ (should be in services)                  │
│ • HTMX response building ✗ (duplicated)                     │
│ • Session management ✗ (scattered)                          │
│ • Template rendering ✗ (complex)                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Services (draft_service.py, creation_service.py, etc.)      │
│ • Core business logic ✓                                     │
│ • Repository coordination ✓                                 │
│ • Comment delegation ✓                                      │
│ • BUT: Some logic still in routers ✗                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Complexity Hotspots (Ranked by Severity)

### 1. `finding_models_browse.py` - HIGHEST PRIORITY

**Severity: HIGH | Effort: MEDIUM**

**Problem**: The `finding_models()` function is 220 lines handling:
- HTMX vs full-page request branching
- List view rendering with pagination
- Detail view rendering with comments
- URL building for browser history
- Error handling with fallbacks
- Context building duplication (list context built twice)

**Code Smell**: Same pagination calculation logic appears twice:
```python
# Lines 79-95 (HTMX branch)
total_pages = max(1, (total_count + per_page - 1) // per_page)
page_range = list(range(start_page, end_page + 1))
...

# Lines 193-209 (full-page branch)
total_pages = max(1, (total_count + per_page - 1) // per_page)
page_range = list(range(start_page, end_page + 1))
...
```

**Recommended Fix**: Extract into `FindingModelService`:
- `prepare_list_context(search, page, per_page)` - returns complete pagination context
- `prepare_detail_context(slug)` - returns model + thread + metadata
- Router becomes thin controller (~50 lines)

---

### 2. `creation.py` - HIGH PRIORITY

**Severity: HIGH | Effort: MEDIUM**

**Problem**: `process_step_1()` and `process_step_2()` are 97 and 77 lines respectively, with:
- Complex draft resume logic (4 different paths)
- Session management mixed with business logic
- AI generation coordination
- Form validation handling

**Code Smells**:
1. Draft lookup/resume logic duplicated between steps
2. Session update patterns repeated throughout
3. Redirect decision logic embedded in router

**Example from `process_step_1()` (lines 111-155)**:
```python
# Draft lookup
draft = await draft_repo.find_editable_by_name(user_id=current_user.id, name=name)
if draft is not None:
    # Session setup (8 lines)
    session.name = draft.name
    session.description = draft.inputs.description
    ...
    return RedirectResponse(url=f"/drafts/{draft.id}?mode=edit", status_code=303)

# Submitted draft lookup (same pattern, 15 more lines)
latest = await draft_repo.find_latest_by_name(...)
if latest is not None and latest.status == "submitted":
    # Session setup (10 lines)
    ...
    return RedirectResponse(...)
```

**Recommended Fix**: Merge into `CreationService`:
- `resolve_name_input(user_id, name) -> WorkflowDecision` - determines path
- `setup_session_from_draft(session, draft)` - populates session
- Router just handles HTTP response based on decision

---

### 3. `drafts/helpers.py` - MEDIUM-HIGH PRIORITY

**Severity: MEDIUM-HIGH | Effort: LOW-MEDIUM**

**Problem**: 448 lines of helper functions that are really **business logic in disguise**:

| Function | Lines | Issue |
|----------|-------|-------|
| `build_htmx_response_with_oob()` | 60 | Response building logic |
| `render_draft_preview_content()` | 40 | Template logic |
| `generate_finding_model_json()` | 55 | **Business logic** (should be in service) |
| `should_regenerate_model()` | 15 | **Business logic** |

**Code Smell**: `generate_finding_model_json()` contains core domain logic:
```python
async def generate_finding_model_json(
    draft: FindingModelDraftDocument,
    creation_service: CreationService,
    user: User,
) -> str | None:
    """Generate the finding model JSON from draft inputs."""
    if not draft.inputs:
        return None
    inputs = FindingModelInputs(...)
    json_data = await creation_service.generate_from_inputs(...)
    return json_data
```

This is **business logic** masquerading as a "helper". It should be in `DraftService`.

**Recommended Fix**:
- Move `generate_finding_model_json()` and `should_regenerate_model()` to `DraftService`
- Move HTMX response building to `HTMXResponseService`
- Keep only pure presentation helpers in `helpers.py` (~100 lines max)

---

### 4. `drafts/views.py` - MEDIUM PRIORITY

**Severity: MEDIUM | Effort: LOW**

**Problem**: `unified_draft_page()` at 123 lines handles too many concerns:
- Permission checking
- Mode validation
- Comment thread fetching
- HTMX vs full-page branching
- Error handling for multiple failure modes

**The function has 5 different return paths:**
1. Redirect to edit mode (no generated JSON)
2. HTMX edit content
3. HTMX preview content with OOB
4. Full page render
5. Error response

**Recommended Fix**: Extend `DraftService`:
- `prepare_view_context(draft_id, user_id, mode) -> DraftViewContext`
- Returns everything needed: draft, author, permissions, comments, resolved mode

---

### 5. `drafts/mutations.py` - LOWER PRIORITY

**Severity: MEDIUM | Effort: LOW**

**Problem**: `save_draft()` at 85 lines is doing validation, session management, and business logic:

```python
# Lines 44-48: Validation logic
if len(new_description.strip()) < 10 or len(new_attributes.strip()) < 20:
    raise HTTPException(status_code=422, detail="Description or attributes are too short")
```

This validation should be in the service layer, not the router.

**Recommended Fix**: Move validation to `DraftService.save_draft()` and let it raise `ValidationError`.

---

## Decisions Made (November 2025)

Based on discussion, the following architectural decisions have been made:

1. **Merge CreationWorkflowService into CreationService** - No justification for separate services; workflow orchestration is part of the creation domain.

2. **HTMX response patterns → `HTMXResponseService`** - These are stateful and coordinate concerns (OOB swaps, URL building, header management). That's a service pattern, not a utility.

3. **Validation stays in services** - Centralized, testable, single source of truth.

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Max router function length | 220 lines | <80 lines |
| Business logic in routers | ~40% | 0% |
| Code duplication (pagination) | 2 copies | 1 copy |
| Test coverage | 81% | 85%+ |
| Helpers with business logic | 3 functions | 0 functions |

---

## Next Steps

See [`service_layer_completion_plan.md`](service_layer_completion_plan.md) for the detailed implementation plan.
