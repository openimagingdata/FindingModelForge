# Reconfigure Claude Code Behavioral Rules

## Problem

Currently, behavioral rules and guidelines for Claude Code are scattered across:
- Multiple `CLAUDE.md` files (root, `app/`, `templates/`, `tests/`, `tests/ui/`)
- Serena memories (`.serena/memories/*.md`)

This is suboptimal because:
- Rules are hard to discover and maintain
- Serena memories are meant for project context, not behavioral rules
- CLAUDE.md files mix documentation with behavioral directives

## Goal

Migrate to `.claude/rules/*.md` pattern which:
- Is automatically loaded by Claude Code every session
- Is checked into git (team-shared)
- Provides topic-focused, discoverable rule files
- Separates behavioral rules from project documentation

## Tasks

1. **Audit existing CLAUDE.md files**
   - `CLAUDE.md` (root)
   - `app/CLAUDE.md`
   - `templates/CLAUDE.md`
   - `tests/CLAUDE.md`
   - `tests/ui/CLAUDE.md`
   - Identify what is documentation vs behavioral rules

2. **Audit Serena memories**
   - List all memories in `.serena/memories/`
   - Identify what should be project context vs behavioral rules

3. **Design new rule structure**
   - Propose `.claude/rules/` file organization
   - Consider path-specific rules using YAML frontmatter
   - Example categories: testing-workflow, orchestration, code-quality, frontend-patterns, backend-patterns

4. **Migrate behavioral rules**
   - Create new rule files in `.claude/rules/`
   - Remove duplicated content from CLAUDE.md files (keep documentation only)
   - Update or remove Serena memories that were storing behavioral rules

5. **Test and validate**
   - Verify rules are being loaded correctly
   - Confirm Claude Code follows the migrated rules

## Specific Rules to Capture (from recent learnings)

- Orchestration pattern: implementer → reviewer, no freelance debugging
- Always run tests and read error messages FIRST before investigating
- Match tools to problems (Playwright for browser/HTMX, not curl)
- Delegate to specialist agents instead of doing implementation work directly
- When implementer reports "done but failing", delegate to reviewer immediately
- **Tiered testing requirements**:
  - **WIP commits** (intermediate checkpoints): `task test-unit` + `task test-integration` adequate for backend-only work
  - **Milestone commits** (phase complete, feature done, PR-ready): **REQUIRE `task test-full`** - no exceptions. This runs unit + integration + UI tests (~2.5 min). A "quick test" of one file is not verification.
  - **Template changes**: Any modification to `templates/` requires UI tests even for WIP commits - template refactoring breaks form submissions, button behaviors, and HTMX interactions in ways unit tests cannot detect
- **PORT variable for testing**: Dev server and UI tests respect the `PORT` environment variable (default: 8000). Use `PORT=8001 task dev` and `PORT=8001 task test-ui` to test on alternate ports.

## Priority

Medium - This is infrastructure improvement, not blocking current work.
