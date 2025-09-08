# Testing Guide - FindingModelForge

This guide covers testing patterns, best practices, and commands for the FindingModelForge test suite.

## Test Organization

Tests are organized into **unit tests** and **integration tests**:

- **Unit tests**: Fast, isolated tests with mocked dependencies (~0.4s for 71 tests)
- **Integration tests**: Tests involving external systems (MongoDB, Redis, GitHub API) (~0.15s for 35 tests)

## ⚠️ CRITICAL: HTMX Testing Patterns for Creation Workflow

**ULTRA-IMPORTANT FOR CREATION WORKFLOW TESTS:**

The finding model creation workflow operates via **HTMX content swaps ONLY**. There are **NO browser page redirects**.

### What This Means for Testing:

- **Single Page**: All workflow happens within `create_finding_model_htmx.html`
- **Container**: All content swaps into `#step-container`
- **Server "Redirects"**: Backend 303 redirects are **intercepted by HTMX** and become content swaps
- **URL Bar Changes**: Via `HX-Push-Url` but **no actual page navigation**

### Required Testing Patterns:

```python
# ✅ CORRECT: HTMX-aware testing
await page.locator("button:has-text('Check for Similar')").click()
await wait_for_ai_completion_and_swap(page, "Check", "#step-container textarea")

# ❌ WRONG: Browser navigation testing (will fail!)
await page.locator("button:has-text('Check for Similar')").click()
await page.wait_for_url("**/drafts/**")  # This will NEVER happen!
```

### Essential HTMX Test Functions:

- `wait_for_htmx_swap(page, expected_selector)` - Wait for HTMX content swap
- `wait_for_ai_completion_and_swap(page, button_prefix, expected_element)` - AI operations
- `wait_for_htmx_to_settle(page)` - Basic HTMX completion

### Common Testing Mistakes:

❌ Using `page.goto()` during workflow testing ❌ Waiting for URL changes with `page.wait_for_url()` ❌ Expecting page
navigation events ❌ Testing outside of `#step-container` context

**If you're testing the creation workflow and thinking about "page redirects", STOP and re-read this section.**

## Running Tests

### Quick Commands

```bash
# All tests with coverage
task test

# Fast unit tests only (recommended during development)
task test-unit
# or
uv run pytest -m "not integration" -v

# Integration tests only (for CI/deployment)
task test-integration
# or
uv run pytest -m integration -v

# Full test suite with quality checks
task test-full

# Specific test file
uv run pytest tests/test_drafts.py -v

# Specific test function
uv run pytest tests/test_drafts.py::test_save_draft -v

# With coverage report
uv run pytest --cov=app --cov-report=term-missing

# Playwright browser tests
task test-playwright
# or
uv run python scripts/run_playwright_tests.py
```

## Test Files Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── data/                    # Test data files (JSON fixtures)
│   ├── abdominal_abscess.fm.json
│   └── coronary_artery_calcifications.fm.json
├── test_*.py               # Test modules
│   ├── test_auth*.py       # Authentication tests
│   ├── test_cache*.py      # Cache layer tests
│   ├── test_database*.py   # Database tests
│   ├── test_drafts*.py     # Draft functionality tests
│   ├── test_finding_models*.py  # Finding model tests
│   ├── test_step4*.py      # Step 4 specific tests
│   └── test_*_playwright.py # Browser automation tests
```

## Testing Patterns

### 1. Unit Test Pattern

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

class TestFindingModels:
    """Unit tests for finding model operations."""

    @pytest.fixture
    def mock_database(self):
        """Create a mock database with repositories."""
        db = MagicMock()
        db.finding_models = AsyncMock()
        db.draft_repo = AsyncMock()
        return db

    @pytest.fixture
    def mock_cache(self):
        """Create a mock cache."""
        cache = AsyncMock()
        cache.is_healthy = AsyncMock(return_value=True)
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        return cache

    async def test_create_finding_model(self, mock_database, mock_cache):
        """Test creating a finding model."""
        # Arrange
        mock_database.finding_models.insert_one.return_value = AsyncMock(
            inserted_id="test-id"
        )

        # Act
        result = await create_finding_model(
            data={"name": "test"},
            database=mock_database,
            cache=mock_cache
        )

        # Assert
        assert result.id == "test-id"
        mock_database.finding_models.insert_one.assert_called_once()
        mock_cache.set.assert_called()
```

