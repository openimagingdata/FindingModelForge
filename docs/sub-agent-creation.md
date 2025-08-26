## Sub-Agent Requirements

### Header Structure (YAML frontmatter)

The sub-agent MUST start with this YAML header:

```yaml
---
name: [kebab-case-name] # Short, descriptive identifier (e.g., api-developer, test-writer)
description: [When to invoke this agent] # Be specific about triggers and use cases. Include phrases like "Use PROACTIVELY for..." or "MUST BE USED when..."
tools: [comma-separated list] # Only include tools this agent actually needs, not all available tools
model: [opus/sonnet/haiku] # Optional, defaults to system model. Use opus for complex tasks, sonnet for standard, haiku for simple
---
```

### System Prompt Guidelines

Write a focused system prompt that:

1. **Defines the agent's identity and expertise** (1-2 sentences)
   - Example: "You are a Senior FastAPI Backend Developer specializing in async Python and RESTful API design."

2. **Lists core responsibilities** (3-5 bullet points)
   - Be specific about what this agent handles
   - Avoid overlap with other agents' responsibilities

3. **Includes domain-specific knowledge** from our project:
   - Key patterns from our CLAUDE.md files that are relevant to this agent's domain
   - Project-specific conventions (but keep it concise - 1-2 paragraphs max)
   - Critical rules or constraints this agent must follow

4. **Provides concrete examples** (2-3 code snippets or patterns)
   - Show the "right way" to do things in our codebase
   - Include anti-patterns to avoid

5. **Specifies deliverables and quality standards**
   - What should the output look like?
   - What tests or validations should be included?

### What Makes a Good Sub-Agent

A good sub-agent is:

- **Single-purpose**: Excels at one specific domain (not a generalist)
- **Self-contained**: Has all context needed to operate independently
- **Actionable**: Knows exactly what to do without asking for clarification
- **Project-aware**: Understands our specific patterns without being overly coupled
- **Tool-efficient**: Only requests tools it actually uses (to save context tokens)

### Example Structure

Here's an example for a test-writing agent:

```markdown
---
name: test-writer
description:
  Use PROACTIVELY after implementing new functions or modifying existing code. Creates comprehensive unit tests with
  mocking and fixtures.
tools: Read, Write, Grep, PythonExecute
model: sonnet
---

You are a Test Engineer specializing in pytest and FastAPI testing for medical imaging applications.

## Core Responsibilities

- Write comprehensive unit tests achieving 80%+ coverage
- Create appropriate fixtures and mocks
- Test happy paths, edge cases, and error conditions
- Ensure tests are independent and idempotent

## Testing Patterns

Follow these established patterns from our codebase:

- Always use async test functions
- Mock external dependencies

## Anti-patterns to Avoid

- Never use real database connections in unit tests
- Don't test implementation details, test behavior
- Avoid time.sleep() - use proper async waiting

When writing tests, always:

1. Start with the happy path test
2. Add edge cases and error conditions
3. Verify all assertions are meaningful
4. Name tests descriptively: test*<function>*<condition>\_<expected_result>
```

## Creating Sub-agents

Consider relevant aspects from our project:

- Relevant information from `CLAUDE.md`, `tests/CLAUDE.md`, `docs/*.md`, `tests/ui/README.md`
- Filter the information to just what's needed for the sub-agent's area of focus
- Carefully design which tools the sub-agent will need
- Include references to external web pages we have found useful that are part of that sub-agent's domain
- The sub-agent definition is like a system-prompt--it should NOT include task-specific information.

The sub-agent should be able to work independently when invoked, without needing to ask for additional context about our
project structure or conventions.

## Key Points for Effective Sub-Agents

Based on best practices and your project patterns:

### 1. **Include Just Enough Context**

- ✅ Include: Core patterns, critical rules, specific conventions
- ❌ Don't include: Entire CLAUDE.md contents, general programming knowledge, obvious best practices

### 2. **Make Descriptions Actionable**

```yaml
# Good description - tells Claude exactly when to use it
description: Use PROACTIVELY after any database schema change to verify migrations and update repository methods. MUST BE USED before committing schema modifications.

# Bad description - too vague
description: Database helper for various tasks
```

### 3. **Tool Selection Matters**

With MCP token constraints, be surgical about tool selection:

```yaml
# Good - only what's needed
tools: Read, Write, Grep, mcp__mongodb__find, mcp__mongodb__update-many

# Bad - kitchen sink approach
tools: # (inherits all tools)
```

### 4. **Provide Executable Examples**

Instead of describing patterns, show them:

- Less effective: "Use our repository pattern for database access"
- More effective: "Access the database through repositories. Never access collections directly in routers."

### 5. **State Anti-Patterns Explicitly**

Tell the agent what NOT to do:

```markdown
## Never Do This

- ❌ Direct MongoDB queries in routers
- ❌ Synchronous functions for I/O operations
- ❌ Custom CSS classes in templates
- ❌ Hardcoded credentials or secrets
```

This approach creates focused, efficient sub-agents that understand our project's patterns without consuming excessive
context tokens. Each agent becomes a specialist that can be invoked automatically by you when appropriate, or explicitly
when I needs specific expertise.
