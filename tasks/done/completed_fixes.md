# Completed Fixes Archive

## October 2025

### Redis Startup Check (Oct 11)
- **Problem**: Server started without Redis, causing silent session failures
- **Solution**: Server now fails fast with clear error if Redis unavailable
- **Branch**: `fix/redis-startup-check`

## September 2025

### Comment System Refactor (Sept 30)
- **Problem**: Duplicate comment logic in DraftService and FindingModelService
- **Solution**: Created shared CommentService for all comment operations
- **Files**: `app/services/comment_service.py`

### Comment UI Fixes (Sept 2)

#### Reply Functionality
- **Problem**: Reply button not working due to Alpine.js scope issues
- **Solution**: Consolidated Alpine.js data context to comment container level

#### Draft Submission Page Reload
- **Problem**: Comment section not appearing after draft submission
- **Solution**: Changed to trigger full page reload via HX-Redirect header

#### Reply Button Visibility
- **Problem**: Reply buttons invisible due to collapsed hover container
- **Solution**: Made reply buttons always visible for logged-in users

### Comment System Bugs (Earlier)
- Draft comment permissions - Removed incorrect user_id restriction
- Template rendering errors - Replaced non-existent `nl2br` filter
- Action button issues - Fixed submit buttons with hardcoded HTML
- Datetime comparison - Fixed rate limiting string-to-datetime conversion
