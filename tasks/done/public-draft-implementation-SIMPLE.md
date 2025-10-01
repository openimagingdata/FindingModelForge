# SIMPLIFIED Implementation: Public Draft Review

## Core Requirement

Add a "public" status between draft and submitted, with a button to make drafts public and a page to view all public
drafts.

## Essential Changes Only (1 Day Total)

### Backend Changes (2 hours)

#### 1. Add Status Enum Value

**File**: `app/models.py`

```python
class DraftStatus(str, Enum):
    DRAFT = "draft"
    PUBLIC = "public"  # ADD THIS LINE
    SUBMITTED = "submitted"
```

#### 2. Add Make-Public Endpoint (with cache invalidation)

**File**: `app/routers/drafts.py`

```python
@router.post("/drafts/{draft_id}/make-public")
async def make_draft_public(
    draft_id: str,
    session: SessionDep,
    draft_repo: DraftRepoDep,
    redis: RedisDep
):
    # Check ownership
    draft = await draft_repo.get_draft_by_id(draft_id)
    if draft.user_id != session.user_id:
        raise HTTPException(403, "Not authorized")

    # Update status
    draft.status = DraftStatus.PUBLIC
    await draft_repo.update_draft(draft)

    # Invalidate cache
    if redis:
        await redis.delete("public_drafts_list")

    return RedirectResponse(f"/drafts/{draft_id}", 303)
```

#### 3. Update View Permissions

**File**: `app/database.py` - In `get_draft_by_id()`:

```python
# Change from:
if draft.user_id != user_id and draft.status != DraftStatus.SUBMITTED:
    return None

# To:
if draft.user_id != user_id and draft.status not in [DraftStatus.PUBLIC, DraftStatus.SUBMITTED]:
    return None
```

#### 4. Update Comment Permissions

**File**: `app/services/comment_service.py` - In `can_comment()`:

```python
# Change from:
if draft.status != DraftStatus.SUBMITTED:
    return False

# To:
if draft.status not in [DraftStatus.PUBLIC, DraftStatus.SUBMITTED]:
    return False
```

#### 5. Block Non-Public Submission (with cache invalidation)

**File**: `app/routers/drafts.py` - In submit endpoint:

```python
if draft.status != DraftStatus.PUBLIC:
    raise HTTPException(400, "Draft must be made public before submission")

# After successful submission, invalidate cache
if redis:
    await redis.delete("public_drafts_list")
```

### Frontend Changes (2 hours)

#### 6. Add Make Public Button

**File**: `templates/draft_edit.html`

```html
<!-- Add after existing Save button, only show for DRAFT status -->
{% if draft.status == 'draft' %}
<form
  action="/drafts/{{ draft.id }}/make-public"
  method="POST"
  onsubmit="return confirm('Make this draft public for review? This cannot be undone.')"
>
  <button type="submit" class="text-white bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">
    Make Public for Review
  </button>
</form>
{% endif %}
```

#### 7. Create Public Drafts Table Page (with simple caching)

**File**: `app/routers/drafts.py`

```python
@router.get("/drafts")
async def public_drafts_page(
    request: Request,
    draft_repo: DraftRepoDep,
    redis: RedisDep  # Existing dependency
):
    # Try cache first (5 minute TTL)
    cache_key = "public_drafts_list"
    if redis:
        cached = await redis.get(cache_key)
        if cached:
            public_drafts = json.loads(cached)
        else:
            public_drafts = await draft_repo.get_drafts_by_status(DraftStatus.PUBLIC)
            await redis.setex(cache_key, 300, json.dumps(public_drafts, default=str))
    else:
        public_drafts = await draft_repo.get_drafts_by_status(DraftStatus.PUBLIC)

    return templates.TemplateResponse(
        "drafts_table.html",
        {"request": request, "drafts": public_drafts}
    )
```

**File**: `templates/drafts_table.html` (NEW - copy pattern from profile.html)

```html
{% extends "base.html" %} {% block content %}
<div class="max-w-6xl mx-auto px-4 py-8">
  <h1 class="text-3xl font-bold mb-6">Drafts Under Review</h1>

  <div class="overflow-x-auto">
    <table class="w-full text-sm text-left">
      <thead class="text-xs uppercase bg-gray-50">
        <tr>
          <th class="px-6 py-3">Title</th>
          <th class="px-6 py-3">Author</th>
          <th class="px-6 py-3">Created</th>
          <th class="px-6 py-3">Comments</th>
          <th class="px-6 py-3">Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for draft in drafts %}
        <tr class="bg-white border-b">
          <td class="px-6 py-4">{{ draft.name }}</td>
          <td class="px-6 py-4">{{ draft.user_name }}</td>
          <td class="px-6 py-4">{{ draft.created_at.strftime('%Y-%m-%d') }}</td>
          <td class="px-6 py-4">{{ draft.comment_count|default(0) }}</td>
          <td class="px-6 py-4">
            <a href="/drafts/{{ draft.id }}" class="text-blue-600 hover:underline"> View & Comment </a>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

#### 8. Add Navigation Link

**File**: `templates/components/navbar.html`

```html
<!-- Add to main navigation -->
<a href="/drafts" class="text-gray-700 hover:text-gray-900">Review Drafts</a>
```

### Testing (2 hours)

#### Quick Manual Test Plan

1. Create a draft
2. Click "Make Public" - verify status changes
3. Check /drafts page - verify draft appears
4. Try to comment - verify it works
5. Try to submit - verify it works
6. Try to submit a non-public draft - verify it's blocked

#### Add Basic Tests

**File**: `tests/test_public_drafts.py`

```python
def test_make_draft_public():
    # Create draft
    # Make public
    # Verify status changed

