# Finding Model Creation Workflow Documentation

This document describes the current finding model creation workflow in FindingModelForge, including the streamlined flow
that was implemented to improve user experience.

## Overview

The finding model creation workflow has been streamlined from a traditional 5-step wizard to a more efficient 2-step
creation + draft editing pattern. This reduces user friction while maintaining the same functionality.

## ⚠️ CRITICAL: HTMX-Only Navigation - NO Browser Redirects

**ULTRA-IMPORTANT FOR DEVELOPERS AND TESTERS:**

This entire workflow operates via **HTMX content swaps ONLY**. There are **NO browser page redirects** at any point in
the creation workflow.

### What This Means:

- **Single Page**: All workflow steps happen within `create_finding_model_htmx.html`
- **Container**: All content is swapped into `#step-container`
- **Server "Redirects"**: When the backend returns HTTP 303 redirects, **HTMX intercepts them** and swaps content
  instead of navigating the browser
- **URL Updates**: HTMX uses `HX-Push-Url` to update the browser URL bar without page navigation
- **Testing**: Tests must wait for HTMX swaps, NOT page navigation events

### Common Misconceptions to Avoid:

❌ "Step 2 redirects to the draft page" → ✅ "Step 2 triggers HTMX swap to draft content" ❌ "Browser navigates to
/drafts/{id}" → ✅ "HTMX swaps draft content into #step-container" ❌ "Wait for page load" → ✅ "Wait for HTMX swap
completion" ❌ "Use page.goto() in tests" → ✅ "Use wait_for_htmx_swap() in tests"

### Technical Flow:

```
User Action → FastAPI Route → 303 Redirect Response → HTMX Intercepts → Content Swap into #step-container
```

**If you find yourself thinking about "page redirects" or "browser navigation" in this workflow, STOP and re-read this
section.**

## Workflow Stages

### Stage 1: Basic Information Entry

- **Endpoint**: `/api/finding-models/create/step/1`
- **User Action**: Enter finding name
- **Button**: "Generate Description"
- **Backend Processing**: AI generation of description based on name
- **Result**: Navigate to step 2 with generated description

### Stage 2: Description Refinement & Similarity Check

- **Endpoint**: `/api/finding-models/create/step/2`
- **User Action**: Review/edit AI-generated description, optionally add synonyms
- **Button**: "Check for Similar"
- **Backend Processing**:
  1. AI similarity analysis against existing models
  2. If similar models found → **HTMX swap** to step 3 content (review similar)
  3. If no similar models found → **Create draft and HTMX swap** to draft edit content
- **Critical Understanding**: Server returns `303 See Other` to
  `/api/finding-models/drafts/{draft_id}?mode=edit&created=true` but **HTMX intercepts this and swaps draft content into
  `#step-container`** instead of browser navigation

### Stage 3: Draft Editing (HTMX Content in #step-container)

- **Important**: This is NOT a separate page - it's **HTMX-swapped content within the same creation page**
- **Content Source**: Draft edit form components swapped into `#step-container`
- **User Interface**:
  - Read-only finding name
  - Editable description field
  - Synonym manager
  - Attributes markdown editor (main content area)
  - Auto-save functionality on changes
- **Primary Action**: "Update & Preview" button
- **Backend Processing**:
  1. Validate and save draft inputs
  2. Generate FindingModel JSON using AI
  3. **HTMX Response**: Return preview content with `HX-Push-Url` to update URL (no navigation)
- **Result**: Content in `#step-container` swaps to preview mode

### Stage 4: Model Preview & Submission (HTMX Content in #step-container)

- **Important**: This is **HTMX-swapped preview content** within the same `#step-container`
- **URL Bar**: Shows `/api/finding-models/drafts/{draft_id}?mode=view` via `HX-Push-Url` (no actual navigation)
- **User Interface**:
  - Generated finding model display
  - Draft status and metadata
  - Action buttons (Submit Draft, Delete Draft)
- **Primary Action**: "Submit Draft" button
- **Backend Processing**: Change draft status from "draft" to "submitted"
- **Result**: **HTMX swap** to final submitted model content with IDs and JSON accordion

## Technical Implementation Details

### Session Management

- **Creation Session**: Tracks user progress through initial steps (1-2)
- **Draft Adoption**: Session can adopt state from existing drafts
- **TTL**: 1-hour expiry with activity refresh

### Draft System

- **Status States**:
  - `draft`: Editable, can be updated/deleted
  - `submitted`: Read-only, shows IDs and JSON
- **Auto-save**: Triggered on textarea changes with debouncing
- **Unified Endpoint**: Single endpoint handles both edit/view modes via query parameter

### HTMX Integration Points

#### Step Transitions (Traditional)

```html
<form hx-post="/api/finding-models/create/step/1" hx-target="#step-container">
  <form hx-post="/api/finding-models/create/step/2" hx-target="#step-container"></form>
</form>
```

#### Draft Mode Switching