### 2. Integration Test Pattern

```python
import pytest
from motor.motor_asyncio import AsyncIOMotorClient

@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests with real MongoDB."""

    @pytest.fixture
    async def real_database(self):
        """Create real database connection."""
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.test_findingmodelforge

        # Setup
        yield db

        # Teardown
        await client.drop_database("test_findingmodelforge")
        client.close()

    async def test_draft_lifecycle(self, real_database):
        """Test complete draft lifecycle with real database."""
        draft_repo = DraftRepo(real_database)

        # Create draft
        draft = await draft_repo.save_draft(
            user_id=1,
            name="test",
            inputs=FindingModelInputs(...)
        )
        assert draft.id is not None
        assert draft.status == "draft"

        # Update draft
        updated = await draft_repo.save_draft(
            user_id=1,
            name="test",
            inputs=FindingModelInputs(...),
            draft_id=draft.id
        )
        assert updated.id == draft.id

        # Submit draft
        submitted = await draft_repo.submit(draft.id, user_id=1)
        assert submitted.status == "submitted"
```

### 3. FastAPI Test Client Pattern

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

class TestAPI:
    """API endpoint tests."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_client(self, client):
        """Create authenticated test client."""
        # Set auth cookies or headers
        client.cookies["access_token"] = "test-jwt-token"
        return client

    def test_create_finding_model_workflow(self, auth_client):
        """Test multi-step creation workflow."""
        # Step 1: Enter name
        response = auth_client.post(
            "/create/step/1",
            data={"name": "test-finding"}
        )
        assert response.status_code == 200

        # Step 2: Edit description
        response = auth_client.post(
            "/create/step/2",
            data={
                "description": "Test description",
                "synonyms": '["test1", "test2"]'
            }
        )
        assert response.status_code in [200, 303]  # May redirect
```

### 4. Session Testing Pattern

```python
class TestSession:
    """Test session management."""

    @pytest.fixture
    def mock_session_manager(self):
        """Create mock session manager."""
        manager = AsyncMock()
        manager.get_session = AsyncMock()
        manager.update_session = AsyncMock()
        return manager

    async def test_session_adoption(self, mock_session_manager):
        """Test adopting draft state into session."""
        # Setup session without draft
        session = FindingModelCreationSession(session_id="test")
        mock_session_manager.get_session.return_value = session

        # Mock draft
        draft = FindingModelDraft(
            id="draft-1",
            name="test",
            inputs=FindingModelInputs(...)
        )

        # Adopt draft into session
        session.draft_id = draft.id
        session.name = draft.name

        # Verify
        assert session.draft_id == "draft-1"
        assert session.name == "test"
```

### 5. Playwright Browser Testing

**CRITICAL**: Playwright tests require authentication to access protected pages. This project provides a test-auth
system for this purpose.

#### Generating Valid Draft Data for UI Tests

**IMPORTANT**: When creating test drafts that need to display finding models (especially for comment functionality), you
MUST use valid FindingModelFull JSON.

##### The Problem with Invalid JSON

Creating simple JSON objects will NOT work:

```python
# ❌ WRONG - This will NOT validate as FindingModelFull
generated_json = json.dumps({
    "name": "Test Draft",
    "description": "Test description",
    "attributes": {"test": "value"}
})
```

When the backend validates this JSON:

```python
# In app/routers/drafts.py line 322
finding_model = FindingModelFull.model_validate_json(draft.generated_json)
```

If validation fails:

- `finding_model` becomes None
- No model is displayed on the draft page
- **Comment sections will NOT appear**
- Tests that depend on comments will fail

##### The Correct Approach

Use the `generate_valid_generated_json()` helper function:

```python
# ✅ CORRECT - Creates valid FindingModelFull JSON
from tests.ui.utils import generate_valid_generated_json

# In async test function:
generated_json = await generate_valid_generated_json("Test Draft Name")

# Then use in seed_draft:
draft_id = await seed_draft(
    user_id=TEST_USER_ID,
    name="Test Draft Name",
    description="Test description",
    status="submitted",
    generated_json=generated_json  # Valid JSON that will pass validation
)
```

The `generate_valid_generated_json()` function:

- Creates a complete finding model structure
- Adds proper IDs and codes
- Ensures all required FindingModelFull fields are present
- Returns JSON that will pass backend validation

##### When This Matters

This is critical for any UI test that:

- Tests comment functionality on drafts
- Needs to display the finding model on draft pages
- Tests the edit/preview mode toggle (which requires generated_json)
- Tests any feature that depends on a valid finding model being displayed

#### Authentication Pattern for Playwright Tests

```python
import pytest
from playwright.async_api import async_playwright

@pytest.mark.playwright
async def test_authenticated_workflow():
    """Test workflow that requires authentication."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # STEP 1: Authenticate via test route
            await page.goto("http://localhost:8000/test-auth/login")
            await page.wait_for_load_state("networkidle")

            # The test-auth system automatically:
            # - Creates user ID 999999 ("playwright-test-user")
            # - Sets JWT cookies
            # - Redirects to /create-finding-model

            # STEP 2: Navigate to your test page
            await page.goto("http://localhost:8000/your-protected-page")

            # STEP 3: Perform your tests
            await page.fill("input[name='name']", "test-finding")
            await page.click("button[type='submit']")

        finally:
            await browser.close()
