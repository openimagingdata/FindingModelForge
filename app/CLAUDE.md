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
- `cache.py` - Redis cache abstraction with health checks

### Authentication
- `auth.py` - JWT token management and GitHub OAuth flow
  - Token creation/validation
  - Cookie-based auth
  - User session management

### Routers
- `finding_models.py` - Core finding model operations
  - Multi-step creation workflow
  - Draft autosave and resume
  - Model generation via AI
- `pages.py` - HTML page rendering for UI
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

### Draft Repository Methods
- `save_draft()` - Create or update with upsert logic
- `get_draft()` - Retrieve by ID with ownership check
- `find_editable_by_name()` - Find draft for resume
- `submit()` - Transition to submitted status
- `delete_draft()` - Remove draft (only if status='draft')

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

### Mocking Dependencies
```python
@pytest.fixture
def mock_database():
    db = MagicMock(spec=Database)
    db.finding_models = MagicMock()
    return db

async def test_create_model(mock_database):
    # Test with mocked database
```

### Integration Tests
```python
@pytest.mark.integration
async def test_full_workflow():
    # Test with real MongoDB/Redis
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