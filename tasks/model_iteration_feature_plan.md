# Model Iteration Feature - Implementation Plan

**Status**: Planning - Under Review
**Created**: 2025-10-29
**Last Updated**: 2025-10-29
**Branch**: TBD

---

## 🎯 Feature Overview

Add capability for users to create **iterations** of existing published finding models through AI-assisted editing paths.

### Two Iteration Methods

1. **Natural Language Iteration**: User submits text prompts describing desired changes
2. **Markdown Edit Iteration**: AI exports model to markdown, user edits, AI applies changes back

**Key Distinction**: Iterations are AI-assisted ONLY. Users cannot manually edit iteration drafts - they must use AI tools or create a brand new model from scratch.

### Requirements

- ✅ Name remains the same as base model
- ✅ One iteration draft per user per published model
- ✅ Full audit trail: prompts + AI responses + changes + rejections
- ✅ Multiple refinement rounds (iterative)
- ✅ Same workflow: draft → public → submitted
- ❌ NO manual editing of iteration drafts

---

## 🏗️ Architecture Changes

### 1. Data Model Extensions

**File**: `app/models.py`

```python
class IterationInteraction(BaseModel):
    """Record of a single AI iteration operation."""
    timestamp: datetime
    user_id: int
    interaction_type: Literal["natural_language", "markdown_edit"]
    user_input: str  # User's prompt or edited markdown
    changes_applied: list[str] = Field(default_factory=list)  # From EditResult.changes
    changes_rejected: list[str] = Field(default_factory=list)  # From EditResult.rejections
    success: bool = True
    error_message: str | None = None

class FindingModelDraft(BaseModel):
    # ... existing fields ...

    # NEW: Iteration tracking
    is_iteration: bool = False
    base_model_id: str | None = None  # oifm_id of model being iterated

    # NEW: AI interaction history (only for iterations)
    iteration_history: list[IterationInteraction] = Field(default_factory=list)
```

**Migration Notes**:
- No MongoDB migration needed (optional fields with defaults)
- Existing drafts will have `is_iteration=False` by default
- `iteration_history` only used when `is_iteration=True`

---

### 2. Database Changes

**File**: `app/database.py` - `DraftRepo` class

#### Uniqueness Constraint Update

Support TWO types of drafts simultaneously:
- **Creation Draft**: `is_iteration=False`, one per `(user_id, name, status='draft')`
- **Iteration Draft**: `is_iteration=True`, one per `(user_id, base_model_id, status='draft')`

```python
class DraftRepo:
    async def upsert_draft(..., is_iteration: bool = False, base_model_id: str | None = None):
        """Create or update draft with proper uniqueness handling."""
        if is_iteration:
            # Iteration drafts: unique by (user_id, base_model_id, status)
            filter_query = {
                "user_id": user_id,
                "base_model_id": base_model_id,
                "status": "draft",
                "is_iteration": True
            }
        else:
            # Creation drafts: unique by (user_id, name, status)
            filter_query = {
                "user_id": user_id,
                "name": name,
                "status": "draft",
                "is_iteration": False
            }
        # ... rest of upsert logic
```

#### New Methods

```python
class DraftRepo:
    async def get_iteration_draft(
        self,
        user_id: int,
        base_model_id: str
    ) -> FindingModelDraft | None:
        """Get user's iteration draft for a specific model."""
        return await self.db.finding_model_drafts.find_one({
            "user_id": user_id,
            "base_model_id": base_model_id,
            "status": "draft",
            "is_iteration": True
        })

    async def add_iteration_interaction(
        self,
        draft_id: str,
        interaction: IterationInteraction
    ) -> None:
        """Append interaction to draft's iteration history."""
        await self.db.finding_model_drafts.update_one(
            {"_id": ObjectId(draft_id)},
            {"$push": {"iteration_history": interaction.model_dump()}}
        )
```

---

### 3. Service Layer

**New File**: `app/services/iteration_service.py`

