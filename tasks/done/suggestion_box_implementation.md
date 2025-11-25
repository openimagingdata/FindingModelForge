# Suggestion Box Feature - Final Implementation Record

**Status**: ✅ COMPLETED
**Implementation Date**: 2025-11-20 to 2025-11-23
**Last Updated**: 2025-11-25 (post-implementation review)

## What We Built

A simple suggestion feature where any user (authenticated or anonymous) can submit finding model ideas. Accessible via navbar link (all pages) and hero button (home page only). Opens modal, user types suggestion + optional email, submits, modal closes, alert appears on current page.

## User Flow

1. Click "Suggest" → modal opens with empty form, input auto-focused
2. Type suggestion (max 300 chars) + optional email
3. Submit → modal closes, form state persists (Alpine.js behavior)
4. Success/error toast alert appears in top-right corner
5. User stays on current page (no navigation)

## Key Design Decisions

### UX Decisions
- **Single-line input** (not textarea) - quick suggestion, not detailed proposal
- **300 char limit** - enforced via `maxlength` attribute (browser prevents over-typing)
- **No character counter** - `maxlength` provides sufficient feedback, counter was unnecessary clutter
- **Auto-focus on open** - input automatically focused when modal opens
- **Form state persists** - if user closes modal accidentally, their input is preserved
- **Toast notification** - success/error appears in fixed top-right position with smooth animation
- **No navigation** - user stays on whatever page they're on

### Data Model (YAGNI Applied)
```
suggestions collection:
- content (str, max 300 chars)
- user_id (int | null)
- submitter_email (str | null)
- created_at (datetime)
```

**Not storing**: status, notes, processed_at, processed_by, submitter_name
**Rationale**: Add admin fields later when we build the admin interface. For now, just collect suggestions.

### Tech Stack Usage
- **HTMX**: Form posts to `/suggestions`, targets `#alert-container`, swaps innerHTML
- **Flowbite**: Modal with `data-modal-toggle` triggers, standard styling
- **Alpine.js**: Form validation, toast animation (x-transition), auto-focus via MutationObserver
- **No custom JavaScript in main.js** - all interactivity handled declaratively

---

## Actual Implementation

### Backend

#### 1. Repository: `app/database.py` (lines 675-697)

```python
class SuggestionRepo:
    """Suggestion repository for MongoDB operations."""

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
        from datetime import UTC, datetime

        doc = {
            "content": content,
            "user_id": user_id,
            "submitter_email": submitter_email,
            "created_at": datetime.now(UTC),
        }
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)
```

#### 2. Dependency: `app/dependencies.py` (lines 64-71)

```python
def get_suggestion_repo(database: DatabaseDep) -> SuggestionRepo:
    """Get SuggestionRepo instance from the database."""
    if database.suggestion_repo is None:
        raise RuntimeError("Database not initialized or SuggestionRepo not available")
    return database.suggestion_repo

SuggestionRepoDep = Annotated[SuggestionRepo, Depends(get_suggestion_repo)]
```

#### 3. Endpoint: `app/routers/home.py` (lines 30-92)

```python
@router.post("/suggestions", response_class=HTMLResponse)
async def submit_suggestion(
    request: Request,
    current_user: OptionalUserDep,
    suggestion_repo: SuggestionRepoDep,
    content: str = Form(..., min_length=1, max_length=300),
    submitter_email: str | None = Form(None),
) -> HTMLResponse:
    """Submit a suggestion from authenticated or anonymous user."""
    # Validate email format if provided (using Pydantic's validate_email)
    # Determine user_id and email based on auth state
    # Save via suggestion_repo.create()
    # Return rendered alert template with success/error message
```

**Note**: Pydantic models (`SuggestionCreate`, `Suggestion`) were not created - the repo works directly with dicts, which is simpler for this use case.

### Frontend

#### 4. Alert Container: `templates/base.html` (line 47)

```html
<!-- Toast Notification Container - Fixed top-right, works on any page -->
<div id="alert-container" class="fixed top-28 right-8 z-50 w-full max-w-xs"></div>
```

#### 5. Modal with Alpine.js Auto-Focus: `templates/base.html` (lines 66-82)

