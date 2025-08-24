# Test Script: Finding Models History Navigation

## Overview

This script documents expected behavior for browser history navigation, including back/forward buttons and
title/breadcrumb restoration.

## Test Scenarios

### Scenario 1: Simple Back/Forward Navigation

1. **Start at**: Homepage (`/`)
2. **Navigate to**: `/finding-models`
   - Title: `Finding Models - Finding Model Forge`
   - Breadcrumb: `Home > Finding Models`
3. **Click table row**: Navigate to detail
   - URL: `/finding-models/test-model`
   - Title: `test model - Finding Model Forge`
   - Breadcrumb: `Home > Finding Models > test model`
4. **Browser Back**:
   - URL: `/finding-models`
   - Title: `Finding Models - Finding Model Forge`
   - Breadcrumb: `Home > Finding Models`
   - List content restored
5. **Browser Forward**:
   - URL: `/finding-models/test-model`
   - Title: `test model - Finding Model Forge`
   - Breadcrumb: `Home > Finding Models > test model`
   - Detail content restored

### Scenario 2: Search State Preservation

1. **Navigate to**: `/finding-models`
2. **Search for**: "abscess"
   - URL: `/finding-models?search=abscess`
   - Title: `Search: abscess - Finding Model Forge`
   - Results filtered
3. **Click result**: Navigate to detail
   - URL: `/finding-models/abdominal-abscess`
   - Title: `abdominal abscess - Finding Model Forge`
4. **Browser Back**:
   - URL: `/finding-models?search=abscess`
   - Title: `Search: abscess - Finding Model Forge`
   - Search box contains "abscess"
   - Filtered results shown

### Scenario 3: Pagination State

1. **Navigate to**: `/finding-models`
2. **Click page 2**:
   - URL: `/finding-models?page=2`
   - Shows results 21-40
3. **Click table row**: Navigate to detail
4. **Browser Back**:
   - URL: `/finding-models?page=2`
   - Page 2 still selected
   - Correct results shown

### Scenario 4: Complex Navigation Chain

1. **Path**: Home → List → Search → Page 2 → Detail → Back → Back → Forward
2. **Each step should**:
   - Restore correct URL
   - Update page title appropriately
   - Show correct breadcrumb
   - Display correct content

## JavaScript Event Monitoring

### htmx:historyRestore Event

1. **Fires when**: Browser back/forward used
2. **Handler should**:
   - Check current content type (list vs detail)
   - Clone appropriate template (list-breadcrumb-template or detail-breadcrumb-template)
   - Update breadcrumb container
   - Clone title template and update document.title
   - Replace PLACEHOLDER_MODEL_NAME if on detail page

### Expected Templates in DOM

1. **List templates**:
   ```html
   <template id="list-breadcrumb-template"> <template id="list-title-template"></template></template>
   ```
2. **Detail templates**:
   ```html
   <template id="detail-breadcrumb-template"> <template id="detail-title-template"></template></template>
   ```

## Title Restoration Logic

### List Page Titles

- Default: `Finding Models - Finding Model Forge`
- With search: `Search: [query] - Finding Model Forge`
- Should update via `<title>` tag in response

### Detail Page Titles

- Format: `[Model Name] - Finding Model Forge`
- Extracted from h1/h2 in content
- Updated via JavaScript on history restore

## Breadcrumb Restoration

### List Page Breadcrumb

- Structure: `Home > Finding Models`
- Home link functional
- "Finding Models" not clickable (current page)

### Detail Page Breadcrumb

- Structure: `Home > Finding Models > [Model Name]`
- Home link functional
- "Finding Models" link uses HTMX navigation
- Model name not clickable (current page)

## URL State Checks

1. **Query parameters preserved**: search, page, per_page
2. **Slugs maintained**: Model slugs in detail URLs
3. **No duplicate history entries**: Single entry per navigation
4. **HX-Push-Url header**: Updates browser URL correctly

## Console Monitoring

- Watch for `htmx:historyRestore` events
- No errors during template cloning
- No "undefined" or "null" in titles/breadcrumbs
- Successful HTMX swaps logged

## Edge Cases

1. **Rapid back/forward**: Should handle quickly without errors
2. **Deep history**: Navigate 5+ pages deep, then back to start
3. **Mixed navigation**: Combine HTMX and direct URL access
4. **Page refresh**: Refreshing should maintain current state