```python
from typing import Annotated
from fastapi import Depends
from app.database import DraftRepo
from app.models import FindingModelDraft, IterationInteraction
from findingmodel import FindingModelFull
from findingmodel.tools import (
    edit_model_natural_language,
    edit_model_markdown,
    export_model_for_editing,
)
import json
from datetime import datetime, UTC

class IterationService:
    """Service for AI-assisted model iterations."""

    def __init__(self, draft_repo: Annotated[DraftRepo, Depends()]):
        self.draft_repo = draft_repo

    async def start_iteration(
        self,
        user_id: int,
        base_model_id: str,
        published_model_json: str
    ) -> FindingModelDraft:
        """
        Create or retrieve iteration draft.

        Args:
            user_id: GitHub user ID
            base_model_id: oifm_id of published model
            published_model_json: Full JSON of published model

        Returns:
            Existing or newly created iteration draft
        """
        # Check for existing iteration draft
        existing = await self.draft_repo.get_iteration_draft(user_id, base_model_id)
        if existing:
            return existing

        # Parse model to extract name
        model_data = json.loads(published_model_json)

        # Create new iteration draft
        # Note: Placeholder inputs required by draft schema
        # These are not used for iteration drafts (AI-only editing)
        draft = await self.draft_repo.create_draft(
            user_id=user_id,
            name=model_data["name"],
            inputs=FindingModelInputs(
                description="",  # Empty - not used for iterations
                synonyms=None,
                attributes_markdown=None
            ),
            is_iteration=True,
            base_model_id=base_model_id,
            generated_json=published_model_json,
            status=DraftStatus.DRAFT
        )

        return draft

    async def iterate_natural_language(
        self,
        draft_id: str,
        user_id: int,
        user_request: str
    ) -> dict:
        """
        Apply natural language iteration request.

        Args:
            draft_id: Draft to iterate
            user_id: User making request
            user_request: Natural language description of changes

        Returns:
            Dict with success, changes, rejections, error
        """
        draft = await self.draft_repo.get_draft(draft_id, user_id)
        if not draft or not draft.is_iteration:
            raise ValueError("Invalid iteration draft")

        # Parse current model
        current_model = FindingModelFull.model_validate_json(draft.generated_json)

        try:
            # Call findingmodel tool (async)
            edit_result = await edit_model_natural_language(
                model=current_model,
                command=user_request
            )

            # Save interaction
            interaction = IterationInteraction(
                timestamp=datetime.now(UTC),
                user_id=user_id,
                interaction_type="natural_language",
                user_input=user_request,
                changes_applied=edit_result.changes,
                changes_rejected=edit_result.rejections,
                success=True
            )

            # Update draft with new model
            updated_json = edit_result.model.model_dump_json(indent=2)
            await self.draft_repo.update_draft(
                draft_id,
                generated_json=updated_json
            )
            await self.draft_repo.add_iteration_interaction(draft_id, interaction)

            return {
                "success": True,
                "changes": edit_result.changes,
                "rejections": edit_result.rejections,
                "error": None
            }

        except Exception as e:
            # Log failed attempt
            interaction = IterationInteraction(
                timestamp=datetime.now(UTC),
                user_id=user_id,
                interaction_type="natural_language",
                user_input=user_request,
                changes_applied=[],
                changes_rejected=[],
                success=False,
                error_message=str(e)
            )
            await self.draft_repo.add_iteration_interaction(draft_id, interaction)

            return {
                "success": False,
                "changes": [],
                "rejections": [],
                "error": str(e)
            }

    async def export_for_editing(
        self,
        draft_id: str,
        user_id: int
    ) -> str:
        """
        Export model to editable markdown format.

        Args:
            draft_id: Draft to export
            user_id: User making request

        Returns:
            Markdown text representation
        """
        draft = await self.draft_repo.get_draft(draft_id, user_id)
        if not draft or not draft.is_iteration:
            raise ValueError("Invalid iteration draft")

        model = FindingModelFull.model_validate_json(draft.generated_json)
        return export_model_for_editing(model)

    async def iterate_markdown(
        self,
        draft_id: str,
        user_id: int,
        edited_markdown: str
    ) -> dict:
        """
        Apply changes from edited markdown.

        Args:
            draft_id: Draft to update
            user_id: User making changes
            edited_markdown: User's edited markdown

        Returns:
            Dict with success, changes, rejections, error
        """
        draft = await self.draft_repo.get_draft(draft_id, user_id)
        if not draft or not draft.is_iteration:
            raise ValueError("Invalid iteration draft")

        current_model = FindingModelFull.model_validate_json(draft.generated_json)

        try:
            # Call findingmodel tool (async)
            edit_result = await edit_model_markdown(
                model=current_model,
                edited_markdown=edited_markdown
            )

            # Save interaction
            interaction = IterationInteraction(
                timestamp=datetime.now(UTC),
                user_id=user_id,
                interaction_type="markdown_edit",
                user_input=edited_markdown,
                changes_applied=edit_result.changes,
                changes_rejected=edit_result.rejections,
                success=True
            )

            # Update draft
            updated_json = edit_result.model.model_dump_json(indent=2)
            await self.draft_repo.update_draft(
                draft_id,
                generated_json=updated_json
            )
            await self.draft_repo.add_iteration_interaction(draft_id, interaction)

            return {
                "success": True,
                "changes": edit_result.changes,
                "rejections": edit_result.rejections,
                "error": None
            }

        except Exception as e:
            interaction = IterationInteraction(
                timestamp=datetime.now(UTC),
                user_id=user_id,
                interaction_type="markdown_edit",
                user_input=edited_markdown,
                changes_applied=[],
                changes_rejected=[],
                success=False,
                error_message=str(e)
            )
            await self.draft_repo.add_iteration_interaction(draft_id, interaction)

            return {
                "success": False,
                "changes": [],
                "rejections": [],
                "error": str(e)
            }
```

---

## 🔄 User Flow

### Entry Point

**Location**: `/finding-models/{slug}` (model detail page)

**Trigger**: User clicks "Create Iteration" button

**Flow**:
1. `POST /iterate/{slug}`
2. Backend fetches published model
3. Backend checks for existing iteration draft
   - **If exists**: Redirect to existing
   - **If new**: Create iteration draft
4. Redirect to `/drafts/{draft_id}?mode=edit`

---

### Iteration Draft Interface

**URL**: `/drafts/{draft_id}?mode=edit` (when `is_iteration=True`)

**Layout**:

```
┌─────────────────────────────────────────────────┐
│ ℹ️ Iterating on: Lung Nodule                    │
│    [View Original Model]                        │
└─────────────────────────────────────────────────┘

┌─────────────┬──────────────────┬─────────────┐
│ Natural     │ Markdown         │ History     │
│ Language    │ Edit             │             │
└─────────────┴──────────────────┴─────────────┘

[Active tab content]

[JSON Preview - shows current state]
```

**Key Difference from Creation Drafts**: No manual edit fields. Users must use AI tools.

---

### Tab 1: Natural Language Iteration

**Interface**:
- Textarea for natural language request
- "Apply Changes" button
- Results area showing:
  - ✅ Changes applied (list)
  - ⚠️ Changes rejected (list with reasons)
  - ❌ Errors

**HTMX Pattern**:
```
Form submits → POST /drafts/{id}/iterate
              → Returns result component
              → Swaps into result area
              → Triggers JSON preview refresh
```

---

### Tab 2: Markdown Edit

**Step 1 - Export**:
- Button: "Export to Markdown"
- Calls `POST /drafts/{id}/export-markdown`
- Returns textarea with markdown

**Step 2 - Edit**:
- User edits markdown in textarea
- Button: "Apply Changes"
- Calls `POST /drafts/{id}/iterate-markdown`
- Returns result component

---

### Tab 3: History

**Display**: Timeline of all iterations
- Timestamp
- Interaction type
- User input (truncated)
- Changes applied (expandable)
- Changes rejected (expandable)
- Success/failure badge

**HTMX Pattern**: Lazy load with `hx-trigger="intersect once"`

---

## 💻 Router Endpoints

### Entry Point

**File**: `app/routers/finding_models_browse.py`