```

#### Test Data Setup for Playwright

When testing with database data, ensure the user ID matches the test-auth system:

```python
async def _seed_test_data(user_id: int, name: str) -> str:
    """Create test data in MongoDB for Playwright tests."""
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    col = db.your_collection

    test_doc = {
        "_id": ObjectId(),
        "user_id": user_id,  # MUST be 999999 for test-auth
        "name": name,
        "created_at": datetime.now(UTC),
        # ... other fields
    }

    await col.insert_one(test_doc)
    await db.command("ping")  # Ensure write is committed
    client.close()
    return str(test_doc["_id"])

class TestYourFeature:
    async def test_feature_with_data(self) -> None:
        # CRITICAL: Use 999999, not TEST_AUTH_USER_ID env var
        test_user_id = 999999  # Hardcoded in test-auth system

        # Create test data
        data_id = await _seed_test_data(test_user_id, "Test Data")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # Authenticate
                await page.goto("http://localhost:8000/test-auth/login")
                await page.wait_for_load_state("networkidle")

                # Test your feature
                await page.goto(f"http://localhost:8000/your-page/{data_id}")
                # ... rest of test

            finally:
                await browser.close()
```

#### Key Authentication Rules

1. **Always use test-auth**: Never try to manually set cookies or use GitHub OAuth in tests
2. **User ID is always 999999**: The test-auth system hardcodes this ID
3. **Database data must match**: Any test data must use user_id=999999
4. **Wait for networkidle**: Ensure auth cookies are set before navigating
5. **Test in development only**: test-auth is disabled in production

#### Example: Complete Playwright Test with Auth

```python
from datetime import UTC, datetime
import pytest
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from playwright.async_api import async_playwright, expect
from app.config import settings

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.playwright]

async def _seed_draft(user_id: int, draft_name: str) -> str:
    """Create a test draft."""
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    col = db.drafts

    draft_doc = {
        "_id": ObjectId(),
        "user_id": user_id,
        "name": draft_name,
        "created_at": datetime.now(UTC),
        "status": "draft",
        "inputs": {
            "description": "Test description",
            "synonyms": ["test"],
            "attributes_markdown": "## Test\n- test: value"
        }
    }

    await col.insert_one(draft_doc)
    await db.command("ping")
    client.close()
    return str(draft_doc["_id"])

