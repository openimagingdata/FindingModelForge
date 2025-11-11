# Pending Fixes and Issues

Track current bugs, technical debt, and deferred features. When fixed, move to `tasks/done/completed_fixes.md`.

## Active Issues

None currently.

## Technical Debt

### Apply Humanize Filter to Timestamps
**Priority**: Medium | **Effort**: 1 hour

The `humanize` filter exists and is registered, but most templates use `.strftime()` instead of the more user-friendly humanize filter.

**Current state**: Only `draft_preview_content.html:104` uses `| humanize`

**Files needing updates**:
- `templates/components/comment_thread.html:58` - Comment timestamps (line 58, 164)
- `templates/components/drafts/save_result.html:6` - Draft save timestamp
- `templates/components/drafts/submit_result.html:6` - Draft submit timestamp

**Expected result**: All timestamps show "2 hours ago" instead of "Nov 10" or "2025-11-10 15:30"

**Solution**:
Replace `{{ timestamp.strftime(...) }}` with `{{ timestamp | humanize }}`

---

### Comment Report Admin Interface
**Priority**: Low | **Effort**: 4-6 hours

Backend reporting is complete and functional, but there's no admin interface to review flagged comments.

**What exists**:
- ✅ `CommentService.report_comment()` - Backend method
- ✅ Router endpoints for reporting comments (drafts and finding models)
- ✅ Database tracking of `reported_by` and `reported_count`

**What's missing**:
- ❌ Admin router/endpoints to view reports
- ❌ Admin UI to review flagged comments
- ❌ Admin actions (dismiss report, remove comment, etc.)

**Solution**:
1. Create `app/routers/admin.py` with report viewing endpoints
2. Add admin authentication/authorization checks
3. Create admin UI template for reviewing reports
4. Add tests for admin workflows

---

## Guidelines

**Adding new issues:**
1. Use concise title and description
2. Include priority (Low/Medium/High) and effort estimate
3. Document current state and proposed solution
4. Reference relevant files with line numbers

**Closing issues:**
1. Move entry to `tasks/done/completed_fixes.md`
2. Include date, branch, and brief solution
