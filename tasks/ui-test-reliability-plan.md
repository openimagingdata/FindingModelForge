# UI Test Reliability Implementation Plan

## Problem Statement

Our UI tests (Playwright) are currently unreliable due to:
1. **State pollution**: Tests leave behind comments, drafts, and user data that interfere with subsequent runs
2. **Hardcoded IDs**: Tests use hardcoded OIFM IDs that could change
3. **Incomplete cleanup**: The `cleanup_test_data()` function doesn't clean all collections
4. **Missing test user**: Test user (ID 999999) might not exist in database
5. **Invalid test data**: Drafts missing valid `generated_json` cause comment sections not to appear

## Goals

- **Idempotent tests**: Same result every run, regardless of prior state
- **Isolated tests**: No interference between tests
- **Resilient tests**: Handle missing data gracefully (skip vs fail)
- **Fast tests**: Minimal setup/teardown overhead
- **Maintainable tests**: Clear patterns, good documentation

## Implementation Plan

### Phase 1: Fix Cleanup Infrastructure (Priority: CRITICAL)

#### 1.1 Update `cleanup_test_data()` function in `/tests/ui/utils.py`

**Current Issues:**
- Doesn't clean `comment_threads` collection
- Doesn't reset user's `comment_index` array
- Incomplete draft cleanup

**Changes Needed:**
```python
async def cleanup_test_data(user_id: int):
    """Clean all test data for a user."""
    # Add cleanup for comment_threads
    await db["comment_threads"].delete_many({
        "$or": [
            {"user_id": user_id},
            {"comments.user_id": user_id},
            {"reference_id": {"$in": ["OIFM_GMTS_004244", "OIFM_GMTS_004245"]}}
        ]
    })

    # Reset user's comment_index
    await db["users"].update_one(
        {"id": user_id},
        {"$set": {"comment_index": []}}
    )

    # Existing cleanup for drafts, sessions, etc.
```

#### 1.2 Add `ensure_test_user_exists()` helper in `/tests/ui/utils.py`

**Purpose:** Ensure test user always exists with clean state

**Implementation:**
```python
async def ensure_test_user_exists():
    """Ensure test user 999999 exists with clean state."""
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]

    user_doc = {
        "id": 999999,
        "login": "playwright-test-user",
        "name": "Playwright Test User",
        "email": "test@example.com",
        "avatar_url": "https://github.com/playwright-test-user.png?size=40",
        "organizations": [],
        "is_active": True,
        "comment_index": [],  # Always start clean
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat()
    }

    # Upsert: create if not exists, update if exists
    await db["users"].replace_one(
        {"id": 999999},
        user_doc,
        upsert=True
    )

    client.close()
```

### Phase 2: Dynamic OIFM ID Resolution (Priority: HIGH)

#### 2.1 Add `get_test_finding_models()` helper in `/tests/ui/utils.py`

**Purpose:** Get actual OIFM IDs instead of hardcoding

**Implementation:**
```python
async def get_test_finding_models() -> dict[str, str]:
    """Get actual OIFM IDs for test finding models.

    Returns:
        Dict mapping slug to OIFM ID, with fallbacks for known models
    """
    from app.services.finding_model_service import FindingModelService
    from app.database import Database
    from app.cache import RedisCache

    # Default fallbacks if service unavailable
    defaults = {
        "abdominal-abscess": "OIFM_GMTS_004244",
        "liver-lesion": "OIFM_GMTS_004245"
    }

    try:
        db = Database()
        cache = RedisCache()
        await cache.initialize()

        service = FindingModelService(
            database=db,
            cache=cache,
            comment_repo=db.comment_repo,
            user_repo=db.user_repo
        )

        models = {}
        for slug in defaults.keys():
            try:
                model, _ = await service.get_model_by_slug(slug)
                if model and model.oifm_id:
                    models[slug] = model.oifm_id
                else:
                    models[slug] = defaults[slug]
            except:
                models[slug] = defaults[slug]

        return models
    except:
        # If service initialization fails, use defaults
        return defaults
```

#### 2.2 Create session-scoped fixture in `/tests/ui/conftest.py`

**Purpose:** Cache OIFM IDs for entire test session

**Implementation:**
```python
@pytest.fixture(scope="session")
async def test_finding_models():
    """Get finding model IDs once per test session."""
    return await get_test_finding_models()

@pytest.fixture(autouse=True)
async def setup_test_environment(test_finding_models):
    """Ensure test environment is ready before each test."""
    # Ensure test user exists
    await ensure_test_user_exists()

    # Clean comments for test models
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]

    # Clean any comments on our test models
    for oifm_id in test_finding_models.values():
        await db["comment_threads"].delete_many({
            "reference_type": "finding_model",
            "reference_id": oifm_id
        })

    client.close()

    yield

    # Cleanup happens in existing cleanup_test_user_data fixture
```

