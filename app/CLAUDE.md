# Backend Development Guide - FindingModelForge

This guide covers backend development patterns and practices for the FastAPI application.

## Architecture Overview

The backend follows a layered architecture:

- **Routers** - HTTP endpoint handlers with request/response logic
- **Dependencies** - Dependency injection for cross-cutting concerns
- **Repositories** - Data access layer (MongoDB operations)
- **Models** - Pydantic models for validation and serialization
- **Core Domain** - Business logic via `findingmodel` library

## Key Files

### Core Application

- `main.py` - FastAPI app factory, lifespan management, middleware setup
- `config.py` - Pydantic Settings for environment configuration
- `dependencies.py` - Dependency injection factories and session management
- `models.py` - Pydantic models for API contracts and data validation

### Data Layer

- `database.py` - MongoDB connection and repository implementations
  - `Database` - Connection management
  - `UserRepo` - User CRUD operations
  - `DraftRepo` - Draft management (save, resume, submit)
  - `CommentRepo` - Comment thread management with atomic operations
- `cache.py` - Redis cache abstraction with health checks

### Authentication

- `auth.py` - JWT token management and GitHub OAuth flow
  - Token creation/validation
  - Cookie-based auth
  - User session management

### Routers (Refactored Architecture v1.3.0)

**Creation Workflow:**

- `creation.py` - Multi-step finding model creation workflow
  - AI-powered generation and similarity detection
  - Session management and state recovery
  - HTMX step navigation (URLs: `/create/*`)

**Draft Management:**

- `drafts.py` - Complete draft lifecycle management
  - Unified edit/view pages with mode parameter
  - Submit, delete, and update operations
  - Session adoption and recovery (URLs: `/drafts/*`)

**Public Browse:**

- `finding_models_browse.py` - Public finding models library
  - Search, pagination, and model details
  - HTMX navigation with caching (URLs: `/finding-models/*`)

**Simple Pages:**

- `home.py` - Landing page (URL: `/`)
- `auth_pages.py` - Login page UI (URL: `/login`)
- `profile.py` - User profile with draft management (URL: `/profile`)

**Core Services:**

- `auth.py` - Authentication endpoints
- `users.py` - User profile management
- `static.py` - Static file serving

## Coding Patterns

### 1. Async Everything

```python
# ✅ CORRECT - Use async/await for all I/O
async def get_finding_model(
    model_id: str,
    database: DatabaseDep,
    cache: CacheDep
) -> FindingModel | None:
    if cached := await cache.get(f"model:{model_id}"):
        return FindingModel.model_validate_json(cached)

    if doc := await database.finding_models.find_one({"_id": model_id}):
        await cache.set(f"model:{model_id}", doc.model_dump_json())
        return FindingModel.model_validate(doc)

    return None
```

### 2. Dependency Injection

```python
# Use FastAPI's dependency system for clean, testable code
from app.dependencies import DatabaseDep, CacheDep, CurrentUserDep

@router.post("/create")
async def create_model(
    request: FindingModelRequest,
    current_user: CurrentUserDep,  # Auto-injected
    database: DatabaseDep,          # Auto-injected
    cache: CacheDep,                # Auto-injected
) -> FindingModel:
    # Implementation
```

### 3. Type Safety

```python
# ALWAYS use type hints
from typing import Annotated

async def process_draft(
    draft_id: Annotated[str, Path(description="Draft ID")],
    user: CurrentUserDep,
) -> FindingModelDraft:
    # Implementation
```

### 4. Error Handling

```python
# Use HTTPException for API errors
from fastapi import HTTPException

async def get_draft(draft_id: str, user_id: int) -> FindingModelDraft:
    draft = await draft_repo.get_draft(draft_id, user_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return draft
```

### 5. Repository Pattern

