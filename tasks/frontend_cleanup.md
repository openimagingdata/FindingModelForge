# Frontend Code Cleanup Plan

**Status**: In Progress (Phase 2.5 next)
**Created**: December 2025
**Updated**: December 2025
**Priority**: High - Maintainability and Consistency

### Progress
- [x] Phase 0: Prerequisites (Profile edit tests) - Completed
- [x] Phase 1: Eliminate Custom JavaScript (`<script>` blocks) - Completed
- [x] Phase 2: Standardize Button Usage - Completed
- [ ] Phase 2.5: Cleanup - Remaining Inline JavaScript (`onclick` handlers)
- [ ] Phase 3: Standardize Badge Usage
- [ ] Phase 4: Consolidate Duplicate Components
- [ ] Phase 5: Final Cleanup and Audit

## Executive Summary

This plan addresses inconsistencies in our frontend code where patterns have drifted from our established standards:

1. **Custom JavaScript** instead of Alpine.js declarative patterns
2. **Ad hoc button styling** instead of using existing `flowbite_button`/`action_button` macros
3. **Ad hoc badge styling** instead of using `flowbite_badge` macro
4. **Duplicate component definitions** that should be consolidated

### Success Criteria (Definition of Done)

The cleanup is complete when ALL of the following are true:

1. **Zero custom JavaScript in templates**:
   ```bash
   grep -rn "<script>" templates/ --include="*.html" | grep -v "main.js"
   # Should return zero results

   grep -rn "onclick=" templates/ --include="*.html"
   # Should return zero results (use Alpine.js @click or HTMX instead)
   ```

2. **All buttons use macros** (no inline button styling):
   ```bash
   grep -rn "class=.*px-[0-9].*py-[0-9].*bg-.*text-white.*rounded" templates/ --include="*.html"
   # Should return zero results (buttons use action_button/flowbite_button)
   ```

3. **All badges use `flowbite_badge` macro**:
   ```bash
   grep -rn "class=.*bg-.*-100.*text-.*-800.*rounded" templates/ --include="*.html" | grep -v flowbite_components
   # Should return zero results (badges use flowbite_badge macro)
   ```

4. **All tests pass**: `task test` shows 100% pass rate

## Critical Rules (MUST READ)

### HTMX Awareness

Every template change must consider:
1. **Does this template get rendered for HTMX requests?** Check for `hx-target`, `hx-swap` pointing to this content
2. **Are there OOB (out-of-band) swaps?** Look for `hx-swap-oob="true"` patterns
3. **Is Flowbite reinitialized?** After HTMX swaps, `initFlowbite()` is called via `main.js`
4. **Is Alpine.js initialized?** After HTMX swaps, `Alpine.initTree(content)` is called

### Alpine.js Patterns

```html
<!-- ✅ CORRECT: Use :class binding for conditional styling -->
<button :class="{ 'bg-primary-600 text-white': isActive, 'bg-white text-gray-700': !isActive }">

<!-- ❌ WRONG: Using JavaScript to manipulate classes -->
<script>
element.className = 'bg-primary-600 text-white';
</script>
```

### Macro Usage

```jinja
{# ✅ CORRECT: Use existing macros #}
{% from "macros/flowbite_components.html" import action_button, flowbite_badge %}
{{ action_button("Submit", type="primary", size="default") }}
{{ flowbite_badge("Draft", color="yellow", size="xs") }}

{# ❌ WRONG: Inline styling #}
<button class="px-4 py-2 bg-blue-600 text-white...">Submit</button>
<span class="bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">Draft</span>
```

---

## Phase 0: Prerequisites (MUST COMPLETE FIRST)

### Task 0.1: Add Profile Edit Tests

**CRITICAL**: There are NO existing UI tests for the profile edit/save workflow. We MUST add tests before refactoring `profile.html` in Task 1.2.

**File**: `tests/ui/test_profile.py`

