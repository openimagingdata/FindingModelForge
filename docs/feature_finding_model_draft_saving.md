# Finding Model Draft Saving & Submission Workflow

## Overview

This document outlines the requirements, data model, and workflow for saving, editing, and submitting Finding Model
drafts in FindingModelForge. It will be updated as the feature is developed.

---

## Goals

- Allow users to save their in-progress Finding Model as a draft at the Edit Attributes stage of the creation workflow.
  Note: Implementation currently supports autosave when entering step 4 and on changes; a manual Save button endpoint
  also exists.
- Store all relevant user input and metadata in MongoDB.
- Enable users to view, resume, and edit their drafts from the "Edit Attributes" step.
- Submitting for review sets status to submitted and freezes the draft from further editing.
- Ensure drafts are only visible/editable by their creator.

---

## Requirements

### Functional

- [x] Save draft at the Edit Attributes step. Implemented as:
  - Autosave when entering step 4 and after step 2/3 transitions
  - Autosave on changes to description/attributes via HTMX triggers
  - Manual save endpoint exists at POST /api/finding-models/drafts/save
- [x] Store user input/state (attributes, synonyms, description, generated JSON) in MongoDB via DraftRepo
- [ ] List user's drafts on profile page in data table (Finding Name, Attribute Names, Status, Date)
- [x] Resume editing a draft (auto-resume by name into step 4; resume submitted into step 5 read-only)
- [x] Submit for review sets status to "submitted" and freezes draft
- [x] Prevent editing after submission (UI gating and server-side guards)
- [x] Only creator can view/edit their drafts (enforced in DraftRepo queries)

### Non-Functional

- [x] Async DB operations (Motor via DraftRepo)
- [x] Pydantic models for draft schema (FindingModelInputs, FindingModelDraft, LogEntry)
- [x] Proper error handling and logging (FastAPI HTTPException, logger warnings/errors)
- [x] Comprehensive tests (HTMX flow tests for step 4 and drafts, DraftRepo query tests)

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
  user_id: int
  action: str
  details: dict | None = None

class FindingModelDraft(BaseModel):
  id: str  # MongoDB ObjectId as hex string
  user_id: int
  name: str
  created_at: datetime
  updated_at: datetime
  inputs: FindingModelInputs
  generated_json: str | None = None
  status: Literal["draft", "submitted", "under-review", "added", "declined"] = "draft"
  action_log: list[LogEntry] = Field(default_factory=list)
```

---

## Workflow

1. **User creates or resumes a Finding Model**
2. **At the Edit Attributes step, draft is saved**

- Autosave on entering step 4 (and when arriving from step 2/3)
- Autosave on changes (HTMX hx-trigger change/keyup with debounce)
- Manual save via POST /api/finding-models/drafts/save also available

3. **User can view list of their drafts, submitted, and authored models**

- PENDING: Profile page table not yet implemented
- Planned: Flowbite data table with Columns: Finding Name, Attribute Names, Status, Date (last updated)
- Planned: Row click resumes to the appropriate step (4 for drafts, 5 for submitted)

4. **User resumes a draft**
   - State loaded into workflow (Edit Attributes step)
5. **User changes status to "submitted"**

- Implemented: POST /api/finding-models/drafts/{id}/submit; draft is frozen (UI + server)
- Status can later progress to "under-review", "added", or "declined" by admins (not implemented yet)

6. **Drafts are only visible/editable by creator**
7. **Deletion policy**

- Implemented: POST /api/finding-models/drafts/{id}/delete only when status="draft"
- After status becomes "submitted" (or later), deletion is disabled

---

## UI/UX Notes

- Draft autosave active at Edit Attributes; manual Save Draft endpoint wired via hidden HTMX div
- User profile page shows:
  - Profile info in a closed accordion
  - PENDING: Data table listing all finding models user is involved in, grouped by status (draft, submitted,
    under-review, added, declined)
  - Table uses Flowbite data table (like /finding-models)
  - Table columns: Finding Name | Attribute Names | Status | Date
  - Actions: resume/edit/delete (for drafts), view (for others); delete disabled once submitted
- "Submit for review" action sets status to "submitted" and freezes editing (implemented)
- Error and success feedback

---

## Action Log (minimal v1)

Actions to record with timestamp and user_id:

- draft.created (on first upsert)
- draft.saved (on each save)
- draft.opened (planned)
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

## Implementation status, blueprint & decisions

Routes (Jinja2 + HTMX; HTML responses only):

- [x] POST /api/finding-models/drafts/save -> Save Draft (returns fragment `components/drafts/save_result.html`)
- [x] POST /api/finding-models/drafts/{id}/submit -> Submit for review; re-renders Step 5 with IDs/JSON visible
- [x] POST /api/finding-models/drafts/{id}/delete -> Delete draft; returns fragment
      `components/drafts/delete_result.html`
- [x] GET/POST /api/finding-models/create/step/\* -> HTMX step routes including autosave logic
- [ ] GET /profile -> add drafts table (grouped by status) with resume/delete actions
- [ ] GET /drafts/row/{id} (optional) -> return a single table row fragment for row-level refreshes

DB shape (Mongo):

- Collection: finding_model_drafts
- Indexes: To add (follow-up): user_id (asc), updated_at (desc), status (asc), and optionally unique (user_id, name,
  status='draft')
- Document: matches FindingModelDraft; action_log append-only; stores generated_json when available

Permissions:

- Owner-only read/write/delete for drafts (enforced in queries)
- Submit allowed only by owner and only from status=draft (enforced by filter)
- Admin status transitions beyond submitted: not implemented

Profile page wiring:

- PENDING: Server-rendered Flowbite data table (drafts + submitted + authored)
- Columns: Finding Name | Attribute Names | Status | Date
- Row click (drafts) links to Create Workflow at Edit Attributes with draft_id parameter
- Delete button only for status=draft; Flowbite modal + hx-post to /drafts/{id}/delete; on success, remove row

Create workflow wiring:

- Edit Attributes autosaves on entry and change events; manual save endpoint is wired via hidden div to update an
  actions area
- On success: UI shows small saved/submit/delete fragments; session keeps draft_id for subsequent saves
- Submit for review button -> posts to /drafts/{id}/submit; disables inputs on success and shows IDs/JSON on final view

---

## DraftRepo repository (with cache)

Purpose

- Encapsulate MongoDB operations for drafts. Caching TBD (not yet implemented in RedisCache).

Collection & indexes

- Collection name: finding_model_drafts
- Suggested Indexes (follow-up):
  - { user_id: 1, updated_at: -1 }
  - { status: 1, updated_at: -1 }
  - Unique (editable drafts): { user_id: 1, name: 1, status: 1 } with status="draft"

Class status and outline

```python
from datetime import UTC, datetime
from typing import Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