class TestDraftEditing:
    async def test_edit_draft_workflow(self) -> None:
        """Test editing a draft through the UI."""
        test_user_id = 999999  # test-auth user ID
        draft_name = "Playwright Test Draft"

        # Create test draft
        draft_id = await _seed_draft(test_user_id, draft_name)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # Authenticate
                await page.goto("http://localhost:8000/test-auth/login")
                await page.wait_for_load_state("networkidle")

                # Navigate to draft edit page
                await page.goto(f"http://localhost:8000/drafts/{draft_id}?mode=edit")

                # Test the editing workflow
                await expect(page.locator("h1")).to_contain_text("Edit Finding Model Draft")

                # Make changes
                await page.fill('textarea[name="description"]', "Updated description")

                # Submit changes
                await page.click('button[type="submit"]:has-text("Update & Preview")')

                # Verify results
                await expect(page.locator("h1")).to_contain_text("Preview Finding Model Draft")

            finally:
                await browser.close()
```

## Fixtures

### Common Fixtures (conftest.py)

```python
# Mock user
@pytest.fixture
def mock_user():
    return User(
        id=1,
        username="testuser",
        github_id=12345
    )

# Mock finding model
@pytest.fixture
def sample_finding_model():
    with open("tests/data/abdominal_abscess.fm.json") as f:
        return json.load(f)

# Mock session
@pytest.fixture
def mock_session():
    return FindingModelCreationSession(
        session_id="test-session",
        name="test-finding",
        current_step=1
    )
```

## Testing Best Practices

### 1. Test Naming

```python
# Good test names describe what is being tested
def test_save_draft_creates_new_when_no_id():
    pass

def test_save_draft_updates_existing_when_id_provided():
    pass

def test_submit_draft_changes_status_to_submitted():
    pass
```

### 2. Arrange-Act-Assert Pattern

```python
async def test_example():
    # Arrange - Set up test data and mocks
    mock_db = create_mock_database()
    test_data = {"name": "test"}

    # Act - Perform the action being tested
    result = await function_under_test(test_data, mock_db)

    # Assert - Verify the results
    assert result.success is True
    mock_db.save.assert_called_once_with(test_data)
```

### 3. Parametrized Tests

```python
@pytest.mark.parametrize("input_name,expected_valid", [
    ("ab", False),  # Too short
    ("valid-name", True),
    ("a" * 201, False),  # Too long
    ("", False),  # Empty
])
def test_name_validation(input_name, expected_valid):
    result = validate_name(input_name)
    assert result.is_valid == expected_valid
```

### 4. Async Test Patterns

```python
# Use pytest-asyncio for async tests
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None

# Or use anyio
import anyio

async def test_with_anyio():
    async with anyio.create_task_group() as tg:
        tg.start_soon(async_operation)
```

### 5. Mock External Services

```python
@patch("app.auth.github_api_call")
async def test_github_login(mock_github):
    mock_github.return_value = {
        "id": 12345,
        "login": "testuser"
    }

    result = await authenticate_with_github("test-code")
    assert result.username == "testuser"
