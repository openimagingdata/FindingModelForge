# Frontend Cleanup - Push 2

**Status**: NOT STARTED
**Created**: December 2025
**Priority**: Medium - Technical debt and refinements from Push 1

## Context

Push 1 (see `tasks/done/frontend_cleanup_push_1.md`) successfully eliminated custom JavaScript, standardized button/badge usage with macros, and established consistent patterns. However, code review and research revealed additional items.

## Tasks by Priority

### HIGH Priority - Latent Bug

#### Task 1: Fix Global `initFlowbite()` Pattern

**Problem**: Our `main.js` calls `initFlowbite()` globally after every HTMX swap. This reinitializes ALL Flowbite components on the page, not just new ones, which can cause duplicate modal instances.

**Evidence**: [Flowbite GitHub Issue #820](https://github.com/themesberg/flowbite/issues/820)

**File**: `src/js/main.js` (lines 268-274)

**Current Code**:
```javascript
htmx.onLoad(function(content) {
  if (typeof initFlowbite === 'function') {
    initFlowbite()  // ← Reinits ALL components
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

### MEDIUM Priority - Refinements

#### Task 2: Consolidate Small Modal Macros

**Problem**: Three nearly identical small macro files:
- `templates/macros/delete_draft_modal.html` (651 bytes)
- `templates/macros/make_public_modal.html` (649 bytes)
- `templates/macros/submit_draft_modal.html` (651 bytes)

**Solution**: Consolidate into single `modal_components.html` with parameterized macro.

**Effort**: Small

---

#### Task 3: Evaluate alpine-morph Extension

**Problem**: When HTMX swaps entire Alpine components, their internal state is lost.

**Current State**: We don't use alpine-morph. Our patterns avoid this issue by keeping Alpine state local to components that don't get fully swapped.

**Task**:
1. Audit current usage to confirm we don't have state loss issues
2. Document decision (use or not use) in `templates/CLAUDE.md`
3. If needed, add alpine-morph extension

**Reference**: [HTMX alpine-morph Extension](https://v1.htmx.org/extensions/alpine-morph/)

**Effort**: Medium

---

#### Task 4: Document Component Patterns in PATTERNS.md

**Problem**: `templates/PATTERNS.md` exists but may be outdated after Push 1 changes.

**Task**:
1. Review current state of `templates/PATTERNS.md`
2. Update with current macro inventory and usage patterns
3. Add examples of correct HTMX/Alpine patterns
4. Cross-reference with `templates/CLAUDE.md`

**Effort**: Medium

---

### LOW Priority - Nice to Have

#### Task 5: Consider `alert()` Macro for Profile Page

**Problem**: `profile.html` uses inline `:class` bindings for success/error alerts instead of the `alert()` macro.

**Current Code** (profile.html ~line 193):
```html
:class="alert.type === 'success' ? 'bg-green-50 border-green-200...' : 'bg-red-50 border-red-200...'"
```

**Consideration**: The inline approach is valid for Alpine.js reactive styling. Evaluate if converting to macro improves maintainability or if current approach is acceptable.

**Effort**: Small

---

#### Task 6: Add Visual Regression Tests

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
1. Task 1 (initFlowbite fix) is resolved
2. Medium priority tasks are either completed or documented as intentional decisions
3. All tests pass
4. Documentation is updated

## References

- [Flowbite GitHub Issue #820](https://github.com/themesberg/flowbite/issues/820)
- [HTMX alpine-morph Extension](https://v1.htmx.org/extensions/alpine-morph/)
- [Ben Nadel - Using Alpine.js in HTMX](https://www.bennadel.com/blog/4787-using-alpine-js-in-htmx.htm)
- [InfoWorld - HTMX and Alpine.js](https://www.infoworld.com/article/3856520/htmx-and-alpine-js-how-to-combine-two-great-lean-front-ends.html)
- [Flowbite JavaScript Docs](https://flowbite.com/docs/getting-started/javascript/)