**Important Template Details** (verified from actual `profile.html`):
- Profile info is inside a **collapsed Flowbite accordion** (`aria-expanded="false"`) - must expand first
- Edit button text is just "Edit" (not "Edit Profile") - located at line 195
- Name input uses `id="full_name"` (not `name='name'`) - line 128
- Organization input has `placeholder="e.g., ACR, RSNA, SIIM"` - line 210
- Save/Cancel buttons are inside the accordion body when in edit mode

**Add this test class**:

```python
class TestProfileEditing:
    """Test profile editing functionality."""

    async def test_profile_edit_mode_toggle(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test toggling between view and edit mode on profile."""
        page, errors, warnings = authenticated_page_with_console
        await navigate_to_profile_page(page)

        # Expand the Profile Information accordion first
        accordion_button = page.locator("[data-accordion-target='#profile-info-accordion-body-1']")
        await expect(accordion_button).to_be_visible(timeout=5000)
        await accordion_button.click()

        # Wait for accordion to expand
        accordion_body = page.locator("#profile-info-accordion-body-1")
        await expect(accordion_body).to_be_visible(timeout=5000)

        # Find and click edit button (text is just "Edit", not "Edit Profile")
        edit_button = page.locator("button:has-text('Edit')")
        await expect(edit_button).to_be_visible(timeout=5000)
        await edit_button.click()

        # Should now see form fields (name input uses id="full_name")
        await expect(page.locator("input#full_name")).to_be_visible()
        await expect(page.locator("button:has-text('Save')")).to_be_visible()
        await expect(page.locator("button:has-text('Cancel')")).to_be_visible()

        await verify_no_console_errors(errors, warnings)

    async def test_profile_organization_add_remove(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test adding and removing organizations."""
        page, errors, warnings = authenticated_page_with_console
        await navigate_to_profile_page(page)

        # Expand accordion and enter edit mode
        await page.locator("[data-accordion-target='#profile-info-accordion-body-1']").click()
        await expect(page.locator("#profile-info-accordion-body-1")).to_be_visible(timeout=5000)
        await page.locator("button:has-text('Edit')").click()
        await expect(page.locator("input#full_name")).to_be_visible()

        # Add organization (placeholder is "e.g., ACR, RSNA, SIIM")
        org_input = page.locator("input[placeholder*='ACR']")
        await org_input.fill("TEST")
        await page.locator("button:has-text('Add')").click()

        # Verify organization badge appears (inside edit mode org list)
        org_badge = page.locator("#profile-info-accordion-body-1 span:has-text('TEST')")
        await expect(org_badge).to_be_visible(timeout=5000)

        # Remove organization (button is inside the badge span)
        remove_button = org_badge.locator("button")
        await remove_button.click()
        await expect(org_badge).to_have_count(0)

        await verify_no_console_errors(errors, warnings)

    async def test_profile_save_success(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test saving profile changes shows success message."""
        page, errors, warnings = authenticated_page_with_console
        await navigate_to_profile_page(page)

        # Expand accordion and enter edit mode
        await page.locator("[data-accordion-target='#profile-info-accordion-body-1']").click()
        await expect(page.locator("#profile-info-accordion-body-1")).to_be_visible(timeout=5000)
        await page.locator("button:has-text('Edit')").click()

        # Make a change (name input uses id="full_name")
        name_input = page.locator("input#full_name")
        await expect(name_input).to_be_visible()
        await name_input.fill("Updated Test Name")

        # Save
        await page.locator("button:has-text('Save')").click()

        # Should see success alert (green styling indicates success)
        # The alert div has class containing 'green' when type='success'
        success_alert = page.locator("[class*='bg-green']")
        await expect(success_alert).to_be_visible(timeout=5000)

        await verify_no_console_errors(errors, warnings)
```

**Verification**:
```bash
# Run profile tests
task test-ui-profile

# All tests must pass before proceeding to Phase 1
```

---

## Phase 1: Eliminate Custom JavaScript (HIGH PRIORITY)

### Task 1.1: Consolidate Draft Editor Routes and Remove Custom JS

