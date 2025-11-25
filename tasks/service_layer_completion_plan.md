# Service Layer Completion Plan

## Overview

This plan completes the service layer refactoring started in `tasks/done/router_cleanup.md`. The goal is to move all remaining business logic from routers to services, creating truly thin controllers.

**Related Documents:**
- Assessment: [`backend_complexity_assessment.md`](backend_complexity_assessment.md)
- Previous work: [`done/router_cleanup.md`](done/router_cleanup.md)

**Estimated Total Effort**: 12-15 hours across 2 phases

---

## Phase 1: Service Layer Completion

**Goal**: Move all business logic from routers to services

### Task 1.1: FindingModelService Context Methods

**Priority**: P1 | **Effort**: 2-3 hours | **Risk**: Low

**Problem**: Pagination context built twice in `finding_models_browse.py` (lines 79-95 and 193-209).

**Changes**:

#### 1.1.1 Add to `app/services/finding_model_service.py`:

```python
from dataclasses import dataclass

@dataclass
class PaginationContext:
    """Complete pagination context for templates."""
    models: list[FindingModelDisplay]
    total_count: int
    current_page: int
    per_page: int
    total_pages: int
    page_range: list[int]
    start_index: int
    end_index: int
    url_params: dict[str, str]
    page_title: str

@dataclass
class ModelDetailContext:
    """Complete detail context for templates."""
    finding_model: FindingModelDisplay
    thread: CommentThread | None
    reference_type: str
    reference_id: str

class FindingModelService:
    # ... existing methods ...

    async def prepare_list_context(
        self,
        search: str | None,
        page: int,
        per_page: int
    ) -> PaginationContext:
        """Prepare complete pagination context for list view."""
        paginated_models, total_count = await self.list_models(search, page, per_page)

        total_pages = max(1, (total_count + per_page - 1) // per_page)
        start_index = (page - 1) * per_page
        end_index = min(start_index + per_page, total_count)

        # Calculate page range (show 5 pages around current)
        start_page = max(1, page - 2)
        end_page = min(total_pages, page + 2)
        page_range = list(range(start_page, end_page + 1))

        # Build URL parameters
        url_params = {}
        if search:
            url_params["search"] = search
        if per_page != 20:
            url_params["per_page"] = str(per_page)

        # Generate title
        page_title = "Finding Models - Finding Model Forge"
        if search:
            page_title = f"Search: {search} - Finding Model Forge"

        return PaginationContext(
            models=paginated_models,
            total_count=total_count,
            current_page=page,
            per_page=per_page,
            total_pages=total_pages,
            page_range=page_range,
            start_index=start_index + 1 if total_count > 0 else 0,
            end_index=end_index,
            url_params=url_params,
            page_title=page_title,
        )

    async def prepare_detail_context(self, slug: str) -> ModelDetailContext:
        """Prepare complete detail context for model view."""
        finding_model = await self.get_model_by_slug(slug)
        thread = await self.get_comments_for_model(finding_model.oifm_id)

        return ModelDetailContext(
            finding_model=finding_model,
            thread=thread,
            reference_type="finding_model",
            reference_id=slug,
        )
```

#### 1.1.2 Refactor `app/routers/finding_models_browse.py`:

Router becomes ~80 lines, just handling HTTP concerns and HTMX branching.

**Testing**:
- [ ] Add unit tests for `prepare_list_context()`
- [ ] Add unit tests for `prepare_detail_context()`
- [ ] Verify existing router tests still pass
- [ ] Manual test: search, pagination, detail view

**Success Criteria**:
- [ ] No pagination calculation in router
- [ ] Router under 100 lines
- [ ] All tests pass

---

### Task 1.2: Move JSON Generation to DraftService

**Priority**: P1 | **Effort**: 1-2 hours | **Risk**: Low

**Problem**: `generate_finding_model_json()` and `should_regenerate_model()` in `drafts/helpers.py` are business logic.

**Changes**:

#### 1.2.1 Add to `app/services/draft_service.py`:

```python
class DraftService:
    # ... existing methods ...

    def should_regenerate_model(
        self,
        draft: FindingModelDraftDocument,
        new_description: str | None,
        new_attributes: str | None,
    ) -> bool:
        """Determine if the finding model JSON needs regeneration."""
        if not draft.generated_json:
            return True
        if not draft.inputs:
            return True
        if new_description and new_description != draft.inputs.description:
            return True
        if new_attributes and new_attributes != draft.inputs.attributes_markdown:
            return True
        return False

    async def generate_finding_model_json(
        self,
        draft: FindingModelDraftDocument,
        user: User,
    ) -> str | None:
        """Generate the finding model JSON from draft inputs."""
        if not draft.inputs:
            return None

        inputs = FindingModelInputs(
            description=draft.inputs.description or "",
            synonyms=draft.inputs.synonyms or [],
            attributes_markdown=draft.inputs.attributes_markdown or "",
        )

        test_mode = self.creation_service.is_test_user(user.id)
        json_data = await self.creation_service.generate_from_inputs(
            name=draft.name,
            inputs=inputs,
            user=user,
            test_mode=test_mode,
        )
        return json_data
```

#### 1.2.2 Update `app/services/draft_service.py` `__init__`:

```python
def __init__(
    self,
    draft_repo: DraftRepo,
    user_repo: UserRepo,
    database: Database,
    comment_service: CommentService,
    creation_service: "CreationService",  # Add this
):
    self.draft_repo = draft_repo
    self.user_repo = user_repo
    self.database = database
    self.comment_service = comment_service
    self.creation_service = creation_service  # Add this
```

#### 1.2.3 Update `app/dependencies.py`:

Wire up `CreationService` dependency into `DraftService`.

#### 1.2.4 Update `app/routers/drafts/helpers.py`:

- Delete `generate_finding_model_json()` function
- Delete `should_regenerate_model()` function
- Update callers to use `draft_service.generate_finding_model_json()`

**Testing**:
- [ ] Move existing tests from `test_generate_finding_model_json.py` to service tests
- [ ] Update mock patterns in router tests
- [ ] Verify all draft workflows still work

**Success Criteria**:
- [ ] No JSON generation logic in helpers.py
- [ ] helpers.py under 350 lines
- [ ] All tests pass

---

### Task 1.3: Creation Workflow Methods in CreationService

**Priority**: P1 | **Effort**: 3-4 hours | **Risk**: Medium

**Problem**: Draft resume logic scattered across `process_step_1()`, `process_step_2()`, and `resume_creation()`.

**Changes**:

#### 1.3.1 Add data classes to `app/services/creation_service.py`:

```python
from dataclasses import dataclass
from enum import Enum

class WorkflowAction(Enum):
    """Possible outcomes of name resolution."""
    CREATE_NEW = "create_new"           # No existing draft, proceed with AI generation
    RESUME_EDITABLE = "resume_editable" # Found editable draft, redirect to edit
    VIEW_SUBMITTED = "view_submitted"   # Found submitted draft, redirect to view

@dataclass
class NameResolutionResult:
    """Result of resolving a name input."""
    action: WorkflowAction
    draft: FindingModelDraftDocument | None = None
    redirect_url: str | None = None

@dataclass
class SessionData:
    """Data needed to populate a session from a draft."""
    name: str
    description: str
    synonyms: list[str]
    attributes_markdown: str
    draft_id: str | None
    draft_status: str | None
    submitted_display_time: str | None
```

#### 1.3.2 Add methods to `CreationService`:

```python
class CreationService:
    # ... existing methods ...

    async def resolve_name_input(
        self,
        user_id: int,
        name: str
    ) -> NameResolutionResult:
        """
        Determine workflow path for a given name.

        Returns:
            - CREATE_NEW: Name is available, proceed with AI generation
            - RESUME_EDITABLE: Found editable draft, redirect to edit
            - VIEW_SUBMITTED: Found submitted draft, redirect to view
        """
        # Check for editable draft
        draft = await self.draft_repo.find_editable_by_name(user_id=user_id, name=name)
        if draft is not None:
            return NameResolutionResult(
                action=WorkflowAction.RESUME_EDITABLE,
                draft=draft,
                redirect_url=f"/drafts/{draft.id}?mode=edit",
            )

        # Check for submitted draft
        latest = await self.draft_repo.find_latest_by_name(user_id=user_id, name=name)
        if latest is not None and latest.status == "submitted":
            return NameResolutionResult(
                action=WorkflowAction.VIEW_SUBMITTED,
                draft=latest,
                redirect_url=f"/drafts/{latest.id}?mode=view",
            )

        # Name is available for new creation
        return NameResolutionResult(action=WorkflowAction.CREATE_NEW)

    def extract_session_data(
        self,
        draft: FindingModelDraftDocument
    ) -> SessionData:
        """Extract session data from an existing draft."""
        return SessionData(
            name=draft.name,
            description=draft.inputs.description if draft.inputs else "",
            synonyms=draft.inputs.synonyms if draft.inputs else [],
            attributes_markdown=(
                draft.inputs.attributes_markdown
                if draft.inputs and draft.inputs.attributes_markdown
                else self.generate_default_attributes_markdown(draft.name)
            ),
            draft_id=str(draft.id),
            draft_status=draft.status,
            submitted_display_time=humanize_timestamp(draft.updated_at) if draft.updated_at else None,
        )
```

