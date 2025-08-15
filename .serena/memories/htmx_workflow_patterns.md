# HTMX Multi-Step Workflow Patterns

## Overview
The Finding Model creation workflow demonstrates best practices for HTMX-driven multi-step forms with server-side session management and draft autosaving.

## Key Patterns

### 1. Session Management with Draft Support
```python
@dataclass
class FindingModelCreationSession:
    session_id: str
    current_step: int = 1
    name: str | None = None
    description: str | None = None
    synonyms: list[str] = field(default_factory=list)
    similar_models: list[dict] | None = None
    attributes_markdown: str | None = None
    final_model: dict | None = None
    # Draft support fields
    draft_id: str | None = None
    draft_status: str | None = None
    submitted_display_time: str | None = None
    error_message: str | None = None
    success_message: str | None = None
```

- Store session state in Redis with TTL
- Use dependency injection for session retrieval
- Automatic session creation if missing
- **Draft ID tracking for autosave and resume**

### 2. Draft Autosave Pattern (Step 4)
```python
# Autosave on GET request to step 4
if request.method == "GET":
    if session.name and session.attributes_markdown:
        inputs = FindingModelInputs(...)
        draft = await draft_repo.save_draft(
            user_id=current_user.id,
            name=session.name,
            inputs=inputs,
            draft_id=session.draft_id
        )
        session.draft_id = draft.id
```

### 3. Session Adoption from Draft
```python
# Recover session state from draft when session is lost
draft_id = request.query_params.get("draft_id")
if draft_id and not session.attributes_markdown:
    draft = await draft_repo.get_draft(draft_id, current_user.id)
    if draft:
        session.name = draft.name
        session.description = draft.inputs.description
        session.synonyms = draft.inputs.synonyms
        session.attributes_markdown = draft.inputs.attributes_markdown
        session.draft_id = draft.id
```

### 4. Form-Based Draft ID Persistence
```html
<!-- Hidden field to maintain draft_id across form submissions -->
<input type="hidden" name="draft_id" value="{{ session_data.draft_id or '' }}">
```

### 5. Submit and Lock Pattern
```python
@router.post("/drafts/{draft_id}/submit")
async def submit_draft(draft_id: str, ...):
    # Transition from 'draft' to 'submitted' status
    draft = await draft_repo.submit(draft_id, user_id)
    # Drafts with 'submitted' status cannot be edited
```

### 6. Template Consolidation
```python
def render_step_template(
    request: Request,
    step_number: int,
    session: FindingModelCreationSession,
    **extra_context: Any
) -> str:
    """Single helper for rendering all step templates."""
    step_templates = {
        1: "components/finding_model_creation/step_1_enter_name.html",
        2: "components/finding_model_creation/step_2_edit_description.html",
        3: "components/finding_model_creation/step_3_review_similar.html",
        4: "components/finding_model_creation/step_4_edit_attributes.html",
        5: "components/finding_model_creation/step_5_review_model.html",
    }
    context = {"request": request, "current_step": step_number, "session_data": session, **extra_context}
    return templates.get_template(step_templates[step_number]).render(**context)
```

### 7. Smart Workflow Routing
```python
# Step 2: Check similarity and conditionally redirect
if not session.similar_models:
    session.current_step = 4  # Skip step 3
    await session_manager.update_session(session)
    return RedirectResponse(url="/api/finding-models/create/step/4", status_code=303)
else:
    session.current_step = 3  # Show similar models
    await session_manager.update_session(session)
```

### 8. FastAPI Response Types
```python
# ✅ CORRECT: Use Response base class for mixed return types
async def process_step_2(...) -> Response:
    if condition:
        return RedirectResponse(url="...", status_code=303)
    else:
        return HTMLResponse(content=rendered_html)

# ❌ WRONG: Union types with response_model=None
# response_model=None  # This is an anti-pattern
# -> Union[HTMLResponse, RedirectResponse]  # This causes validation errors
```

### 9. Resume from Draft Pattern
```python
@router.post("/drafts/resume")
async def resume_draft(draft_id: str = Form(...)):
    draft = await draft_repo.get_draft(draft_id, user_id)
    if draft:
        # Populate session from draft
        session.name = draft.name
        session.description = draft.inputs.description
        # ... populate other fields
        session.draft_id = draft.id
        # Redirect to appropriate step
        return RedirectResponse(url="/api/finding-models/create/step/4")
```

## Component Reuse

### 1. Template Includes
- `finding_model_complete_display.html` - Full model display with JSON accordion
- `finding_model_display.html` - Formatted display only
- Use `{% include %}` for consistency

### 2. JSON Accordion Pattern
```jinja
{% from 'macros/json_accordion.html' import json_accordion %}
{{ json_accordion(finding_model, "finding-model-json", "JSON Data") }}
```

### 3. Step Template Structure
- Base template: `step_base.html`
- Consistent navigation and styling
- HTMX target: `#step-container`

## Alpine.js and HTMX Integration

### Draft ID Management in Forms
```javascript
// Alpine.js manages draft_id in form data
x-data='{
  draft_id: "{{ session_data.draft_id or "" }}",
  // Other data...
}'

// Hidden input automatically syncs
<input type="hidden" name="draft_id" x-model="draft_id">
```

### HTMX Events for Draft Status
```javascript
// Handle draft save success
@htmx:after-settle="if ($event.detail.xhr.status === 200) { 
  this.draft_saved = true; 
}"
```

## Testing Patterns

### 1. Draft Testing
- Test draft creation and updates
- Test session adoption from drafts
- Test draft submission and locking
- Test draft deletion

### 2. Session Testing
- Mock `FindingModelCreationSession` in tests
- Test session state transitions
- Verify workflow routing logic
- Test draft ID persistence

### 3. HTMX Integration Tests
- Use Playwright for end-to-end workflow testing
- Test step transitions and form submissions
- Verify component reinitialization after HTMX swaps
- Test draft autosave behavior

## Performance Considerations

1. **Session TTL**: Set appropriate expiration for creation sessions
2. **Draft TTL**: Drafts persist longer than sessions for recovery
3. **Template Caching**: Jinja2 templates are cached in production
4. **Component Reuse**: Avoid duplicate code with shared templates
5. **HTMX Swapping**: Minimal DOM updates for better performance
6. **Autosave Debouncing**: Consider debouncing for frequent saves

## Security Notes

1. **Session Isolation**: Each session has unique ID
2. **Draft Ownership**: Drafts are user-scoped via user_id
3. **Form Validation**: Server-side validation with FastAPI Form()
4. **CSRF Protection**: Built into HTMX patterns
5. **Input Sanitization**: Pydantic models handle validation
6. **Draft Status Control**: Only 'draft' status can be edited