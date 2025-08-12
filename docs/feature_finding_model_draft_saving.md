# Finding Model Draft Saving & Submission Workflow

## Overview

This document outlines the requirements, data model, and workflow for saving, editing, and submitting Finding Model
drafts in FindingModelForge. It will be updated as the feature is developed.

---

## Goals

- Allow users to save their in-progress Finding Model as a draft only at the Edit Attributes stage of the creation
  workflow.
- Store all relevant user input and metadata in MongoDB.
- Enable users to view, resume, and edit their drafts from the "Edit Attributes" step.
- Submitting for review sets status to submitted and freezes the draft from further editing.
- Ensure drafts are only visible/editable by their creator.

---

## Requirements

### Functional

- [ ] Save draft only at the Edit Attributes step in the creation workflow (manual save via button)
- [ ] Store all user input/state (attributes, synonyms, description, etc.)
- [ ] List user's drafts on their profile page in a data table with columns: Finding Name, Attribute Names, Status, Date
      (last updated)
- [ ] Resume editing a draft (load state into workflow)
- [ ] Submit for review action sets status to "submitted" and freezes draft
- [ ] Prevent editing after submission
- [ ] Only creator can view/edit their drafts

### Non-Functional

- [ ] Async DB operations (Motor)
- [ ] Pydantic models for draft schema
- [ ] Proper error handling and logging
- [ ] Comprehensive tests

---

## Data Model (Draft)

```python
from typing import Literal
from pydantic import BaseModel, Field

class FindingModelInputs(BaseModel):
    description: str
    synonyms: list[str] | None = None
    attributes_markdown: str | None = None

class LogEntry(BaseModel):
    timestamp: datetime
    user_id: str
    action: str
    details: dict | None = None

class FindingModelDraft(BaseModel):
    id: PyObjectId  # MongoDB ObjectId
    user_id: str
    finding_name: str
    created_at: datetime
    updated_at: datetime
    inputs: FindingModelInputs
    status: Literal["draft", "submitted", "under-review", "added", "declined"] = "draft"
    action_log: list[LogEntry] = Field(default_factory=list)
    # Additional metadata as needed
```

---

## Workflow

1. **User creates or resumes a Finding Model**
2. **At the Edit Attributes step, user can save as draft**
   - Manual save via button; on click, state is persisted to MongoDB
3. **User can view list of their drafts, submitted, and authored models**
   - Data table view (like /finding-models page), grouped by status
   - Columns: Finding Name, Attribute Names, Status, Date (last updated)
   - When user clicks a row, they get taken to the Edit Attributes stage of the create
4. **User resumes a draft**
   - State loaded into workflow (Edit Attributes step)
5. **User changes status to "submitted"**
   - Draft is frozen (no further edits allowed)
   - Status can progress to "under-review", "added", or "declined" by admins
6. **Drafts are only visible/editable by creator**
7. **Deletion policy**
   - Drafts can be deleted while in status "draft" only
   - After status becomes "submitted" (or later), deletion is disabled

---

## UI/UX Notes

- Draft save button only at Edit Attributes and Final Review steps
- User profile page shows:
  - Profile info in a closed accordion
  - Data table listing all finding models user is involved in, grouped by status (draft, submitted, under-review, added,
    declined)
  - Table uses Flowbite data table (like /finding-models)
  - Table columns: Finding Name | Attribute Names | Status | Date
  - Actions: resume/edit/delete (for drafts), view (for others); delete disabled once submitted
- "Submit for review" action sets status to "submitted" and freezes editing
- Error and success feedback

---

## Action Log (minimal v1)

Actions to record with timestamp and user_id:

- draft.created
- draft.saved
- draft.opened
- draft.deleted (only when status="draft")
- status.changed (details: from_status, to_status)

Details payload examples:

- status.changed: { from_status: "draft", to_status: "submitted" }
- draft.saved: { step: "edit-attributes" }

---

## Next Steps

- Finalize data model
- Plan API endpoints and UI changes
- Implement draft save/load logic
- Add tests and documentation

---

## Implementation blueprint & decisions needed

Routes (Jinja2 + HTMX; HTML responses only):

- GET /profile -> render full page with involvement table (no JSON)
- POST /drafts/save -> manual Save Draft from Edit Attributes; returns small HTML fragment (toast or banner), may
  include draft_id in a hidden input via oob
- POST /drafts/{id}/submit -> submit for review; returns fragment to reflect "submitted" and disable editing controls
- POST /drafts/{id}/delete -> delete draft (only when status=draft); returns 204 or a fragment that removes/replaces the
  table row
- GET /drafts/row/{id} (optional) -> return a single table row fragment for row-level refreshes

DB shape (Mongo):

- Collection: finding_model_drafts
- Indexes: user_id (asc), updated_at (desc), status (asc)
- Document: matches FindingModelDraft; store action_log entries append-only

Permissions:

- Owner-only read/write/delete for drafts
- Submit action allowed only by owner and only from status=draft
- Admins can transition statuses beyond submitted (under-review -> added/declined)

