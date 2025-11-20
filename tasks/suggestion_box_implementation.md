# Suggestion Box Feature - Implementation Plan

**Status**: Ready for implementation
**Date**: 2025-11-20

## What We're Building

A simple suggestion feature where any user (authenticated or anonymous) can submit finding model ideas. Accessible via navbar link (all pages) and hero button (home page only). Opens modal, user types suggestion + optional email, submits, modal closes, alert appears on current page.

## User Flow

1. Click "Suggest" → modal opens with empty form
2. Type suggestion (max 300 chars) + optional email
3. Submit or cancel → modal closes, form clears
4. If submitted: success/error alert appears on current page
5. User stays on whatever page they're on (no navigation)

## Key Decisions

### UX
- **Single-line input** (not textarea) - quick suggestion, not detailed proposal
- **300 char limit** (not 2000) - keeps it brief
- **Form clears on close** - no persistence, simple interaction
- **Alert inline** (not toast) - user sees confirmation on current page
- **No navigation** - stay where you are

### Data Model (YAGNI - store minimum)
```
suggestions collection:
- content (str, max 300 chars)
- user_id (int | null)
- submitter_email (str | null)
- created_at (datetime)
```

**Not storing**: status, notes, processed_at, processed_by, submitter_name
**Rationale**: Add admin fields later when we build the admin interface. For now, just collect suggestions.

### Tech Approach
- **HTMX**: Form posts to `/suggestions`, targets `#alert-container`, swaps innerHTML
- **Modal**: Global in base.html (available all pages), Flowbite `data-modal-toggle`
- **Alert**: Flowbite dismissible alert, backend returns rendered HTML
- **Validation**: Alpine.js for character counter + disabled state, Pydantic for email format

## Implementation Details

### Backend

**1. models.py** - Add two Pydantic models:
```python
class SuggestionCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=300)
    submitter_email: EmailStr | None = None

class Suggestion(BaseModel):
    id: str = Field(alias="_id")
    content: str
    user_id: int | None = None
    submitter_email: str | None = None
    created_at: datetime
    model_config = ConfigDict(populate_by_name=True)
```

**2. database.py** - Add SuggestionRepo:
```python
class SuggestionRepo:
    def __init__(self, db: AsyncIOMotorDatabase[Any]) -> None:
        self.db = db
        self.collection = db.suggestions

    async def create(
        self,
        content: str,
        user_id: int | None = None,
        submitter_email: str | None = None,
    ) -> str:
        """Create suggestion. Returns ID."""
        doc = {
            "content": content,
            "user_id": user_id,
            "submitter_email": submitter_email,
            "created_at": datetime.now(UTC),
        }
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)
```

Also update `Database` class:
- Add `suggestion_repo: SuggestionRepo | None = None` to `__init__`
- In `connect()`: `self.suggestion_repo = SuggestionRepo(self.db)`
- In `connect()`: `await self.db.suggestions.create_index([("created_at", -1)])`

**3. dependencies.py** - Add dependency:
```python
async def get_suggestion_repo(request: Request) -> SuggestionRepo:
    return request.app.state.database.suggestion_repo

SuggestionRepoDep = Annotated[SuggestionRepo, Depends(get_suggestion_repo)]
```

**4. home.py** - Add endpoint with this flow:
```python
@router.post("/suggestions", response_class=HTMLResponse)
async def submit_suggestion(
    request: Request,
    current_user: OptionalUserDep,
    suggestion_repo: SuggestionRepoDep,
    content: str = Form(..., min_length=1, max_length=300),
    submitter_email: str | None = Form(None),
) -> HTMLResponse:
    # Validate email if provided
    # Determine user_id and email based on auth state
    # Save: await suggestion_repo.create(content, user_id, email)
    # Return alert template with success=True/False
```

Key logic:
- `user_id = current_user.id if current_user else None`
- `email = submitter_email or (current_user.email if current_user else None)`
- Return `templates.TemplateResponse("components/suggestion_alert.html", {"success": bool, "message": str})`

