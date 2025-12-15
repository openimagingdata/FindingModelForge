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

1. **Development Server**: Tests require the development server running (default `localhost:8000`, configurable via `PORT` env var)

   ```bash
   task dev  # In separate terminal
   # Or with custom port: PORT=3000 task dev
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
- `generate_valid_generated_json()`: Create valid FindingModel JSON **(CRITICAL - see note below)**
- `verify_model_display()`: Verify model display elements
- `verify_no_console_errors()`: Check for frontend errors
- `wait_for_htmx_settled()`: Wait for HTMX operations to complete (replaces old `wait_for_htmx_to_settle()`)

**⚠️ IMPORTANT**: When creating test drafts that need to display finding models (especially for comment functionality),
you MUST use `generate_valid_generated_json()` to create valid FindingModelFull JSON. Simple JSON objects will NOT pass
backend validation. See [tests/CLAUDE.md](../CLAUDE.md#generating-valid-draft-data-for-ui-tests) for detailed
documentation on why this is critical and how to use it correctly.

## UI Testing Anti-Patterns to Avoid

### ❌ 1. Conditional Logic That Makes Tests Pass (Schrödinger's Tests)

Never use conditional logic that allows a test to pass without testing:

```python
# ❌ WRONG - Test can pass without testing anything
if await element.count() > 0:
    await expect(element).to_be_visible()
# Test passes whether element exists or not!

# ✅ CORRECT - Test fails if element missing
await expect(element).to_be_visible()
```

**Real example from this codebase (test_profile.py, now fixed):**

```python
# ❌ WRONG - Conditional allows silent pass
view_button_count = await draft_card.locator("a[title='View']").count()
if view_button_count > 0:
    await draft_card.locator("a[title='View']").first.click()

# ✅ CORRECT - Must verify element exists
view_button = draft_card.locator("a[title='View']")
await expect(view_button).to_be_visible(timeout=5000)
await view_button.first.click()
```

**Double-conditional anti-pattern (test_finding_models_navigation.py, now fixed):**

```python
# ❌ WRONG - Two conditionals = test can pass without testing
if page.url.endswith("/non-existent-model-slug"):
    error_message = page.locator("text=/not found/i").first
    if await error_message.is_visible():  # Second conditional!
        await expect(error_message).to_be_visible()

# ✅ CORRECT - Single conditional with proper assertion
if page.url.endswith("/non-existent-model-slug"):
    table = page.locator("table").first
    await expect(table).to_be_visible(timeout=5000)
else:
    assert "/finding-models" in page.url
```

**Impact:** Fixed 10 Schrödinger's Tests that were passing without testing, preventing silent failures (5 from Sprint 1,
5 from Sprint 2).

### ❌ 2. Arbitrary Timeouts and networkidle Waits

Don't use arbitrary delays - use HTMX-aware waiting or Playwright's built-in auto-waiting:

```python
# ❌ WRONG - Arbitrary delays (found in 41 places before cleanup)
await page.wait_for_load_state("networkidle")  # Adds 500ms+ delay EVERY time
await button.click()
await page.wait_for_timeout(500)  # Arbitrary wait

# ✅ CORRECT - HTMX-aware waiting
await button.click()
await wait_for_htmx_settled(page)  # Waits only as long as needed

# ✅ CORRECT - Playwright auto-waiting
await button.click()
await expect(element).to_be_visible()  # Auto-waits up to timeout
```

**Why networkidle is bad:**

- Adds 500ms+ delay EVERY time, even when page is already ready
- Doesn't actually guarantee HTMX operations are complete
- Accumulates: 41 waits × 500ms = 20+ seconds of pure waiting

**Impact:** Removed 41 `networkidle` waits, reduced UI test suite from 5+ min to 2.5 min (2x speedup).

### ❌ 3. Real AI API Calls in Tests

Don't call real AI APIs - use real test data templates:

```python
# ❌ WRONG - Calls OpenAI API
fm = await create_model_from_markdown(info, markdown_text=md)
# Problems:
# - 10-30 second delay per call
# - Costs real money
# - Unreliable (rate limits, network issues)
# - Non-deterministic results

