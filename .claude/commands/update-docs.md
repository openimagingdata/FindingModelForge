# Update Documentation and Best Practices

Analyze the recent work completed in this project and update all relevant documentation. Use Serena's memory to
understand what has changed and what knowledge should be preserved. Follow these steps:

## 1. ANALYZE RECENT CHANGES

- Review git history for commits from the last ${ARGUMENTS:-7} days
- Use Serena to examine modified files and understand semantic changes
- Check Serena's memories in .serena/memories/ for context about recent decisions
- Identify new patterns, APIs, components, or architectural changes

## 2. SCAN EXISTING DOCUMENTATION

Review all documentation in these locations:

- Root directory: README.md, CLAUDE.md, CHANGELOG.md
- .claude/: All .md files including rules and command templates
- docs/: All documentation files
- .serena/memories/: Review stored project knowledge and decisions

## 3. UPDATE DOCUMENTATION SYSTEMATICALLY

### Update README.md

- New features or capabilities added
- Installation/setup changes
- Updated usage examples reflecting current implementation
- New dependencies or requirements

### Update CLAUDE.md (and sub-directory CLAUDE.md)

- New coding patterns discovered during implementation
- Updated best practices based on what worked well
- Anti-patterns to avoid based on issues encountered
- New project-specific conventions established

### Update CHANGELOG.md

- Use the standard CHANGELOG.md format as seen at https://keepachangelog.com/en/1.0.0/
- Add entry for recent changes with date
- Group by: Added, Changed, Fixed, Deprecated, Removed, Security
- Reference relevant commits

### Update API Documentation

- New endpoints, methods, or interfaces
- Changed parameters or return types
- Deprecated features with migration guides
- Updated examples using actual code from tests

## 4. UPDATE SERENA'S MEMORY (Integration Only)

**Integrate into existing memories** - never create new ones:

- `project_overview`: Expand architecture sections if patterns/structure changed
- `current_development_status`: Add timeline entry for completed work
- Existing component memories: Update if that component was modified

## 5. VALIDATE DOCUMENTATION

For each updated document:

- Ensure code examples are valid and run
- Verify all links work
- Check that instructions are reproducible
- Confirm consistency across all docs
- Test that newcomers could follow the guides

## 6. IMPORTANT RULES

- Use bash's `date` command to find the current date--you won't know it otherwise
- NEVER remove existing valid documentation without explicit approval
- ALWAYS preserve historical context and rationale
- USE Serena's semantic understanding to ensure accuracy
- MAINTAIN consistent tone and formatting across all docs
- INCLUDE practical examples from actual implementation
- TEST all code snippets and commands before documenting
- CITE relevant commits or PRs when documenting changes

## SERENA INTEGRATION NOTES

- Serena stores memories in .serena/memories/ - use this knowledge
- Leverage Serena's understanding of code relationships
- Use Serena's symbol-level comprehension for accurate API docs
- Let Serena help identify what's truly important to document

Remember: Good documentation is a living artifact that evolves with the code. Use both git history and Serena's semantic
memory to create documentation that captures not just WHAT changed, but WHY it changed and HOW to use it effectively.
