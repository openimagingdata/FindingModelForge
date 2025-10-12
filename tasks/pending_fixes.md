# Pending Fixes and Issues

Track current bugs, technical debt, and deferred features. When fixed, move to `tasks/done/completed_fixes.md`.

## Active Issues

None currently.

## Technical Debt

### Humanize Filter for Dates
**Priority**: Medium | **Effort**: 2-3 hours

Templates reference `| humanize` filter that doesn't exist. Causes errors when rendering dates.

**Files affected**: `templates/components/comment_thread.html`, others

**Solution**:
1. `uv add humanize`
2. Add filter to `app/templates.py`
3. Apply consistently across date displays

---

### Repository Pattern Violation
**Priority**: Low | **Effort**: 1 hour

`add_to_comment_index()` directly calls `user_repo.collection.update_one()` instead of using repository method.

**Solution**: Add `add_comment_index_entry()` method to UserRepo

---

## Deferred Features

### Comment Report Admin Interface
**Priority**: Low | **Effort**: 4-6 hours

Backend has `report_comment()` but no router integration or admin interface.

**Solution**:
1. Add report endpoints to routers
2. Create admin interface for reviewing reports
3. Add tests for reporting flow

---

### Future Comment Enhancements
**Priority**: Low | **Effort**: Large

Potential features:
- Pagination for threads with > 100 comments
- Rich text/markdown editor
- Email notifications for replies
- Sort order toggle
- Comment editing with history
- Voting/reactions

---

## Guidelines

**Adding new issues:**
1. Use concise title and description
2. Include priority (Low/Medium/High) and effort estimate
3. Document current state and proposed solution
4. Reference relevant files

**Closing issues:**
1. Move entry to `tasks/done/completed_fixes.md`
2. Include date, branch, and brief solution
