# Essential Development Commands

## Setup and Installation

```bash
task setup              # Full setup: install deps + create .env + build assets
task install            # Install Python and Node dependencies only
```

## Development Servers

```bash
task dev                # Start development server (recommended)
task dev-vite           # With Vite dev server for JS hot reload
task dev-watch          # With CSS watch mode
```

## Code Quality (Run After Changes)

```bash
task lint               # Format + fix linting + type check (comprehensive)
task format             # Format code and markdown
task check              # Read-only quality checks (for CI)
```

## Testing

```bash
task test-unit          # Fast unit tests (for development)
task test               # Full test suite with coverage
task test-integration   # Integration tests only
task test-full          # Tests + quality checks
task test-playwright    # Run Playwright browser tests
```

> When we think we're done, `task pre-commit` runs all lintings and testings to make sure we're commit-ready.

## Frontend Development

```bash
npm run build           # Build CSS and JS
npm run dev             # Vite dev server
npm run watch:css       # CSS watch mode
task build-frontend     # Build all frontend assets
```

## Docker

```bash
task build              # Build Docker image
task run-container      # Run in container
docker-compose up -d    # Start MongoDB and Redis locally
```

## Essential Python Commands

```bash
uv sync --all-extras --dev  # Install Python dependencies
uv run uvicorn app.main:app --reload  # Run server directly
uv run pytest                         # Run tests directly
uv run pytest -m "not integration"    # Unit tests only
uv run pytest -m integration          # Integration tests only
uv run mypy .                         # Type checking
uv run ruff format .                  # Format code
uv run ruff check --fix .             # Fix linting issues
```

## Draft Management Commands

```bash
# Test draft functionality
uv run pytest tests/test_drafts.py -v

# Test step 4 autosave
uv run pytest tests/test_step4_edge_cases.py -v

# Test resume workflow
uv run pytest tests/test_step4_resume.py -v
```

## When Task is Complete

1. `task lint` - Format, lint, and type check
2. `task test-unit` - Run fast tests
3. Git commit with conventional commit messages

## Common Workflows

### After making UI changes:

1. `npm run build` - Rebuild CSS/JS
2. Check in browser with dev server running

### After backend changes:

1. `task lint` - Clean up code
2. `task test-unit` - Verify tests pass
3. Check logs with `tail -f logs/app.log`

### Before committing:

1. `task lint` - Ensure code quality
2. `task test-unit` - Verify functionality
3. `git status` - Review changes
4. Use conventional commit format