```python
@router.post("/iterate/{slug}")
async def start_iteration(
    slug: str,
    request: Request,
    user: CurrentUserDep,
    iteration_service: IterationServiceDep,
    finding_model_service: FindingModelServiceDep,
):
    """Start iterating on a published finding model."""
    model = await finding_model_service.get_by_slug(slug)
    if not model:
        raise HTTPException(404, "Model not found")

    # Create or retrieve iteration draft
    draft = await iteration_service.start_iteration(
        user_id=user.id,
        base_model_id=model.oifm_id,
        published_model_json=model.model_dump_json()
    )

    return RedirectResponse(
        f"/drafts/{draft.id}?mode=edit",
        status_code=303
    )
```

---

### AI Iteration Endpoints

**File**: `app/routers/drafts/workflows.py` (add to existing file)

**Rationale**: Iteration operations are state transitions (they modify draft state), so they belong in `workflows.py` alongside submit, delete, etc. This maintains the existing modular router pattern:
- `views.py` - GET endpoints
- `mutations.py` - POST CRUD operations
- `workflows.py` - POST state transitions (submit, delete, **iterate**)
- `comments.py` - POST comment operations

**HTMX Request Handling Pattern**:
- **GET endpoints** (return partials): Check `is_htmx_request()` and redirect to parent page if false
- **POST endpoints** (return partials): In error handling, check `is_htmx_request()` to return HTML error (HTMX) or raise HTTPException (non-HTMX)

Following existing patterns from research:

```python
# Add to existing app/routers/drafts/workflows.py
from fastapi import Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Annotated
from app.models import User
from app.dependencies import require_current_user, get_templates
from app.services.iteration_service import IterationService
from app.database import DraftRepo
from app.routers.drafts.helpers import is_htmx_request, build_htmx_response_with_oob

# Type aliases already defined in workflows.py

# Type aliases for cleaner code
CurrentUserDep = Annotated[User, Depends(require_current_user)]
IterationServiceDep = Annotated[IterationService, Depends()]
DraftRepoDep = Annotated[DraftRepo, Depends()]

@router.post("/drafts/{draft_id}/iterate")
async def iterate_natural_language(
    draft_id: str,
    user_request: Annotated[str, Form()],
    request: Request,
    current_user: CurrentUserDep,
    iteration_service: IterationServiceDep,
    templates = Depends(get_templates)
):
    """Apply natural language iteration to draft."""
    try:
        result = await iteration_service.iterate_natural_language(
            draft_id, current_user.id, user_request
        )

        # Return HTMX partial (always partial for this endpoint)
        return templates.TemplateResponse(
            request=request,
            name="components/iteration_result.html",
            context={
                "result": result,
                "draft_id": draft_id
            }
        )
    except Exception as e:
        if is_htmx_request(request):
            error_html = templates.get_template("components/error_display.html").render(
                request=request,
                error_message=f"Error applying iteration: {str(e)}"
            )
            return HTMLResponse(content=error_html, status_code=500)
        else:
            raise HTTPException(500, f"Error applying iteration: {str(e)}")

@router.get("/drafts/{draft_id}/export-markdown")
async def export_markdown(
    draft_id: str,
    request: Request,
    current_user: CurrentUserDep,
    iteration_service: IterationServiceDep,
    templates = Depends(get_templates)
):
    """Export model to editable markdown format."""
    # Redirect to draft page if not HTMX request
    if not is_htmx_request(request):
        return RedirectResponse(f"/drafts/{draft_id}?mode=edit", status_code=303)

    try:
        markdown_text = await iteration_service.export_for_editing(
            draft_id, current_user.id
        )

        # Return textarea component with markdown
        return templates.TemplateResponse(
            request=request,
            name="components/markdown_editor.html",
            context={
                "markdown": markdown_text,
                "draft_id": draft_id
            }
        )
    except Exception as e:
        # For HTMX requests, return error HTML
        error_html = templates.get_template("components/error_display.html").render(
            request=request,
            error_message=f"Error exporting markdown: {str(e)}"
        )
        return HTMLResponse(content=error_html, status_code=500)

@router.post("/drafts/{draft_id}/iterate-markdown")
async def iterate_markdown(
    draft_id: str,
    edited_markdown: Annotated[str, Form()],
    request: Request,
    current_user: CurrentUserDep,
    iteration_service: IterationServiceDep,
    templates = Depends(get_templates)
):
    """Apply changes from edited markdown."""
    try:
        result = await iteration_service.iterate_markdown(
            draft_id, current_user.id, edited_markdown
        )

        return templates.TemplateResponse(
            request=request,
            name="components/iteration_result.html",
            context={
                "result": result,
                "draft_id": draft_id
            }
        )
    except Exception as e:
        if is_htmx_request(request):
            error_html = templates.get_template("components/error_display.html").render(
                request=request,
                error_message=f"Error applying markdown changes: {str(e)}"
            )
            return HTMLResponse(content=error_html, status_code=500)
        else:
            raise HTTPException(500, f"Error applying markdown changes: {str(e)}")

@router.get("/drafts/{draft_id}/iteration-history")
async def get_iteration_history(
    draft_id: str,
    request: Request,
    current_user: CurrentUserDep,
    draft_repo: DraftRepoDep,
    templates = Depends(get_templates)
):
    """Get iteration history timeline."""
    # Redirect to draft page if not HTMX request
    if not is_htmx_request(request):
        return RedirectResponse(f"/drafts/{draft_id}?mode=edit", status_code=303)

    draft = await draft_repo.get_draft(draft_id, current_user.id)
    if not draft:
        raise HTTPException(404, "Draft not found")

    # Return partial for HTMX (lazy-loaded via intersect trigger)
    return templates.TemplateResponse(
        request=request,
        name="components/iteration_history_timeline.html",
        context={
            "interactions": draft.iteration_history,
            "draft": draft
        }
    )
```

**Note**: No router registration needed - these endpoints are added directly to the existing `workflows.py` router.

---

## 🎨 UI Templates & Components

### Component Organization