```html
<!-- Edit/View mode toggle buttons -->
<button hx-get="/api/finding-models/drafts/{id}?mode=edit" hx-target="#draft-content" hx-push-url="true">
  <button hx-get="/api/finding-models/drafts/{id}?mode=view" hx-target="#draft-content" hx-push-url="true"></button>
</button>
```

#### Draft Form Submission

```html
<form hx-post="/api/finding-models/drafts/{id}/update-and-redirect"></form>
```

#### Auto-save Mechanism

```html
<div
  hx-post="/api/finding-models/drafts/save"
  hx-trigger="change from:find textarea delay:500ms, keyup from:find textarea delay:1000ms changed"
  hx-target="#draft-actions"
></div>
```

## AI Operations & Timeouts

### Description Generation (Step 1)

- **Timeout**: ~2-5 seconds
- **Fallback**: Default description if AI fails

### Similarity Analysis (Step 2)

- **Timeout**: ~15-30 seconds
- **Process**: Semantic search against existing finding models
- **Result**: Either redirect to draft or show similar models for review

### Model Generation (Draft Update)

- **Timeout**: ~30-90 seconds (longest operation)
- **Process**: Generate complete FindingModel JSON from inputs
- **Includes**: ID assignment, standard codes, validation

## URL Patterns

| Stage            | URL Pattern                                 | Purpose                                  |
| ---------------- | ------------------------------------------- | ---------------------------------------- |
| Initial          | `/create-finding-model`                     | Entry point, loads step 1                |
| Step 1           | `/api/finding-models/create/step/1`         | Name entry and description generation    |
| Step 2           | `/api/finding-models/create/step/2`         | Description editing and similarity check |
| Step 3 (similar) | `/api/finding-models/create/step/3`         | Review similar models (if found)         |
| Draft Edit       | `/api/finding-models/drafts/{id}?mode=edit` | Draft editing interface                  |
| Draft View       | `/api/finding-models/drafts/{id}?mode=view` | Model preview and submission             |
| Draft Actions    | `/api/finding-models/drafts/{id}/submit`    | Submit draft                             |
| Draft Actions    | `/api/finding-models/drafts/{id}/delete`    | Delete draft                             |

## Success & Error Handling

### Success Indicators

- **Draft Created**: Success banner with "Draft created successfully!" message
- **Model Generated**: Preview content shows generated finding model
- **Submitted**: Status changes, IDs and JSON become visible

### Error Scenarios

- **AI Timeout**: Graceful degradation with retry options
- **Invalid Input**: Form validation with specific error messages
- **Draft Not Found**: 404 error with helpful message
- **Permission Denied**: 403 error for drafts not owned by user

## Testing Considerations

### ⚠️ CRITICAL: HTMX Testing Patterns

**ALL tests must use HTMX-aware waiting functions. NEVER use `page.goto()` or wait for page navigation.**

### Key Elements to Test

1. **Step 1→2 Transition**: HTMX swap from step 1 to step 2 content in `#step-container`
2. **Step 2→Draft Content**: HTMX swap from step 2 to draft edit content in `#step-container`
3. **Draft Edit Form**: Form functionality within `#step-container`
4. **Update & Preview**: HTMX swap from edit to preview content in `#step-container`
5. **Submit Draft**: HTMX swap to final submitted content in `#step-container`

### Required Test Utility Functions

```python
# ✅ CORRECT - Use these HTMX-aware functions
await wait_for_htmx_swap(page, expected_selector)
await wait_for_ai_completion_and_swap(page, button_prefix, expected_element)
await wait_for_htmx_to_settle(page)

# ❌ WRONG - Never use these for workflow testing
await page.goto()
await page.wait_for_load_state()
await expect(page).to_have_url()
```

### Critical Test Patterns

```python
# ✅ CORRECT: Wait for HTMX swap to draft content
await page.locator("button:has-text('Check for Similar')").click()
await wait_for_ai_completion_and_swap(
    page,
    "Check",  # Button text changes during AI processing
    "#step-container textarea[name='attributes_markdown']"  # Expected after swap
)

# ❌ WRONG: Expecting page navigation
await page.locator("button:has-text('Check for Similar')").click()
await page.wait_for_url("**/drafts/**")  # This will never happen!
```

### Critical Selectors (All in #step-container)

- `#step-container button:has-text('Generate Description')` - Step 1
- `#step-container button:has-text('Check for Similar')` - Step 2
- `#step-container button:has-text('Update & Preview')` - Draft edit
- `#step-container button:has-text('Submit Draft')` - Draft submission
- `#step-container #success-alert` - Success indicators

### Timeouts for Testing

- Description generation: 60 seconds (AI operation)
- Similarity check: 60 seconds (AI operation)
- Model generation: 90 seconds (longest AI operation)
- HTMX swaps: 10 seconds (fast operations)

## Integration with Profile/Dashboard

Drafts created through this workflow appear in:

- **Profile Page**: `/profile` - Shows user's drafts and submitted models
- **Draft List**: Paginated view with edit/delete actions
- **Resume Functionality**: Can resume editing from profile page

---

_Last Updated: August 2025_ _This workflow represents the current implementation as of the unified draft pattern
introduction._