### Phase 3: Update Test Files (Priority: HIGH)

#### 3.1 Update `/tests/ui/test_comments.py`

**Changes:**
- Replace hardcoded `"OIFM_GMTS_004244"` with fixture value
- Use `test_finding_models` fixture in all tests
- Ensure proper cleanup between tests

**Example:**
```python
async def test_report_comment(authenticated_page, test_finding_models):
    """Test reporting a comment."""
    page = authenticated_page

    # Get actual OIFM ID from fixture
    oifm_id = test_finding_models["abdominal-abscess"]

    # Seed test comment
    await seed_comment(
        reference_type="finding_model",
        reference_id=oifm_id,  # Use dynamic ID
        user_id=TEST_USER_ID,
        comment_text=f"Test comment {int(time.time())}"
    )

    # Rest of test...
```

#### 3.2 Update `/tests/ui/test_draft_comments.py`

**Changes:**
- Ensure drafts have valid `generated_json` for comments to appear
- Use `generate_valid_generated_json()` helper
- Use dynamic OIFM IDs

### Phase 4: Documentation and Verification (Priority: MEDIUM)

#### 4.1 Add test setup documentation

Create `/tests/ui/README.md`:
```markdown
# UI Test Setup

## Prerequisites
- MongoDB running locally
- Redis running (optional but recommended)
- FastAPI dev server running on port 8000

## Test User
All UI tests use user ID 999999 (playwright-test-user).
This user is created automatically by test fixtures.

## Finding Models
Tests use real finding models from GitHub. The actual OIFM IDs
are resolved dynamically at test runtime. Default models:
- abdominal-abscess
- liver-lesion

## Running Tests
```bash
# Run all UI tests
task test-ui

# Run specific test file
uv run pytest tests/ui/test_comments.py -v

# Run with visible browser (debugging)
PLAYWRIGHT_HEADLESS=false uv run pytest tests/ui/test_comments.py -v
```
```

#### 4.2 Add cleanup verification tests

Create tests to verify cleanup is working:
```python
async def test_cleanup_removes_all_test_data():
    """Verify cleanup function removes all test data."""
    # Create test data
    await seed_comment(...)
    await seed_draft(...)

    # Run cleanup
    await cleanup_test_data(TEST_USER_ID)

    # Verify everything is gone
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]

    # Check comments are gone
    comments = await db["comment_threads"].find_one({"comments.user_id": TEST_USER_ID})
    assert comments is None

    # Check drafts are gone
    drafts = await db["finding_model_drafts"].find_one({"user_id": TEST_USER_ID})
    assert drafts is None

    client.close()
```

## Implementation Order

1. **Day 1**: Implement Phase 1 (cleanup fixes)
   - Update `cleanup_test_data()`
   - Add `ensure_test_user_exists()`
   - Test manually that cleanup works

2. **Day 1-2**: Implement Phase 2 (dynamic IDs)
   - Add `get_test_finding_models()`
   - Create fixtures
   - Verify OIFM ID resolution works

3. **Day 2**: Implement Phase 3 (update tests)
   - Update test_comments.py
   - Update test_draft_comments.py
   - Run full test suite, fix any failures

4. **Day 2-3**: Implement Phase 4 (documentation)
   - Create documentation
   - Add verification tests
   - Final test suite run

## Success Criteria

- [ ] All 17 UI tests pass consistently
- [ ] Tests pass on first run with clean database
- [ ] Tests pass on subsequent runs without manual cleanup
- [ ] Tests handle missing finding models gracefully
- [ ] No hardcoded OIFM IDs in test files
- [ ] Cleanup verified to remove all test data
- [ ] Documentation complete and accurate

## Risk Mitigation

1. **If finding model service unavailable**: Use hardcoded fallbacks
2. **If cleanup fails**: Log error but don't fail test
3. **If test user creation fails**: Skip tests with clear message
4. **If MongoDB connection fails**: Skip integration tests

## Testing the Fix

After implementation:
1. Drop test database completely
2. Run `task test-ui` - should pass
3. Run `task test-ui` again - should still pass
4. Check database - no test data should remain

## Notes

- Always use user ID 999999 for UI tests (test-auth requirement)
- Never use production database for tests
- Keep test data realistic but clearly marked as test data
- Consider adding timestamps to test data for debugging
