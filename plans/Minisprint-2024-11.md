# MiniSprint November 2024

## New Function: Create Finding Model from Finding Name

### Library

- [x] Copy over and start updating `FindingModel` definition
- [x] Get code that uses LLM to generate description from finding model name
- [ ] Create a function `finding_name_to_finding_model()` that:
  - Uses LLM to generate a description from the finding name if one is not provided
  - Generates a `FindingModel` object using the given name and generated (or specified) description
    - Adds `presence` attribute with standard structure/options
    - Adds `change_from_prior` attribute with standard structure/options
  - [ ] Save to the database
  - Outputs the finding model as JSON

### CLI

- [ ] Offer a CLI command exposing the `finding_name_to_finding_model()` (requires direct OpenAI API key)

### API

- [ ] Add API key authentication for protected function
- [ ] Expose `finding_name_to_finding_model()` as an API function

## Future Items

- [ ] Allow for adding a `location` attribute to a new finding model (optionally)
- [ ] Allow for adding a `size` attribute to a new finding model (optionally)
- [ ] Deploy new API to Azure App Service
- [ ] Transition CLI tool to use the API (and API key) rather than internal code
- [ ] Web interface for creating/listing/viewing finding models with GitHub OAuth authentication
