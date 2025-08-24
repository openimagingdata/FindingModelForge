# Test Script: Finding Models List Page

## Overview

This script documents the expected behavior and elements for the Finding Models list page, including search and
pagination functionality.

## Test URL

`http://localhost:8000/finding-models`

## Expected Page Elements

### Initial Load

1. **Page Title**: `Finding Models - Finding Model Forge`
2. **Main Heading**: `<h1>Finding Models</h1>`
3. **Breadcrumb**: `Home > Finding Models` (Home should be clickable)
4. **Search Input**:
   - Placeholder: "Search finding models..."
   - Located in top section with magnifying glass icon
   - Compact size (p-2.5 padding)
5. **Table Structure**:
   - Headers: ID | Name
   - Rows are clickable (cursor-pointer class)
   - Alternating row colors (odd/even)

### Search Interaction

1. **Type in search box**: "test"
2. **Expected behavior**:
   - 500ms delay before request (debounce)
   - URL updates to `/finding-models?search=test`
   - Page title changes to: `Search: test - Finding Model Forge`
   - Results update in place (no full page reload)
   - Shows "Showing X to Y of Z results for 'test'"
3. **Empty search results**:
   - Shows: "No finding models found matching 'test'"

### Pagination (if more than 20 items)

1. **Pagination controls**: Located top-right
2. **Elements**:
   - Previous button (disabled on page 1)
   - Page numbers (current page highlighted in blue)
   - Next button (disabled on last page)
3. **Clicking page 2**:
   - URL updates to `/finding-models?page=2`
   - Content swaps via HTMX
   - Shows "Showing 21 to 40 of X results"

### Table Row Click

1. **Click any table row**
2. **Expected behavior**:
   - HTMX navigation (no full page reload)
   - Content swaps into #main-content
   - URL updates to `/finding-models/{slug}`
   - Breadcrumb updates to: `Home > Finding Models > [Model Name]`
   - Page title changes to: `[Model Name] - Finding Model Forge`

## Console Checks

- No JavaScript errors
- No "applyStyles$1" errors
- No Flowbite initialization errors
- No Alpine.js errors

## HTMX Verification

- All navigation uses HTMX (check for htmx-request class during transitions)
- Content swaps into `#main-content` div
- HX-Push-Url header updates browser URL

## Dark Mode

- Toggle dark mode button in navbar
- Table should maintain readability in dark mode
- Search input should have dark styling

## Mobile Responsive

- Search input should stack above pagination on mobile
- Table should be horizontally scrollable if needed
- Breadcrumb should remain visible
