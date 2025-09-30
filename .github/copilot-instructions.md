# GitHub Copilot Instructions for FindingModelForge

## Project Overview

FindingModelForge is a modern FastAPI web application for creating and managing medical imaging finding models. These
models define semantic labels and structured attributes for medical imaging findings.

**Current Branch**: `dev` (main branch: `main`)

## Quick Technology Reference

**Backend**: FastAPI (Python 3.12+), Pydantic, Motor (MongoDB), Redis, JWT + GitHub OAuth
**Frontend**: Jinja2, Tailwind CSS v4, Alpine.js, Flowbite components, HTMX
**Tools**: uv (package manager), Task (automation), Ruff (linting), MyPy (type checking), Pytest

For detailed technology information, see **CLAUDE.md**.

## Core Development Principles

⚠️ **CRITICAL**: Always reference the detailed guides before coding:

- **CLAUDE.md** - Project architecture, principles, and workflows
- **app/CLAUDE.md** - Backend patterns (FastAPI, async, repositories, testing)
- **templates/CLAUDE.md** - Frontend rules (Flowbite components, Alpine.js)
- **tests/CLAUDE.md** - Testing strategies and patterns

### Key Rules Summary

1. **Type Safety**: Extensive type hints required (see `app/CLAUDE.md`)
2. **Async Patterns**: Use async/await for all I/O operations (see `app/CLAUDE.md`)
3. **UI Components**: ONLY use Flowbite components + Alpine.js (see `templates/CLAUDE.md`)
4. **Testing**: 100% test success rate maintained (see `tests/CLAUDE.md`)
5. **Architecture**: Follow repository pattern and dependency injection (see `app/CLAUDE.md`)

## Development Workflow

**Quick Start**: `task setup` → `task dev` → Edit `.env` for GitHub OAuth credentials
**Quality**: `task lint` (fix issues) → `task test` (run tests) → `task check` (CI checks)
**Frontend**: `task build-frontend` (build assets) → `task dev-watch` (CSS watching)

For detailed workflow information, see **CLAUDE.md**.

### 🚨 CRITICAL UI Rules

**MANDATORY**: Read **templates/CLAUDE.md** before ANY UI work.

**Golden Rules:**
- ✅ ALWAYS use Flowbite components from https://flowbite.com/docs/
- ✅ ALWAYS use Alpine.js for interactivity
- ❌ NEVER create custom CSS classes or JavaScript
- ❌ NEVER deviate from Flowbite patterns

**Before coding UI**: Check `templates/CLAUDE.md` + `docs/UI_COMPONENT_MACROS.md` for existing components.

## Key Features & Patterns

**Multi-step Creation Workflow**: HTMX-driven, server-side logic (see `docs/finding-model-creation-workflow.md`)
**Comment System**: Collaborative feedback on models/drafts (see `docs/RECENT_UPDATES_SUMMARY.md`)
**Draft Management**: Unified edit/view with autosave (see `docs/DRAFT_WORKFLOW.md`)
**Profile Management**: In-place editing with real-time validation (see `docs/PROFILE_PAGE_FEATURES.md`)
**Cache Layer**: Redis with graceful degradation (see `docs/REDIS_CACHE_IMPLEMENTATION.md`)

## Before You Code Checklist

1. **Read relevant CLAUDE.md files** for your work area
2. **Check existing components** in `templates/` and `docs/UI_COMPONENT_MACROS.md`
3. **Follow Flowbite + Alpine.js patterns** (never custom CSS/JS)
4. **Use async/await patterns** for all I/O operations
5. **Write tests** following `tests/CLAUDE.md` patterns

**Deployment**: Docker containerization with Railway platform (see `CLAUDE.md` for details)

## Authentication & Security

**Authentication**: GitHub OAuth + JWT with HTTP-only cookies (see `app/CLAUDE.md`)
**Security**: Environment variables, CORS, Pydantic validation (see `CLAUDE.md`)
**Patterns**: Check `app/CLAUDE.md` for security best practices

## Database & API Patterns

**Database**: MongoDB with Motor (async), repository pattern (see `app/CLAUDE.md`)
**Schemas**: See `docs/database.md` for collection structures
**API Design**: FastAPI dependency injection, Pydantic models (see `app/CLAUDE.md`)

**URL Structure**: Simplified in v1.3.0 (see `CLAUDE.md` for current routes)
**Router Architecture**: Domain-focused organization (see `app/CLAUDE.md`)

## Testing

**Current Status**: 144 tests passing (100% success rate)
**Patterns**: Unit + integration tests, Playwright UI tests (see `tests/CLAUDE.md`)
**Requirements**: HTMX-aware testing, test-auth system for UI tests

## Environment Configuration

**Required**: SECRET_KEY, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, MONGODB_URI
**Optional**: REDIS_* for caching

See `CLAUDE.md` for complete environment variable reference.

## Common Development Tasks

**Add API Endpoint**: See `app/CLAUDE.md` for router patterns and testing
**Add UI Component**: See `templates/CLAUDE.md` for Flowbite + Alpine.js patterns
**Add Tests**: See `tests/CLAUDE.md` for comprehensive testing strategies
**Database Operations**: See `app/CLAUDE.md` for repository patterns

## Debugging & Monitoring

**Logging**: Loguru with structured logging (see `app/CLAUDE.md`)
**Health Checks**: `/api/health/*` endpoints available
**Debugging Tips**: See `CLAUDE.md` for common issues and solutions

## Best Practices for Development

**Domain Context**: Medical imaging finding models - maintain professional standards
**Code Quality**: Type hints, async patterns, comprehensive testing (see domain-specific CLAUDE.md files)
**UI Development**: Flowbite components only, Alpine.js for interactivity (see `templates/CLAUDE.md`)
**Performance**: Async throughout, MongoDB optimization, Redis caching (see `app/CLAUDE.md`)
**Deployment**: Docker + Railway platform (see `CLAUDE.md`)

## Documentation Reference

**CRITICAL**: Always check the domain-specific CLAUDE.md files for detailed development guidance:

- **CLAUDE.md** - Main project guide with architecture and core principles
- **app/CLAUDE.md** - Backend development patterns, FastAPI, async patterns, repositories
- **templates/CLAUDE.md** - Frontend/UI development, Flowbite components, Alpine.js (MANDATORY rules)
- **tests/CLAUDE.md** - Testing patterns, fixtures, Playwright browser testing
- **docs/DOCUMENTATION_INDEX.md** - Complete documentation index

### Key Documentation by Task Type

**UI/Frontend Work:**
- MUST read `templates/CLAUDE.md` first - Contains mandatory Flowbite/Alpine.js rules
- Check `docs/UI_COMPONENT_MACROS.md` for existing components
- Never create custom CSS/JS - Use Flowbite components only

**Backend Development:**
- Read `app/CLAUDE.md` for FastAPI patterns and repository layer
- Check `docs/database.md` for MongoDB schemas
- Follow async/await patterns throughout

**Testing:**
- Read `tests/CLAUDE.md` for testing strategies
- Use Playwright with test-auth system for UI tests
- Follow HTMX testing patterns for creation workflow

**Recent Changes:**
- Check `docs/RECENT_UPDATES_SUMMARY.md` for latest features and patterns
- Review `docs/TEAM_UPDATE_SEPTEMBER_2025.md` for current project status

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

---

**Remember**: This is a professional medical domain application. Always check the relevant CLAUDE.md files before coding, follow established patterns, and maintain comprehensive test coverage.