### Frontend

**5. base.html** - Add two things:

After navbar, add alert container:
```html
<div id="alert-container" class="container mx-auto px-4 pt-4"></div>
```

Before `</body>`, add global modal:
```html
<div id="suggestion-modal" tabindex="-1" aria-hidden="true" class="hidden ...">
  <!-- Standard Flowbite modal structure -->
  <div class="p-4 md:p-5">
    {% include 'components/suggestion_form.html' %}
  </div>
</div>
```

**6. suggestion_form.html** - Form with HTMX + Alpine.js:
```html
<form hx-post="/suggestions"
      hx-target="#alert-container"
      hx-swap="innerHTML"
      x-data="{
          content: '',
          get contentLength() { return this.content.length; },
          get canSubmit() { return this.content.trim().length >= 1 && this.content.length <= 300; }
      }">

  <!-- Single-line input with character counter -->
  <input type="text" name="content" x-model="content" maxlength="300" required>
  <p><span x-text="contentLength"></span>/300 characters</p>

  <!-- Conditional email field -->
  {% if not user %}
    <input type="email" name="submitter_email" placeholder="you@example.com">
  {% else %}
    <p>Submitting as {{ user.name or user.login }}
       {% if user.email %} — we'll notify you at {{ user.email }}{% endif %}
    </p>
  {% endif %}

  <!-- Submit button with modal close -->
  <button type="submit" :disabled="!canSubmit" data-modal-hide="suggestion-modal">
    Submit Suggestion
  </button>
</form>
```

**7. suggestion_alert.html** - Flowbite dismissible alert:
```html
{% if success %}
  <div id="suggestion-alert" class="... bg-green-50 text-green-800 ...">
    <svg>...</svg>
    <div>{{ message }}</div>
    <button data-dismiss-target="#suggestion-alert">×</button>
  </div>
{% else %}
  <div id="suggestion-alert" class="... bg-red-50 text-red-800 ...">
    <!-- Same structure, different colors -->
  </div>
{% endif %}
```

**8. navbar.html** - Add link to desktop + mobile nav:
```html
<!-- After "Finding Models" link -->
<a href="#" data-modal-target="suggestion-modal" data-modal-toggle="suggestion-modal">
  <svg><!-- lightbulb icon --></svg>
  Suggest
</a>
```

**9. index.html** - Add outline button to hero CTA section:
```html
<button type="button"
        data-modal-target="suggestion-modal"
        data-modal-toggle="suggestion-modal"
        class="... border-2 border-primary-600 text-primary-600 ...">
  <svg><!-- lightbulb icon --></svg>
  Suggest a Finding Model
</button>
```

### Testing

**10. tests/unit/test_suggestion_repo.py** - Repository tests:
- Test `create()` with authenticated user (verify user_id populated, email from session)
- Test `create()` with anonymous user + email (verify user_id=None, email from form)
- Test `create()` with anonymous user without email (verify both None)
- Verify document has exactly 4 fields: content, user_id, submitter_email, created_at
- Verify no extra fields (no status, notes, etc.)

**11. tests/test_suggestions.py** - Endpoint integration tests:
- Test POST as authenticated user (user_id + email populated from session)
- Test POST as anonymous with email (user_id=None, email from form)
- Test POST as anonymous without email (both None)
- Test invalid email format (returns error alert HTML)
- Test content validation (empty = error, >300 chars = error, valid = success)
- Test alert HTML structure (verify success/error context passed correctly)
- Verify suggestion stored in database with correct field values

**12. tests/ui/test_suggestion_box.py** - UI workflow tests:
- Test "Suggest" link visible in navbar on home page
- Test "Suggest" link visible in navbar on other pages (e.g., /finding-models)
- Test hero button visible on home page
- Test clicking navbar link opens modal
- Test clicking hero button opens modal
- Test form shows email input for anonymous users
- Test form shows user info (no email input) for authenticated users
- Test character counter updates as user types
- Test submit button disabled when content empty
- Test submit button disabled when content > 300 chars
- Test modal closes after submit
- Test user stays on current page (no navigation)
- Test alert appears in #alert-container
- Test alert is dismissible with close button
- Test form clears when modal reopens after submission
- Use `wait_for_htmx_settled()` for HTMX interactions

