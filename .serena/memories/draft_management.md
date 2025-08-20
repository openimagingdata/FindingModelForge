# Draft Management System

## Overview

The FindingModelForge draft system provides autosave, resume, and submission functionality for finding model creation
workflows. Drafts are stored in MongoDB with user isolation and action logging.

## Core Components

### 1. Draft Model

```python
class FindingModelDraft(BaseModel):
    id: str
    user_id: int
    name: str  # Finding model name
    created_at: datetime
    updated_at: datetime
    inputs: FindingModelInputs
    generated_json: str | None
    status: Literal["draft", "submitted"]
    action_log: list[ActionLogEntry] = []
```

### 2. DraftRepo (app/database.py)

Repository pattern for MongoDB draft operations:

```python
class DraftRepo:
    async def save_draft(
        user_id: int,
        name: str,
        inputs: FindingModelInputs,
        draft_id: str | None = None,
        generated_json: str | None = None
    ) -> FindingModelDraft

    async def get_draft(draft_id: str, user_id: int) -> FindingModelDraft | None

    async def list_for_user(user_id: int) -> list[FindingModelDraft]

    async def find_editable_by_name(user_id: int, name: str) -> FindingModelDraft | None

    async def find_latest_by_name(user_id: int, name: str) -> FindingModelDraft | None

    async def delete_draft(draft_id: str, user_id: int) -> bool

    async def submit(draft_id: str, user_id: int) -> FindingModelDraft
```

## Key Features

### 1. Autosave on Step 4

- Automatically saves draft when arriving at attributes editing step
- Preserves work in case of session loss or browser issues
- Updates existing draft if draft_id is present

### 2. Unique Draft per User/Name

- Upsert pattern: one editable draft per (user_id, name, status='draft')
- Case-insensitive name matching
- Prevents duplicate drafts for same finding model

### 3. Draft States

- **draft**: Editable, can be updated, deleted, or submitted
- **submitted**: Locked, no further edits allowed

### 4. Action Logging

Each draft maintains an action log:

- `draft.created`: Initial draft creation
- `draft.saved`: Each save operation
- `status.changed`: Submission or other status changes

### 5. Session Integration

```python
class FindingModelCreationSession:
    draft_id: str | None = None
    draft_status: str | None = None
    submitted_display_time: str | None = None
```

## Workflow Patterns

### 1. Create or Update Draft

```python
# First save (no draft_id)
draft = await draft_repo.save_draft(
    user_id=current_user.id,
    name=session.name,
    inputs=inputs,
    draft_id=None  # Creates new or updates existing by name
)

# Subsequent saves
draft = await draft_repo.save_draft(
    user_id=current_user.id,
    name=session.name,
    inputs=inputs,
    draft_id=session.draft_id  # Updates specific draft
)
```

### 2. Resume from Draft

```python
# Option A: Resume specific draft
@router.post("/drafts/resume")
async def resume_draft(draft_id: str = Form(...)):
    draft = await draft_repo.get_draft(draft_id, user_id)
    # Populate session from draft
    session.name = draft.name
    session.description = draft.inputs.description
    session.draft_id = draft.id
    # Redirect to step 4

# Option B: Find latest by name
latest = await draft_repo.find_latest_by_name(user_id, name)
if latest:
    session.draft_id = latest.id
```

### 3. Session Adoption Pattern

When session is lost but draft_id is in URL/form:

```python
draft_id = request.query_params.get("draft_id")
if draft_id and not session.attributes_markdown:
    draft = await draft_repo.get_draft(draft_id, user_id)
    if draft:
        # Adopt draft state into session
        session.name = draft.name
        session.draft_id = draft.id
        # ... populate other fields
```

### 4. Submit and Lock

```python
@router.post("/drafts/{draft_id}/submit")
async def submit_draft(draft_id: str):
    draft = await draft_repo.submit(draft_id, user_id)
    # Status changes from 'draft' to 'submitted'
    # No further edits allowed
```

## Frontend Integration

### 1. Draft ID Persistence

```html
<!-- Hidden field in forms -->
<input type="hidden" name="draft_id" value="{{ session_data.draft_id or '' }}" />

<!-- URL parameter for session recovery -->
<a href="/api/finding-models/create/step/4?draft_id={{ draft.id }}">Resume</a>
```

### 2. Draft Status Display

```jinja
{% if session_data.draft_status == 'submitted' %}
  <div class="alert-info">
    Model submitted {{ session_data.submitted_display_time }}
  </div>
{% endif %}
```

### 3. My Drafts Page

- Lists all user's drafts
- Shows status (draft/submitted)
- Provides resume/view/delete actions
- Humanized timestamps (e.g., "2 hours ago")

## Database Schema

### Collection: finding_model_drafts

```javascript
{
  _id: ObjectId,
  user_id: Number,
  name: String,
  created_at: Date,
  updated_at: Date,
  inputs: {
    description: String,
    synonyms: Array,
    attributes_markdown: String
  },
  generated_json: String | null,
  status: "draft" | "submitted",
  action_log: [
    {
      timestamp: Date,
      user_id: Number,
      action: String,
      details: Object | null
    }
  ]
}
```

### Indexes

- Compound: (user_id, name, status) - for upsert uniqueness
- Single: user_id - for user draft listing
- Single: updated_at - for sorting

## Error Handling

### 1. Invalid Draft ID

- Returns None for get operations
- Returns False for delete operations
- Raises ValueError for submit operations

### 2. Permission Checks

- All operations verify user_id ownership
- No cross-user draft access

### 3. Status Validation

- Only 'draft' status can be edited
- Only 'draft' status can be submitted
- Only 'draft' status can be deleted

## Testing Considerations

1. **Unit Tests**
   - Draft CRUD operations
   - Status transitions
   - Action logging

2. **Integration Tests**
   - Full workflow with autosave
   - Session adoption scenarios
   - Resume from draft

3. **Edge Cases**
   - Concurrent draft updates
   - Session loss and recovery
   - Invalid draft references
   - Case-insensitive name matching
