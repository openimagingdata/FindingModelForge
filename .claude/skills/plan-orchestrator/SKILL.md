---
name: plan-orchestrator
description: Orchestrate multi-phase plan implementation via implement-evaluate cycles with specialized subagents. Use when implementing plans, executing roadmaps, or coordinating phased development tasks.
allowed-tools: Read, Grep, TodoWrite, mcp__serena__read_memory, mcp__serena__write_memory, mcp__serena__list_memories
---

# Plan Orchestrator

Coordinate specialized subagents to implement multi-phase technical plans through implement-evaluate cycles.

## Setup

Read Serena memories: `project_overview`, `current_development_status`, `code_style_conventions`.

Read plan file (typically from `tasks/*.md`), identify phases and dependencies, create TodoWrite checklist.

## Workflow

For each phase:

1. **Delegate to implementer**
   ```
   Use [implementer-name] to [task].

   Plan: [file:lines]
   Files: [paths to read]
   Deliverables: [specifics]
   Criteria: [from plan]
   ```

2. **Delegate to reviewer**
   ```
   Use [reviewer-name] to evaluate.

   Criteria: [from plan]
   Report: APPROVED | NEEDS_REVISION | BLOCKED
   ```

3. **Handle result**
   - **APPROVED**: Request user run tests → commit → mark complete
   - **NEEDS_REVISION**: Summarize issues → re-delegate fixes → re-evaluate (max 3 cycles)
   - **BLOCKED**: Check Serena → provide guidance or escalate to user

4. **Update progress**
   - Mark phase in TodoWrite
   - Update Serena memories with key architectural decisions only (not one-off fixes)

## Implementer/Reviewer Mapping

### Backend Development
- **Implementer**: `backend-implementer` - FastAPI endpoints, services, repositories, database operations
- **Reviewer**: `backend-reviewer` - Validates FastAPI patterns, type safety, async best practices
- **Test Updater**: `test-unit-updater` - Fixes broken imports/mocks after refactoring
- **Test Reviewer**: `test-unit-reviewer` - Validates unit tests pass with 75%+ coverage

### Frontend/UI Development
- **Implementer**: `frontend-implementer` - Flowbite + Alpine.js + HTMX UI components
- **Reviewer**: `frontend-reviewer` - STRICT Flowbite/Alpine.js/HTMX adherence validation
- **Test Updater**: `test-ui-updater` - Updates HTMX and Playwright tests after URL changes
- **Test Reviewer**: `test-ui-reviewer` - Validates end-to-end workflows and browser tests

### Refactoring
- **Implementer**: `refactor-implementer` - Extracting services, reorganizing routers per `tasks/router_cleanup.md`
- **Reviewer**: `refactor-reviewer` - Quality verification before committing

## Phase Sequencing

**Typical order:**
1. Backend implementation → backend review
2. Update unit tests → test unit review
3. Frontend implementation → frontend review
4. Update UI tests → test UI review
5. Full integration validation

**After refactoring, ALWAYS:**
1. Use `test-unit-updater` to fix broken tests IMMEDIATELY
2. Use `test-ui-updater` if routes/URLs changed

## Parallel Execution

When phases have no dependencies, delegate multiple implementers in one message:
```
I'm delegating these independent tasks in parallel:
[Multiple Task tool calls in single message]
```

## Delegation Guidelines

**Include:**
- Plan reference with line numbers (e.g., `tasks/feature-plan.md:45-67`)
- File paths for agents to read (not full contents)
- Specific acceptance criteria from plan
- Serena memory references (if relevant)
- Context about what NOT to do (e.g., "don't create custom CSS")

**Avoid:**
- Copying entire plan sections into prompt
- Prescribing exact implementation approach
- Vague requirements like "make it better"
- Overloading with unnecessary context

## Escalation

Escalate after 3 failed cycles or when reviewer reports BLOCKED on design decisions.

Format:
```
⚠️ [Phase] - [Issue]
Blocker: [specific problem]
Options: [possible approaches, if known]
Recommendation: [your assessment]
```

## Orchestration Constraints

These project constraints affect orchestration decisions:

- **100% test success required**: Always include test reviewers in phases, never skip test validation
- **UI must use Flowbite**: Frontend reviewer will reject custom CSS/JS, set clear expectations for implementer
- **Async patterns required**: Backend reviewer checks for async/await, ensure implementer knows this requirement
- **Test updates after refactoring**: Mandatory use of test-unit-updater and test-ui-updater agents

## Example Session

```
1. Read tasks/comment-system.md → 4 phases identified
2. TodoWrite created: Backend API, Unit tests, Frontend UI, UI tests
3. Phase 1: Use backend-implementer to create comment endpoints...
   Plan: tasks/comment-system.md:15-42
   Files: app/routers/drafts/, app/services/
   Deliverables: POST /drafts/{id}/comments, GET comments
   Criteria: Async, type-safe, rate limiting
4. Use backend-reviewer to evaluate against FastAPI patterns...
5. NEEDS_REVISION: Missing async on L45, type hint error L67
6. Re-delegate fixes to backend-implementer...
   Issues: Add async to get_comments(), fix Comment return type
7. Use backend-reviewer again...
8. APPROVED → Phase 2
9. Use test-unit-updater to add comment service tests...
10. Use test-unit-reviewer to validate coverage...
11. APPROVED → Phase 3
12. Use frontend-implementer to create comment UI components...
    Context: MUST use Flowbite form components, Alpine.js for state
13. Use frontend-reviewer to check Flowbite compliance...
14. APPROVED → Phase 4
15. Use test-ui-updater to add Playwright tests...
16. Use test-ui-reviewer to validate workflows...
17. APPROVED → Request user: run `task test` and commit
```
