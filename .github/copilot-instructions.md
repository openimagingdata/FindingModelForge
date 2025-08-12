# GitHub Copilot Instructions for FindingModelForge

## Project Overview

FindingModelForge is a modern FastAPI web application for creating and managing finding models, which defining semantic
labels for medical imaging findings. This is a professional tool built with contemporary Python web development best
practices.

We always strive to use updated libraries and frameworks, with a focus on type safety, async patterns, and comprehensive
testing. The project is designed to be maintainable, scalable, and secure. Make sure to use tools such as Context7 to
get updated documentation for libraries and frameworks as needed.

## Core Technologies & Architecture

### Backend Stack

- **FastAPI** - Modern Python web framework for APIs and web applications
- **Python 3.12+** - Target Python version with extensive type hinting
- **Pydantic** - Data validation and serialization (drives APIs, DB models, UI, JSON schemas)
- **Redis** - In-memory data structure store for caching and session management
- **Motor** - Async MongoDB driver for database operations
- **Loguru** - Structured application logging
- **JWT + GitHub OAuth** - Authentication and authorization system

### Frontend Stack

- **Jinja2 Templates** - Server-side rendering with template inheritance
- **Tailwind CSS** - Utility-first CSS framework with custom dark theme support
- **Alpine.js** - Lightweight JavaScript framework for interactivity
- **Flowbite Components** - Pre-built UI components with data attribute-based functionality

Use websearch and Context7 to ensure you are using the latest Flowbite components and patterns, and always prefer
pre-built Flowbite components over custom implementations. Where possible, pull out re-usable components into Jinja2
macros (see `docs/UI_COMPONENT_MACROS.md` for information; see `templates/macros/*.html` for current implementations).

Please make sure to use Alpine.js for any interactivity—this includes handling user input, toggling UI elements, and
making AJAX requests. Minimize custom JavaScript where possible.

### Development Tools

- **uv** - Fast Python package manager (primary dependency management)
- **Task** - Task runner for automation (defined in Taskfile.yml)
- **Ruff** - Lightning-fast linting and formatting
- **MyPy** - Static type checking with strict configuration
- **Pytest** - Testing framework with coverage and async support
- **Pre-commit** - Automated code quality hooks

To use the local environment, run `uv python <scriptname>.py` for test scripts.

Use `uv ruff check` for linting and formatting checks, and `uv ruff format` to automatically fix issues.

Use `uv mypy` for type checking.

## Code Standards & Practices

### Python Code Quality

1. **Type Hinting**: Use extensive type hinting for all functions, methods, and variables
2. **Pydantic Models**: Use Pydantic for all data structures (API models, DB models, config)
3. **Async/Await**: Prefer async patterns for I/O operations (database, HTTP requests)
4. **Error Handling**: Use proper exception handling with descriptive error messages
5. **Logging**: Use Loguru for structured logging with appropriate levels
6. **Configuration**: Use pydantic-settings for environment-based configuration
7. **Dependency Injection**: Use FastAPI's dependency injection for services (database, auth, config)

### Code Organization

