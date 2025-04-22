# FindingModelForge

Tool set for creating finding models for defining the semantic labels for imaging findings.

In `findingmodelforge`, there is a [NiceGUI](https://nicegui.io)/FastAPI application exposing [`findingmodel`](https://github.com/openimagingdata/findingmodel) functionality. The app uses GitHub OAuth for authentication.

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
task build_image
task run_container
```

Browse to [localhost:8000](http://localhost:8000) to see the API interface exposed by FastAPI.

## Development Processes

### Dev Tooling/CI

- Linting and formatting using [ruff](https://astral.sh/ruff) configured via a `pyproject.toml` file. Workspace VS Code settings to include automatic lint/format on save.
- Type checking using [mypy](https://www.mypy-lang.org/)
- [ ] Unit testing and coverage with [pytest](https://docs.pytest.org/en/stable/)
- [x] Use `task` for integration tasks (lint, format, type-check, test, build)
- [ ] Use GitHub Actions for automatic checking on commit for formatting, linting, and passing tests
- [ ] Set up [Dependabot](https://docs.github.com/en/code-security/getting-started/dependabot-quickstart-guide) to keep dependencies up to date

### Deployment (eventually CD)

- Build any packages and create releases on GitHub; automate with GitHub actions as appropriate
- Build app container image with `task` and push to [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- Temporarily, manual deployment to [Railway](https://railway.com), with separate staging/
production environments.
- Later, move to continuous deployment with GitHub Actions

### Code Concerns

- Target Python version 3.12
- Use type hinting as extensively as possible
- Use environment variables for configuration; propose to use [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) to load configuration from the environment

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
  - [`nicegui`](https://github.com/zauberzeug/nicegui/) - Python and browser based front-end
- **Logging**
  - [`loguru`](https://github.com/Delgan/loguru) - Application logging and debugging infrastructure
- **Utility**
  - [`case-switcher`](https://github.com/fields8/case-switcher) - String case format standardization and conversion
  - `platformtools`