**Existing Macros to Reuse**:
- `macros/flowbite_components.html` - `flowbite_button()`, `flowbite_badge()`
- `macros/form_validation.html` - `validated_textarea()`
- `macros/creation_components.html` - `success_alert()`, `error_alert()`
- `macros/json_accordion.html` - `json_accordion()`

**New Macro File to Create**:
- `macros/iteration_components.html` - Iteration-specific helpers (spinner, info alert)

**New Component Templates**:
- `components/iteration_result.html` - Shows changes/rejections + triggers JSON refresh via OOB
- `components/markdown_editor.html` - Markdown textarea form
- `components/iteration_history_timeline.html` - Timeline display
- `drafts/iteration_tabs.html` - Tab interface

---

### 1. New Iteration Macros File

**New File**: `templates/macros/iteration_components.html`

```jinja
{# Flowbite spinner for HTMX indicators #}
{% macro htmx_spinner(id, text="Loading...") %}
<div id="{{ id }}" class="htmx-indicator inline-block ml-3" role="status">
  <svg aria-hidden="true" class="w-6 h-6 text-gray-200 animate-spin dark:text-gray-600 fill-blue-600" viewBox="0 0 100 101" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z" fill="currentColor"/>
    <path d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z" fill="currentFill"/>
  </svg>
  <span class="sr-only">{{ text }}</span>
</div>
{% endmacro %}

{# Info alert for iteration instructions #}
{% macro iteration_info_alert(message) %}
<p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
  {{ message }}
</p>
{% endmacro %}

{# Iteration banner alert #}
{% macro iteration_banner(model_name, base_model_slug) %}
<div class="flex items-center p-4 mb-4 text-sm text-blue-800 border border-blue-300 rounded-lg bg-blue-50 dark:bg-gray-800 dark:text-blue-400 dark:border-blue-800" role="alert">
  <svg class="flex-shrink-0 inline w-4 h-4 me-3" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20">
    <path d="M10 .5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 .5ZM9.5 4a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3ZM12 15H8a1 1 0 0 1 0-2h1v-3H8a1 1 0 0 1 0-2h2a1 1 0 0 1 1 1v4h1a1 1 0 0 1 0 2Z"/>
  </svg>
  <div>
    <span class="font-medium">Iterating on:</span> {{ model_name }}
    <a href="/finding-models/{{ base_model_slug }}" class="ml-2 font-medium underline hover:no-underline">View Original</a>
  </div>
</div>
{% endmacro %}
```

---

### 2. Iteration Button on Model Detail

**File**: `templates/finding_models/detail.html`

```html
{% if current_user %}
<div class="mt-4">
  <form method="post" action="/iterate/{{ finding_model.slug }}">
    <button type="submit"
            class="text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800">
      🔧 Create Iteration
    </button>
  </form>
</div>
{% endif %}
```

---

### 3. Enhanced Draft Editor

**File**: `templates/drafts/edit.html`

```html
{% from "macros/iteration_components.html" import iteration_banner %}
{% from "macros/json_accordion.html" import json_accordion %}

{% if draft.is_iteration %}
  <!-- Iteration Banner -->
  {{ iteration_banner(draft.name, base_model_slug) }}

  <!-- Iteration Tabs Interface -->
  {% include 'drafts/iteration_tabs.html' %}

{% else %}
  <!-- Standard creation draft editor -->
  {% include 'components/draft_edit_form_content.html' %}
{% endif %}

<!-- JSON Preview (shared by both types) -->
{% if draft.generated_json %}
  <div id="draft-json-container">
    {{ json_accordion(data=draft.generated_json, id="draft-json", title="Current Model JSON") | safe }}
  </div>
{% endif %}
```

**Note**: Wraps JSON in container with ID for OOB swaps to refresh it.

---

### 3. Iteration Tabs Interface

**New File**: `templates/drafts/iteration_tabs.html`

**STRICT Flowbite adherence - using exact patterns from Flowbite docs**:

```html
{% from "macros/iteration_components.html" import htmx_spinner %}

<div x-data="{ activeTab: 'natural-language' }" class="mb-6">
  <!-- Tab Navigation - Flowbite Tabs Pattern -->
  <div class="border-b border-gray-200 dark:border-gray-700">
    <ul class="flex flex-wrap -mb-px text-sm font-medium text-center" role="tablist">
      <li class="me-2" role="presentation">
        <button
          @click="activeTab = 'natural-language'"
          :class="activeTab === 'natural-language' ?
            'inline-block p-4 text-blue-600 border-b-2 border-blue-600 rounded-t-lg active' :
            'inline-block p-4 border-b-2 border-transparent rounded-t-lg hover:text-gray-600 hover:border-gray-300 dark:hover:text-gray-300'"
          type="button"
          role="tab">
          Natural Language
        </button>
      </li>
      <li class="me-2" role="presentation">
        <button
          @click="activeTab = 'markdown'"
          :class="activeTab === 'markdown' ?
            'inline-block p-4 text-blue-600 border-b-2 border-blue-600 rounded-t-lg active' :
            'inline-block p-4 border-b-2 border-transparent rounded-t-lg hover:text-gray-600 hover:border-gray-300 dark:hover:text-gray-300'"
          type="button"
          role="tab">
          Markdown Edit
        </button>
      </li>
      <li role="presentation">
        <button
          @click="activeTab = 'history'"
          :class="activeTab === 'history' ?
            'inline-block p-4 text-blue-600 border-b-2 border-blue-600 rounded-t-lg active' :
            'inline-block p-4 border-b-2 border-transparent rounded-t-lg hover:text-gray-600 hover:border-gray-300 dark:hover:text-gray-300'"
          type="button"
          role="tab">
          History
        </button>
      </li>
    </ul>
  </div>

  <!-- Tab Panels -->
  <div class="mt-4">
    <!-- Natural Language Tab -->
    <div x-show="activeTab === 'natural-language'" role="tabpanel">
      {% include 'components/iteration_natural_language_form.html' %}
    </div>

    <!-- Markdown Edit Tab -->
    <div x-show="activeTab === 'markdown'" role="tabpanel">
      {% include 'components/iteration_markdown_form.html' %}
    </div>

    <!-- History Tab -->
    <div x-show="activeTab === 'history'"
         role="tabpanel"
         hx-get="/drafts/{{ draft.id }}/iteration-history"
         hx-trigger="intersect once"
         hx-swap="innerHTML">
      <!-- Loading spinner using macro -->
      <div class="flex justify-center items-center py-8">
        {{ htmx_spinner(id="history-loading", text="Loading history...") }}
      </div>
    </div>
  </div>
</div>
```

