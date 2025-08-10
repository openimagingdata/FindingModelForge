# Finding Model Creation Refactoring Plan

## Overview

The current `create_finding_model.html` template has several architectural issues that need to be addressed:

1. **Code Organization**: 691-line monolithic file that's difficult to maintain
2. **Flowbite Integration**: Ad hoc Tailwind usage instead of proper Flowbite components
3. **JavaScript Architecture**: Too much raw JavaScript, improper Alpine.js usage
4. **Client-Heavy Architecture**: Business logic should be server-side, not client-side

## Goals

- Break down monolithic template into modular components
- Replace custom UI with proper Flowbite components
- Introduce HTMX for server-driven interactions
- Move business logic to server-side endpoints
- Simplify Alpine.js to UI-only interactions

## Current Issues Analysis

### File Structure

- Single 691-line template file
- Inline JavaScript (280+ lines)
- Complex state management in Alpine.js
- No component reusability

### Flowbite Compliance

- Custom progress indicator instead of Flowbite stepper
- Ad hoc Tailwind classes instead of Flowbite form components
- Inconsistent button patterns
- Custom error handling instead of Flowbite alerts

### Architecture

- Heavy client-side business logic
- Complex API orchestration in JavaScript
- State management prone to loss
- Difficult error recovery

## Refactoring Plan

### 1. File Structure Refactoring

**New Structure:**

```
templates/
├── create_finding_model.html (main orchestrator, ~50 lines)
├── components/finding_model_creation/
│   ├── step_name_input.html
│   ├── step_description_edit.html
│   ├── step_similar_review.html
│   ├── step_attributes_edit.html
│   └── step_final_display.html
└── macros/
    └── creation_components.html (shared macros)
```

### 2. HTMX Integration

**Technology Addition:**

- Add HTMX to project dependencies
- Each step becomes an HTMX endpoint returning HTML fragments
- Form submissions trigger server-side processing
- Use `hx-get`, `hx-post`, `hx-target` for seamless updates

**Benefits:**

- Server-driven interactions
- Reduced JavaScript complexity
- Progressive enhancement
- Better error handling

### 3. Server-Side Architecture

**New Endpoints:**

```python
# New endpoints in app/routers/finding_models.py
@router.get("/create/step/{step_number}")  # Returns step HTML
@router.post("/create/step/{step_number}") # Processes step data
@router.get("/create/progress/{session_id}") # Progress state
```

**Session Management:**

- Store creation state in Redis/database
- Each step validates and saves progress
- Enables reliable back/forward navigation

### 4. Flowbite Compliance

**Components to Implement:**

- **Progress Indicator**: Replace custom with Flowbite stepper component (`data-stepper`)
- **Forms**: Use Flowbite form components with proper validation states
- **Buttons**: Use Flowbite button patterns (`btn-primary`, `btn-secondary`)
- **Alerts**: Replace custom error display with Flowbite alert components
- **Loading States**: Flowbite spinner components

**Before/After Example:**

```html
<!-- Before: Custom progress indicator -->
<div class="flex items-center justify-between">
  <div class="flex space-x-4">
    <div class="flex-shrink-0 w-8 h-8 rounded-full..." :class="...">
      <!-- After: Flowbite stepper -->
      <ol class="flex items-center w-full text-sm font-medium text-center" data-stepper>
        <li class="flex md:w-full items-center" data-stepper-item></li>
      </ol>
    </div>
  </div>
</div>
```

### 5. Alpine.js Simplification

**Current State:** 280+ lines of complex logic **Target State:** ~50 lines for UI interactions only

```javascript
// Before: Complex state management
function findingModelCreator() {
  return {
    step: 1,
    loading: false,
    formData: {...},
    // 280+ lines of logic
  }
}

// After: Simple UI interactions
x-data="{
  loading: false,
  showError: false,
  toggleSynonym(index) { /* simple UI toggle */ }
}"
```

### 6. HTMX Patterns

```html
<!-- Step navigation -->
<button hx-get="/create/step/2" hx-target="#step-container" hx-indicator="#loading" class="btn btn-primary">
  Next Step
</button>

<!-- Form submission -->
<form hx-post="/create/step/1" hx-target="#step-container" hx-swap="outerHTML">
  <!-- Flowbite form components -->
</form>

<!-- Loading states -->
<div id="loading" class="htmx-indicator">
  <!-- Flowbite spinner -->
</div>
```

## Implementation Phases

### Phase 1: Foundation (Setup HTMX & Structure)

- [ ] Add HTMX to the project (via CDN or npm)
- [ ] Create new component directory structure
- [ ] Create session-based state management utilities
- [ ] Set up basic routing structure

### Phase 2: Server Endpoints

- [ ] Create step-specific FastAPI endpoints
- [ ] Implement session-based progress tracking
- [ ] Move validation logic to server
- [ ] Add proper error handling

### Phase 3: Component Refactoring

- [ ] Break down monolithic template into components
- [ ] Replace custom components with Flowbite patterns
- [ ] Implement proper Flowbite stepper
- [ ] Add Flowbite form components

### Phase 4: HTMX Integration

- [ ] Replace Alpine.js API calls with HTMX requests
- [ ] Implement progressive enhancement
- [ ] Add loading states and transitions
- [ ] Test all user interactions

### Phase 5: Testing & Polish

- [ ] Test all user flows end-to-end
- [ ] Ensure accessibility compliance
- [ ] Performance optimization
- [ ] Update documentation

## Success Criteria

### Code Quality

- [ ] Main template under 100 lines
- [ ] Each component under 50 lines
- [ ] No business logic in Alpine.js
- [ ] All UI follows Flowbite patterns

### Performance

- [ ] Reduced JavaScript bundle size
- [ ] Server-side rendering for better initial load
- [ ] Progressive enhancement working
- [ ] Proper loading states

### Maintainability

- [ ] Clear component separation
- [ ] Reusable macros
- [ ] Consistent patterns throughout
- [ ] Good error handling

### User Experience

- [ ] Reliable state persistence
- [ ] Clear progress indication
- [ ] Proper error messages
- [ ] Accessible interactions

## Files to Modify/Create

### New Files

- `templates/components/finding_model_creation/step_*.html` (5 files)
- `templates/macros/creation_components.html`
- `docs/finding_model_creation_flow.md` (user documentation)

### Modified Files

- `templates/create_finding_model.html` (major refactoring)
- `app/routers/finding_models.py` (new endpoints)
- `app/dependencies.py` (session management)
- `templates/base.html` (HTMX integration)
- `package.json` (HTMX dependency)

## Risk Mitigation

1. **Incremental Approach**: Implement one phase at a time
2. **Feature Flagging**: Keep old system running during transition
3. **Comprehensive Testing**: Test each phase thoroughly
4. **Documentation**: Document new patterns for team

## Timeline Estimate

- **Phase 1**: 1-2 days (setup)
- **Phase 2**: 2-3 days (server endpoints)
- **Phase 3**: 3-4 days (component refactoring)
- **Phase 4**: 2-3 days (HTMX integration)
- **Phase 5**: 2-3 days (testing & polish)

**Total**: 10-15 days for complete refactoring

---

_Last Updated: 2025-01-08_ _Status: Planning Phase_