```

## Testing Specific Features

### Draft System Tests

#### Comprehensive Test Coverage

The draft system has extensive test coverage in `test_finding_models_comprehensive.py`:

##### Priority 1: Critical Happy Path Tests

```python
class TestCriticalHappyPaths:
    async def test_process_step_4_happy_path(self, authenticated_client, mock_session):
        """Test step 4 processing with complete valid data."""
        response = authenticated_client.post(
            "/create/step/4",
            data={
                "description": "Complete medical description for testing purposes",
                "synonyms": '["synonym1", "synonym2"]',
                "attributes_markdown": "## Section 1\n- attribute: value\n\n## Section 2\n- another: value"
            }
        )
        assert response.status_code in [200, 303]

    async def test_unified_draft_page_view_mode(self, authenticated_client):
        """Test unified draft page in view mode."""
        draft_id = "507f1f77bcf86cd799439011"  # Valid ObjectId
        response = authenticated_client.get(f"/drafts/{draft_id}?mode=view")
        assert response.status_code in [200, 404]

    async def test_unified_draft_page_edit_mode(self, authenticated_client):
        """Test unified draft page in edit mode (default)."""
        draft_id = "507f1f77bcf86cd799439011"
        response = authenticated_client.get(f"/drafts/{draft_id}")
        assert response.status_code in [200, 404]

    async def test_update_draft_and_redirect(self, authenticated_client):
        """Test updating draft and redirecting to view mode."""
        draft_id = "507f1f77bcf86cd799439011"
        response = authenticated_client.post(
            f"/drafts/{draft_id}/update-and-redirect",
            data={
                "description": "Updated description for redirect test",
                "synonyms": '["updated1", "updated2"]',
                "attributes_markdown": "## Updated Section\n- updated: value"
            }
        )
        assert response.status_code in [200, 303, 404]
```

##### Priority 2: Draft State Transitions

```python
class TestDraftStateTransitions:
    async def test_save_draft_with_existing_draft_id(self, authenticated_client):
        """Test updating existing draft via draft_id parameter."""
        response = authenticated_client.post(
            "/create/step/4",
            data={
                "draft_id": "507f1f77bcf86cd799439011",
                "description": "Updated description for existing draft",
                "synonyms": '["updated1", "updated2"]',
                "attributes_markdown": "## Updated Section\n- updated: value"
            }
        )
        assert response.status_code in [200, 303, 404]

    async def test_submit_draft_happy_path(self, authenticated_client):
        """Test submitting draft changes status to submitted."""
        draft_id = "507f1f77bcf86cd799439011"
        response = authenticated_client.post(f"/drafts/{draft_id}/submit")
        assert response.status_code in [200, 303, 404]

    async def test_delete_draft_happy_path(self, authenticated_client):
        """Test deleting draft (only works for draft status)."""
        draft_id = "507f1f77bcf86cd799439011"
        response = authenticated_client.post(f"/drafts/{draft_id}/delete")
        assert response.status_code in [200, 303, 404]

    async def test_resume_creation_draft_status(self, authenticated_client):
        """Test resuming creation with draft status."""
        response = authenticated_client.post(
            "/drafts/resume",
            data={"draft_id": "507f1f77bcf86cd799439011"}
        )
        assert response.status_code in [200, 303, 404]

    async def test_get_step_4_autosave_on_get(self, authenticated_client, mock_session):
        """Test that GET to step 4 triggers autosave."""
        response = authenticated_client.get("/create/step/4")
        assert response.status_code == 200
        # Should trigger autosave if session has name
```

##### Priority 3: Error Handling & Edge Cases

```python
class TestErrorHandlingEdgeCases:
    async def test_step_4_with_invalid_draft_id(self, authenticated_client):
        """Test step 4 with malformed draft_id."""
        response = authenticated_client.post(
            "/create/step/4",
            data={
                "draft_id": "invalid-not-objectid",
                "description": "Valid description for error case testing",
                "synonyms": '["valid"]',
                "attributes_markdown": "## Valid\n- test: value"
            }
        )
        assert response.status_code in [200, 400, 422]

    async def test_unified_draft_page_invalid_id(self, authenticated_client):
        """Test unified draft page with invalid draft ID."""
        response = authenticated_client.get("/drafts/invalid-id")
        assert response.status_code == 400

    async def test_step_4_validation_short_description(self, authenticated_client):
        """Test step 4 with description too short."""
        response = authenticated_client.post(
            "/create/step/4",
            data={
                "description": "short",  # Too short
                "synonyms": '["test"]',
                "attributes_markdown": "## Test\n- test: value"
            }
        )
        assert response.status_code in [200, 400, 422]
