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

## 🔍 Known Remaining Issues

### 1. **CRITICAL: Server Should Fail to Start Without Redis**

**Issue**: The creation workflow absolutely requires Redis for session management, but the server starts successfully even when Redis is unavailable. This causes silent failures where:
- Sessions are saved but not persisted (cache operations return `True` but do nothing)
- New sessions are created on every request
- Users see "Session name must be set before processing step 2" errors
- The actual problem (Redis down) is hidden behind cryptic workflow errors

**Root Cause**: 
- `RedisCache.connect()` catches connection failures and logs a warning but doesn't fail
- Cache operations return success (`True`) even when Redis is disconnected
- This "graceful degradation" approach works for optional caching but NOT for critical session management

**Impact**: Production-breaking - creation workflow completely broken when Redis is down

**Fix Needed**:
1. Add startup health check in `app/main.py` `lifespan()` function
2. If Redis is enabled (`settings.redis_enabled`) but connection fails, **raise exception to prevent server startup**
3. Session management is NOT optional - fail fast rather than silent failure

**Code Location**:
- `app/cache.py` - `RedisCache.connect()` line ~45-60 (currently catches and logs)
- `app/main.py` - `lifespan()` function line ~40-55 (needs health check after `await cache.connect()`)

**Suggested Implementation**:
```python
# In app/main.py lifespan() function after cache.connect():
if settings.redis_enabled:
    await cache.connect()
    if not await cache.is_healthy():
        raise RuntimeError(
            "Redis connection required but unavailable. "
            "Session management will not work. "
            "Check REDIS_HOST/REDIS_PORT settings or disable with REDIS_ENABLED=false"
        )
    logger.info("Redis cache initialized and healthy")
```

**Priority**: 🔴 HIGH - Should be fixed before next deployment

---

### Previous Issues (All Resolved)

- Comments on finding models ✅
- Comments on submitted drafts ✅
- Reply functionality ✅
- Rate limiting ✅
- Proper page refresh after submission ✅