Profile page wiring:

- Server-rendered Flowbite data table (drafts + submitted + authored)
- Columns: Finding Name | Attribute Names | Status | Date
- Row click (drafts) links to Create Workflow at Edit Attributes with draft_id parameter
- Delete button only for status=draft; Flowbite modal + hx-post to /drafts/{id}/delete; on success, remove row

Create workflow wiring:

- At Edit Attributes, show Save Draft button -> hx-post to /drafts/save (form-encoded), include draft_id if present
- On success: show toast/banner; keep draft_id (in hidden input/state) for subsequent saves
- Submit for review button -> hx-post to /drafts/{id}/submit; disable inputs on success

---

## DraftRepo repository (with cache)

Purpose

- Encapsulate MongoDB operations for drafts and apply simple, safe caching.
- Mirror the pattern of UserRepo and RedisCache with draft-specific helpers.

Collection & indexes

- Collection name: finding_model_drafts
- Indexes:
  - { user_id: 1, updated_at: -1 }
  - { status: 1, updated_at: -1 }
  - Unique: { user_id: 1, "finding_name": 1 }

Class outline

```python
from datetime import UTC, datetime
from typing import Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

class DraftRepo:
        def __init__(self, db: AsyncIOMotorDatabase[Any]) -> None:
                self.db = db
                self.collection = db.finding_model_drafts

        async def save_draft(
                self,
                user_id: int,
                inputs: FindingModelInputs,
                draft_id: str | None,
        ) -> FindingModelDraft:
                """Create new or update existing draft owned by user.
                - If draft_id is None: insert new with status="draft"
                - If present: update state; enforce owner and status in ["draft"]
                - Always update updated_at and append action_log entry
                """

        async def get_draft(self, draft_id: str, user_id: int) -> FindingModelDraft | None:
                """Return draft if owned by user; otherwise None."""

        async def list_for_user(self, user_id: int) -> list[FindingModelDraft]:
                """All drafts/models the user is involved in (start with owned drafts)."""

        async def delete_draft(self, draft_id: str, user_id: int) -> bool:
                """Delete only when status == "draft" and owner matches."""

        async def submit(self, draft_id: str, user_id: int) -> FindingModelDraft:
                """Transition from draft -> submitted, freeze further edits, append action_log."""
```

Caching strategy (RedisCache)

- Keys:
  - draft:{id}
  - drafts_by_user:{user_id}
- Read flow:
  - get_draft: hit draft:{id}; on miss, load from DB, then cache
  - list_for_user: hit drafts_by_user:{user_id}; on miss, query and cache (short TTL)
- Write/transition flow (save/submit/delete):
  - Invalidate draft:{id} and drafts_by_user:{user_id}
  - Optionally set fresh values after write
- TTLs:
  - draft:{id}: ~300s (5m)
  - drafts_by_user:{user_id}: ~120s (2m)
- Cache is optional; failures are no-ops (consistent with existing cache behavior)

Proposed RedisCache helpers (to add later)

```python
async def get_draft(self, draft_id: str) -> FindingModelDraft | None: ...
async def set_draft(self, draft_id: str, draft: FindingModelDraft, expires_in: timedelta | None = None) -> bool: ...
async def delete_draft(self, draft_id: str) -> bool: ...
async def get_user_drafts(self, user_id: int) -> list[dict[str, Any]] | None: ...
async def set_user_drafts(self, user_id: int, drafts: list[dict[str, Any]], expires_in: timedelta | None = None) -> bool: ...
```

Action logging in repo

- On save: append LogEntry(action="draft.saved", details={"step":"edit-attributes"})
- On submit: append LogEntry(action="status.changed", details={"from_status":"draft","to_status":"submitted"})
- On delete: append LogEntry(action="draft.deleted") before removal (optional, or store in an audit collection)

Permissions & guards

- Owner-only access for get/update/delete/submit
- delete allowed only when status == draft
- submit allowed only when status == draft
- All updates set updated_at = now (UTC)

Dependency wiring (planning only)

- Database gains: draft_repo: DraftRepo | None
- During Database.connect(): self.draft_repo = DraftRepo(self.db)
- Add get_draft_repo() in dependencies.py with Annotated alias (mirrors UserRepoDep)

Tests

- Unit: save_draft (new vs update), get_draft ownership, delete rules, submit transition
- Integration: HTMX flows (save, list, resume, submit, delete)
- Cache: verify read-through on miss and invalidation on writes; behavior is no-op when Redis disabled

Tests:

- Unit: model validation, status transitions, permission checks
- Integration: save draft, list drafts, resume, submit, forbid edits after submit, delete only in draft
- UI (Playwright): save button behavior, list rendering, resume navigation, delete disabled post-submit

Open decisions to confirm:

- Name source of Finding Name and Attribute Names for list (from state.name and parsed attribute titles from
  attributes_markdown?)
- Do we allow multiple drafts per user per finding name, or enforce uniqueness by (user_id, state.name)?
- Do we keep an activity cap for action_log (e.g., last 100 entries) or allow unbounded?
