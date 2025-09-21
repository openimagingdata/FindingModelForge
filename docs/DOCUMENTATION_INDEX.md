# FindingModelForge Documentation Index

This document serves as a comprehensive index to all documentation in the FindingModelForge repository. Use this as a reference guide for finding relevant documentation during development.

## Core Documentation Architecture

The project uses a layered documentation approach:

### 1. Main Project Guide
- **[CLAUDE.md](../CLAUDE.md)** - Primary development guide with project overview, architecture, and key principles

### 2. Domain-Specific Guides
- **[app/CLAUDE.md](../app/CLAUDE.md)** - Backend development patterns, FastAPI, async patterns, repositories
- **[templates/CLAUDE.md](../templates/CLAUDE.md)** - Frontend/UI development, Flowbite components, Alpine.js patterns
- **[tests/CLAUDE.md](../tests/CLAUDE.md)** - Testing patterns, fixtures, Playwright browser testing

### 3. Feature Documentation
- **[docs/*](./README.md)** - Detailed feature guides and implementation details

### 4. GitHub Copilot Integration
- **[.github/copilot-instructions.md](../.github/copilot-instructions.md)** - Concise project overview with documentation references for GitHub Copilot

## Quick Reference by Development Area

### 🎯 Starting Development
1. **[CLAUDE.md](../CLAUDE.md)** - Read this first for project overview
2. **[RECENT_UPDATES_SUMMARY.md](./RECENT_UPDATES_SUMMARY.md)** - Latest changes and features
3. **[TEAM_UPDATE_SEPTEMBER_2025.md](./TEAM_UPDATE_SEPTEMBER_2025.md)** - Current project status

### 🔧 Backend Development
- **[app/CLAUDE.md](../app/CLAUDE.md)** - FastAPI patterns, async development, repository layer
- **[database.md](./database.md)** - MongoDB schemas, collections, indexing
- **[REDIS_CACHE_IMPLEMENTATION.md](./REDIS_CACHE_IMPLEMENTATION.md)** - Cache layer patterns

### 🎨 Frontend/UI Development
- **[templates/CLAUDE.md](../templates/CLAUDE.md)** - UI development rules and patterns
- **[UI_COMPONENT_MACROS.md](./UI_COMPONENT_MACROS.md)** - Reusable UI components and macros
- **[htmx-comment-patterns.md](./htmx-comment-patterns.md)** - HTMX implementation patterns

### 🧪 Testing
- **[tests/CLAUDE.md](../tests/CLAUDE.md)** - Testing strategies, fixtures, Playwright patterns
- **[playwright-testing-patterns.md](./playwright-testing-patterns.md)** - Browser testing guidelines

### 📋 Features & Workflows
- **[finding-model-creation-workflow.md](./finding-model-creation-workflow.md)** - Multi-step creation process
- **[PROFILE_PAGE_FEATURES.md](./PROFILE_PAGE_FEATURES.md)** - User profile functionality
- **[DRAFT_WORKFLOW.md](./DRAFT_WORKFLOW.md)** - Draft management system
- **[feature_finding_model_draft_saving.md](./feature_finding_model_draft_saving.md)** - Draft saving mechanics

### 📈 Architecture & Planning
- **[refactoring_plan_finding_model_creation.md](./refactoring_plan_finding_model_creation.md)** - System architecture evolution
- **[sub-agent-creation.md](./sub-agent-creation.md)** - AI agent development patterns

### 🔧 Development Utilities
- **[humanize-usage.md](./humanize-usage.md)** - Time formatting utilities

## Documentation Usage Patterns

### For New Features
1. Check **[CLAUDE.md](../CLAUDE.md)** for architectural principles
2. Review domain-specific guides (**app/**, **templates/**, **tests/**)
3. Look for similar feature documentation in **docs/**
4. Check **[RECENT_UPDATES_SUMMARY.md](./RECENT_UPDATES_SUMMARY.md)** for recent patterns

### For Bug Fixes
1. Check relevant domain guide for debugging tips
2. Review **[tests/CLAUDE.md](../tests/CLAUDE.md)** for testing patterns
3. Check feature-specific documentation for implementation details

### For Code Reviews
1. Verify adherence to **[CLAUDE.md](../CLAUDE.md)** principles
2. Check domain-specific best practices
3. Ensure testing follows **[tests/CLAUDE.md](../tests/CLAUDE.md)** patterns

## Critical Rules from Documentation

### UI Development (MANDATORY)
- ✅ ALWAYS use Flowbite components from docs
- ✅ ALWAYS use Alpine.js for interactivity
- ❌ NEVER create custom CSS classes
- ❌ NEVER write custom JavaScript
- See **[templates/CLAUDE.md](../templates/CLAUDE.md)** for details

### Backend Development
- Always use async/await patterns
- Type hints required throughout
- Repository pattern for data access
- See **[app/CLAUDE.md](../app/CLAUDE.md)** for patterns

### Testing Requirements
- 100% test success rate maintained
- Playwright tests require test-auth system
- HTMX testing requires special patterns
- See **[tests/CLAUDE.md](../tests/CLAUDE.md)** for details

## File Organization Quick Reference

```
FindingModelForge/
├── CLAUDE.md                     # Main development guide
├── app/
│   └── CLAUDE.md                 # Backend development guide
├── templates/
│   └── CLAUDE.md                 # Frontend development guide
├── tests/
│   └── CLAUDE.md                 # Testing guide
└── docs/
    ├── DOCUMENTATION_INDEX.md    # This file
    ├── RECENT_UPDATES_SUMMARY.md # Latest changes
    ├── UI_COMPONENT_MACROS.md    # UI component reference
    ├── finding-model-creation-workflow.md
    ├── PROFILE_PAGE_FEATURES.md
    ├── REDIS_CACHE_IMPLEMENTATION.md
    ├── database.md
    ├── htmx-comment-patterns.md
    ├── playwright-testing-patterns.md
    ├── humanize-usage.md
    ├── DRAFT_WORKFLOW.md
    ├── feature_finding_model_draft_saving.md
    ├── refactoring_plan_finding_model_creation.md
    ├── sub-agent-creation.md
    └── TEAM_UPDATE_SEPTEMBER_2025.md
```

## AI Context Integration

For AI assistants (like Claude), the most effective approach is to:

1. **Always attach [CLAUDE.md](../CLAUDE.md)** - Provides core project context
2. **Attach domain-specific guides** as needed:
   - Backend work: **[app/CLAUDE.md](../app/CLAUDE.md)**
   - Frontend work: **[templates/CLAUDE.md](../templates/CLAUDE.md)**
   - Testing work: **[tests/CLAUDE.md](../tests/CLAUDE.md)**
3. **Include feature-specific docs** for complex features
4. **Reference this index** to find additional relevant documentation

## Maintenance

This index should be updated when:
- New documentation files are added
- Major architectural changes occur
- Documentation is reorganized
- New development patterns emerge

---

*Last Updated: September 19, 2025*