**Files**:
- `templates/draft_editor.html` (lines 98-166) - Contains custom JavaScript
- `app/routers/drafts/views.py` (line 65) - Uses `draft_editor.html`

**Current State**:
Two routes serve draft editing:
1. `GET /drafts/{id}/edit` → uses `draft_editor.html` (has custom JS)
2. `GET /drafts/{id}?mode=edit` → uses `draft_unified.html` (Jinja-based, correct)

**Problem**: The `draft_editor.html` has ~70 lines of custom JavaScript for mode toggling that should use server-side Jinja conditionals like `draft_unified.html` does.

**Solution**: Update `draft_editor.html` to use the same pattern as `draft_unified.html`:
1. Remove the `<script>` block entirely (lines 98-166)
2. Replace the mode toggle buttons with the `draft_mode_toggle_header.html` component
3. Keep the template for the `/drafts/{id}/edit` route (it serves direct navigation to edit mode)

**Updated Template Pattern** (similar to `draft_unified.html`):
```jinja
{# Replace mode toggle buttons (lines 48-79) with: #}
{% if draft.generated_json %}
    {% set target_container = '#editor-container' %}
    {% include 'components/draft_mode_toggle_header.html' with context %}
{% endif %}

{# REMOVE the entire <script> block (lines 98-166) #}
{# The mode toggle component handles HTMX navigation server-side #}
```

**HTMX Behavior**:
- Mode toggle buttons use `hx-get` to request the new mode
- Server returns the appropriate partial (`draft_edit_form.html` or `draft_preview.html`)
- `hx-push-url="true"` updates browser URL
- No JavaScript needed - HTMX and server handle everything

**Verification**:
- Navigate to `/drafts/{id}/edit` directly - should work
- Click mode toggle buttons - should switch modes via HTMX
- Run: `task test-ui`

---

### Task 1.2: Refactor `profile.html` Profile Manager

**File**: `templates/profile.html` (lines 384-531)

**Problem**: ~145 lines of custom JavaScript `profileManager()` function with:
- Manual state management
- Custom `saveProfile()` async function
- DOM manipulation for alerts and organizations

**Solution**: Convert to Alpine.js declarative patterns while keeping the API call functionality.

**Reference Pattern** (from existing `unified_form_data.html`):
```html
<div x-data='{
    // State
    profile: {{ profile | tojson }},
    isEditing: false,
    isSaving: false,
    newOrganization: "",
    alert: { show: false, type: "success", message: "" },

    // Computed properties
    get canAddOrganization() {
        return /^[A-Z]{3,4}$/.test(this.newOrganization.toUpperCase());
    },

    // Methods
    addOrganization() {
        const org = this.newOrganization.trim().toUpperCase();
        if (this.canAddOrganization && !this.profile.organizations.includes(org)) {
            this.profile.organizations.push(org);
            this.newOrganization = "";
        }
    },

    removeOrganization(index) {
        this.profile.organizations.splice(index, 1);
    },

    async saveProfile() {
        this.isSaving = true;
        try {
            const response = await fetch("/api/users/profile", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: this.profile.name || null,
                    email: this.profile.email || null,
                    avatar_url: this.profile.avatar_url || null,
                    organizations: this.profile.organizations
                })
            });
            if (response.ok) {
                this.showAlert("success", "Profile updated!");
                this.isEditing = false;
            } else {
                const error = await response.json();
                this.showAlert("error", error.detail || "Update failed");
            }
        } catch (e) {
            this.showAlert("error", "Network error");
        } finally {
            this.isSaving = false;
        }
    },

    showAlert(type, message) {
        this.alert = { show: true, type, message };
        setTimeout(() => this.alert.show = false, 5000);
    }
}'>
```

**Actions**:
1. Move the `profileManager()` logic into inline `x-data` attribute
2. Remove the `<script>` block entirely
3. Use Alpine's `:class` bindings for conditional styling
4. Keep the async fetch for profile save (Alpine supports async methods)