#### 1.3.3 Update `app/services/creation_service.py` `__init__`:

```python
def __init__(
    self,
    index: Index,
    database: Database,
    draft_repo: DraftRepo,  # Add this
):
    self.index = index
    self.database = database
    self.draft_repo = draft_repo  # Add this
```

#### 1.3.4 Refactor `app/routers/creation.py`:

```python
@router.post("/step/1")
async def process_step_1(
    request: Request,
    current_user: CurrentUserDep,
    session: CreationSessionDep,
    session_manager: SessionManagerDep,
    creation_service: CreationServiceDep,
    name: str = Form(min_length=3, max_length=200),
) -> Response:
    """Process step 1: Check name and generate description."""
    try:
        # Resolve what to do with this name
        resolution = await creation_service.resolve_name_input(current_user.id, name)

        if resolution.action == WorkflowAction.RESUME_EDITABLE:
            session_data = creation_service.extract_session_data(resolution.draft)
            _apply_session_data(session, session_data)
            await session_manager.update_session(session)
            return RedirectResponse(url=resolution.redirect_url, status_code=303)

        if resolution.action == WorkflowAction.VIEW_SUBMITTED:
            session_data = creation_service.extract_session_data(resolution.draft)
            _apply_session_data(session, session_data)
            await session_manager.update_session(session)
            return RedirectResponse(url=resolution.redirect_url, status_code=303)

        # CREATE_NEW path
        is_available = await creation_service.check_name_availability(name, current_user.id)
        if not is_available:
            session.error_message = f"Name '{name}' already exists in the index"
            await session_manager.update_session(session)
            return HTMLResponse(content=render_step_template(request, 1, session, form_data={"name": name}))

        # Generate finding info
        test_mode = creation_service.is_test_user(current_user.id)
        finding_info = await creation_service.generate_finding_info(name, test_mode=test_mode)

        # Update session for step 2
        session.name = name
        session.draft_id = None
        session.description = finding_info.description
        session.synonyms = finding_info.synonyms or []
        session.current_step = 2
        await session_manager.update_session(session)

        return HTMLResponse(content=render_step_template(request, 2, session))

    except Exception as e:
        logger.error(f"Error processing step 1: {str(e)}", exc_info=True)
        session.error_message = f"Error generating description: {str(e)}"
        await session_manager.update_session(session)
        return HTMLResponse(
            content=render_step_template(request, 1, session, form_data={"name": name}, error_message=session.error_message),
            status_code=500
        )

def _apply_session_data(session: CreationSession, data: SessionData) -> None:
    """Apply extracted session data to a session object."""
    session.name = data.name
    session.description = data.description
    session.synonyms = data.synonyms
    session.attributes_markdown = data.attributes_markdown
    session.draft_id = data.draft_id
    session.draft_status = data.draft_status
    session.submitted_display_time = data.submitted_display_time
```

**Testing**:
- [ ] Add unit tests for `resolve_name_input()` (all 3 paths)
- [ ] Add unit tests for `extract_session_data()`
- [ ] Update router tests to mock service methods
- [ ] Manual test: new creation, resume draft, view submitted

**Success Criteria**:
- [ ] Draft resolution logic in service
- [ ] `process_step_1()` under 50 lines
- [ ] `process_step_2()` under 50 lines
- [ ] All tests pass

---

### Task 1.4: DraftService View Context Method

**Priority**: P2 | **Effort**: 1-2 hours | **Risk**: Low

**Problem**: `unified_draft_page()` does permission checking, mode validation, and data fetching.

**Changes**:

#### 1.4.1 Add to `app/services/draft_service.py`:

```python
@dataclass
class DraftViewContext:
    """Complete context for rendering a draft view."""
    draft: FindingModelDraftDocument
    author_name: str
    can_edit: bool
    can_delete: bool
    resolved_mode: str  # "edit" or "view"
    thread: CommentThread | None
    finding_model: FindingModel | None
    needs_redirect_to_edit: bool  # If view requested but no generated_json

class DraftService:
    # ... existing methods ...

    async def prepare_view_context(
        self,
        draft_id: str,
        user_id: int | None,
        requested_mode: str,
    ) -> DraftViewContext:
        """Prepare complete context for draft view/edit."""
        # Fetch draft with author
        draft, author_name = await self.get_draft_with_author(draft_id)
        if not draft:
            raise NotFoundError(f"Draft {draft_id} not found")

        # Check permissions
        is_owner = user_id is not None and draft.user_id == user_id
        can_edit = is_owner and draft.status == "draft"
        can_delete = is_owner and draft.status == "draft"

        # Resolve mode
        if requested_mode not in ["view", "edit"]:
            requested_mode = "view"
        if requested_mode == "edit" and not can_edit:
            requested_mode = "view"

        # Check if redirect needed
        needs_redirect = (
            requested_mode == "view"
            and not draft.generated_json
            and draft.status == "draft"
            and can_edit
        )

        # Parse finding model
        finding_model = None
        if draft.generated_json:
            try:
                finding_model = FindingModel.model_validate_json(draft.generated_json)
            except Exception:
                pass

        # Get comments for public/submitted
        thread = None
        if user_id and draft.status in ["public", "submitted"]:
            thread = await self.get_comments_for_draft(str(draft.id))

        return DraftViewContext(
            draft=draft,
            author_name=author_name,
            can_edit=can_edit,
            can_delete=can_delete,
            resolved_mode=requested_mode,
            thread=thread,
            finding_model=finding_model,
            needs_redirect_to_edit=needs_redirect,
        )
```

#### 1.4.2 Refactor `app/routers/drafts/views.py`:

Router becomes much simpler - just handles HTMX branching and template selection.

**Testing**:
- [ ] Add unit tests for `prepare_view_context()` (all permission scenarios)
- [ ] Update router tests
- [ ] Manual test: owner vs non-owner, draft vs submitted

**Success Criteria**:
- [ ] No permission logic in router
- [ ] `unified_draft_page()` under 60 lines
- [ ] All tests pass

---

### Task 1.5: Move Validation to Services

**Priority**: P2 | **Effort**: 1 hour | **Risk**: Low

**Problem**: Validation in `save_draft()` router.

**Changes**:

#### 1.5.1 Update `app/services/__init__.py`:

```python
class ValidationError(ServiceError):
    """Raised when input validation fails."""
    pass
```

#### 1.5.2 Update `app/services/draft_service.py` `save_draft()`:

```python
async def save_draft(
    self,
    user_id: int,
    name: str,
    inputs: FindingModelInputs,
    draft_id: str | None = None,
    user: User | None = None,
) -> FindingModelDraftDocument:
    """Save or update a draft with validation."""
    # Validate inputs
    if len(inputs.description.strip()) < 10:
        raise ValidationError("Description must be at least 10 characters")
    if len(inputs.attributes_markdown.strip()) < 20:
        raise ValidationError("Attributes must be at least 20 characters")

    # ... rest of existing logic
```

#### 1.5.3 Update `app/routers/drafts/mutations.py`:

```python
try:
    draft = await draft_service.save_draft(...)
except ValidationError as e:
    raise HTTPException(status_code=422, detail=str(e))
```

**Testing**:
- [ ] Add unit tests for validation in service
- [ ] Update router tests to expect validation from service
- [ ] All tests pass

**Success Criteria**:
- [ ] No validation logic in router
- [ ] ValidationError properly handled
- [ ] All tests pass

---

## Phase 2: HTMX Response Service

**Goal**: Standardize HTMX response patterns across all routers

### Task 2.1: Create HTMXResponseService

**Priority**: P2 | **Effort**: 2-3 hours | **Risk**: Low

**Problem**: HTMX response building logic duplicated across routers and helpers.

**Changes**:

#### 2.1.1 Create `app/services/htmx_response_service.py`:

```python
from dataclasses import dataclass
from fastapi import Request
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates

@dataclass
class OOBSwap:
    """Configuration for an out-of-band swap."""
    target_id: str
    template: str
    context: dict

class HTMXResponseService:
    """Service for building HTMX responses with standardized patterns."""

    def __init__(self, templates: Jinja2Templates):
        self.templates = templates

    def is_htmx_request(self, request: Request) -> bool:
        """Check if the request is an HTMX request."""
        return request.headers.get("HX-Request") == "true"

    def build_response(
        self,
        request: Request,
        template: str,
        context: dict,
        push_url: str | None = None,
        oob_swaps: list[OOBSwap] | None = None,
        status_code: int = 200,
    ) -> HTMLResponse:
        """Build an HTMX response with optional OOB swaps and URL push."""
        # Render main content
        main_content = self.templates.get_template(template).render(request=request, **context)

        # Render OOB swaps
        oob_content = ""
        if oob_swaps:
            for swap in oob_swaps:
                swap_html = self.templates.get_template(swap.template).render(
                    request=request, **swap.context
                )
                oob_content += f'\n<div id="{swap.target_id}" hx-swap-oob="true">{swap_html}</div>'

        response = HTMLResponse(content=main_content + oob_content, status_code=status_code)

        if push_url:
            response.headers["HX-Push-Url"] = push_url

        return response

    def build_error_response(
        self,
        request: Request,
        error_message: str,
        status_code: int = 500,
    ) -> HTMLResponse:
        """Build a standardized error response."""
        error_html = self.templates.get_template("components/error_display.html").render(
            request=request, error_message=error_message
        )
        return HTMLResponse(content=error_html, status_code=status_code)

    def build_push_url(
        self,
        base_path: str,
        params: dict[str, str | int] | None = None,
    ) -> str:
        """Build a URL with query parameters for HX-Push-Url."""
        if not params:
            return base_path

        query_parts = []
        for key, value in params.items():
            if value and (key != "page" or value != 1):  # Skip default page=1
                query_parts.append(f"{key}={value}")

        if query_parts:
            return f"{base_path}?{'&'.join(query_parts)}"
        return base_path
```

#### 2.1.2 Add dependency in `app/dependencies.py`:

```python
def get_htmx_response_service(
    request: Request,
) -> "HTMXResponseService":
    from app.services.htmx_response_service import HTMXResponseService
    return HTMXResponseService(templates)

HTMXResponseServiceDep = Annotated[HTMXResponseService, Depends(get_htmx_response_service)]
```

**Testing**:
- [ ] Add unit tests for `HTMXResponseService`
- [ ] Test OOB swap rendering
- [ ] Test URL building

**Success Criteria**:
- [ ] Service handles all HTMX response patterns
- [ ] Clean interface for routers
- [ ] All tests pass

---

### Task 2.2: Migrate Routers to Use HTMXResponseService

**Priority**: P2 | **Effort**: 2-3 hours | **Risk**: Low

**Changes**:
- Update `finding_models_browse.py` to use service
- Update `drafts/views.py` to use service
- Update `drafts/helpers.py` - remove `build_htmx_response_with_oob()`

**Testing**:
- [ ] All existing UI tests pass
- [ ] Manual test of HTMX interactions

**Success Criteria**:
- [ ] No direct HTMX response building in routers
- [ ] `drafts/helpers.py` under 200 lines
- [ ] All tests pass

---

## Summary Checklist

### Phase 1 Tasks
- [ ] 1.1: FindingModelService context methods (2-3h)
- [ ] 1.2: Move JSON generation to DraftService (1-2h)
- [ ] 1.3: Creation workflow methods in CreationService (3-4h)
- [ ] 1.4: DraftService view context method (1-2h)
- [ ] 1.5: Move validation to services (1h)

### Phase 2 Tasks
- [ ] 2.1: Create HTMXResponseService (2-3h)
- [ ] 2.2: Migrate routers to use service (2-3h)

### Final Verification
- [ ] All unit tests pass
- [ ] All UI tests pass
- [ ] Coverage >= 85%
- [ ] No business logic in routers
- [ ] All router functions < 80 lines
- [ ] `drafts/helpers.py` < 200 lines

---

## Rollback Plan

Each task can be rolled back independently:

1. Git revert the specific commit
2. Restore old function/method
3. Update callers to use old pattern

No database migrations required - all changes are code-only.

---

## Post-Implementation

After completing both phases:

1. Update `app/CLAUDE.md` with new service patterns
2. Update `current_development_status` memory
3. Archive this plan to `tasks/done/`
4. Consider extracting remaining repositories to `app/repositories/`
