# Claude Code Instructions for FindingModelForge

## Project Overview

FindingModelForge is a FastAPI-based web application for creating and managing medical imaging finding models. These
models define semantic labels and structured attributes for medical imaging findings.

**Current Branch**: `feature/finding-model-draft-saving` (main branch: `main`)

## Domain-Specific Guides

📚 **See specialized guides for detailed instructions:**

- **Backend Development**: [`app/CLAUDE.md`](app/CLAUDE.md) - FastAPI, async patterns, repositories
- **Frontend/UI Development**: [`templates/CLAUDE.md`](templates/CLAUDE.md) - Flowbite, Alpine.js, HTMX
- **Testing**: [`tests/CLAUDE.md`](tests/CLAUDE.md) - Testing patterns, fixtures, commands

## Technical Stack

### Backend

- **FastAPI** (0.115.0+) - Async web framework
- **Python 3.12+** - With type hints throughout
- **Pydantic** - Data validation and settings
- **Motor** - Async MongoDB driver
- **Redis** - Optional caching layer
- **JWT + GitHub OAuth** - Authentication

### Frontend

- **Jinja2** - Server-side templating
- **Tailwind CSS v4** - Utility-first CSS
- **Alpine.js** - Reactive JavaScript
- **Flowbite** - Pre-built UI components
- **HTMX** - Server-driven interactions
- **Vite** - Build system

### Infrastructure

- **MongoDB** - Primary data store
- **Redis** - Session and cache storage
- **Docker** - Containerization
- **GitHub Actions** - CI/CD

## Project Structure

```
FindingModelForge/
├── app/                    # Backend application (see app/CLAUDE.md)
│   ├── routers/           # API endpoints
│   ├── database.py        # Repositories
│   ├── dependencies.py    # DI & sessions
│   └── models.py          # Data models
├── templates/             # Frontend templates (see templates/CLAUDE.md)
│   ├── components/        # Reusable UI
│   └── macros/           # Jinja2 macros
├── tests/                 # Test suite (see tests/CLAUDE.md)
├── static/               # Built assets
├── src/                  # Frontend source
├── docs/                 # Documentation
└── .serena/              # AI context & memories
```

## Core Principles

### 1. Type Safety First

- **Always** use type hints
- Use `Annotated` for FastAPI dependencies
- Run `mypy` before committing

### 2. Async All The Way

- Use `async/await` for all I/O operations
- Never block the event loop
- Leverage Motor for MongoDB, aioredis for Redis

### 3. UI Component Rules

⚠️ **CRITICAL UI RULES** ⚠️

- ✅ **ALWAYS** use Flowbite components from docs
- ✅ **ALWAYS** use Alpine.js for interactivity
- ❌ **NEVER** create custom CSS classes
- ❌ **NEVER** write custom JavaScript
- See [`templates/CLAUDE.md`](templates/CLAUDE.md) for details

### 4. Testing Philosophy

- **Comprehensive unit tests** (70 tests, 71% router coverage achieved)
- **Priority-based organization**: Critical paths → State transitions → Edge cases → Access control
- **Realistic test data**: Valid ObjectIds, proper session mocking, comprehensive assertions
- **Integration tests** for full workflows with real services
- **Playwright** for end-to-end browser testing
- **Router testing patterns**: See [`tests/CLAUDE.md`](tests/CLAUDE.md) for examples

### 5. Security Best Practices

- Validate all input with Pydantic
- Check resource ownership before access
- Use parameterized database queries
- Store secrets in environment variables
- Enable CORS restrictions in production

## Development Workflow

### Quick Start

```bash
# Setup everything
task setup

# Run development server
task dev

# Run tests
task test-unit  # Fast unit tests
task test       # Full test suite
```

### Before Committing

1. **Format & Lint**: `task lint`
2. **Type Check**: `uv run mypy app`
3. **Test**: `task test-unit` (fast) or `task test` (comprehensive)
4. **Check UI**: Ensure Flowbite patterns followed
5. **Verify**: All router tests pass (71% coverage maintained)

### Common Tasks

- **Add API endpoint**: See [`app/CLAUDE.md`](app/CLAUDE.md)
- **Add UI component**: See [`templates/CLAUDE.md`](templates/CLAUDE.md)
- **Add tests**: See [`tests/CLAUDE.md`](tests/CLAUDE.md)

## Environment Configuration

Required `.env` file:

```env
# Security
SECRET_KEY="strong-random-key"
GITHUB_CLIENT_ID="your-oauth-app-id"
GITHUB_CLIENT_SECRET="your-oauth-secret"

# Database
MONGODB_URI="mongodb://localhost:27017"
MONGODB_DB="findingmodelforge"

# Redis (optional but recommended)
REDIS_ENABLED=true
REDIS_HOST="localhost"
REDIS_PORT=6379
```

## Key Features

### Finding Model Creation

- Multi-step workflow with HTMX
- AI-powered generation and similarity detection
- Draft autosave and resume functionality
- Submit and lock mechanism

### Draft Management System

**Complete lifecycle with unified approach:**

- **Unified endpoint pattern**: `GET /drafts/{id}?mode=edit|view` for all draft operations
- **Auto-save on step 4**: Automatic draft creation/update during attributes editing
- **Session adoption**: Seamless recovery when sessions are lost via draft_id
- **User isolation**: One editable draft per (user_id, name) with secure ownership
- **Action logging**: Comprehensive audit trail for all operations
- **Status management**: draft → submitted (locked from further edits)
- **Smart resume**: Name-based lookup shows submitted models in view mode

## Debugging Tips

1. **Check logs**: `tail -f logs/app.log`
2. **Verify services**: `docker-compose ps`
3. **Session issues**: Check Redis connection
4. **UI problems**: Ensure `initFlowbite()` called after HTMX swaps
5. **Type errors**: Run `mypy app --show-error-codes`

## Important Guidelines

1. **Do what's asked, nothing more** - Avoid over-engineering
2. **Prefer editing over creating** - Modify existing files when possible
3. **Follow conventions** - Match existing code style
4. **Document complex logic** - But avoid obvious comments
5. **Test critical paths** - Especially auth and data operations

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Flowbite Components**: https://flowbite.com/docs/components/
- **Alpine.js**: https://alpinejs.dev
- **Tailwind CSS**: https://tailwindcss.com
- **Finding Model Library**: Internal `findingmodel` package

---

_Remember: This is a medical domain application. Maintain high code quality, comprehensive testing, and proper error
handling throughout._
