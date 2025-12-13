# Router Refactoring - Code Smell Assessment

## Overview

Assessment of router functions that need refactoring due to complexity, deep nesting, or mixed concerns.

## Priority 1: Very Smelly

### `finding_models()` in `app/routers/finding_models_browse.py`
- **Lines**: 21-192 (171 lines)
- **Issues**:
  - Two `@router.get` decorators handling both list AND detail in one function
  - Deep nesting: `if hx_request → if slug → try/except → else`
  - Massive duplicate `context.update()` calls (10+ keys repeated 3 times)
  - Error handling copy-pasted in multiple places
- **Recommendation**: Split into `list_finding_models()` and `get_finding_model_detail()` functions

### `unified_draft_page()` in `app/routers/drafts/views.py`
- **Lines**: 88-200 (112 lines)
- **Issues**:
  - Cascading if/else: HTMX vs non-HTMX, mode edit vs view, from_public vs not
  - Special case for `from_public` adds another nesting level
  - Template rendering logic spread across multiple branches
- **Recommendation**: Extract HTMX handling to separate function, use strategy pattern for mode handling

## Priority 2: Moderate Smell

### `update_draft_and_redirect()` in `app/routers/drafts/mutations.py`
- **Lines**: 154-241 (87 lines)
- **Issues**:
  - Does too much: fetch, validate, parse, check regeneration, generate, save, render
  - Mixed concerns (validation, business logic, response building)
- **Recommendation**: Move regeneration logic to service layer, extract response building

## Priority 3: Acceptable (No Action Needed)

### `process_step_2()` in `app/routers/creation.py`
- **Lines**: 164-240 (76 lines)
- Linear flow, clear step-by-step logic
- Complexity is inherent to the workflow

### `build_htmx_response_with_oob()` in `app/routers/drafts/helpers.py`
- **Lines**: 137-194 (57 lines)
- Focused helper function doing one thing
- Could be cleaner but not blocking

## Refactoring Principles

1. **Single Responsibility**: Each function should do one thing
2. **Flat over Nested**: Prefer early returns over deep nesting
3. **Extract to Service Layer**: Business logic belongs in services, not routers
4. **Consistent Patterns**: HTMX handling should follow the same pattern everywhere
5. **DRY Context Building**: Context dictionaries should be built once, not duplicated

## Related Tasks

- See `tasks/reconfigure_claude_code_rules.md` for Claude Code configuration improvements