```

##### Priority 4: Access Control & Validation

```python
class TestAccessControlValidation:
    async def test_unified_draft_page_ownership_check(self, authenticated_client):
        """Test that users can only access their own drafts."""
        # This would test with a draft belonging to different user
        draft_id = "507f1f77bcf86cd799439011"
        response = authenticated_client.get(f"/drafts/{draft_id}")
        assert response.status_code in [200, 403, 404]

    async def test_step_4_session_required(self):
        """Test that step 4 requires valid session."""
        client = TestClient(app)  # No authentication
        response = client.post("/create/step/4")
        assert response.status_code in [401, 403]
```

#### Key Testing Patterns

##### Authenticated Client Setup

```python
@pytest.fixture
def authenticated_client(self, mock_user) -> TestClient:
    """Create authenticated test client with session cookie."""
    client = TestClient(app)
    client.cookies["creation_session_id"] = "test-session"
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return client
```

##### Valid ObjectId Usage

```python
# Always use valid MongoDB ObjectIds in tests
VALID_DRAFT_ID = "507f1f77bcf86cd799439011"
VALID_USER_ID = 999999  # For Playwright tests

# In tests
response = client.get(f"/api/drafts/{VALID_DRAFT_ID}")
```

##### Session Mocking

```python
@pytest.fixture
def mock_session_manager():
    """Mock session manager with realistic session data."""
    manager = AsyncMock()
    test_session = FindingModelCreationSession(
        session_id="test-session",
        current_step=4,
        name="Test Finding Model",
        description="Test description for comprehensive testing",
        synonyms=["test1", "test2"],
        attributes_markdown="## Test Section\n- test: value"
    )
    manager.get_or_create_session = AsyncMock(return_value=test_session)
    return manager
```

#### Test Results

Current test coverage for `app/routers/finding_models.py`:

- **Total tests**: 70 passing, 4 skipped, 0 failing
- **Coverage**: 71% (up from 49%)
- **Lines covered**: 850+ lines of router code
- **Test execution time**: ~0.4s for unit tests

### Session Management Tests

Located in `test_session_*.py`:

```python
# Test session creation
async def test_session_auto_creation():
    pass

# Test session adoption
async def test_session_adopts_draft_state():
    pass

# Test session TTL
async def test_session_expires_after_timeout():
    pass
```

### HTMX Workflow Tests

Located in `test_finding_models_htmx.py`:

```python
# Test step transitions
def test_step_navigation():
    pass

# Test conditional routing
def test_skip_step_3_when_no_similar():
    pass

# Test form validation
def test_step_validation_errors():
    pass
```

## Coverage Goals

- **Overall**: Aim for >80% coverage
- **Critical paths**: 100% coverage for auth, drafts, session management
- **UI logic**: Test with Playwright for end-to-end coverage

Check coverage:

```bash
uv run pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Debugging Tests

### 1. Print Debugging

```python
def test_something():
    result = function_under_test()
    print(f"Result: {result}")  # Will show with pytest -s
    assert result is not None
```

### 2. Debugger

```python
def test_something():
    import pdb; pdb.set_trace()  # Breakpoint
    result = function_under_test()
```

### 3. Verbose Output

```bash
# Show all output
pytest -vvs

# Show locals on failure
pytest --showlocals

# Stop on first failure
pytest -x
```

### 4. Run Specific Tests

```bash
# Run tests matching pattern
pytest -k "draft"

# Run specific test class
pytest tests/test_drafts.py::TestDraftRepo

# Run with specific marker
pytest -m "not integration"
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mongodb:
        image: mongo:7
      redis:
        image: redis:7

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install uv
          uv sync --all-extras --dev

      - name: Run unit tests
        run: uv run pytest -m "not integration"

      - name: Run integration tests
        run: uv run pytest -m integration
```

## Common Issues and Solutions

