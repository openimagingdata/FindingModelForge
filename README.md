# FindingModelForge

Tool set for creating finding models for defining the semantic labels for imaging findings.

FindingModelForge is a FastAPI web application exposing
[`findingmodel`](https://github.com/openimagingdata/findingmodel) functionality. The app uses GitHub OAuth for
authentication, Jinja2 for templating, and provides a modern web interface with Tailwind CSS and Alpine.js.

## Run

### Prereqs

Requirements:

- [uv](https://docs.astral.sh/uv/): Install with:

  ```sh
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- [Task](https://taskfile.dev): Install via uv (recommended), brew, or winget:

  ```sh
  # Using uv (cross-platform, recommended)
  uv tool install go-task-bin

  # Or using Homebrew (macOS/Linux)
  brew install go-task

  # Or using winget (Windows)
  winget install Task.Task
  ```

- [Docker](https://docker.com)

### Build/Run Docker Image

#### Prerequisites

1. **Backing services** - MongoDB and Redis must be running locally (default ports 27017 and 6379).
   You can use the included docker-compose file or run them however you prefer:
   ```sh
   docker-compose up -d
   ```

2. **DuckDB data files** must exist in your data directory:
   - macOS: `~/Library/Application Support/findingmodel/`
   - Linux: `~/.local/share/findingmodel/`

   Required files: `finding_models.duckdb`, `anatomic_locations.duckdb`

3. **GitHub OAuth App** - Create one at [GitHub Developer Settings](https://github.com/settings/developers):
   - **Homepage URL**: `http://localhost:8000`
   - **Authorization callback URL**: `http://localhost:8000/auth/callback`

4. **Environment configuration**:
   ```sh
   cp .env.container.sample .env.container
   # Edit .env.container with your GitHub OAuth credentials and OpenAI API key
   ```

#### Running the Container

```sh
# Build the image
task build

# Run in detached mode (with health check)
task run-container

# Stop the container
task stop-container
```

Browse to [localhost:8000](http://localhost:8000) to access the web application.

#### Debugging Container Issues

If the container fails to start, run in attached mode to see the full output:

```sh
task run-container-attached
```

Press `Ctrl+C` to stop.

#### Custom Port

Override the default port (8000) with the `PORT` environment variable:

```sh
PORT=8080 task run-container
```

### Development Mode

For development with hot reload:

```sh
task dev
```

For development with CSS watching:

```sh
task dev-watch
```

Common development commands:

```sh
task setup          # Install deps + create .env + build assets
task test            # Run tests with coverage (144 tests passing, 100% success rate)
task test-unit       # Fast unit tests only (~0.4s for 71 tests)
task test-ui         # Playwright UI tests only (~2.5min for 85 tests, 2x faster than before)
task lint            # Lint and fix code issues
task format          # Format code
task check           # Quality checks (CI-friendly)
task pre-commit      # Run all pre-commit checks (lint, format, test)
task build-frontend  # Build CSS and JS assets
```

## Development Processes

### Dev Tooling/CI

- [x] Linting and formatting using [ruff](https://astral.sh/ruff) configured via a `pyproject.toml` file
- [x] Type checking using [mypy](https://www.mypy-lang.org/) with strict mode
- [x] Unit testing and coverage with [pytest](https://docs.pytest.org/en/stable/)
- [x] Use `task` for integration tasks (lint, format, type-check, test, build)
- [x] Pre-commit hooks for automated code quality checks
- [ ] GitHub Actions for automatic checking on commit for formatting, linting, and passing tests
- [ ] Set up [Dependabot](https://docs.github.com/en/code-security/getting-started/dependabot-quickstart-guide) to keep
      dependencies up to date

### Deployment (eventually CD)

- Build any packages and create releases on GitHub; automate with GitHub actions as appropriate
- Build app container image with `task` and push to
  [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- Temporarily, manual deployment to [Railway](https://railway.com), with separate staging/ production environments.
- Later, move to continuous deployment with GitHub Actions

### Code Standards

- Target Python version 3.12+
- Extensive type hinting throughout the codebase
- Environment variables for configuration using
  [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- Async/await patterns for I/O operations
- Comprehensive error handling and logging

### Testing Standards

- **100% test success rate** - 144 tests passing (71 unit + 73 integration)
- **High-performance test suite** - UI tests complete in 2.5 minutes (2x faster via optimization)
- **HTMX-aware testing patterns** - Purpose-built utilities for framework-specific testing
- **No Schrödinger's Tests** - Tests must fail when they can't verify their intended behavior
- **Realistic test data** - Production data templates instead of AI API calls
- **Priority-based organization** - Critical paths → State transitions → Edge cases → Access control

### Draft Management System

**Complete draft lifecycle** with autosave, resume, submit, and delete functionality:

- **Auto-save on Step 4**: Drafts automatically created/updated when editing attributes
- **Unified draft pages**: Single endpoint handles both edit and view modes via `?mode=` parameter
- **Session adoption**: Automatic recovery of draft state when sessions are lost
- **User isolation**: One editable draft per (user_id, name) combination with secure ownership checks
- **Action logging**: Comprehensive audit trail for all draft operations
- **Status management**: draft → submitted → [future: under-review | added | declined]
- **Smart resume**: Entering the same finding name after submit shows final display view
- **Redis integration**: Cache layer available throughout with graceful degradation

### Finding Models Display System

**Public browseable finding models library** with search, navigation, and responsive UI:

- **Server-side search and pagination**: Efficient filtering and page navigation with debounced search (500ms)
- **HTMX navigation**: Seamless transitions between list and detail pages with proper browser history
- **Dynamic page titles**: Context-aware titles that update for search results and model details
- **Smart breadcrumb system**: OOB (Out-of-Band) breadcrumb updates with history navigation support
- **Cache optimization**: Redis caching for finding models data with graceful fallback
- **Responsive design**: Flowbite components with mobile-first design and dark mode support
- **SEO-friendly URLs**: Clean URL structure with proper meta tags and search indexing

### UI Guidelines

- Flowbite components first; keep to their HTML structure and data-attributes.
- Alpine.js for local state and interactivity (`x-data`, `x-model`, `x-show`, computed methods). Avoid custom vanilla
  JS.
- Use Jinja2 macros in `templates/macros` where possible (see `flowbite_components.html`, `layout_components.html`,
  `json_accordion.html`).
- HTMX is used for server-driven fragments in multi-step forms.

### Preferred Libraries

- **Data**
  - [pydantic](https://docs.pydantic.dev/latest/) for data model definitions:
    - Drives APIs
    - Drives database models via ODM
    - Drives web UI
    - Exports JSON schemas
    - Used for structured data extraction
  - [`motor`](https://github.com/mongodb/motor) - Asynchronous MongoDB operations and queries

- **Web**
  - [`fastapi`](https://github.com/tiangolo/fastapi) - REST API development and endpoint handling
  - [`uvicorn`](https://github.com/encode/uvicorn) - ASGI server implementation for application hosting
  - [`jinja2`](https://jinja.palletsprojects.com/) - Server-side templating engine with template inheritance
  - [`redis`](https://redis.io/) - In-memory caching layer for performance optimization

- **Frontend**
  - [`tailwindcss`](https://tailwindcss.com/) - Utility-first CSS framework with dark mode support
  - [`alpinejs`](https://alpinejs.dev/) - Lightweight JavaScript framework for interactivity
  - [`flowbite`](https://flowbite.com/) - Pre-built UI components with data-attribute patterns
  - [`vite`](https://vitejs.dev/) - Modern frontend build system with hot reload
  - [`htmx`](https://htmx.org/) - Server-driven interactivity for multi-step flows

- **Logging**
  - [`loguru`](https://github.com/Delgan/loguru) - Application logging and debugging infrastructure

- **Authentication & Security**
  - [`pyjwt`](https://pyjwt.readthedocs.io/) - JWT token generation and validation
  - [`httpx`](https://www.python-httpx.org/) - HTTP client for OAuth integration