**Button Bindings** (use `:class` for button states):
```html
<button
    type="button"
    @click="saveProfile()"
    :disabled="isSaving"
    :class="{ 'opacity-50 cursor-not-allowed': isSaving }"
    class="inline-flex items-center px-4 py-2 ...">
    <span x-show="isSaving" class="animate-spin ...">...</span>
    <span x-text="isSaving ? 'Saving...' : 'Save Changes'"></span>
</button>
```

**Verification**:
- Profile edit/save workflow still works
- Organizations can be added/removed
- Alert messages appear correctly
- Run: `task test-ui`

### Phase 1 Completion Verification

After completing Tasks 1.1 and 1.2, verify no custom JavaScript remains:

```bash
# Should return ZERO results (no <script> blocks except main.js references)
grep -rn "<script>" templates/ --include="*.html"

# Should return ZERO results (no function definitions)
grep -rn "function\s\+\w\+\s*(" templates/ --include="*.html"
```

---

## Phase 2: Standardize Button Usage

### Task 2.1: Create Button Standards Reference

Create a reference section in `templates/PATTERNS.md` (or update existing) documenting when to use each button type:

| Button Type | Macro | Use Case |
|-------------|-------|----------|
| Navigation Link | `flowbite_button()` | Links to other pages (`<a>` element) |
| Form Submit | `action_button()` | Form submissions (`<button type="submit">`) |
| Action Trigger | `action_button()` | JavaScript actions, modals (`<button type="button">`) |
| Icon Only | `flowbite_icon_button()` | Compact actions in tables/cards |

### Task 2.2: Update `create_workflow_elements.html`

**File**: `templates/macros/create_workflow_elements.html`

**Problem**: `submit_button()` and `back_button()` macros duplicate functionality in `flowbite_components.html`.

**Solution**: Update to use existing macros internally:

```jinja
{% from 'macros/flowbite_components.html' import action_button %}

{# Submit button with HTMX indicator #}
{% macro submit_button(text="Continue", loading_text="Processing...", extra_classes="", disabled=false) %}
{% set spinner_icon %}
<span class="htmx-indicator">
    <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 0 1 4 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
    {{ loading_text }}
</span>
<span>{{ text }}</span>
{% endset %}
<button type="submit"
        class="inline-flex items-center font-medium rounded-lg text-center transition-colors focus:outline-none focus:ring-4 px-5 py-2.5 text-sm text-white bg-blue-700 hover:bg-blue-800 focus:ring-blue-300 dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800 disabled:opacity-50 disabled:cursor-not-allowed {{ extra_classes }}"
        {% if disabled %}disabled{% endif %}>
    {{ spinner_icon|safe }}
</button>
{% endmacro %}
```

**Note**: Keep the HTMX indicator pattern (`htmx-indicator` class) - this is intentional.

### Task 2.3: Update Creation Workflow Steps

**Files**:
- `templates/components/finding_model_creation/step_1_enter_name.html`
- `templates/components/finding_model_creation/step_2_edit_description.html`
- `templates/components/finding_model_creation/step_3_review_overlap.html`

**Action**: Replace inline button styling with macros:

**Before**:
```html
<button type="submit"
        :disabled="!canSubmit"
        :class="{'opacity-50 cursor-not-allowed': !canSubmit}"
        class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed">
```

**After**:
```jinja
{% from "macros/create_workflow_elements.html" import submit_button %}
{{ submit_button(text="Generate Description", loading_text="Generating...", extra_classes=":disabled='!canSubmit' :class=\"{'opacity-50 cursor-not-allowed': !canSubmit}\"") }}
```

**IMPORTANT**: The Alpine.js bindings (`:disabled`, `:class`) must be preserved for form validation integration!

### Task 2.4: Update Draft Components

**Files**:
- `templates/components/drafts/save_result.html`
- `templates/components/drafts/delete_result.html`
- `templates/components/draft_edit_form.html`
- `templates/components/draft_preview_content.html`

