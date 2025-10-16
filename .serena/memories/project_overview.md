# FindingModelForge Project Overview

## Purpose

FindingModelForge is a FastAPI-based web application for creating and managing medical imaging finding models. These
models define semantic labels and structured attributes for medical imaging findings, using the `findingmodel` library
(0.3.1+) for core functionality.

## Key Features

- AI-powered finding model generation and similarity detection
- Step-by-step finding model creation workflow with draft saving
- **Draft management system with autosave functionality**
- GitHub OAuth authentication with JWT tokens
- MongoDB persistence with Redis caching (Redis REQUIRED)
- Modern frontend with Tailwind CSS, Alpine.js, and Vite
- **Resume workflow from drafts**
- **Submit and lock draft functionality**
- **Comment system for collaborative feedback**

## Tech Stack

### Backend

- **FastAPI** (0.115.0+) - Async web framework with automatic API documentation
- **Python 3.12+** - With extensive type hinting throughout
- **Pydantic** - Data validation for models, API contracts, and config
- **Motor** - Async MongoDB driver for data persistence
- **Redis** - **REQUIRED** for session management (not optional)
- **JWT + GitHub OAuth** - Authentication system with HTTP-only cookies
- **Loguru** - Structured logging framework

### Frontend

- **Jinja2** - Server-side templating with component macros
- **Tailwind CSS v4** - Utility-first CSS with dark mode support
- **Alpine.js** - Reactive JavaScript for interactivity
- **Flowbite** - Pre-built UI components (data-attribute driven)
- **Vite** - Modern frontend build system with hot reload
- **HTMX** - For dynamic server-driven interactions

### Core Domain Library

- **findingmodel** (0.3.1+) - Core library for finding model operations
  - Provides `FindingInfo`, `FindingModelFull`, `Index`, `Person`, `Organization` models
  - Tools for AI-powered model generation and similarity detection

## Backend Architecture

### Layered Structure

```
HTTP Request
    ↓
Router (app/routers/)           # HTTP handling, request/response
    ↓
Service (app/services/)         # Business logic orchestration
    ↓
Repository (app/database.py)    # Data access layer
    ↓
Database (MongoDB)              # Persistence
```

### Router Organization

#### Simple Routers (Single File)
For focused functionality with few endpoints:
- **`creation.py`** - Creation workflow endpoints (3 steps)
- **`finding_models_browse.py`** - Browse and detail pages
- **`home.py`** - Landing page
- **`auth_pages.py`** - Login page
- **`profile.py`** - User profile

#### Modular Routers (Directory Structure)
For complex functionality with many endpoints, use module pattern:

```
app/routers/drafts/
├── __init__.py              # Combines all routers
├── views.py                 # GET endpoints (pages)
├── mutations.py             # POST endpoints (CRUD)
├── workflows.py             # POST endpoints (state transitions)
├── comments.py              # POST endpoints (comment operations)
└── helpers.py               # Shared helper functions (11 helpers)
```

**Benefits of Modular Pattern**:
- **Discoverability**: Clear separation by HTTP method and purpose
- **Maintainability**: Smaller files (~250 lines vs 866 lines)
- **Testability**: Helpers can be unit tested independently
- **Scalability**: Easy to add new routers without growing monolith

**When to Use Modular Pattern**:
- Router file exceeds ~500 lines
- Multiple distinct workflows (view, edit, submit, delete, comment)
- Complex helper functions that deserve unit tests
- Team working on same router (reduces merge conflicts)

### Service Layer Patterns

Services orchestrate business logic and coordinate between repositories:

```python
class DraftService:
    def __init__(self, draft_repo: DraftRepo, user_repo: UserRepo, ...):
        self.draft_repo = draft_repo
        self.user_repo = user_repo

    async def save_draft(...):
        # Orchestration: ensure user exists, save draft, log action
        await ensure_person_for_user(self.user_repo, user)
        draft = await self.draft_repo.save_draft(...)
        return draft
```

**Service Responsibilities**:
- Ownership verification
- Workflow state transitions
- Cross-repository coordination
- Business rule enforcement

**NOT Service Responsibilities**:
- Simple CRUD (call repo directly from router)
- Data filtering (do in database queries)
- HTTP concerns (router responsibility)

### Repository Pattern

Repositories provide async database operations:

```python
class DraftRepo:
    async def save_draft(...)  # Create or update
    async def get_draft(...)   # Read by ID
    async def list_for_user(...)  # Query with filters
    async def delete_draft(...)  # Delete
```

**Repository Best Practices**:
- Use MongoDB queries for filtering (not Python loops)
- Return domain models (FindingModelDraft, User, etc.)
- Handle database errors, raise domain exceptions
- Use indexes for performance

## Infrastructure Requirements

### Redis (REQUIRED)
- **Purpose**: Session management for creation workflow
- **Behavior**: Server fails to start if Redis unavailable
- **Configuration**: `REDIS_HOST`, `REDIS_PORT` in `.env` (no enable/disable flag)
- **Implementation**: [`app/main.py:34-51`](app/main.py#L34-L51) checks health on startup
- **Error**: Raises `RuntimeError` with clear message if unavailable

### MongoDB (REQUIRED)
- **Purpose**: Primary data store for all application data
- **Behavior**: Server fails to start if MongoDB unavailable
- **Configuration**: `MONGODB_URI`, `MONGODB_DB` in `.env`

## Draft System Features

- **Autosave on Step 4**: Automatically saves drafts during attribute editing
- **Draft Repository**: MongoDB-backed draft storage with action logging
- **Draft States**: `draft` (editable) and `submitted` (locked)
- **Resume Workflow**: Can resume from draft at any step
- **Session Adoption**: Automatic draft state recovery on session loss
- **User-Scoped Drafts**: Each user's drafts are isolated

## Current Branch

- Working branch: `dev`
- Main branch: `main`

## Environment

- Platform: Darwin (macOS)
- Python: 3.12+
- Node.js required for frontend build tools