### Issue: Tests fail with "Event loop is closed"

**Solution**: Use `pytest-asyncio` or ensure proper async test setup

### Issue: MongoDB connection errors in tests

**Solution**: Ensure MongoDB is running: `docker-compose up -d mongodb`

## Database Testing with MongoDB MCP

### Using MongoDB MCP for Test Database Management

The MongoDB MCP server provides direct database access for test setup, cleanup, and debugging. This is particularly
useful for integration tests and test data management.

#### Connecting to Test Database

```python
# Within Claude Code or test setup scripts
mcp__mongodb__connect("mongodb://localhost:27017")

# List databases to verify test database exists
mcp__mongodb__list-databases()

# Use test database
mcp__mongodb__list-collections("test_findingmodels_db")
```

#### Pre-Test Database Setup

Use MongoDB MCP to prepare test data before running tests:

```python
# Create test users for Playwright tests
mcp__mongodb__insert-many("test_findingmodels_db", "users", [
    {
        "id": 999999,
        "login": "test-user",
        "name": "Test User",
        "email": "test@example.com",
        "avatar_url": "https://example.com/avatar.png",
        "organizations": ["test-org"],
        "is_active": true,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
])

# Create test drafts for specific test scenarios
mcp__mongodb__insert-many("test_findingmodels_db", "finding_model_drafts", [
    {
        "user_id": 999999,
        "name": "Test Draft",
        "status": "draft",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "inputs": {
            "description": "Test description for integration testing",
            "synonyms": ["test", "example"],
            "attributes_markdown": "## Test Attributes\n- test: value"
        },
        "generated_json": null,
        "action_log": [{
            "timestamp": "2024-01-01T00:00:00Z",
            "user_id": 999999,
            "action": "draft.created",
            "details": null
        }]
    }
])
```

#### Post-Test Database Cleanup

Clean up test data after test runs:

```python
# Remove test data from specific collections
mcp__mongodb__delete-many("test_findingmodels_db", "finding_model_drafts",
                          {"user_id": 999999})

# Clean up temporary test users
mcp__mongodb__delete-many("test_findingmodels_db", "users",
                          {"login": {"$regex": "^test-"}})

# Remove all documents from a collection (full reset)
mcp__mongodb__delete-many("test_findingmodels_db", "temp_drafts", {})

# For complete database reset
mcp__mongodb__drop-database("test_findingmodels_db")
```

#### Database State Verification

Verify database state during test debugging:

```python
# Check document counts
mcp__mongodb__count("test_findingmodels_db", "finding_model_drafts")
mcp__mongodb__count("test_findingmodels_db", "users", {"is_active": true})

# Find specific test data
mcp__mongodb__find("test_findingmodels_db", "finding_model_drafts",
                   {"user_id": 999999}, limit=5)

# Verify data integrity
mcp__mongodb__find("test_findingmodels_db", "finding_model_drafts",
                   {"status": {"$nin": ["draft", "submitted"]}})
```

#### Test Data Factories via MCP

Use MCP to create realistic test data factories:

```python
# Create multiple test drafts with variations
test_drafts = []
for i in range(5):
    test_drafts.append({
        "user_id": 999999,
        "name": f"Test Draft {i+1}",
        "status": "draft" if i < 3 else "submitted",
        "created_at": f"2024-01-{i+1:02d}T00:00:00Z",
        "updated_at": f"2024-01-{i+1:02d}T12:00:00Z",
        "inputs": {
            "description": f"Test description for draft {i+1}",
            "synonyms": [f"test{i+1}", f"example{i+1}"],
            "attributes_markdown": f"## Test Attributes {i+1}\n- attr{i+1}: value{i+1}"
        },
        "generated_json": '{"test": true}' if i >= 2 else None,
        "action_log": [{
            "timestamp": f"2024-01-{i+1:02d}T00:00:00Z",
            "user_id": 999999,
            "action": "draft.created",
            "details": None
        }]
    })

mcp__mongodb__insert-many("test_findingmodels_db", "finding_model_drafts", test_drafts)
```