**Action for `save_result.html`** (lines 9-22):

**Before**:
```html
<button hx-post="/drafts/{{ draft.id }}/submit" ...
        class="px-3 py-1 text-xs rounded bg-green-600 hover:bg-green-700 text-white">
    Submit for review
</button>
```

**After**:
```jinja
{% from "macros/flowbite_components.html" import action_button %}
{{ action_button(
    text="Submit for review",
    type="success",
    size="xs",
    attributes='hx-post="/drafts/' ~ draft.id ~ '/submit" hx-target="#draft-actions" hx-swap="outerHTML"'
) }}
```

**HTMX Note**: These buttons use `hx-post`, `hx-target`, `hx-swap` - preserve these attributes via the `attributes` parameter.

---

## Phase 2.5: Cleanup - Remaining Inline JavaScript

*Added during implementation when reviewer discovered pre-existing `onclick` handlers not covered by Phase 1.*

### Task 2.5.1: Convert Table Row Navigation

**File**: `templates/drafts_table.html` (line 29)

**Problem**: Uses inline `onclick` for row navigation instead of proper link or HTMX pattern.

**Current**:
```html
<tr onclick="window.location.href='/drafts/{{ draft.id }}?from=public'" ...>
```

**Solution**: Convert to HTMX navigation pattern or wrap content in `<a>` tag.

**Option A - HTMX approach** (recommended):
```html
<tr hx-get="/drafts/{{ draft.id }}?from=public"
    hx-target="#main-content"
    hx-push-url="true"
    class="... cursor-pointer">
```

**Option B - Anchor wrapper**:
```html
<tr class="...">
    <td colspan="4">
        <a href="/drafts/{{ draft.id }}?from=public" class="block w-full">
            <!-- Row content restructured as flex -->
        </a>
    </td>
</tr>
```

### Task 2.5.2: Convert JSON Accordion Buttons

**File**: `templates/macros/json_accordion.html` (lines 44, 52)

**Problem**: Uses inline `onclick` handlers to call global functions from `main.js`.

**Current**:
```html
<button onclick="downloadJSON(`{{ finding_model.model_dump_json(...) }}`, '{{ filename }}')" ...>
<button onclick="copyToClipboard(`{{ finding_model.model_dump_json(...) }}`)" ...>
```

**Solution**: Convert to Alpine.js with `@click` directives.

**Updated pattern**:
```html
<div x-data="{ jsonData: `{{ finding_model.model_dump_json(indent=2, exclude_none=True) | replace('`', '\\`') }}` }">
    <!-- Download button -->
    <button type="button"
            @click="downloadJSON(jsonData, '{{ finding_model.name | replace(' ', '_') | lower }}.fm.json')"
            class="...">
        Download
    </button>

    <!-- Copy button -->
    <button type="button"
            @click="copyToClipboard(jsonData)"
            class="...">
        Copy
    </button>
</div>
```

**Note**: The `downloadJSON()` and `copyToClipboard()` functions remain in `main.js` as global utilities. The change is using Alpine.js `@click` instead of inline `onclick` handlers.

### Phase 2.5 Verification

```bash
# Should return ZERO results after completion
grep -rn "onclick=" templates/ --include="*.html"
```

---

## Phase 3: Standardize Badge Usage

### Task 3.1: Update Draft Result Fragments

**Files**:
- `templates/components/drafts/save_result.html`
- `templates/components/drafts/submit_result.html`
- `templates/components/drafts/delete_result.html`

**Before** (`save_result.html` line 3):
```html
<span class="inline-flex items-center gap-1 rounded-md bg-blue-100 px-2 py-1 text-sm font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-200">
    Saved draft
</span>
```

**After**:
```jinja
{% from "macros/flowbite_components.html" import flowbite_badge %}
{{ flowbite_badge("Saved draft", color="blue", size="sm") }}
```

### Task 3.2: Update Profile Draft Cards

