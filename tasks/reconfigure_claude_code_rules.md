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

## Priority

Medium - This is infrastructure improvement, not blocking current work.