```python
class DraftRepo:
    """Encapsulate all draft-related database operations."""

    def __init__(self, db: AsyncIOMotorDatabase[Any]) -> None:
        self.db = db
        self.collection = db.finding_model_drafts

    async def save_draft(
        self,
        user_id: int,
        name: str,
        inputs: FindingModelInputs,
        draft_id: str | None = None,
    ) -> FindingModelDraft:
        # Upsert logic with proper error handling
        # Return validated Pydantic model
```

## Session Management

The application uses Redis-backed sessions for the multi-step workflow:

```python
class FindingModelCreationSession(BaseModel):
    """Session data for finding model creation workflow."""
    session_id: str
    current_step: int = 1
    name: str | None = None
    description: str | None = None
    synonyms: list[str] = []
    attributes_markdown: str | None = None
    final_model: dict[str, Any] | None = None
    # Draft support
    draft_id: str | None = None
    draft_status: str | None = None
```

### Session Patterns

1. **Auto-creation** - Sessions created on-demand via dependency
2. **TTL Management** - 1-hour expiry with activity refresh
3. **Draft Adoption** - Recover state from draft if session lost
4. **Cookie Storage** - Session ID stored in HTTP-only cookie

## Draft System

### Draft Lifecycle

1. **Create** - Upsert by (user_id, name, status='draft')
2. **Autosave** - On GET to step 4, save current state
3. **Update** - POST to step 4 updates existing draft
4. **Submit** - Lock draft by changing status to 'submitted'
5. **Resume** - Populate session from draft, redirect to step

### Unified Draft Page Pattern

The draft system uses a single endpoint for all draft operations:

```python
@router.get("/drafts/{draft_id}", response_model=None)
async def unified_draft_page(
    draft_id: str,
    mode: str = Query("edit", description="Mode: edit or view"),
    request: Request,
    current_user: CurrentUserDep,
    database: DatabaseDep,
    session_manager: SessionManagerDep,
    draft_repo: DraftRepoDep,
) -> Response:
    """Unified endpoint for draft editing and viewing."""
```

#### Mode Parameter Usage

- **`?mode=edit`** (default) - Renders draft in edit mode with form
- **`?mode=view`** - Renders draft in read-only preview mode

#### Template Integration

```html
<!-- Edit mode -->
<a href="/api/finding-models/drafts/{{ draft.id }}">Edit Draft</a>

<!-- View mode -->
<a href="/api/finding-models/drafts/{{ draft.id }}?mode=view">Preview Draft</a>

<!-- Form submission with mode switching -->
<form hx-post="/api/finding-models/drafts/{{ draft.id }}/update-and-redirect">
  <!-- Updates draft and redirects to view mode -->
</form>
```

### Draft Repository Methods

- `save_draft()` - Create or update with upsert logic and action logging
- `get_draft()` - Retrieve by ID with ownership check
- `find_editable_by_name()` - Find draft for resume (case-insensitive)
- `find_latest_by_name()` - Get most recent draft by name
- `submit()` - Transition to submitted status with validation
- `delete_draft()` - Remove draft (only if status='draft')
- `list_for_user()` - Get all drafts for user with pagination

### Session Adoption Pattern

When a session is lost but draft_id is available:

```python
# Check for draft_id in query params or form data
draft_id = request.query_params.get("draft_id") or form_data.get("draft_id")

if draft_id and not session.attributes_markdown:
    draft = await draft_repo.get_draft(draft_id, current_user.id)
    if draft and draft.status == "draft":
        # Adopt draft state into session
        session.name = draft.name
        session.description = draft.inputs.description
        session.synonyms = draft.inputs.synonyms
        session.attributes_markdown = draft.inputs.attributes_markdown
        session.draft_id = draft.id
        session.draft_status = draft.status
        await session_manager.update_session(session)
```

## Response Types

### HTML Responses

```python
# For page rendering
@router.get("/page", response_class=HTMLResponse)
async def get_page(request: Request) -> str:
    return templates.get_template("page.html").render(
        request=request,
        data=data
    )
```

### Mixed Response Types

```python
# Use Response base class for flexibility
from fastapi import Response

async def process_step() -> Response:
    if should_redirect:
        return RedirectResponse(url="/next", status_code=303)
    else:
        return HTMLResponse(content=rendered_html)
```