---

### 4. Natural Language Form Component

**New File**: `templates/components/iteration_natural_language_form.html`

```html
{% from "macros/form_validation.html" import validated_textarea %}
{% from "macros/iteration_components.html" import iteration_info_alert, htmx_spinner %}

<div class="space-y-4">
  <!-- Info Text using macro -->
  {{ iteration_info_alert("Describe the changes you want to make in plain English. The AI will apply safe changes and reject anything that would break the model.") }}

  <!-- Form -->
  <form hx-post="/drafts/{{ draft.id }}/iterate"
        hx-target="#iteration-result"
        hx-swap="innerHTML"
        hx-indicator="#iterate-spinner">

    <!-- Textarea using validated_textarea macro -->
    {{ validated_textarea(
      name="user_request",
      label="Requested Changes",
      value="",
      rows=4,
      required=true,
      minlength=10,
      maxlength=2000,
      placeholder="e.g., 'Add a new attribute for calcification pattern with options: central, peripheral, popcorn, and amorphous'"
    ) | safe }}

    <!-- Submit Button (Flowbite) -->
    <div class="flex items-center gap-3">
      <button type="submit"
              class="text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center inline-flex items-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800">
        Apply Changes
      </button>

      <!-- Spinner using macro -->
      {{ htmx_spinner(id="iterate-spinner", text="Applying changes...") }}
    </div>
  </form>

  <!-- Result Container -->
  <div id="iteration-result" class="mt-4">
    <!-- HTMX will swap result here -->
  </div>
</div>
```

---

### 5. Markdown Edit Form Component

**New File**: `templates/components/iteration_markdown_form.html`

```html
{% from "macros/iteration_components.html" import iteration_info_alert, htmx_spinner %}

<div class="space-y-4" x-data="{ markdownLoaded: false }">
  <!-- Info Text using macro -->
  {{ iteration_info_alert("Export the model to a markdown format, edit it, then apply your changes. The AI will interpret your edits and update the model.") }}

  <!-- Step 1: Export Button -->
  <div x-show="!markdownLoaded">
    <button @click="markdownLoaded = true"
            type="button"
            hx-get="/drafts/{{ draft.id }}/export-markdown"
            hx-target="#markdown-editor-container"
            hx-swap="innerHTML"
            hx-indicator="#export-spinner"
            class="text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center inline-flex items-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800">
      Export to Markdown
    </button>

    <!-- Spinner using macro -->
    {{ htmx_spinner(id="export-spinner", text="Exporting...") }}
  </div>

  <!-- Step 2: Markdown Editor (loaded by HTMX) -->
  <div id="markdown-editor-container" x-show="markdownLoaded">
    <!-- Will be populated by HTMX -->
  </div>
</div>
```

---

### 6. Markdown Editor Component

**New File**: `templates/components/markdown_editor.html`

```html
{% from "macros/iteration_components.html" import htmx_spinner %}

<form hx-post="/drafts/{{ draft_id }}/iterate-markdown"
      hx-target="#markdown-result"
      hx-swap="innerHTML"
      hx-indicator="#markdown-spinner">

  <!-- Textarea (Flowbite Form) -->
  <label for="edited-markdown" class="block mb-2 text-sm font-medium text-gray-900 dark:text-white">
    Editable Markdown
  </label>
  <textarea id="edited-markdown"
            name="edited_markdown"
            rows="20"
            required
            class="block p-2.5 w-full text-sm text-gray-900 bg-gray-50 rounded-lg border border-gray-300 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 font-mono">{{ markdown }}</textarea>

  <!-- Buttons -->
  <div class="mt-3 flex gap-2 items-center">
    <button type="submit"
            class="text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center inline-flex items-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800">
      Apply Changes
    </button>

    <button type="button"
            @click="markdownLoaded = false"
            class="text-gray-900 bg-white border border-gray-300 focus:outline-none hover:bg-gray-100 focus:ring-4 focus:ring-gray-100 font-medium rounded-lg text-sm px-5 py-2.5 dark:bg-gray-800 dark:text-white dark:border-gray-600 dark:hover:bg-gray-700 dark:hover:border-gray-600 dark:focus:ring-gray-700">
      Cancel
    </button>

    <!-- Spinner using macro -->
    <div class="ml-auto">
      {{ htmx_spinner(id="markdown-spinner", text="Applying...") }}
    </div>
  </div>
</form>

<!-- Result Container -->
<div id="markdown-result" class="mt-4">
  <!-- HTMX will swap result here -->
</div>
```

---

### 7. Iteration Result Component

**New File**: `templates/components/iteration_result.html`

**Displays summary of changes and rejections (NOT JSON diff)**:

```html
{% from "macros/creation_components.html" import success_alert, error_alert %}

{% if result.success %}
  <!-- Success Alert using macro -->
  <div class="flex p-4 mb-4 text-sm text-green-800 rounded-lg bg-green-50 dark:bg-gray-800 dark:text-green-400" role="alert">
    <svg class="flex-shrink-0 inline w-4 h-4 me-3 mt-[2px]" aria-hidden="true" fill="currentColor" viewBox="0 0 20 20">
      <path d="M10 .5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 .5ZM9.5 4a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3ZM12 15H8a1 1 0 0 1 0-2h1v-3H8a1 1 0 0 1 0-2h2a1 1 0 0 1 1 1v4h1a1 1 0 0 1 0 2Z"/>
    </svg>
    <div class="flex-1">
      <span class="font-medium">Iteration Applied</span>

      <!-- Changes Applied -->
      {% if result.changes %}
      <div class="mt-2">
        <p class="font-semibold mb-1">Changes Applied:</p>
        <ul class="list-disc list-inside space-y-1">
          {% for change in result.changes %}
          <li>{{ change }}</li>
          {% endfor %}
        </ul>
      </div>
      {% endif %}

      <!-- Changes Rejected -->
      {% if result.rejections %}
      <div class="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded dark:bg-gray-700 dark:border-yellow-800">
        <p class="font-semibold text-yellow-800 dark:text-yellow-400 mb-1">Some changes were rejected:</p>
        <ul class="list-disc list-inside space-y-1 text-yellow-700 dark:text-yellow-300">
          {% for rejection in result.rejections %}
          <li>{{ rejection }}</li>
          {% endfor %}
        </ul>
      </div>
      {% endif %}
    </div>
  </div>

{% else %}
  <!-- Error Alert using macro -->
  {{ error_alert(result.error) }}
{% endif %}
```

