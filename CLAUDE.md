# Claude Code Instructions for FindingModelForge

## Project Overview

FindingModelForge is a FastAPI-based web application for creating and managing medical imaging finding models. These models define semantic labels and structured attributes for medical imaging findings, using the `findingmodel` library for core functionality.

**Current Branch**: `dev` (main branch: `main`)

## Technical Stack

### Backend
- **FastAPI** (0.115.0+) - Async web framework with automatic API documentation
- **Python 3.12+** - With extensive type hinting throughout
- **Pydantic** - Data validation for models, API contracts, and config
- **Motor** - Async MongoDB driver for data persistence
- **Redis** - Optional caching layer (configurable via env)
- **JWT + GitHub OAuth** - Authentication system with HTTP-only cookies
- **Loguru** - Structured logging framework

### Frontend
- **Jinja2** - Server-side templating with component macros
- **Tailwind CSS v4** - Utility-first CSS with dark mode support
- **Alpine.js** - Reactive JavaScript for interactivity
- **Flowbite** - Pre-built UI components (data-attribute driven)
- **Vite** - Modern frontend build system with hot reload

### Core Domain Library
- **findingmodel** (0.3.1+) - Core library for finding model operations
  - Provides `FindingInfo`, `Index`, `Person`, `Organization` models
  - Tools for AI-powered model generation and similarity detection

## Project Structure

```
/Users/talkasab/Repos/FindingModelForge/
├── app/                      # FastAPI application
│   ├── main.py              # Application factory and lifespan
│   ├── auth.py              # JWT and OAuth implementation
│   ├── cache.py             # Redis cache abstraction
│   ├── config.py            # Pydantic settings management
│   ├── database.py          # MongoDB connection and repositories
│   ├── dependencies.py      # FastAPI dependency injection
│   ├── models.py            # Pydantic data models
│   ├── health.py            # Health check endpoints
│   ├── vite_manifest.py     # Vite asset management
│   └── routers/
│       ├── auth.py          # Authentication routes
│       ├── finding_models.py # Finding model CRUD operations
│       ├── pages.py         # HTML page rendering
│       ├── static.py        # Static file serving
│       └── users.py         # User management
├── templates/               # Jinja2 templates
│   ├── base.html           # Base template with Tailwind/Alpine
│   ├── components/         # Reusable UI components
│   ├── macros/             # Jinja2 macros for components
│   └── *.html              # Page templates
├── static/                 # Static assets
│   ├── css/               # Compiled Tailwind CSS
│   ├── js/                # Vite-built JavaScript
│   └── images/            # Icons and images
├── src/                   # Frontend source files
│   ├── input.css         # Tailwind input file
│   └── js/main.js        # JavaScript entry point
├── tests/                 # Pytest test suite
├── docs/                  # Documentation
├── package.json          # Node dependencies (Tailwind, Vite, Alpine)
├── pyproject.toml        # Python dependencies and tool config
├── vite.config.js        # Vite configuration
├── Taskfile.yml          # Task runner definitions
└── docker-compose.yml    # Local development services

```

## Key Patterns & Conventions

### Type Safety
- **Always** use type hints for function signatures
- Use `Annotated` for FastAPI dependencies
- Prefer explicit types over `Any`
- Enable MyPy strict mode compliance

### Async Patterns
```python
# Always use async/await for I/O operations
async def get_finding_model(
    model_id: str,
    database: DatabaseDep,
    cache: CacheDep
) -> FindingModel | None:
    # Check cache first
    if cached := await cache.get(f"model:{model_id}"):
        return FindingModel.model_validate_json(cached)

    # Fetch from database
    if doc := await database.finding_models.find_one({"_id": model_id}):
        # Cache for next time
        await cache.set(f"model:{model_id}", doc.model_dump_json())
        return FindingModel.model_validate(doc)

    return None
```

### Dependency Injection
```python
# Use FastAPI's dependency system
from app.dependencies import DatabaseDep, CacheDep, CurrentUserDep

@router.post("/create")
async def create_model(
    request: FindingModelRequest,
    current_user: CurrentUserDep,  # Auto-injected auth user
    database: DatabaseDep,          # Auto-injected database
    cache: CacheDep,                # Auto-injected cache
) -> FindingModel:
    ...
```

### Frontend Components

**CRITICAL: Use Flowbite's data-attribute patterns, NOT custom JavaScript**

```html
<!-- ✅ CORRECT: Flowbite accordion -->
<div data-accordion="collapse">
    <h2 id="accordion-heading-1">
        <button type="button"
                data-accordion-target="#accordion-body-1"
                aria-expanded="false"
                aria-controls="accordion-body-1">
            Toggle Section
        </button>
    </h2>
    <div id="accordion-body-1" class="hidden" aria-labelledby="accordion-heading-1">
        Content here
    </div>
</div>

<!-- ❌ WRONG: Custom implementation -->
<button onclick="toggleSection()">Toggle</button>
```