## Testing Patterns

### Router Unit Testing

For comprehensive router testing, use the established patterns:

```python
class TestFindingModelsRouter:
    """Comprehensive router tests with proper mocking."""

    @pytest.fixture
    def mock_database(self) -> Database:
        """Create mock database with repositories."""
        db = Database()
        db.draft_repo = MagicMock(spec=DraftRepo)

        # Mock draft operations
        async def _save_draft(user_id, name, inputs, draft_id=None, generated_json=None):
            return FindingModelDraft(
                id=draft_id or "mock-draft-id",
                user_id=user_id,
                name=name,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                inputs=inputs,
                generated_json=generated_json,
                status="draft",
                action_log=[]
            )

        db.draft_repo.save_draft = _save_draft
        db.draft_repo.get_draft = AsyncMock(return_value=None)
        return db

    @pytest.fixture
    def authenticated_client(self, mock_user) -> TestClient:
        """Create authenticated test client."""
        client = TestClient(app)
        # Set session cookie for authentication
        client.cookies["creation_session_id"] = "test-session"

        # Mock the auth dependency
        app.dependency_overrides[get_current_user] = lambda: mock_user
        return client
```

### Test Categories by Priority

#### Priority 1: Critical Happy Path Tests

```python
async def test_process_step_4_happy_path(authenticated_client, mock_session):
    """Test step 4 processing with complete valid data."""
    response = authenticated_client.post(
        "/api/finding-models/create/step/4",
        data={
            "description": "Complete medical description for testing purposes",
            "synonyms": '["synonym1", "synonym2"]',
            "attributes_markdown": "## Section 1\n- attribute: value\n\n## Section 2\n- another: value"
        }
    )
    assert response.status_code in [200, 303]

async def test_unified_draft_page_edit_mode(authenticated_client):
    """Test unified draft page in edit mode."""
    draft_id = "507f1f77bcf86cd799439011"  # Valid ObjectId
    response = authenticated_client.get(f"/api/finding-models/drafts/{draft_id}")
    assert response.status_code in [200, 404]  # 404 if draft not found

async def test_unified_draft_page_view_mode(authenticated_client):
    """Test unified draft page in view mode."""
    draft_id = "507f1f77bcf86cd799439011"
    response = authenticated_client.get(f"/api/finding-models/drafts/{draft_id}?mode=view")
    assert response.status_code in [200, 404]
```

#### Priority 2: Draft State Transitions

```python
async def test_save_draft_with_existing_draft_id(authenticated_client):
    """Test updating existing draft via draft_id parameter."""
    response = authenticated_client.post(
        "/api/finding-models/create/step/4",
        data={
            "draft_id": "507f1f77bcf86cd799439011",
            "description": "Updated description for existing draft",
            "synonyms": '["updated1", "updated2"]',
            "attributes_markdown": "## Updated Section\n- updated: value"
        }
    )
    assert response.status_code in [200, 303, 404]

async def test_submit_draft_happy_path(authenticated_client):
    """Test submitting draft changes status to submitted."""
    draft_id = "507f1f77bcf86cd799439011"
    response = authenticated_client.post(f"/api/finding-models/drafts/{draft_id}/submit")
    assert response.status_code in [200, 303, 404]
```

#### Priority 3: Error Handling & Edge Cases

```python
async def test_step_4_with_invalid_draft_id(authenticated_client):
    """Test step 4 with malformed draft_id."""
    response = authenticated_client.post(
        "/api/finding-models/create/step/4",
        data={
            "draft_id": "invalid-not-objectid",
            "description": "Valid description for error case testing",
            "synonyms": '["valid"]',
            "attributes_markdown": "## Valid\n- test: value"
        }
    )
    # Should handle gracefully, not crash
    assert response.status_code in [200, 400, 422]

async def test_unified_draft_page_invalid_id(authenticated_client):
    """Test unified draft page with invalid draft ID."""
    response = authenticated_client.get("/api/finding-models/drafts/invalid-id")
    assert response.status_code == 400  # Bad Request for invalid ObjectId
```