**CRITICAL: JSON Preview Refresh via Out-of-Band Swap**

The endpoint should use HTMX out-of-band (OOB) swaps to refresh the JSON preview instead of inline scripts.

**New Generic OOB Helper** (to be added to `app/routers/drafts/helpers.py`):

```python
def build_htmx_response_with_oob(
    main_content: str,
    oob_swaps: dict[str, str],
) -> HTMLResponse:
    """
    Build HTMX response with arbitrary out-of-band swaps.

    Args:
        main_content: Primary HTML content for the hx-target
        oob_swaps: Dict of element_id -> HTML content for OOB updates

    Returns:
        HTMLResponse with main content and OOB swap fragments
    """
    oob_fragments = []
    for element_id, html in oob_swaps.items():
        if 'hx-swap-oob' not in html:
            oob_fragments.append(
                f'<div id="{element_id}" hx-swap-oob="true">\n{html}\n</div>'
            )
        else:
            oob_fragments.append(html)

    return _combine_content_with_oob_fragments(main_content, oob_fragments)
```

**Usage in Iteration Endpoints** (`app/routers/drafts/workflows.py`):

```python
# After successful iteration
result_html = templates.TemplateResponse(
    "components/iteration_result.html",
    {"request": request, "result": result}
).body.decode()

# Render updated JSON accordion
updated_draft = await draft_repo.get_draft(draft_id, current_user.id)
updated_json_html = templates.TemplateResponse(
    "macros/json_accordion.html",
    {"request": request, "data": updated_draft.model_dict(),
     "id": "draft-json", "title": "Current Model JSON"}
).body.decode()

# Combine with OOB swap using new generic helper
return build_htmx_response_with_oob(
    main_content=result_html,
    oob_swaps={'draft-json-container': updated_json_html}
)
```

**Refactoring Required**: The existing `build_htmx_response_with_oob` function is draft-specific and should be renamed to `build_draft_mode_toggle_response`. Create the new generic helper above and extract shared logic to `_combine_content_with_oob_fragments` internal helper.

---

### 8. Iteration History Timeline

**New File**: `templates/components/iteration_history_timeline.html`

**Uses Flowbite Timeline component**:

```html
{% from "macros/flowbite_components.html" import flowbite_badge %}

{% if interactions %}
  <!-- Flowbite Timeline -->
  <ol class="relative border-s border-gray-200 dark:border-gray-700 ms-3">
    {% for interaction in interactions %}
    <li class="mb-10 ms-6">
      <!-- Timeline Icon -->
      <span class="absolute flex items-center justify-center w-8 h-8 bg-blue-100 rounded-full -start-4 ring-4 ring-white dark:ring-gray-900 dark:bg-blue-900">
        {% if interaction.interaction_type == "natural_language" %}
        <svg class="w-3.5 h-3.5 text-blue-800 dark:text-blue-300" fill="currentColor" viewBox="0 0 20 20">
          <path d="M18 4.5a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1v-11a1 1 0 0 1 1-1h16zM2 3a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2H2z"/>
        </svg>
        {% else %}
        <svg class="w-3.5 h-3.5 text-blue-800 dark:text-blue-300" fill="currentColor" viewBox="0 0 20 20">
          <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
        </svg>
        {% endif %}
      </span>

      <!-- Timeline Content Card -->
      <div class="p-4 bg-white border border-gray-200 rounded-lg shadow-sm dark:bg-gray-700 dark:border-gray-600">
        <!-- Header -->
        <div class="items-center justify-between mb-3 sm:flex">
          <time class="mb-1 text-xs font-normal text-gray-400 sm:order-last sm:mb-0 dark:text-gray-500">
            {{ interaction.timestamp.strftime('%b %d, %Y at %I:%M %p') }}
          </time>
          <div class="text-sm font-normal flex items-center gap-2">
            <span class="font-semibold text-gray-900 dark:text-white">
              {{ interaction.interaction_type.replace('_', ' ').title() }}
            </span>
            {% if interaction.success %}
              {{ flowbite_badge(text="Success", color="green", size="xs") | safe }}
            {% else %}
              {{ flowbite_badge(text="Failed", color="red", size="xs") | safe }}
            {% endif %}
          </div>
        </div>

        <!-- User Input -->
        <div class="p-3 mb-2 text-xs italic font-normal text-gray-500 border border-gray-200 rounded-lg bg-gray-50 dark:bg-gray-600 dark:border-gray-500 dark:text-gray-300">
          {{ interaction.user_input | truncate(300) }}
        </div>

        <!-- Changes Applied -->
        {% if interaction.success and interaction.changes_applied %}
        <div class="mb-2">
          <p class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Changes Applied:</p>
          <ul class="text-xs text-gray-600 dark:text-gray-400 list-disc list-inside space-y-1">
            {% for change in interaction.changes_applied[:3] %}
            <li>{{ change }}</li>
            {% endfor %}
            {% if interaction.changes_applied|length > 3 %}
            <li class="text-gray-500">... and {{ interaction.changes_applied|length - 3 }} more</li>
            {% endif %}
          </ul>
        </div>
        {% endif %}

        <!-- Changes Rejected -->
        {% if interaction.changes_rejected %}
        <div class="p-2 mb-2 bg-yellow-50 border border-yellow-200 rounded dark:bg-gray-600 dark:border-yellow-700">
          <p class="text-xs font-semibold text-yellow-800 dark:text-yellow-400 mb-1">Rejected:</p>
          <ul class="text-xs text-yellow-700 dark:text-yellow-300 list-disc list-inside">
            {% for rejection in interaction.changes_rejected[:2] %}
            <li>{{ rejection }}</li>
            {% endfor %}
            {% if interaction.changes_rejected|length > 2 %}
            <li>... and {{ interaction.changes_rejected|length - 2 }} more</li>
            {% endif %}
          </ul>
        </div>
        {% endif %}

        <!-- Error -->
        {% if not interaction.success and interaction.error_message %}
        <div class="p-2 text-xs text-red-800 bg-red-50 border border-red-200 rounded dark:bg-gray-600 dark:border-red-700 dark:text-red-400">
          <span class="font-semibold">Error:</span> {{ interaction.error_message }}
        </div>
        {% endif %}
      </div>
    </li>
    {% endfor %}
  </ol>

{% else %}
  <!-- Empty State -->
  <div class="text-center py-12">
    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
    </svg>
    <h3 class="mt-2 text-sm font-semibold text-gray-900 dark:text-white">No iterations yet</h3>
    <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
      Use the Natural Language or Markdown Edit tabs to iterate on this model.
    </p>
  </div>
{% endif %}
```