- **app/** - Main FastAPI application code
- **app/routers/** - API endpoint modules organized by domain
- **app/models.py** - Pydantic data models
- **app/auth.py** - Authentication and JWT utilities
- **app/config.py** - Application configuration management
- **app/database.py** - MongoDB connection and utilities
- **tests/** - Comprehensive test suite with pytest
- **templates/** - Jinja2 HTML templates
- **static/** - CSS, JavaScript, and image assets

### Formatting & Linting Rules

- **Line Length**: 120 characters maximum
- **Import Sorting**: Use Ruff to organize imports
- **Code Style**: Follow Ruff's extended rule set (see pyproject.toml)
- **Type Checking**: MyPy strict mode enabled with comprehensive checks
- **Markdown files**: Follow Markdownlint rules, especially remembering to include blank lines as appropriate.

## Development Workflow

### Getting Started

1. Use `task setup` to install dependencies and configure environment
2. Use `task dev` for development server with hot reload
3. Use `task dev-watch` for development with CSS watching
4. Edit `.env` file for GitHub OAuth credentials

### Code Quality Commands

- `task lint` - Format and fix linting issues
- `task check` - Run read-only quality checks (CI-friendly)
- `task test` - Run tests with coverage
- `task test-full` - Full test suite with quality checks

### Frontend Development

- `task build-frontend` - Build all frontend assets
- `task watch-css` - Watch for CSS changes
- Use Tailwind utility classes with custom dark theme
- Alpine.js for progressive enhancement

#### UI & Component Guidelines (MANDATORY)

🚨 **CRITICAL: NO custom JS/CSS. ALWAYS use Flowbite and Alpine.js.**

**Before writing ANY UI code:**

1. ✅ Check https://flowbite.com/docs/components/ FIRST
2. ✅ Use their exact HTML structure and CSS classes
3. ✅ Use Alpine.js `x-data`, `x-model`, computed properties for reactivity
4. ✅ Never deviate from established patterns without explicit approval
5. ❌ Do NOT create custom validation, modal, or interaction code

**Component/Macro Usage:**

- Always check for existing macros/components before creating new ones.
- Key macros: `flowbite_components.html`, `app_components.html`, `layout_components.html` (see
  `docs/UI_COMPONENT_MACROS.md`).
- Use `{% from ... import ... %}` and `{% include ... %}` for reuse.

**Component Discovery Checklist:**

1. Search `templates/components/` and `templates/macros/` for similar functionality
2. Reuse or extend existing macros/components
3. Only create new ones if truly needed, and document them

**Example of CORRECT Flowbite usage:**

```html
<!-- ✅ CORRECT: Uses Flowbite data attributes -->
<div data-accordion="collapse">
  <button data-accordion-target="#content" aria-expanded="false">Toggle</button>
  <div id="content" class="hidden">Content</div>
</div>
```

**Example of INCORRECT custom implementation:**

```html
<!-- ❌ WRONG: Custom JavaScript -->
<button onclick="toggleCustom()">Toggle</button>
<script>
  function toggleCustom() {
    /* custom code */
  }
</script>
```

**Alpine.js & HTMX Patterns:**

- Use Alpine.js for all UI interactivity (`x-data`, `x-model`, computed properties)
- Never write ad hoc JavaScript or manual DOM manipulation
- HTMX is used for multi-step forms and server-driven UI (e.g., finding model creation)
- Alpine.js is only for local UI state, not for business logic or API orchestration

## Profile Page Features

- The profile page (`/profile`) uses in-place editing, Alpine.js validation, and Flowbite components for all UI.
- Organization management uses badges, real-time validation, and no duplicate orgs (see
  `docs/PROFILE_PAGE_FEATURES.md`).

## Redis Cache Implementation

- The cache is always present and gracefully degrades if Redis is unavailable (see
  `docs/REDIS_CACHE_IMPLEMENTATION.md`).
- Used for user, GitHub, and finding model data.
- All cache operations are safe no-ops if Redis is down; no conditional logic needed in app code.

## Finding Model Creation Workflow

- Multi-step creation is modularized into separate templates (see `docs/refactoring_plan_finding_model_creation.md`).
- HTMX is used for step transitions and server-driven UI.
- All business logic is server-side; Alpine.js is only for UI state.
- Flowbite stepper and form components are required for all steps.

## Before You Code Checklist

1. Check Flowbite docs for the component you need
2. Check for existing macros/components in `templates/`
3. Use Alpine.js for interactivity, never ad hoc JS
4. Never write custom JS/CSS unless absolutely necessary and approved
5. Update documentation and tests when adding or changing macros/components

### Docker & Deployment

- `task build` - Build Docker image with frontend assets
- `task run-container` - Run application in container
- Multi-stage Dockerfile for production optimization

## Authentication & Security

### GitHub OAuth Integration

- OAuth flow handled in `app/routers/auth.py`
- JWT tokens with HTTP-only cookies for security
- Access and refresh token management
- XSS protection through secure token storage

### Security Best Practices

- Environment variables for secrets management
- Proper CORS configuration
- Secure cookie settings
- Input validation via Pydantic models

## Database Patterns

### MongoDB with Motor

- Use async/await patterns for all database operations
- Connection management in `app/database.py`
- Pydantic models for document schemas
- Proper error handling for database operations

### Example Database Usage

```python
# Always use async patterns and dependency injection
async def get_user(user_id: str, database=Annotated[Database, Depends(get_database)]) -> User | None:
    document = await database.users.find_one({"_id": user_id})
    return User(**document) if document else None