class DraftRepo:
  # Implemented with methods: save_draft, get_draft, list_for_user, find_editable_by_name, find_latest_by_name,
  # delete_draft, submit. Upsert logic ensures at most one editable draft per (user_id, name).
```

Caching strategy (RedisCache)

- Not implemented yet. Proposed for follow-up:
  - Keys:
    - draft:{id}
    - drafts_by_user:{user_id}
  - Invalidate on save/submit/delete; short TTLs (5m/2m).
  - Fail-open semantics consistent with existing cache behavior.

Proposed RedisCache helpers (to add later)

```python
async def get_draft(self, draft_id: str) -> FindingModelDraft | None: ...
async def set_draft(self, draft_id: str, draft: FindingModelDraft, expires_in: timedelta | None = None) -> bool: ...
async def delete_draft(self, draft_id: str) -> bool: ...
async def get_user_drafts(self, user_id: int) -> list[dict[str, Any]] | None: ...
async def set_user_drafts(self, user_id: int, drafts: list[dict[str, Any]], expires_in: timedelta | None = None) -> bool: ...
```

Action logging in repo

- Implemented:
  - On insert: draft.created + draft.saved
  - On update: draft.saved
  - On submit: status.changed {from:draft,to:submitted}
  - Delete currently hard-deletes without logging (optional follow-up: pre-delete log or audit collection)

Permissions & guards

- Enforced:
  - Owner-only access for get/update/delete/submit via query filters
  - delete allowed only when status == draft
  - submit allowed only when status == draft
  - All updates set updated_at = now (UTC)

Dependency wiring

- Implemented: Database.connect() wires DraftRepo; get_draft_repo() provided in dependencies.py

Tests

- Implemented:
  - HTMX flows: step 4 generation, save, submit, delete endpoints
  - DraftRepo query helpers unit tests (find_latest_by_name, find_editable_by_name)
- Pending:
  - Full DraftRepo integration tests against MongoDB
  - Profile list UI tests (Playwright)
  - Cache behavior tests once added

Tests:

- Unit: model validation, status transitions, permission checks
- Integration: save draft, list drafts, resume, submit, forbid edits after submit, delete only in draft
- UI (Playwright): save button behavior, list rendering, resume navigation, delete disabled post-submit

Decisions (updated):

- Attribute Names: Extract from the generated JSON associated with the draft (preferred over parsing markdown).
- Uniqueness: Enforce one draft per user/finding name combination. For editable drafts, maintain uniqueness on (user_id,
  name, status='draft'); submitted drafts retain historical records.
- Action log: Not a priority right now—no cap or special handling needed at this time.
