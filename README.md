# FindingModelForge

Tool set for creating finding models for defining the semantic labels for imaging findings.

## Packages

`packages` directory contains the sub-projects which can inter-depend.

- `packages/findingmodelforge`: The core library code for all of the Finding Model Forge functionality,
  including underlying model definitions.
  - Includes `fmf_cli`, which exposes library functionality via a command-line interface
- `packages/fmf-api`: A FastAPI application that exposes the `findingmodelforge` library functions via
  api. Its features include:
  - [ ] [NiceGUI](https://nicegui.io/) front-end exposing functionality
  - [ ] [GitHub OAuth](https://thelinuxcode.com/how-to-set-up-a-github-oauth-application/) for interactive user-based authentication
  - [ ] Enable [GitHub OAuth authentication](https://github.com/chrisK824/fastapi-sso-example/blob/main/authentication.py) for backend application connections. (Does this get stored in a JWT token, session, or...) 

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
- [x] Use `task` for integration tasks (lint, format, type-check, test, build)
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
- Use environment variables for configuration; propose to use [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) to load configuration from the environment
- Where possible, pull prompt definitions out into non-code files ([Jinja2 templates](https://jinja.palletsprojects.com/en/stable/templates/)); see `findingmodelforge.prompt_templates`

### Preferred Libraries

- **Data Models**
  - [pydantic](https://docs.pydantic.dev/latest/) for data model definitions:
    - Drives APIs
    - Drives database models via ODM
    - Drives web UI
    - Exports JSON schemas
    - Used for structured data extraction
  - [Beanie](https://beanie-odm.dev) as our object document mapper, directly moving between Pydantic objects and documents in the database.
- **LLMs**:
  - [`openai`](https://github.com/openai/openai-python) - Core LLM
  - [`sentence-transformers`](https://github.com/UKPLab/sentence-transformers) - Generate embeddings for semantic similarity and search
  - [`tiktoken`](https://github.com/openai/tiktoken) - Token counting and management for LLM interactions
  - [`instructor`](https://github.com/jxnl/instructor) - Type-safe structured output parsing from LLM responses
  - [`tokenizers`](https://github.com/huggingface/tokenizers) - Text tokenization for model input processing
  - [`semantic-text-splitter`](https://github.com/jerpint/semantic_text_splitter) - Intelligent document chunking for LLM context windows
- **Database**
  - [`beanie`](https://github.com/roman-right/beanie) - MongoDB object-document mapper for data persistence
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