```

## API Design Principles

### FastAPI Patterns

- Use dependency injection for database, auth, and configuration
- Proper HTTP status codes and error responses
- Comprehensive API documentation via OpenAPI
- Request/response models with Pydantic

### Router Organization

- `/auth/*` - Authentication endpoints
- `/api/*` - API endpoints with versioning consideration
- Page routes in `app/routers/pages.py` for HTML responses

## Testing Guidelines

### Test Structure

- Unit tests for business logic
- Integration tests for API endpoints
- Async test patterns with pytest-asyncio
- High test coverage expectations (see coverage configuration)

### Test Categories

- `test_auth.py` - Authentication and JWT functionality
- `test_health.py` - Health check endpoints
- `test_pages.py` - Page rendering and templates
- `test_user_repo.py` - User data operations

## Environment Configuration

### Required Environment Variables

```env
# Application basics
APP_NAME="FindingModelForge"
DEBUG=true
ENVIRONMENT="development"

# Security
SECRET_KEY="your-secret-key-here"
ACCESS_TOKEN_EXPIRE_MINUTES=30

# GitHub OAuth (required for auth)
GITHUB_CLIENT_ID="your-github-client-id"
GITHUB_CLIENT_SECRET="your-github-client-secret"

# Database
MONGODB_URL="mongodb://localhost:27017"
DATABASE_NAME="findingmodelforge"
```

## Common Tasks & Patterns

### Adding New API Endpoints

1. Create router in `app/routers/`
2. Define Pydantic models for request/response
3. Implement async endpoint functions
4. Add comprehensive tests
5. Update documentation

### Adding New Pages

1. Create Jinja2 template in `templates/`—make sure to use Flowbite components where applicable
2. Add route in `app/routers/pages.py`
3. Handle authentication if required
4. Style with Tailwind CSS utilities

### Database Operations

1. Use Motor async patterns
2. Define Pydantic models for documents
3. Implement proper error handling
4. Add appropriate logging

## Debugging & Monitoring

### Logging Strategy

- Use Loguru for all logging
- Structured logging with context
- Appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- Request/response logging for debugging

### Health Checks

- `/api/health` - Basic health status
- `/api/health/ready` - Readiness check
- `/api/health/live` - Liveness check

## Best Practices for Copilot

### When Writing Code

1. **Always include type hints** - This is critical for this project
2. **Use async/await** for I/O operations
3. **Follow the established patterns** in existing code
4. **Use Pydantic models** for all data structures
5. **Include proper error handling** and logging
6. **Write comprehensive docstrings** for functions and classes
7. **ALWAYS use Flowbite components properly** - Never create custom implementations when Flowbite provides the
   functionality

### When Suggesting Changes

1. **Consider the entire request/response cycle** (auth, validation, business logic, response)
2. **Maintain consistency** with existing code patterns
3. **Use Context7 to check Flowbite documentation** before implementing UI components
4. **Include appropriate tests** when adding functionality
5. **Update related documentation** if needed
6. **Consider security implications** especially for auth-related changes

### When Troubleshooting

1. **Check logs** using Loguru output
2. **Verify environment configuration** in `.env`
3. **Run quality checks** with `task check`
4. **Test changes** with `task test`
5. **Consider async/await patterns** for any hanging or timing issues
6. **For UI issues, check if Flowbite components are properly initialized** with `initFlowbite()`

## Project-Specific Considerations

### Finding Models Domain

- This application deals with medical imaging finding models
- Focus on semantic labels and structured data
- Integration with the `findingmodel` library
- Professional medical software standards apply

### Performance Considerations

- Use async patterns consistently
- Optimize database queries
- Efficient static asset serving
- Consider caching strategies for production

### Deployment Context

- Containerized deployment with Docker
- Railway deployment platform
- GitHub Container Registry for images
- Environment-based configuration management

## Quick Reference Commands

```bash
# Development
task dev              # Start development server
task dev-watch        # Start with CSS watching
task setup            # Full environment setup

# Quality
task lint             # Format and fix issues
task check            # Read-only quality checks
task test             # Run tests with coverage

# Build
task build-frontend   # Build CSS and JS assets
task build            # Build Docker image
task run-container    # Run in container
```

Remember: This is a professional application with high code quality standards. Always prioritize type safety, proper
error handling, and comprehensive testing when making changes.