---

## 🔌 findingmodel API Integration

### Actual Available Functions

From `findingmodel.tools` (external library: https://github.com/openimagingdata/findingmodel):

```python
from findingmodel import FindingModelFull
from findingmodel.tools import (
    edit_model_natural_language,
    edit_model_markdown,
    export_model_for_editing,
)

# EditResult structure (Pydantic BaseModel)
class EditResult:
    model: FindingModelFull      # Updated model
    rejections: list[str]         # Changes that were rejected with reasons
    changes: list[str]            # Changes that were applied

# Function signatures (NOTE: First two are async!)
async def edit_model_natural_language(
    model: FindingModelFull,
    command: str,
    *,
    agent: Agent[EditDeps, EditResult] | None = None
) -> EditResult:
    """Edit model using natural language commands."""

async def edit_model_markdown(
    model: FindingModelFull,
    edited_markdown: str,
    *,
    agent: Agent[EditDeps, EditResult] | None = None
) -> EditResult:
    """Edit model using markdown-like text."""

def export_model_for_editing(
    model: FindingModelFull,
    *,
    attributes_only: bool = False
) -> str:
    """Export model to editable markdown format."""
```

**IMPORTANT**: The editing functions are **async** and must be awaited. The `agent` parameter is optional and defaults to a built-in agent if not provided.

### Guardrails

Built into the tools:
- ✅ Preserves all OIFM IDs
- ✅ Only allows safe additions and non-semantic edits
- ✅ Validates against FindingModel schema
- ✅ Rejects requests that would break model integrity
- ✅ Summarizes rejections via secondary LLM call

---

## 🧪 Testing Strategy

### Unit Tests

**File**: `tests/unit/services/test_iteration_service.py`

Test cases:
- `test_start_iteration_creates_new_draft`
- `test_start_iteration_returns_existing`
- `test_iterate_natural_language_success`
- `test_iterate_natural_language_with_rejections`
- `test_iterate_natural_language_failure`
- `test_export_for_editing`
- `test_iterate_markdown_success`
- `test_interaction_logging`

### Integration Tests

**File**: `tests/integration/test_iteration_workflow.py`

Test cases:
- `test_full_iteration_flow_natural_language`
- `test_full_iteration_flow_markdown`
- `test_iteration_draft_uniqueness`
- `test_multiple_iterations_on_same_draft`
- `test_iteration_draft_submission`

### UI Tests

**File**: `tests/ui/test_iteration_ui.py`

Test cases:
- `test_iterate_button_appears_for_authenticated_users`
- `test_iterate_button_creates_draft`
- `test_iteration_banner_displays`
- `test_tab_switching_works`
- `test_natural_language_iteration_form_submission`
- `test_markdown_export_and_edit`
- `test_history_timeline_loads`
- `test_changes_and_rejections_display`

---

## 📋 Implementation Checklist

### Phase 1: Foundation (Backend)

- [ ] Create `IterationInteraction` model in `app/models.py`
- [ ] Add `is_iteration`, `base_model_id`, `iteration_history` to `FindingModelDraft`
- [ ] Update `DraftRepo.upsert_draft()` with iteration uniqueness logic
- [ ] Add `get_iteration_draft()` method to `DraftRepo`
- [ ] Add `add_iteration_interaction()` method to `DraftRepo`
- [ ] Create `app/services/iteration_service.py`
- [ ] Implement `IterationService` class methods
- [ ] Add dependency injection for `IterationService`
- [ ] Write unit tests for `IterationService`
- [ ] Verify all tests pass

### Phase 2: API Endpoints

- [ ] Add `POST /iterate/{slug}` to `finding_models_browse.py`
- [ ] Add iteration endpoints to `app/routers/drafts/workflows.py`:
  - [ ] Implement `POST /drafts/{id}/iterate` (natural language)
  - [ ] Implement `GET /drafts/{id}/export-markdown` (idempotent export)
  - [ ] Implement `POST /drafts/{id}/iterate-markdown` (apply markdown edits)
  - [ ] Implement `GET /drafts/{id}/iteration-history` (lazy-loaded timeline)
- [ ] Add base_model_slug lookup to `GET /drafts/{id}` in `views.py`
- [ ] Create new OOB helper functions in `helpers.py`:
  - [ ] Rename existing `build_htmx_response_with_oob` → `build_draft_mode_toggle_response`
  - [ ] Add `_combine_content_with_oob_fragments` (internal helper)
  - [ ] Add new generic `build_htmx_response_with_oob`
  - [ ] Update existing calls to use new names
- [ ] Write integration tests
- [ ] Verify all tests pass

### Phase 3: UI Implementation

- [ ] Add iteration button to `finding_models/detail.html`
- [ ] Update `drafts/edit.html` with conditional iteration/creation rendering
- [ ] Create `drafts/iteration_tabs.html` with Flowbite tabs
- [ ] Create `components/iteration_natural_language_form.html`
- [ ] Create `components/iteration_markdown_form.html`
- [ ] Create `components/markdown_editor.html`
- [ ] Create `components/iteration_result.html`
- [ ] Create `components/iteration_history_timeline.html`
- [ ] Test HTMX interactions manually
- [ ] Write Playwright UI tests
- [ ] Verify all tests pass

### Phase 4: Integration & Polish

- [ ] Test with real `findingmodel.tools` functions
- [ ] Verify loading states and spinners work
- [ ] Enhance error messages and feedback
- [ ] Test with large models and long histories
- [ ] Update `CLAUDE.md` with iteration feature docs
- [ ] Update relevant Serena memories
- [ ] Code review and cleanup
- [ ] Final comprehensive test run

---

## ⚠️ Important Considerations & Open Questions

### 1. Manual Editing Restriction

**Decision**: Iteration drafts CANNOT be manually edited via the standard draft editor.

**Reason**: Iterations must go through AI tools to maintain audit trail and ensure changes are validated.

**Implementation**: Draft editor detects `is_iteration=True` and shows tabs interface instead of manual form.

**Question**: Should we allow users to "convert" an iteration draft to a creation draft if they want manual control?

---

### 2. Base Model Slug Lookup

**Issue**: Need slug to link back to original model from iteration banner.

**Solution**: Fetch model from finding_model_service using `base_model_id` when rendering iteration draft page.

**Implementation** (in `app/routers/drafts/views.py`, `GET /drafts/{draft_id}` endpoint):

```python
# After fetching draft, before rendering template
base_model_slug = None
if draft.is_iteration and draft.base_model_id:
    try:
        base_model = await finding_model_service.get_by_oifm_id(draft.base_model_id)
        base_model_slug = base_model.slug if base_model else None
    except Exception as e:
        logger.warning(f"Could not fetch base model {draft.base_model_id}: {e}")
        # Continue rendering without slug - banner will handle gracefully

# Add to template context
context = {
    "draft": draft,
    "mode": mode,
    "base_model_slug": base_model_slug,  # ← Add this
    ...
}
```

**Template Usage** (`templates/macros/iteration_components.html`):

```jinja
{% macro iteration_banner(model_name, base_model_slug) %}
<div class="...">
  <span class="font-medium">Iterating on:</span> {{ model_name }}
  {% if base_model_slug %}
  <a href="/finding-models/{{ base_model_slug }}" ...>View Original</a>
  {% endif %}
</div>
{% endmacro %}
```

---

### 3. Iteration History Size Management

**Concern**: After many iterations, `iteration_history` array could grow large.

**Mitigation**:
- Each interaction is relatively small (text + string arrays)
- MongoDB document limit: 16 MB (should handle 1000s of iterations)
- If needed later: Add pagination to history tab

**Recommendation**: Start simple, monitor in production.

---

### 4. Contributor Attribution

**Question**: Should iteration authors be added to `contributors` list?

**Current Thinking**: Yes, when iteration draft is submitted and approved, the user should be added as a contributor with role indicating they improved the model.

**Implementation**: Handle in review/approval workflow (not in this phase).

---

### 5. Concurrent Iterations

**Scenario**: User A and User B both iterate on "Lung Nodule".

**Behavior**:
- Each gets their own iteration draft
- Both can submit independently
- Reviewers evaluate separately
- May accept both, one, or neither

**This is expected and desired** - like pull requests on GitHub.

---

### 6. Summary vs JSON Diff

**Decision**: Show SUMMARY of changes (from `EditResult.changes` list), not line-by-line JSON diff.

**Rationale**:
- More readable for users
- Focuses on semantic changes
- Generated by AI tools with medical context

**Future Enhancement**: Could add detailed JSON diff as "Advanced" option.

---

### 7. Rejection Handling

**Critical Feature**: Display rejected changes with reasons.

**UX**: Show rejections in yellow/warning style to educate users about what's not allowed.

**Example Rejections**:
- "Cannot change model name (preserves identity)"
- "Cannot remove existing attributes (breaks compatibility)"
- "Requested change outside medical imaging domain"

---

### 8. No "Undo" in MVP

**Future Enhancement**: Add ability to restore previous version from history.

**Implementation**:
- Store full model JSON at each interaction (currently not stored)
- Add "Restore This Version" button in timeline
- Endpoint: `POST /drafts/{id}/restore/{interaction_index}`

**Not critical for MVP** - users can just iterate again to revert.

---

## 📚 Documentation Updates Needed

1. **`CLAUDE.md`**: Add section on iteration feature and distinction from creation
2. **`app/CLAUDE.md`**: Document `IterationService` and AI integration patterns
3. **`templates/CLAUDE.md`**: Document iteration components and Flowbite patterns used
4. **`tests/CLAUDE.md`**: Add testing patterns for AI iterations
5. **Serena Memory (`current_development_status`)**: Update with iteration feature status

---

## 🎯 Success Criteria

### MVP (Minimum Viable Product)

- ✅ User can create iteration from any published model
- ✅ Iteration draft created with proper uniqueness constraint
- ✅ Natural language iteration works with changes/rejections display
- ✅ Markdown export/edit iteration works
- ✅ Full audit trail in iteration history
- ✅ History timeline displays properly
- ✅ Iteration drafts follow submission workflow
- ✅ All existing tests continue to pass
- ✅ New tests for iteration feature pass

### Out of Scope (Future Enhancements)

- 🔮 Detailed JSON diff visualization
- 🔮 Version restore/undo functionality
- 🔮 Batch iterations across multiple models
- 🔮 AI-suggested iterations
- 🔮 Iteration templates
- 🔮 Reviewer-specific comparison views

---

## 🚀 Next Steps

1. **Review this plan** - Discuss any concerns or questions
2. **Create implementation branch** - e.g., `feature/model-iterations`
3. **Begin Phase 1** - Data models and service layer
4. **Iterative development** - Test thoroughly at each phase

---

_Last Updated: 2025-10-29_