## Files to Change

**Backend (5 files)**:
- app/models.py
- app/database.py
- app/dependencies.py
- app/routers/home.py
- (new) tests/unit/test_suggestion_repo.py
- (new) tests/test_suggestions.py

**Frontend (4 files)**:
- templates/base.html
- templates/components/navbar.html
- templates/index.html
- (new) templates/components/suggestion_form.html
- (new) templates/components/suggestion_alert.html
- (new) tests/ui/test_suggestion_box.py

## Technical Notes

### HTMX Integration
- Form: `hx-post="/suggestions"` + `hx-target="#alert-container"` + `hx-swap="innerHTML"`
- On submit: HTMX posts form data, replaces alert container content with response HTML
- Modal close: `data-modal-hide="suggestion-modal"` on submit button (Flowbite handles this)
- No custom JavaScript needed - HTMX + Flowbite handle the entire flow

### Authentication Handling
- Use `OptionalUserDep` in endpoint (allows both auth states)
- For authenticated: email pulled from `current_user.email`, no form field needed
- For anonymous: optional email input in form
- Logic: `email = submitter_email or (current_user.email if current_user else None)`

### Form State Management
- Form clears automatically when modal closes (browser default behavior)
- No persistence - each modal open starts with empty form (except user info display)
- Alpine.js reactive state (`content`, `contentLength`, `canSubmit`) resets when modal reopens

### Alert Display
- HTMX targets `#alert-container` (global div in base.html)
- Alert appears on whatever page user is currently on
- User doesn't navigate away - stays on same page
- Alert is dismissible via Flowbite's `data-dismiss-target="#suggestion-alert"`
- Backend returns rendered alert HTML with `success` and `message` context

### Validation Strategy
**Client-side** (Alpine.js):
- Reactive character counter: `<span x-text="contentLength"></span>/300`
- Submit button disabled when invalid: `:disabled="!canSubmit"`
- Prevents submission of empty or too-long content

**Server-side** (Pydantic + custom):
- `content: str = Form(..., min_length=1, max_length=300)`
- `submitter_email: EmailStr | None = None` (validates format if provided)
- Custom check: `EmailStr._validate(submitter_email)` with try/except for friendly error

## What We're NOT Building (Yet)

- Status tracking (pending/reviewed/accepted/rejected)
- Admin interface to review suggestions
- Email notifications
- Rate limiting
- Duplicate detection
- Name field for anonymous users (just email is enough)

Add these when we need them, not before.

## Why This Approach is Simple

**YAGNI applied**:
- Store only 4 fields (content, user_id, submitter_email, created_at)
- No status tracking, no admin fields, no submitter_name
- Add those when we build the admin interface, not before

**Standard patterns**:
- HTMX for form submission (existing pattern)
- Flowbite components (modal, alert, form inputs)
- Alpine.js for reactivity (character counter, validation)
- Repository pattern (matches DraftRepo, CommentRepo)
- OptionalUserDep (allows both auth states)

**No custom code**:
- No custom JavaScript event listeners
- No special HTMX headers or events
- No complex state management
- Browser + Flowbite + HTMX handle everything

**Total implementation**: ~250 lines of code across 12 files

## Success Criteria

- [ ] Any user can submit suggestion from any page
- [ ] Authenticated users don't need to enter email
- [ ] Anonymous users can optionally provide email
- [ ] Modal closes and form clears after submit
- [ ] Success/error alert appears on current page
- [ ] User stays on current page (no navigation)
- [ ] All tests pass (unit + integration + UI)
- [ ] Database stores exactly 4 fields, no more
