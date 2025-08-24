# Test Script: Finding Models Detail Page

## Overview

This script documents the expected behavior for navigating to and viewing finding model detail pages.

## Test Scenarios

### Scenario 1: HTMX Navigation from List

1. **Start at**: `/finding-models`
2. **Action**: Click on first table row
3. **Expected**:
   - No full page reload (HTMX swap)
   - URL changes to `/finding-models/{slug}`
   - Breadcrumb updates via OOB swap to: `Home > Finding Models > [Model Name]`
   - Page title changes to: `[Model Name] - Finding Model Forge`
   - Detail content appears in #main-content

### Scenario 2: Direct URL Access

1. **Navigate to**: `/finding-models/abdominal-abscess` (or any valid slug)
2. **Expected on load**:
   - Full page loads with proper structure
   - Breadcrumb shows: `Home > Finding Models > abdominal abscess`
   - Page title: `abdominal abscess - Finding Model Forge`
   - Model details displayed with accordion sections

## Expected Detail Page Elements

### Header Section

1. **Model Name**: Large heading (h1 or h2)
2. **Description**: Paragraph text below name
3. **Synonyms**: Listed if present
4. **IDs**: OIFM ID displayed

### Accordion Sections

1. **Attributes**: Expandable section with model attributes
2. **JSON**: Expandable section with full JSON (if show_json=true)
3. **Flowbite accordion functionality**: Click to expand/collapse

### Breadcrumb Navigation

1. **"Finding Models" link**:
   - Should be clickable
   - Uses HTMX to navigate back to list
   - URL changes to `/finding-models`
   - Content swaps back to list view
   - Page title reverts to: `Finding Models - Finding Model Forge`

### Navigation Elements

1. **Home breadcrumb**: Links to homepage
2. **Finding Models breadcrumb**: Returns to list via HTMX
3. **Current model**: Not clickable (current page)

## Browser History Navigation

### Back Button from Detail

1. **State**: On detail page `/finding-models/test-model`
2. **Action**: Click browser back button
3. **Expected**:
   - Returns to list page
   - URL changes to `/finding-models`
   - Breadcrumb updates to: `Home > Finding Models`
   - Page title updates to: `Finding Models - Finding Model Forge`
   - List content restored (via HTMX history)

### Forward Button to Detail

1. **State**: Back on list page after using back button
2. **Action**: Click browser forward button
3. **Expected**:
   - Returns to detail page
   - URL changes back to `/finding-models/test-model`
   - Breadcrumb restores to: `Home > Finding Models > test model`
   - Page title restores to: `test model - Finding Model Forge`
   - Detail content restored

## 404 Handling

1. **Navigate to**: `/finding-models/non-existent-slug`
2. **Expected**: 404 error page or error message

## Console Checks

- No JavaScript errors during navigation
- No errors during accordion interaction
- htmx:historyRestore events fire correctly
- No Flowbite reinitialization errors

## Dark Mode

- Detail content readable in dark mode
- Accordion maintains proper contrast
- Code blocks (if any) have appropriate syntax highlighting