# ✅ CORRECT - Use real test data template
generated_json = await generate_valid_generated_json(name)
# Benefits:
# - <1ms execution
# - Free
# - 100% reliable
# - Deterministic
```

**Why `generate_valid_generated_json()` matters:**

```python
# Located in tests/ui/utils.py
async def generate_valid_generated_json(name: str) -> str:
    """Create valid FindingModelFull JSON from real test data."""
    test_data_path = Path(__file__).parent.parent / "data" / "abdominal_abscess.fm.json"
    with open(test_data_path) as f:
        template = json.load(f)
    template["name"] = name
    return json.dumps(template, indent=2)
```

This ensures:

- Valid FindingModelFull structure that passes backend validation
- All required fields present (id, codes, attributes, etc.)
- Comment sections will render (requires valid generated_json)
- Tests are fast and deterministic

**Impact:** Eliminated 18+ AI API calls from test_draft_management.py, reduced from 408s to 40s (10x speedup).

### ❌ 4. Testing Impossible Scenarios

Don't write tests for scenarios that can't happen in the UI:

```python
# ❌ WRONG - test_draft_management.py had this
async def test_model_reuse_when_no_changes():
    """Test that unchanged forms can be submitted."""
    # BUT: Alpine.js validation correctly PREVENTS submission when no changes!
    # This test was impossible to pass via UI and caused server errors

# ✅ CORRECT - Test the actual behavior
async def test_form_submission_blocked_when_no_changes():
    """Test that Alpine.js validation blocks unchanged form submission."""
    submit_button = page.locator("button[type='submit']")
    await expect(submit_button).to_be_disabled()
```

**Lesson:** If you have to work around the application's correct behavior to test something, you're testing the wrong
thing. Either:

1. Test that the application correctly prevents the action, OR
2. Test the backend unit directly (not via UI)

**Impact:** Deleted 1 impossible test that was causing server errors despite passing.

### ❌ 5. Missing Validation of Expected Server Errors

If your test causes server errors, either:

- Fix the test so it doesn't cause errors, OR
- Explicitly validate the error is expected

```python
# ❌ WRONG - Test passes but server logs errors
await page.goto("/finding-models/non-existent-slug")
# Server logs: "ERROR: Finding model 'non-existent-slug' not found"
await expect(page.locator("table")).to_be_visible()  # Passes (fallback to list)

# ✅ CORRECT - Validate the expected behavior
await page.goto("/finding-models/non-existent-slug")
if page.url.endswith("/non-existent-slug"):
    # Server returned 404 page
    await expect(page.locator("text=/not found/i")).to_be_visible()
else:
    # Server redirected to list view (also valid)
    await expect(page.locator("table")).to_be_visible()
```

**Impact:** Fixed 2 tests that were passing despite causing unvalidated server errors.

## Summary of Anti-Pattern Fixes (November 2025)

**Sprint 0 & 1 Results:**

- ✅ Removed 41 networkidle waits → 2x speedup
- ✅ Eliminated 18+ AI API calls → 10x speedup for draft management tests
- ✅ Fixed 5 Schrödinger's Tests → prevented silent failures
- ✅ Deleted 1 impossible test → eliminated server errors
- ✅ Overall: UI test suite 5+ min → 2.5 min

**Sprint 2 Results:**

- ✅ Fixed 5 additional Schrödinger's Tests in test_comments.py
- ✅ Completed 3 incomplete workflows (reply submission, thread structure, nested replies)
- ✅ Established database setup pattern: seed/cleanup → navigate → wait for content → test WITHOUT conditionals
- ✅ All 17/17 comment tests passing with proper selector specificity

**See also:** [tests/CLAUDE.md](../CLAUDE.md) for general testing philosophy and cross-cutting patterns.

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