### Session Testing Patterns

```python
@pytest.fixture
def mock_session_manager():
    """Mock session manager for testing."""
    manager = AsyncMock()

    # Default session state
    test_session = FindingModelCreationSession(
        session_id="test-session",
        current_step=4,
        name="Test Finding Model",
        description="Test description",
        synonyms=["test1", "test2"],
        attributes_markdown="## Test\n- test: value"
    )

    manager.get_or_create_session = AsyncMock(return_value=test_session)
    manager.update_session = AsyncMock(return_value=None)
    return manager

async def test_session_adoption_from_draft(mock_session_manager, mock_database):
    """Test session adopting state from draft."""
    # Setup draft
    draft = FindingModelDraft(
        id="test-draft-id",
        user_id=123,
        name="Draft Finding",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(
            description="Draft description",
            synonyms=["draft1"],
            attributes_markdown="## Draft\n- test: value"
        ),
        status="draft",
        action_log=[]
    )

    mock_database.draft_repo.get_draft = AsyncMock(return_value=draft)

    # Test session adoption logic
    session = await mock_session_manager.get_or_create_session()
    session.draft_id = draft.id
    session.name = draft.name

    assert session.draft_id == "test-draft-id"
    assert session.name == "Draft Finding"
```

### Integration Tests

```python
@pytest.mark.integration
async def test_full_workflow():
    # Test with real MongoDB/Redis
    pass

@pytest.mark.integration
async def test_draft_persistence():
    # Test draft operations with real database
    pass
```

## Common Tasks

### Adding a New Endpoint

1. Define Pydantic models in `models.py`
2. Add route handler in appropriate router
3. Use dependency injection for services
4. Add unit and integration tests
5. Update API documentation

### Adding a New Repository

1. Create class in `database.py`
2. Initialize in `Database.__init__()`
3. Add dependency in `dependencies.py`
4. Type with `Annotated[Repo, Depends(get_repo)]`

### Modifying Session Structure

1. Update `FindingModelCreationSession` in `dependencies.py`
2. Handle migration for existing sessions
3. Update session manager save/load logic
4. Test session adoption scenarios

## Security Best Practices

1. **Never trust user input** - Always validate with Pydantic
2. **Check ownership** - Verify user owns resource before access
3. **Use parameterized queries** - Avoid injection attacks
4. **Hash sensitive data** - Never store plaintext passwords
5. **Validate JWTs** - Check signature and expiration
6. **CORS configuration** - Restrict origins in production

## Performance Tips

1. **Use Redis cache** - Cache expensive operations
2. **Batch database operations** - Use `insert_many` when possible
3. **Index MongoDB collections** - Add indexes for common queries
4. **Async all the way** - Never block the event loop
5. **Connection pooling** - Reuse database connections

## Debugging

### Logging

```python
from loguru import logger

logger.info("Processing draft", draft_id=draft_id, user_id=user_id)
logger.error("Draft save failed", exc_info=True)
```

### Common Issues

- **Session loss** - Check Redis connection and TTL
- **Auth failures** - Verify JWT secret and cookie settings
- **Database errors** - Check MongoDB connection string
- **Type errors** - Run `mypy app` for type checking

## Environment Variables

Required in `.env`:

```env
# Security
SECRET_KEY=<strong-random-key>
GITHUB_CLIENT_ID=<oauth-app-id>
GITHUB_CLIENT_SECRET=<oauth-secret>

# Database
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=findingmodelforge

# Redis (optional but recommended)
REDIS_ENABLED=true
REDIS_HOST=localhost
```

## Quick Commands

```bash
# Run server with reload
uv run uvicorn app.main:app --reload

# Type checking
uv run mypy app

# Format code
uv run ruff format app

# Run tests
uv run pytest tests/ -v

# Test specific file
uv run pytest tests/test_drafts.py -v
```