### Jinja2 Macros
```jinja
{# Use macros for reusable components #}
{% from "macros/app_components.html" import render_finding_model %}

{{ render_finding_model(model_data) }}
```

## Development Workflow

### Environment Setup
```bash
# Install Python dependencies
uv sync --all-extras --dev

# Install Node dependencies and build frontend
npm install
npm run build

# Or use Task runner
task setup
```

### Running Development Server
```bash
# With hot reload
task dev

# With CSS watching
task dev-watch

# Manual
uv run uvicorn app.main:app --reload
```

### Code Quality
```bash
# Format and lint
task lint
# or
uv run ruff format .
uv run ruff check --fix .

# Type checking
task typecheck
# or
uv run mypy app

# Run tests
task test
# or
uv run pytest
```

### Frontend Development
```bash
# Build CSS
npm run build:css

# Watch CSS changes
npm run watch:css

# Build JavaScript with Vite
npm run build:js

# Full frontend build
task build-frontend
```

## Environment Configuration

Required `.env` file:
```env
# Application
APP_NAME="FindingModelForge"
DEBUG=true
ENVIRONMENT=development

# Security
SECRET_KEY="your-secret-key-here"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# GitHub OAuth
GITHUB_CLIENT_ID="your-client-id"
GITHUB_CLIENT_SECRET="your-client-secret"

# MongoDB
MONGODB_URI="mongodb://localhost:27017"
MONGODB_DB="findingmodelforge"

# Redis (optional)
REDIS_ENABLED=true
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_DB=0

# Server
HOST="0.0.0.0"
PORT=8000
```

## Finding Model Domain

The application works with medical imaging finding models that have:
- **Name**: Primary identifier for the finding
- **Description**: Clinical description
- **Synonyms**: Alternative names
- **Attributes**: Structured properties with controlled vocabularies
- **Tags**: Categorization metadata

### Key Operations
1. **Check Name Availability** - Verify uniqueness in index
2. **Generate Finding Info** - AI-powered description/synonym generation
3. **Find Similar Models** - Detect potential duplicates
4. **Create Model** - Generate complete model with attributes
5. **Index Management** - Store and retrieve models from MongoDB

## Common Tasks

### Adding a New API Endpoint
1. Define Pydantic models in `app/models.py`
2. Create route handler in appropriate router
3. Use dependency injection for database/cache/auth
4. Add tests in `tests/`
5. Update API documentation if needed

### Adding a New Page
1. Create template in `templates/`
2. Use Flowbite components and Alpine.js
3. Add route in `app/routers/pages.py`
4. Style with Tailwind utilities
5. Test authentication if protected

### Working with the Database
```python
# In app/database.py or repositories
async def create_finding_model(
    self,
    model_data: FindingModelCreate
) -> FindingModel:
    doc = model_data.model_dump()
    doc["created_at"] = datetime.now(UTC)

    result = await self.collection.insert_one(doc)
    doc["_id"] = result.inserted_id

    return FindingModel.model_validate(doc)
```

### Using the Cache
```python
# Cache operations are optional (check if enabled)
if cache and await cache.is_healthy():
    await cache.set(
        key="model:123",
        value=model.model_dump_json(),
        ttl=3600  # 1 hour
    )
```

## Testing

### Running Tests
```bash
# All tests with coverage
task test

# Specific test file
uv run pytest tests/test_auth.py -v

# Integration tests only
uv run pytest -m integration
```

### Test Structure
- Unit tests for business logic
- Integration tests for API endpoints
- Async test patterns with `pytest-asyncio`
- Mock external services when appropriate

## Docker & Deployment

### Local Development
```bash
# Start MongoDB and Redis
docker-compose up -d

# Build application image
task build

# Run in container
task run-container
```

### Production Considerations
- Set strong `SECRET_KEY`
- Configure production MongoDB URI
- Enable Redis for caching
- Set `DEBUG=false`
- Configure proper CORS origins
- Use HTTPS termination

## Important Guidelines

1. **Type Safety**: Always include type hints
2. **Async First**: Use async/await for all I/O
3. **Error Handling**: Proper exception handling with HTTPException
4. **Logging**: Use Loguru with appropriate levels
5. **UI Components**: Use Flowbite's built-in functionality
6. **Testing**: Write tests for new features
7. **Security**: Never commit secrets, use env vars

## Debugging Tips

1. Check logs with Loguru output
2. Verify `.env` configuration
3. Run `task check` for code quality
4. For UI issues, ensure `initFlowbite()` is called
5. Check MongoDB connection status
6. Verify Redis cache if enabled

## Resources

- FastAPI Docs: https://fastapi.tiangolo.com
- Flowbite Components: https://flowbite.com/docs
- Alpine.js: https://alpinejs.dev
- Tailwind CSS: https://tailwindcss.com
- Finding Model Library: Internal `findingmodel` package

---

Remember: This is a medical domain application. Maintain high code quality, comprehensive testing, and proper error handling throughout.
