# UI Tests

This directory contains all browser-based UI tests using Playwright. The tests are organized by functionality for better
maintainability and clearer test intentions.

## Structure

```
tests/ui/
├── README.md                    # This file
├── __init__.py                  # Package initialization
├── conftest.py                  # Shared fixtures for all UI tests
├── utils.py                     # Shared helper functions
├── test_profile.py              # Profile/My Forge page tests
├── test_creation_workflow.py    # Creation workflow end-to-end tests
└── test_draft_management.py     # Draft editing and management tests
```

## Test Categories

### Profile Page Tests (`test_profile.py`)

- **TestDraftCards**: Draft and submitted card display and actions
- **TestDeleteModal**: Delete modal functionality
- **TestEmptyState**: Empty state handling when no drafts exist
- **TestProfileNavigation**: Navigation to/from profile page

### Creation Workflow Tests (`test_creation_workflow.py`)

- **TestBasicCreationFlow**: Happy path creation workflow (steps 1-5)
- **TestSynonymManagement**: Synonym persistence across creation steps
- **TestCreateToEditWorkflow**: Create → generate → edit → regenerate cycles
- **TestMultipleEditCycles**: Multiple rounds of editing and regenerating
- **TestResumeFlow**: Resume creation with existing drafts

### Draft Management Tests (`test_draft_management.py`)

- **TestUnifiedDraftPage**: Edit/preview mode switching
- **TestFormValidation**: Alpine.js validation logic
- **TestModelReuse**: Model reuse vs regeneration detection
- **TestBackNavigation**: Back navigation with form persistence
- **TestDraftAutosave**: Draft autosave behavior

## Running Tests

### All UI Tests

```bash
task test-ui              # Headless mode
task test-ui-headed       # With visible browser
```

### Specific Test Categories

```bash
task test-ui-profile      # Profile page tests only
task test-ui-creation     # Creation workflow tests only
task test-ui-drafts       # Draft management tests only
```

### Individual Test Files

```bash
uv run pytest tests/ui/test_profile.py -v
uv run pytest tests/ui/test_creation_workflow.py -v
uv run pytest tests/ui/test_draft_management.py -v
```

### Debugging

```bash
# Run with visible browser for debugging
PLAYWRIGHT_HEADLESS=false uv run pytest tests/ui/test_profile.py::TestDraftCards::test_draft_and_submitted_cards_display -v -s
```

## Test Requirements

1. **Development Server**: Tests require the development server running on `localhost:8000`

   ```bash
   task dev  # In separate terminal
   ```

2. **Database**: Tests use MongoDB for test data seeding and cleanup

3. **Authentication**: Tests use the test-auth system (user ID 999999)

## Shared Utilities

### Fixtures (`conftest.py`)

- `authenticated_page`: Page with test-auth login completed
- `page_with_console_tracking`: Page with console error/warning collection
- `test_user_id`: Test user ID constant
- `cleanup_test_user_data`: Automatic test data cleanup

### Helper Functions (`utils.py`)

- `authenticate_user()`: Handle test-auth login
- `seed_draft()` / `seed_drafts()`: Create test drafts in database
- `generate_valid_generated_json()`: Create valid FindingModel JSON
- `verify_model_display()`: Verify model display elements
- `verify_no_console_errors()`: Check for frontend errors
- `wait_for_htmx_to_settle()`: Wait for HTMX operations to complete

## Test Data Management

- Tests automatically clean up data before and after execution
- Each test uses unique finding names to avoid conflicts
- Database state is verified to ensure proper test isolation
- Test user ID is hardcoded to 999999 for consistency

## Backward Compatibility

Legacy Taskfile commands are maintained:

- `task test-playwright` → `task test-ui`
- `task test-playwright-headed` → `task test-ui-headed`

## Migration from Old Tests

Previous Playwright tests have been reorganized:

- `test_profile_playwright.py` → `tests/ui/test_profile.py`
- `test_integration_htmx_playwright.py` → `tests/ui/test_creation_workflow.py`
- Form validation tests → `tests/ui/test_draft_management.py`

Old files are preserved in `tests/old_playwright_tests/` for reference.

## Test Coverage

The new structure provides comprehensive coverage of:

- ✅ Profile page draft/submitted card functionality
- ✅ Complete creation workflow (steps 1-5)
- ✅ Synonym management across workflow steps
- ✅ Create-to-edit-to-regenerate cycles
- ✅ Multiple edit/regenerate iterations
- ✅ Draft edit/preview mode switching
- ✅ Alpine.js form validation
- ✅ Model reuse vs regeneration logic
- ✅ HTMX content swapping
- ✅ Back navigation with form persistence
- ✅ Draft autosave functionality
- ✅ Resume workflow with existing drafts

This represents a significant improvement over the previous test coverage and provides a solid foundation for future UI
testing needs.