**File**: `templates/profile.html` (lines 317-324)

**Before**:
```html
<span class="px-2 py-0.5 rounded text-[10px] bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">{{ a }}</span>
```

**After**:
```jinja
{{ flowbite_badge(a, color="blue", size="xs") }}
```

**Note**: The `text-[10px]` is a non-standard size. Use `size="xs"` which gives `text-xs` (12px).

### Task 3.3: Review Synonym Manager Badge

**File**: `templates/macros/synonym_manager.html` (line 12)

The current styling is close to Flowbite but not identical. This is acceptable because it's a **removable badge** with close button - Flowbite supports this pattern. Document this as intentional deviation if kept.

---

## Phase 4: Consolidate Duplicate Components

### Task 4.1: Consolidate Form Input Macros

**Current State**:
- `macros/flowbite_components.html`: `form_input()`, `form_textarea()`
- `macros/form_validation.html`: `validated_input()`, `validated_textarea()`
- `macros/create_workflow_elements.html`: `input_field()`, `textarea_field()`

**Files importing from `create_workflow_elements.html`**:
- `step_1_enter_name.html`: imports `htmx_form`, `submit_button`, `status_indicator`
- `step_2_edit_description.html`: imports `input_field`, `navigation_buttons`
- `step_3_review_overlap.html`: imports `back_button`, `submit_button`

**Decision**: Keep `form_validation.html` macros as the primary - they include Alpine.js `x-model` bindings. Deprecate others.

**Actions**:
1. Update `step_2_edit_description.html` to import from `form_validation.html` instead
2. Remove `input_field()` and `textarea_field()` from `create_workflow_elements.html`
3. Keep `form_input()` and `form_textarea()` in `flowbite_components.html` for non-Alpine forms (rare cases)
4. Keep other macros (`htmx_form`, `submit_button`, `back_button`, etc.) in `create_workflow_elements.html` - they're workflow-specific

### Task 4.2: Consolidate Success Alert

**Files with duplicate success alerts**:
- `templates/draft_unified.html` (lines 37-51)
- `templates/draft_editor.html` (lines 23-37)
- `templates/components/draft_preview_content.html` (lines 5-23)

**Existing Macro**: `flowbite_components.html` already has an `alert()` macro (lines 226-265) that uses Alpine.js `x-show` for dismissal. This works correctly - do NOT enhance or complicate it.

**Action**: Replace inline alerts with the existing `alert()` macro:

**Before** (`draft_unified.html` lines 37-51):
```html
<div id="success-alert" class="flex items-center p-4 mb-6 text-green-800 border border-green-300 rounded-lg bg-green-50 dark:bg-gray-800 dark:text-green-400 dark:border-green-800" role="alert">
    ...
</div>
```

**After**:
```jinja
{% from "macros/flowbite_components.html" import alert %}
{% if request.query_params.get('created') == 'true' %}
    {{ alert(
        message='<strong>Draft created successfully!</strong> Your finding model "' ~ draft.name ~ '" has been saved.',
        type="success",
        dismissible=true
    ) }}
{% endif %}
```

**Note**: The existing `alert()` macro works. Don't add complexity for "consistency" - if it works, ship it.

---

## Phase 5: Final Cleanup and Audit

### Task 5.1: Audit Remaining Ad Hoc Patterns

After completing Phases 1-4, run these searches to verify no patterns remain:

```bash
# Search for remaining ad hoc button patterns
grep -rn "px-[0-9] py-[0-9].*bg-.*rounded" templates/ --include="*.html"

# Search for remaining ad hoc badge patterns
grep -rn "rounded.*text-.*-800.*bg-.*-100" templates/ --include="*.html"

# Search for remaining custom JavaScript
grep -rn "<script>" templates/ --include="*.html"
grep -rn "function\s" templates/ --include="*.html"
```

### Task 5.2: Update Documentation

After completing refactoring:
1. Update `templates/PATTERNS.md` with any new patterns discovered
2. Update `templates/CLAUDE.md` if macro signatures changed
3. Verify `tasks/reference/ui_component_reference.md` matches current state

