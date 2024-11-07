# FindingModelForge

Tool set for creating finding models for defining the semantic labels for imaging findings.

## Packages

`packages` directory contains the sub-projects which can inter-depend.

- `packages/findingmodelforge`: The core library code for all of the Finding Model Forge functionality,
  including underlying model definitions.
- `packages/fmf-api`: A FastAPI application that exposes the `findingmodelforge` library functions via
  api. Its features include:
  - [ ] FastUI front-end exposing functionality
  - [ ] GitHub OAuth for interactive user-based authentication
  - [ ] Temporary: enable API key authenitcation for backend application connections. Hope to
        transition this to GitHub-based OAuth authentication also
- `packages/fmf-cli`: Command-line interface for using `findingmodelforge` functionality. Some overlap
  with the UI (pushed into the library as much as possible), some usage of the API, a lot of overlap
  functionality.

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

- [ ] Need to update `Taskfile.yml` to allow for PowerShell versus shell commands.

- Docker

### Build/Run Docker Image

```sh
task build_api
task run_api
```

Browse to [localhost:8000](http://localhost:8000/docs) to see the API interface exposed by FastAPI.

## Development Processes

### Dev Tooling/CI

- Linting and formatting using [ruff](https://astral.sh/ruff) configured via a `ruff.toml` file in the main directory (_not_ in the individual package directories). Workspace VS Code settings to include automatic lint/format on save.
- Type checking using [mypy](https://www.mypy-lang.org/)
- [ ] Version management with [commitizen](https://commitizen-tools.github.io/commitizen/)
- Unit testing and coverage with [pytest](https://docs.pytest.org/en/stable/)
- [ ] Use `task` for integration tasks (lint, format, type-check, test, build)
- [ ] Use GitHub Actions for automatic checking on commit for formatting, linting, and passing tests
- [ ] Set up [Dependabot](https://docs.github.com/en/code-security/getting-started/dependabot-quickstart-guide) to keep dependencies up to date

### Deployment (eventually CD)

- Build any packages and create releases on GitHub; automate with GitHub actions as appropriate
- Build app container image with `task` and push to [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- Temporarily, manual deployment to [Azure App Service](https://learn.microsoft.com/en-us/azure/app-service/quickstart-custom-container); ideally, use  [slots](https://learn.microsoft.com/en-us/azure/app-service/deploy-staging-slots) for staging and production
- Later, move to continuous deployment with GitHub Actions

### Code Concerns

- Target Python version 3.12
- Use type hinting as extensively as possible
- Use environment variables for configuration; propose to use [python-decouple](https://github.com/HBNetwork/python-decouple) to load configuration from the environment


### Preferred Libraries

- [pydantic] for data model definitions:
  - Drives APIs
  - Drives database models via ODM
  - Drives web UI
  - Exports JSON schemas
  - Used for structured data extraction
- LLMs:
  - `openai`
  - `sentence-transformers`
  - `tiktoken`
  - `instructor`
  - `tokenizers`
  - `semantic-text-splitter`
- Database
  - `beanie`
  - `motor`
- Web
  - `fastapi`
  - `uvicorn`
- Logging
  - `loguru`

- Utility
  - `case-switcher`
