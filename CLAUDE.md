# Claude Code Instructions for FindingModelForge

## Project Overview

FindingModelForge is a FastAPI-based web application for creating and managing medical imaging finding models. These
models define semantic labels and structured attributes for medical imaging findings.

**Current Branch**: `refactor/router-cleanup` (main branch: `main`)

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
│   ├── routers/           # Focused API endpoints
│   │   ├── creation.py    # Creation workflow (/create/*)
│   │   ├── drafts.py      # Draft management (/drafts/*)
│   │   ├── finding_models_browse.py  # Browse/detail (/finding-models/*)
│   │   ├── home.py        # Landing page (/)
│   │   ├── auth_pages.py  # Login page (/login)
│   │   └── profile.py     # User profile (/profile)
│   ├── services/          # Business logic layer
│   │   ├── creation_service.py      # AI generation & workflow
│   │   ├── draft_service.py         # Draft CRUD operations
│   │   └── finding_model_service.py # Model browsing & caching
│   ├── utils/             # Utilities and helpers
│   │   └── slug.py        # URL slug generation
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

- **100% test success rate** (144 tests passing: unit tests + UI tests)
- **Comprehensive coverage**: Unit tests for backend logic, Playwright tests for UI workflows
- **Priority-based organization**: Critical paths → State transitions → Edge cases → Access control
- **Realistic test data**: Valid ObjectIds, proper session mocking, comprehensive assertions
- **Playwright MCP integration**: Browser automation for debugging and verification
- **HTMX-aware testing**: Proper content swap detection and dynamic title testing
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
5. **Verify**: All router tests pass (78%+ coverage maintained)

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

### URL Structure (Simplified in v1.3.0)

**Current URL structure (clean, simplified):**

```
Creation Workflow:
  /create/step/1      # Step 1: Name and description entry
  /create/step/2      # Step 2: Description editing and similarity
  /create/step/3      # Step 3: Review similar models
  /create/restart     # Restart creation workflow
  /create/resume      # Resume from existing draft

Draft Management:
  /drafts/{id}                    # Unified draft page (edit/view modes)
  /drafts/{id}/submit             # Submit draft for review
  /drafts/{id}/delete             # Delete draft
  /drafts/{id}/update-and-redirect # Update and switch to view mode

Public Browse:
  /finding-models                 # Browse all finding models
  /finding-models/{slug}          # Individual model details

Simple Pages:
  /                   # Home page
  /login              # Login page
  /profile            # User profile with drafts
```

**Replaced URLs (removed in v1.3.0):**

- `/api/finding-models/create/*` → `/create/*`
- `/api/finding-models/drafts/*` → `/drafts/*`

### Finding Model Creation

- **Multi-step workflow with HTMX** - 3-step process with content swapping
- **AI-powered generation and similarity detection** - OpenAI integration for intelligent assistance
- **Draft autosave and resume functionality** - Seamless workflow interruption/resumption
- **Submit and lock mechanism** - Prevent edits after submission

### Comment System

**Collaborative feedback and discussion system:**

- **Scope**: Comments on submitted drafts and public finding models only
- **Single-level threading**: Comments can have replies (no nested replies)
- **Rate limiting**: 3 comments per minute per user with 429 enforcement
- **Report functionality**: Flag inappropriate content with double-report prevention
- **User comment index**: Track comment history for user profiles
- **Authentication required**: Only logged-in users can comment
- **Character limits**: 1-2000 characters with real-time validation
- **HTMX dynamic updates**: Comments update without page reload
- **MongoDB architecture**: Separate `comment_threads` collection for clean separation

### Draft Management System

**Complete lifecycle with unified approach:**

- **Unified endpoint pattern**: `GET /drafts/{id}?mode=edit|view` for all draft operations
- **Auto-save on step 4**: Automatic draft creation/update during attributes editing
- **Session adoption**: Seamless recovery when sessions are lost via draft_id
- **User isolation**: One editable draft per (user_id, name) with secure ownership
- **Action logging**: Comprehensive audit trail for all operations
- **Status management**: draft → submitted (locked from further edits)
- **Smart resume**: Name-based lookup shows submitted models in view mode

### Finding Models Display System

**Public browseable library with advanced HTMX patterns:**

- **History element configuration**: `hx-history-elt="true"` on `#main-content` prevents CSS-in-JS conflicts
- **OOB breadcrumb swaps**: Conditional `hx-swap-oob="true"` prevents duplicate breadcrumbs on initial load
- **Dynamic page titles**: Backend generates context-aware titles, HTMX handles automatic updates
- **Template-based navigation**: Hidden DOM templates for clean browser history restoration
- **Debounced search**: Server-side filtering with `input changed delay:500ms` trigger
- **Smart caching**: Redis optimization with graceful fallback for GitHub API model data
- **SEO optimization**: Proper URL structure and meta tags for search indexing

## Debugging Tips

1. **Check logs**: `tail -f logs/app.log` or `tail -f test.log` for development
2. **Verify services**: `docker-compose ps`
3. **Session issues**: Check Redis connection
4. **UI problems**: Ensure `initFlowbite()` called after HTMX swaps
5. **Type errors**: Run `mypy app --show-error-codes`
6. **HTMX issues**: Use `hx-history-elt="true"` on main container to prevent CSS conflicts
7. **Playwright debugging**: Use Playwright MCP for real-time browser inspection
8. **Test failures**: Run `uv run pytest --no-cov -q` for fast test execution
9. **Breadcrumb duplicates**: Check conditional OOB rendering with `is_htmx_request` flag

## Important Guidelines

1. **Do what's asked, nothing more** - Avoid over-engineering
2. **Prefer editing over creating** - Modify existing files when possible
3. **Follow conventions** - Match existing code style
4. **Document complex logic** - But avoid obvious comments
5. **Test critical paths** - Especially auth and data operations

## Technical Debt Management

When deferring features or identifying technical debt:

- Document issues in `tasks/technical_debt.md`
- Include priority, effort estimate, and proposed solution
- Reference the technical debt file in relevant code comments
- Review and address high-priority items before new features

## Critical Planning Rule

**NEVER make unilateral changes to agreed plans**. When a plan has been documented and agreed upon:

- Follow the plan exactly as specified
- If changes seem necessary, STOP and discuss with the user
- Document any proposed deviations and get explicit approval
- Router names, URL structures, and architectural decisions must match the plan
- "Avoiding breaking changes" is NOT a valid reason to deviate from the plan
- All documented URL mappings, file names, and structures must be implemented as planned

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Flowbite Components**: https://flowbite.com/docs/
- **Alpine.js**: https://alpinejs.dev
- **Tailwind CSS**: https://tailwindcss.com
- **Finding Model Library**: Internal `findingmodel` package

---

_Remember: This is a medical domain application. Maintain high code quality, comprehensive testing, and proper error
handling throughout._