---

## Testing Strategy

### Baseline Verification (BEFORE ANY CHANGES)

Run the full test suite and confirm 100% pass rate:

```bash
task test
```

**Expected**: All tests passing with no failures

If any tests fail, DO NOT proceed with refactoring until they pass.

### Test Commands Reference

```bash
# Full test suite (unit + integration + UI)
task test

# Fast unit tests only (~0.4s)
task test-unit

# UI tests only (~2.5 min)
task test-ui

# Specific UI test categories
task test-ui-profile    # Profile page tests
task test-ui-drafts     # Draft management tests
task test-ui-creation   # Creation workflow tests

# Run specific test file
uv run pytest tests/ui/test_profile.py -v

# Run specific test class
uv run pytest tests/ui/test_draft_management.py::TestUnifiedDraftPage -v

# Run with visible browser for debugging
PLAYWRIGHT_HEADLESS=false uv run pytest tests/ui/test_profile.py -v
```

### Per-Phase Testing Protocol

**Note**: Profile edit tests are defined in Task 0.1 above. Complete that task before Phase 1.

#### Phase 1: Custom JavaScript Elimination

**Task 1.1 (draft_editor.html):**
```bash
# Before changes
task test-ui-drafts

# After changes
task test-ui-drafts

# Manual verification
# Navigate to /drafts/{id}/edit directly
# Verify mode toggle buttons work
```

**Task 1.2 (profile.html):**
```bash
# 1. ADD profile edit tests first (see above)
# 2. Run tests to establish baseline
task test-ui-profile

# 3. Make changes

# 4. Verify all tests pass
task test-ui-profile
```

#### Phase 2: Button Standardization

```bash
# Before each task
task test-ui

# After each task
task test-ui

# Key verification: HTMX attributes preserved
# - Modal triggers work (data-modal-toggle)
# - Form submissions work
# - HTMX swaps complete
```

#### Phase 3: Badge Standardization

```bash
# Before changes
task test-ui

# After changes
task test-ui

# Manual: Visual inspection in light/dark mode
```

#### Phase 4: Consolidation

```bash
# Before changes
task test-unit
task test-ui

# After changes
task test-unit
task test-ui

# Verify: Form validation still works, alerts dismiss
```

#### Phase 5: Final Verification

```bash
# Full test suite
task test

# Manual verification checklist (see below)
```

### Manual Verification Checklist

After all phases complete:

- [ ] **Profile Page**
  - [ ] View profile shows user info
  - [ ] Edit button toggles to edit mode
  - [ ] Can modify name/email fields
  - [ ] Can add organization (3-4 letter code)
  - [ ] Can remove organization
  - [ ] Save shows success message
  - [ ] Cancel returns to view mode
  - [ ] Works in dark mode

- [ ] **Draft Mode Toggle**
  - [ ] `/drafts/{id}/edit` loads in edit mode
  - [ ] `/drafts/{id}?mode=edit` loads in edit mode
  - [ ] `/drafts/{id}?mode=view` loads in view mode
  - [ ] Toggle buttons switch modes via HTMX
  - [ ] URL updates with `hx-push-url`
  - [ ] Active button has correct styling

- [ ] **Buttons**
  - [ ] Primary buttons are blue
  - [ ] Danger buttons are red
  - [ ] Success buttons are green
  - [ ] Disabled state works (opacity, cursor)
  - [ ] HTMX attributes trigger correctly
  - [ ] Modal toggles open modals
  - [ ] Forms submit correctly

- [ ] **Badges**
  - [ ] Draft status: yellow
  - [ ] Public status: blue
  - [ ] Submitted status: green
  - [ ] Proper sizing (xs, sm, default)
  - [ ] Dark mode colors correct

- [ ] **Alerts**
  - [ ] Success alerts are green
  - [ ] Error alerts are red
  - [ ] Dismiss button works
  - [ ] Alert disappears on dismiss