#### Integration Test Database Patterns

For integration tests requiring real database operations:

```python
class TestDraftIntegration:
    """Integration tests using MongoDB MCP for setup/teardown."""

    @classmethod
    def setup_class(cls):
        """Set up test database via MCP."""
        # Create test collections and indexes
        mcp__mongodb__create-collection("test_findingmodels_db", "test_drafts")

        # Insert base test data
        mcp__mongodb__insert-many("test_findingmodels_db", "users", [
            {"id": 888888, "login": "integration-user", "name": "Integration User"}
        ])

    @classmethod
    def teardown_class(cls):
        """Clean up test database via MCP."""
        # Remove test collections
        mcp__mongodb__drop-collection("test_findingmodels_db", "test_drafts")

        # Clean up test data
        mcp__mongodb__delete-many("test_findingmodels_db", "users",
                                  {"id": {"$gte": 888888}})

    def test_draft_persistence(self):
        """Test that drafts persist correctly in real database."""
        # Test implementation using real database operations
        pass
```

#### Database Performance Testing

Use MCP to test database performance and query patterns:

```python
# Create large dataset for performance testing
large_dataset = []
for i in range(1000):
    large_dataset.append({
        "user_id": 100000 + (i % 100),  # 100 different users
        "name": f"Performance Test Draft {i}",
        "status": "draft",
        "created_at": f"2024-01-01T{i % 24:02d}:00:00Z",
        "inputs": {"description": f"Performance test description {i}"}
    })

mcp__mongodb__insert-many("test_findingmodels_db", "performance_test_drafts", large_dataset)

# Test query performance
mcp__mongodb__explain("test_findingmodels_db", "performance_test_drafts",
                      [{"name": "find", "arguments": {"filter": {"user_id": 100050}}}])

# Check collection size
mcp__mongodb__collection-storage-size("test_findingmodels_db", "performance_test_drafts")

# Cleanup
mcp__mongodb__drop-collection("test_findingmodels_db", "performance_test_drafts")
```

#### Debugging Test Failures

When tests fail due to database issues, use MCP to investigate:

```python
# Check what data exists
mcp__mongodb__find("test_findingmodels_db", "finding_model_drafts", {}, limit=10)

# Verify test user exists
mcp__mongodb__find("test_findingmodels_db", "users", {"id": 999999})

# Check for orphaned data
mcp__mongodb__aggregate("test_findingmodels_db", "finding_model_drafts", [
    {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "id", "as": "user"}},
    {"$match": {"user": {"$size": 0}}}
])

# Get collection statistics
mcp__mongodb__db-stats("test_findingmodels_db")
```

**Best Practices:**

- Always use test-specific database names (e.g., `test_findingmodels_db`)
- Clean up test data after each test run to avoid interference
- Use realistic test data that matches production data structures
- Verify database state before and after tests when debugging
- Use MCP for both setup/teardown and mid-test data verification

### Issue: Session tests fail randomly

**Solution**: Mock time/UUID generation for deterministic tests

### Issue: Playwright tests timeout

**Solution**: Increase timeout or run with headed mode for debugging:

```python
browser = await p.chromium.launch(headless=False, slow_mo=500)
```

## Test Data Management

### Using Fixtures

```python
# Load from JSON files
@pytest.fixture
def sample_finding_model():
    with open("tests/data/sample.json") as f:
        return json.load(f)
```

### Factory Pattern

```python
def create_test_draft(**kwargs):
    defaults = {
        "id": "test-id",
        "user_id": 1,
        "name": "test",
        "status": "draft"
    }
    defaults.update(kwargs)
    return FindingModelDraft(**defaults)
```

## Resources

- **Pytest Docs**: https://docs.pytest.org/
- **pytest-asyncio**: https://github.com/pytest-dev/pytest-asyncio
- **Playwright Python**: https://playwright.dev/python/
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/
