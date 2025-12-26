# Frontend Cleanup - Push 2

**Status**: IN PROGRESS **Created**: December 2025 **Priority**: Medium - Technical debt and refinements from Push 1

## Context

Push 1 (see `tasks/done/frontend_cleanup_push_1.md`) successfully eliminated custom JavaScript, standardized
button/badge usage with macros, and established consistent patterns. However, code review and research revealed
additional items.

## Tasks by Priority

### CRITICAL Priority - Visible Bug

#### Task 0: Fix "Update & Preview" Button Showing Raw HTML

**Problem**: The "Update & Preview" button on the draft edit page displays raw HTML/SVG markup as escaped text instead
of rendering a loading spinner.

**Screenshot Evidence**: Button shows literal `<span class="htmx-indicator">...` text.

**Root Cause**: The `action_button` macro in `flowbite_components.html` outputs `{{ text }}` without the `|safe` filter
(line 121). When raw HTML is passed to the `text` parameter, Jinja2's auto-escaping converts it to escaped entities.

**Broken Code** (`templates/components/draft_edit_form_content.html` lines 80-88):

```jinja
{{ action_button(
    text='<span class="htmx-indicator">...SVG...</span><span>Update & Preview</span>',
    ...
) }}
```

**Why This Pattern is Wrong**: Passing HTML to macro parameters defeats Jinja2's XSS protection. The `action_button`
macro intentionally does NOT use `|safe` on `text` for security.

**Working Pattern** (already exists in `templates/components/draft_edit_form.html` lines 83-95 and
`templates/macros/create_workflow_elements.html` lines 16-32):

```html
<button type="submit" class="...">
  <span class="htmx-indicator">
    <svg class="animate-spin ...">...</svg>
    Loading...
  </span>
  <span>Button Text</span>
</button>
```

**Solution**: Enhanced `action_button` macro with optional `loading_text` parameter for HTMX loading indicators.

**What Was Done**:

1. Added `loading_text` parameter to `action_button` macro in `flowbite_components.html`
2. When `loading_text` is provided, macro renders spinner + loading text inside `htmx-indicator` span
3. Updated all templates to use the enhanced macro instead of passing HTML
4. Removed duplicate `submit_button` macro from `create_workflow_elements.html`
5. Added regression test to catch escaped HTML in buttons

**Example Usage**:
```jinja
{{ action_button(
    text="Update & Preview",
    loading_text="Updating...",
    button_type="submit",
    attributes=':disabled="!canSubmit"'
) }}
```

**Why This Approach**: Keeps HTML generation inside the macro where it's safe, rather than passing HTML through
parameters which defeats Jinja2's XSS protection.

**Acceptance Criteria**:

- [x] **Regression test added** that explicitly checks for escaped HTML in button text
- [x] Regression test fails BEFORE fix, passes AFTER fix (TDD verification)
- [x] Button displays "Update & Preview" with hidden spinner (visible during HTMX requests)
- [x] No raw HTML visible on page
- [x] Draft editing workflow functions correctly
- [x] `task test-ui` passes (all existing + new regression test)

**Effort**: Small (30 minutes including test)

**Why This Bug Wasn't Caught**: Playwright's `:has-text()` selector matches on text content. The escaped HTML
`&lt;span class="htmx-indicator"&gt;...Update &amp; Preview...` still contains the literal text "Update & Preview", so
tests passed despite the visual bug.

**References**:

- [HTMX hx-indicator docs](https://htmx.org/attributes/hx-indicator/)
- [Flowbite Spinner in Buttons](https://flowbite.com/docs/components/spinner/)
- [Jinja2 Auto-escaping](https://jinja.palletsprojects.com/en/stable/templates/#html-escaping)

---

### HIGH Priority - Latent Bug

#### Task 1: Fix Global `initFlowbite()` Pattern

**Problem**: Our `main.js` calls `initFlowbite()` globally after every HTMX swap. This reinitializes ALL Flowbite
components on the page, not just new ones, which can cause duplicate modal instances.

**Evidence**: [Flowbite GitHub Issue #820](https://github.com/themesberg/flowbite/issues/820)

**File**: `src/js/main.js` (lines 268-274)

**Current Code**:

```javascript
htmx.onLoad(function (content) {
  if (typeof initFlowbite === "function") {
    initFlowbite() // ← Reinits ALL components
  }
  // ...
})
```

**Solution Options**:

1. Use component-specific init functions (`initModals()`, `initDropdowns()`) on the swapped content only
2. Wait for Flowbite to implement `initFlowbite({uninitializedOnly: true})`
3. Track initialized elements and skip re-initialization

**Acceptance Criteria**:

- Modal workflows still work (test with `task test-ui`)
- No duplicate modal instances when HTMX swaps content containing modals
- Console shows no Flowbite warnings about duplicate instances

---

### MEDIUM Priority - Consolidation & Refinements

_Note: Task 6 (Document Patterns) should be done LAST after all consolidation work is complete._

#### Task 2: Consolidate Small Modal Macros

**Problem**: Three nearly identical small macro files:

- `templates/macros/delete_draft_modal.html` (651 bytes)
- `templates/macros/make_public_modal.html` (649 bytes)
- `templates/macros/submit_draft_modal.html` (651 bytes)

**Solution**: Consolidate into single `modal_components.html` with parameterized macro.

**Effort**: Small

---

#### Task 3: Create Centralized Icon Library

**Problem**: 20+ duplicate icon definitions scattered across 9+ template files. The same icons (home, folder, edit,
delete, check, eye, spinner, etc.) are defined inline repeatedly.

**Files with inline icons** (from macro review):

- `templates/macros/flowbite_components.html` - spinner icon in `action_button`
- `templates/components/draft_preview_content.html` - eye, delete, check icons
- `templates/components/finding_model_display.html` - info icons
- `templates/profile.html` - folder, edit, trash icons
- `templates/home.html` - feature icons
- `templates/finding_models_browse.html` - search, filter icons
- Multiple creation workflow templates - navigation icons

**Solution**:

1. Create `templates/macros/icons.html` with parameterized icon macros
2. Support size variants (sm, md, lg) and color customization
3. Update templates to use `{{ icon('edit', size='sm') }}` pattern
4. Keep frequently-used icons (spinner, check, x, edit, delete, eye, home, folder)

**Example Implementation**:

```jinja
{% macro icon(name, size="md", classes="") %}
  {% set sizes = {"sm": "w-4 h-4", "md": "w-5 h-5", "lg": "w-6 h-6"} %}
  {% if name == "spinner" %}
    <svg class="animate-spin {{ sizes[size] }} {{ classes }}" fill="none" viewBox="0 0 24 24">...</svg>
  {% elif name == "edit" %}
    <svg class="{{ sizes[size] }} {{ classes }}" fill="none" stroke="currentColor" viewBox="0 0 24 24">...</svg>
  {% endif %}
{% endmacro %}
```

**Why Do This Early**: Other consolidation tasks will touch templates. Having centralized icons first means we can use
them consistently in those changes.

**Effort**: Medium (high file count, but mechanical changes)

---

#### Task 4: Consolidate Avatar Macros

**Problem**: Two avatar macros that do essentially the same thing:

- `contributor_avatar(contributor, size)` in `flowbite_components.html`
- `user_avatar(name, avatar_url, size)` in `flowbite_components.html`

**Current Usage**: `contributor_avatar` is only used in `finding_model_display.html` for showing model contributors.

**Solution**:

1. Remove `contributor_avatar` macro
2. Update `finding_model_display.html` to use `user_avatar(contributor.name, contributor.avatar_url)`
3. Document `user_avatar` as the single avatar solution

**Effort**: Small

---

#### Task 5: Simplify Form Validation Architecture

**Problem**: Two form validation macros with overlapping but confusing responsibilities:

| Macro | Location | Used In | Issue |
|-------|----------|---------|-------|
| `validation_data` | `form_validation.html` | Step 1 only | Overengineered - has description/attributes logic never used |
| `unified_form_data` | `unified_form_data.html` | Step 2 + Draft Edit | Well-designed, purpose-built |

**Analysis** (from deep code review):

The `validation_data` macro (lines 46-66) has complex conditional logic for "draft editing form", "name-only form", and
"description-only form" modes. But it's only ever used for step 1 (name-only), making most of this code dead.

**The HTMX/Alpine Pattern is Correct**: Server provides initial values → HTMX swaps → `Alpine.initTree()` creates fresh
state → No alpine-morph needed because server IS the source of truth.

**Solution**:

1. **Rename and simplify `validation_data`** → `name_validation_data` (step 1 only):
   ```jinja
   {% macro name_validation_data(initial_name='') %}
   {
       name: {{ initial_name | tojson }},
       get isValid() { return this.name.length >= 3 && this.name.length <= 200; }
   }
   {% endmacro %}
   ```

2. **Keep `unified_form_data`** unchanged (it's well-designed for step 2 + draft editing)

3. **Standardize button bindings**:
   - Step 1: `:disabled="!isValid"`
   - Step 2: `:disabled="!canSubmitStep2"`
   - Draft edit: `:disabled="!canSubmit"`

4. **Remove legacy `validation_component()` alias** (line 76-78)

**Effort**: Small (isolated changes, no cross-file impact)

---

#### Task 6: Document Component Patterns in PATTERNS.md

**⚠️ DO THIS TASK LAST** - after all consolidation work (Tasks 2-5) is complete.

**Problem**: `templates/PATTERNS.md` exists but may be outdated after Push 1 and Push 2 changes.

**Task**:

1. Review current state of `templates/PATTERNS.md`
2. Update with current macro inventory:
   - `flowbite_components.html` - buttons (with `loading_text`), badges, alerts, avatars
   - `icons.html` - centralized icon library (after Task 3)
   - `modal_components.html` - confirmation modals (after Task 2)
   - `form_validation.html` - validated inputs, name validation
   - `unified_form_data.html` - step 2 + draft form state
3. Add examples of correct HTMX/Alpine patterns
4. Cross-reference with `templates/CLAUDE.md`

**Effort**: Medium

---

### LOW Priority - Nice to Have

#### Task 7: Alert Macro Consolidation Review

**Problem**: Multiple alert-related patterns exist:

1. `alert(message, type, dismissible, id)` macro in `flowbite_components.html` - the standard
2. `profile.html` uses inline `:class` bindings for Alpine.js reactive alerts
3. Potential duplicate `error_alert`/`success_alert` macros (if they exist)

**Current Code** (profile.html ~line 193):

```html
:class="alert.type === 'success' ? 'bg-green-50 border-green-200...' : 'bg-red-50 border-red-200...'"
```

**Task**:

1. Audit for any `error_alert`/`success_alert` duplicate macros and remove them
2. Evaluate profile.html pattern - the inline approach IS valid for Alpine.js reactive styling
3. Document when to use `alert()` macro vs inline Alpine.js reactive patterns

**Consideration**: The profile.html inline approach may be intentional for reactive state. Don't force macro usage where
Alpine reactivity is needed.

**Effort**: Small

---

#### Task 8: Evaluate Form Input Macro Duplication

**Problem**: Two sets of form input macros exist:

| Macros | Location | Features |
|--------|----------|----------|
| `form_input`, `form_textarea` | `flowbite_components.html` | Basic Flowbite styling |
| `validated_input`, `validated_textarea` | `form_validation.html` | Adds `x-model` binding |

**Analysis**: The `validated_*` macros hard-code `x-model="{{ name }}"`, assuming the Alpine variable matches the input
name. This is implicit coupling but works because macros must be used inside matching x-data contexts.

**Task**:

1. Document the intended use case for each set
2. Determine if consolidation is possible/desirable
3. If keeping both, add clear documentation about when to use which

**Effort**: Small (evaluation/documentation)

---

#### Task 9: Add Visual Regression Tests

**Problem**: UI changes can introduce subtle visual regressions not caught by functional tests.

**Solution**: Add Playwright visual comparison tests for key pages:

- Home page
- Finding models list
- Draft editor
- Profile page

**Effort**: Medium

**Note**: This may require setting up baseline screenshots and CI integration.

---

## Testing Requirements

All tasks must pass:

- `task test-unit`
- `task test-ui` (requires dev server running)

For milestone commits: `task test-full`

## Success Criteria

Push 2 is complete when:

1. **Task 0 (CRITICAL)**: ✓ "Update & Preview" button renders correctly
2. **Task 1 (HIGH)**: initFlowbite fix is resolved
3. **Tasks 2-6 (MEDIUM)**: Consolidation tasks completed in order:
   - Task 2: Modal macros consolidated
   - Task 3: Icon library created
   - Task 4: Avatar macros consolidated
   - Task 5: Form validation simplified
   - Task 6: PATTERNS.md updated (LAST)
4. All tests pass (`task test-unit` + `task test-ui`)
5. LOW priority tasks (7-9) documented as intentional decisions or deferred

## Related Research

Technology decisions made during this work are documented in:
- **Decisions**: `technology_decisions` Serena memory
- **Detailed research**: `research/alpine_plugins_evaluation.md`, `research/flowbite_4_upgrade_assessment.md`

## References

- [Flowbite GitHub Issue #820](https://github.com/themesberg/flowbite/issues/820)
- [Flowbite JavaScript Docs](https://flowbite.com/docs/getting-started/javascript/)
