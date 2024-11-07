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

Browse to https://localhost:8000/docs to see the API interface exposed by FastAPI.