```html
<div id="suggestion-modal"
     tabindex="-1"
     aria-hidden="true"
     class="hidden overflow-y-auto overflow-x-hidden fixed top-0 right-0 left-0 z-50 ..."
     x-data="{ isOpen: false }"
     x-init="$watch('isOpen', value => { if (value) $nextTick(() => document.getElementById('suggestion-content')?.focus()) });
             new MutationObserver(() => { isOpen = !$el.classList.contains('hidden') }).observe($el, { attributes: true, attributeFilter: ['class'] })">
    <!-- Modal content -->
    <div class="p-4 md:p-5">
        {% include 'components/suggestion_form.html' %}
    </div>
</div>
```

**Key pattern**: Uses Alpine.js `$watch` + MutationObserver to detect when Flowbite opens the modal (class change), then auto-focuses the input. This keeps the focus logic co-located with the modal element rather than in a separate JS file.

#### 6. Form: `templates/components/suggestion_form.html`

```html
<form hx-post="/suggestions"
      hx-target="#alert-container"
      hx-swap="innerHTML"
      hx-on::after-request="setTimeout(() => { document.querySelector('[data-modal-hide=suggestion-modal]').click(); }, 100);"
      @submit="setTimeout(() => { content = ''; }, 200);"
      x-data="{
          content: '',
          get canSubmit() { return this.content.trim().length >= 1 && this.content.length <= 300; }
      }"
      class="space-y-4">

    <!-- Single-line input with maxlength (NO character counter) -->
    <input type="text"
           id="suggestion-content"
           name="content"
           x-model="content"
           maxlength="300"
           required
           class="...flowbite classes..."
           placeholder="e.g., Pulmonary embolism, Brain tumor classification">

    <!-- Conditional email field (anonymous only) -->
    {% if not user %}
    <input type="email" name="submitter_email" placeholder="you@example.com">
    {% else %}
    <div class="...info box...">
        Submitting as <strong>{{ user.name or user.login }}</strong>
        {% if user.email %} — we'll notify you at <strong>{{ user.email }}</strong>{% endif %}
    </div>
    {% endif %}

    <!-- Buttons -->
    <button type="button" data-modal-hide="suggestion-modal">Cancel</button>
    <button type="submit" :disabled="!canSubmit">Submit Suggestion</button>
</form>
```

#### 7. Toast Alert: `templates/components/suggestion_alert.html`

```html
<div id="suggestion-alert"
     x-data="{ show: false }"
     x-init="setTimeout(() => show = true, 10)"
     x-show="show"
     x-transition:enter="transition ease-out duration-300"
     x-transition:enter-start="opacity-0 transform -translate-y-2"
     x-transition:enter-end="opacity-100 transform translate-y-0"
     class="flex items-center w-full p-4 text-green-800 bg-green-50 rounded-lg shadow-lg ..."
     role="alert">
    <!-- Icon, message, close button -->
    <button @click="show = false" aria-label="Close">×</button>
</div>
```

**Key pattern**: Animation handled entirely by Alpine.js `x-transition` - no custom JavaScript needed.

#### 8. Navbar Link: `templates/components/navbar.html`

```html
<a href="#" data-modal-target="suggestion-modal" data-modal-toggle="suggestion-modal"
   class="...">
    <svg><!-- lightbulb icon --></svg>
    Suggest
</a>
```

Present in both desktop nav and mobile menu.

#### 9. Hero Button: `templates/index.html` (line 30-35)

```html
<button type="button"
        data-modal-target="suggestion-modal"
        data-modal-toggle="suggestion-modal"
        class="...outline button styles...">
    <svg><!-- lightbulb icon --></svg>
    Suggest
</button>
```

### Testing

#### 10. Unit/Integration Tests: `tests/test_suggestions.py`

**TestSuggestionEndpoint** (with mocked dependencies):
- `test_submit_as_authenticated_user` - verifies user_id + email from session
- `test_submit_as_anonymous_with_email` - verifies user_id=None, email from form
- `test_submit_as_anonymous_without_email` - verifies both None
- `test_invalid_email_format` - verifies error handling
- `test_content_empty_validation` - FastAPI 422 response
- `test_content_too_long_validation` - FastAPI 422 response
- `test_email_validation_accepts_valid_formats` - various valid emails
- `test_email_validation_rejects_invalid_formats` - various invalid emails

