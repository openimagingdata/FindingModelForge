# Testing Guide - FindingModelForge

This guide covers testing patterns, best practices, and commands for the FindingModelForge test suite.

## Test Organization

Tests are organized into **unit tests** and **integration tests**:

- **Unit tests**: Fast, isolated tests with mocked dependencies (~0.4s for 71 tests)
- **Integration tests**: Tests involving external systems (MongoDB, Redis, GitHub API) (~0.15s for 35 tests)

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
            "/api/finding-models/create/step/1",
            data={"name": "test-finding"}
        )
        assert response.status_code == 200
        
        # Step 2: Edit description
        response = auth_client.post(
            "/api/finding-models/create/step/2",
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

```python
import pytest
from playwright.async_api import async_playwright

@pytest.mark.playwright
async def test_full_workflow_browser():
    """Test complete workflow in browser."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate to app
        await page.goto("http://localhost:8000")
        
        # Login
        await page.click("text=Login with GitHub")
        
        # Start creation workflow
        await page.click("text=Create Finding Model")
        
        # Step 1: Enter name
        await page.fill("input[name='name']", "test-finding")
        await page.click("button[type='submit']")
        
        # Step 2: Description
        await page.fill("textarea[name='description']", "Test description")
        await page.click("text=Continue")
        
        # Verify draft saved
        await page.wait_for_selector("text=Draft saved")
        
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

Located in `test_drafts.py`, `test_step4_*.py`:

```python
# Test autosave
async def test_step4_autosaves_on_get():
    # GET request to step 4 should save draft
    pass

# Test resume
async def test_resume_from_draft():
    # Resume should populate session from draft
    pass

# Test submit
async def test_submit_locks_draft():
    # Submitted drafts cannot be edited
    pass
```

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
        python-version: '3.12'
    
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