### Regression Risk Assessment

| Change | Risk Level | Mitigation |
|--------|------------|------------|
| Task 1.1 (draft_editor.html) | Medium | Extensive existing tests cover mode toggle |
| Task 1.2 (profile.html) | **HIGH** | **No existing tests** - must add before refactoring |
| Task 2.x (buttons) | Low | Tests verify button click actions work |
| Task 3.x (badges) | Low | Visual-only changes |
| Task 4.1 (form consolidation) | Medium | Form validation tests exist |
| Task 4.2 (alert consolidation) | Low | Simple refactor |

---

## Verification Checklist

After each phase, verify:

- [ ] `task lint` passes
- [ ] `task test-unit` passes
- [ ] `task test-ui` passes
- [ ] Manual testing of affected workflows (use checklist above)

---

## HTMX-Specific Considerations

### Templates That Serve HTMX Requests

These templates are returned as fragments in HTMX responses:

| Template | HTMX Target | Swap Type |
|----------|-------------|-----------|
| `draft_edit_form.html` | `#main-content` | innerHTML |
| `draft_preview.html` | `#main-content` | innerHTML |
| `draft_mode_toggle_header.html` | N/A (OOB) | outerHTML |
| `drafts/save_result.html` | `#draft-actions` | outerHTML |
| `drafts/submit_result.html` | `#draft-actions` | outerHTML |
| `drafts/delete_result.html` | Card element | delete |
| Step templates (1-3) | `#main-content` | innerHTML |

### OOB Swap Patterns

The `delete_result.html` uses OOB to update multiple elements:
```html
{# When last draft is deleted, show empty state #}
{% if deleted and remaining_count <= 0 %}
<div id="no-drafts" hx-swap-oob="outerHTML">...</div>
<div id="drafts-grid" hx-swap-oob="outerHTML" class="hidden"></div>
{% endif %}
```

**Do not break these patterns** when refactoring.

### Component Reinitialization

After HTMX swaps, `main.js` automatically:
1. Calls `initFlowbite()` for Flowbite components
2. Calls `Alpine.initTree(content)` for Alpine.js

This means:
- New Alpine.js `x-data` components will be initialized
- Flowbite data attributes (`data-modal-toggle`, `data-accordion-target`) will work
- **No manual initialization code needed in templates**

---

## Reference: Correct Button Classes by Type

### Primary Button (Flowbite Standard)
```
text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 dark:bg-blue-600 dark:hover:bg-blue-700 focus:outline-none dark:focus:ring-blue-800
```

### Secondary Button
```
text-gray-900 bg-white border border-gray-300 hover:bg-gray-100 focus:ring-4 focus:ring-gray-200 font-medium rounded-lg text-sm px-5 py-2.5 dark:bg-gray-800 dark:text-white dark:border-gray-600 dark:hover:bg-gray-700 dark:focus:ring-gray-700
```

### Success Button
```
text-white bg-green-700 hover:bg-green-800 focus:ring-4 focus:ring-green-300 font-medium rounded-lg text-sm px-5 py-2.5 dark:bg-green-600 dark:hover:bg-green-700 focus:outline-none dark:focus:ring-green-800
```

### Danger Button
```
text-white bg-red-700 hover:bg-red-800 focus:ring-4 focus:ring-red-300 font-medium rounded-lg text-sm px-5 py-2.5 dark:bg-red-600 dark:hover:bg-red-700 focus:outline-none dark:focus:ring-red-800
```

---

## Reference: Correct Badge Classes

### Default Badge
```
bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded dark:bg-blue-900 dark:text-blue-300
```

### Pill Badge
```
bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded-full dark:bg-blue-900 dark:text-blue-300
```

### Color Variants
- **Gray**: `bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300`
- **Red**: `bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300`
- **Green**: `bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300`
- **Yellow**: `bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300`
- **Indigo**: `bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300`
- **Purple**: `bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300`

---

**End of Plan**