**TestSuggestionRepo** (with mocked DB):
- `test_create_authenticated_user` - verifies field structure
- `test_create_anonymous_with_email`
- `test_create_anonymous_without_email`
- `test_create_field_count_validation` - **exactly 4 fields, no more**
- `test_created_at_timestamp` - UTC datetime verification

**TestSuggestionRepoIntegration** (with real MongoDB):
- `test_create_suggestion_in_database`
- `test_create_authenticated_suggestion`
- `test_create_anonymous_with_email`

#### 11. UI Tests: `tests/ui/test_suggestion_box.py`

**TestSuggestionBoxVisibility**:
- `test_navbar_suggest_link_visible_on_home_page`
- `test_navbar_suggest_link_visible_on_finding_models_page`
- `test_hero_button_visible_on_home_page_only`

**TestSuggestionBoxModalOpening**:
- `test_navbar_link_opens_modal`
- `test_hero_button_opens_modal`

**TestSuggestionBoxFormContent**:
- `test_form_shows_email_input_for_anonymous_users`
- `test_form_shows_user_info_for_authenticated_users`

**TestSuggestionBoxReactiveValidation**:
- `test_input_respects_maxlength_attribute`
- `test_submit_button_disabled_when_content_empty`
- `test_submit_button_enabled_at_max_length`
- `test_submit_button_enabled_when_content_valid`

**TestSuggestionBoxSubmissionFlow**:
- `test_modal_closes_and_alert_appears_after_submit`
- `test_user_stays_on_current_page_after_submit`
- `test_alert_has_close_button_with_alpine_interaction`

**TestSuggestionBoxStateManagement**:
- `test_form_state_persists_across_modal_close_reopen`

**TestSuggestionBoxPersistence**:
- `test_suggestion_persisted_to_database` - verifies MongoDB storage

---

## Files Changed

**Backend (4 files)**:
- `app/database.py` - Added `SuggestionRepo` class
- `app/dependencies.py` - Added `SuggestionRepoDep` dependency
- `app/routers/home.py` - Added `POST /suggestions` endpoint
- `app/models.py` - (No changes - repo uses dicts directly)

**Frontend (5 files)**:
- `templates/base.html` - Added `#alert-container` and `#suggestion-modal`
- `templates/components/navbar.html` - Added "Suggest" links
- `templates/index.html` - Added hero "Suggest" button
- `templates/components/suggestion_form.html` - (new) Form component
- `templates/components/suggestion_alert.html` - (new) Toast component

**Tests (2 files)**:
- `tests/test_suggestions.py` - (new) Unit and integration tests
- `tests/ui/test_suggestion_box.py` - (new) Playwright UI tests

**No changes to `src/js/main.js`** - all JavaScript functionality handled via Alpine.js in templates.

---

## Technical Patterns Used

### Alpine.js for All Interactivity
- **Form validation**: `x-data` with computed `canSubmit` property
- **Toast animation**: `x-transition` directives (no custom JS)
- **Auto-focus**: `$watch` + `$nextTick` + MutationObserver on modal element
- **Alert dismissal**: `@click="show = false"` with `x-show`

### HTMX for Server Interaction
- `hx-post="/suggestions"` - form submission
- `hx-target="#alert-container"` - where to put response
- `hx-swap="innerHTML"` - how to update target
- `hx-on::after-request` - close modal after submission

### Flowbite for Modal
- `data-modal-target` / `data-modal-toggle` - triggers
- `data-modal-hide` - close button
- Standard Flowbite modal HTML structure

### Repository Pattern
- `SuggestionRepo` follows existing `DraftRepo`, `CommentRepo` patterns
- Simple `create()` method, returns ID
- Stores exactly 4 fields (YAGNI)

---

## Success Criteria (All Met)

- [x] Any user can submit suggestion from any page
- [x] Authenticated users don't need to enter email
- [x] Anonymous users can optionally provide email
- [x] Modal closes after submit
- [x] Success/error alert appears as toast notification
- [x] User stays on current page (no navigation)
- [x] Database stores exactly 4 fields, no more
- [x] Auto-focus on modal open
- [x] Smooth animations (Alpine.js x-transition)
- [x] All tests passing

---

## Future Enhancements (Not Built)

- Status tracking (pending/reviewed/accepted/rejected)
- Admin interface to review suggestions
- Email notifications to submitters
- Rate limiting
- Duplicate detection

Add these when needed, not before.