def test_public_draft_visibility():
    # Create public draft
    # Verify other user can view

def test_comment_on_public_draft():
    # Create public draft
    # Add comment as other user
    # Verify comment saved
```

## Smart Addition: Simple Caching

✅ **Redis caching for public drafts list** - High value, low effort:

- Cache the list for 5 minutes (many reads, few writes)
- Invalidate on status changes (make-public, submit)
- Adds ~5 lines of code total
- Big performance win for repeated access

## What We're NOT Building (Yet)

- ❌ Archive system (add if needed later)
- ❌ Complex timestamps and tracking fields
- ❌ Email notifications
- ❌ Activity tracking
- ❌ Feature flags
- ❌ Migration scripts
- ❌ Denormalized fields

## Timeline

- **Morning**: Backend changes (4 endpoints/methods)
- **Afternoon**: Frontend changes (1 button, 1 page)
- **Next Morning**: Testing and polish

## Total Effort: ~6-8 hours of actual coding

This is the MVP. Ship it, get feedback, iterate.

---

## FIXES NEEDED (Post-MVP Issues)

### Issue 1: Author Edit Access for Public Drafts

**Problem**: Authors can't edit their own public drafts **Solution**:

- **Backend**: Update `unified_draft_page` endpoint to allow edit mode for draft owner regardless of public status
- **Frontend**: Show edit button/link for draft owner even when status is public
- **Delegation**: Frontend/UI agent
- **Test**: Verify author can edit public draft, non-owner cannot

### Issue 2: Delete Public Drafts

**Problem**: Authors can't delete public drafts **Solution**:

- **Backend**: Update `delete_draft` in DraftRepo to allow deletion of PUBLIC status drafts
- **Frontend**: Show delete button for both DRAFT and PUBLIC status (when user is owner)
- **Delegation**: Backend agent for repo change, Frontend agent for UI
- **Test**: Verify author can delete public draft, submitted drafts still protected

### Issue 3: Author Information on Preview Page

**Problem**: Draft preview doesn't show author name **Solution**:

- **Backend**: Add MongoDB aggregation pipeline to join with people collection when fetching single draft
- **Frontend**: Display author name in draft preview template
- **Delegation**: Backend agent for data fetching, Frontend agent for display
- **Test**: Verify author name appears on draft preview page

### Issue 4: Context-Aware Breadcrumbs

**Problem**: Breadcrumbs always go to profile, not back to public drafts list **Solution**:

- **Frontend**: Add `?from=public` parameter when linking from public drafts table
- **Frontend**: Check parameter in draft preview template to show correct breadcrumb
- **Delegation**: Frontend/UI agent
- **Test**: Navigate from /drafts, verify breadcrumb goes back to "Public Drafts"

### Issue 5: Date Display in Public Drafts Table

**Problem**: Created date shows "N/A" instead of actual date **Solution**:

- **Backend**: Ensure `created_at` field is included in query and properly formatted
- **Backend**: Format date in backend before sending to template (avoid strftime in template)
- **Delegation**: Backend agent
- **Test**: Verify dates display correctly in public drafts table

### Issue 6: Clickable Table Rows

**Problem**: Need separate "View & Comment" link instead of clickable rows **Solution**:

- **Frontend**: Remove Actions column, make entire row clickable with Alpine.js
- **Frontend**: Add hover effects and cursor pointer
- **Delegation**: Frontend/UI agent
- **Test**: Click anywhere on row, verify navigation to draft

### Issue 7: Navbar Text

**Problem**: Link text should be "Drafts" not "Review Drafts" **Solution**:

- **Frontend**: Change navbar text to just "Drafts"
- **Delegation**: Frontend/UI agent
- **Test**: Visual verification of navbar

## Implementation Order

1. Backend fixes first (Issues 2, 3, 5)
2. Frontend fixes second (Issues 1, 4, 6, 7)
3. Comprehensive testing

## Testing Strategy

- **Unit tests**: Backend permission and data fetching changes
- **UI tests**: Navigation flows, edit access, clickable rows
- **Manual testing**: Full workflow from creation to submission
