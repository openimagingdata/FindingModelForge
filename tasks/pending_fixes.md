# Pending Fixes and Issues

##  Completed Fixes (2025-09-02)

### 1. Reply Functionality in Comments

- **Issue**: Reply button wasn't working because Alpine.js scopes were separated
- **Fix**: Consolidated Alpine.js data context to the comment container level, allowing the reply button to access
  `showReplyForm` variable
- **File Changed**: `templates/components/comment_thread.html`
  - Moved `x-data` to the parent comment div (line 40)
  - Replaced `action_button` macro with hardcoded button HTML
  - Fixed malformed SVG path in reply icon (changed `717 7` to `7 7`)
  - All Alpine.js variables now in same scope
- **Verified with Playwright**: Reply button appears on hover, form shows when clicked, and replies post successfully

### 2. Draft Submission Page Reload

- **Issue**: After submitting a draft, the comment section wasn't appearing without a manual page reload
- **Fix**: Changed draft submission to trigger a full page reload instead of HTMX content swap
- **File Changed**: `app/routers/drafts.py`
  - Modified `submit_draft` function to return `HX-Redirect` header for HTMX requests
  - HTMX respects the redirect header and performs full page navigation (not content swap)
  - Ensures comment thread and all components are properly initialized after submission
- **Verified with Playwright**: After submission, page correctly reloads to view mode with comment section visible

### 3. Reply Button Visibility Issue

- **Issue**: Reply buttons were not visible to users because the hover area had 0 width and height
- **Root Cause**: The hover container div only contained a hidden element (`x-show="showActions"` started as false),
  causing it to collapse
- **Fix**: Removed the hover-based visibility entirely and made Reply buttons always visible for logged-in users
- **Files Changed**: `templates/components/comment_thread.html`
  - Removed the hover container and `@mouseenter`/`@mouseleave` handlers (lines 61-72)
  - Removed `showActions` variable from Alpine.js data (line 40)
  - Made Reply button always visible for better UX
- **Verified with Playwright**: Reply buttons are now always visible, clicking them shows the reply form, and replies
  post successfully

## =' Previously Fixed Issues

### Comment System Bugs (Fixed Earlier)

1. **Draft comment permissions** - Removed incorrect user_id restriction on draft comments
2. **Template rendering errors** - Replaced non-existent `nl2br` filter with `whitespace-pre-wrap`
3. **Action button issues** - Fixed submit buttons by using hardcoded HTML instead of macro
4. **Datetime comparison** - Fixed rate limiting string-to-datetime conversion

## � Known Remaining Issues

None currently identified. All major comment system functionality is working:

- Comments on finding models 
- Comments on submitted drafts 
- Reply functionality 
- Rate limiting 
- Proper page refresh after submission 
