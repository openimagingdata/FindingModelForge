# FindingModelForge

Tool set for creating finding models for defining the semantic labels for imaging findings.

FindingModelForge is a FastAPI web application exposing [`findingmodel`](https://github.com/openimagingdata/findingmodel) functionality. The app uses GitHub OAuth for authentication, Jinja2 for templating, and provides a modern web interface with Tailwind CSS and Alpine.js.

## Run

### Prereqs

Requirements:

- [uv](https://docs.astral.sh/uv/): Install with:

  ```sh
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- [Task](https://taskfile.dev): Install depends on system;

  MacOS:

  ```sh
  brew install gotask
  ```

  Windows:

  ```ps
  winget install Task.Task
  ```

- [Docker](https://docker.com)

### Build/Run Docker Image

```sh
task build
task run-container
```

Browse to [localhost:8000](http://localhost:8000) to access the web application.

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
task test            # Run tests with coverage
task lint            # Lint and fix code issues
task format          # Format code
task check           # Quality checks (CI-friendly)
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
- [ ] Set up [Dependabot](https://docs.github.com/en/code-security/getting-started/dependabot-quickstart-guide) to keep dependencies up to date

### Deployment (eventually CD)

- Build any packages and create releases on GitHub; automate with GitHub actions as appropriate
- Build app container image with `task` and push to [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- Temporarily, manual deployment to [Railway](https://railway.com), with separate staging/
production environments.
- Later, move to continuous deployment with GitHub Actions

### Code Standards

- Target Python version 3.12+
- Extensive type hinting throughout the codebase
- Environment variables for configuration using [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- Async/await patterns for I/O operations
- Comprehensive error handling and logging

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

- **Logging**
  - [`loguru`](https://github.com/Delgan/loguru) - Application logging and debugging infrastructure

- **Authentication & Security**
  - [`pyjwt`](https://pyjwt.readthedocs.io/) - JWT token generation and validation
  - [`httpx`](https://www.python-httpx.org/) - HTTP client for OAuth integration
