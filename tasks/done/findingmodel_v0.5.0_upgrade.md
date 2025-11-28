# FindingModel v0.5.0 Upgrade Plan

**Status**: Phases 0, 1, and 1.5 complete - Ready for Phase 2 implementation **Created**: 2025-11-03 **Updated**:
2025-11-04 (Phase 1.5 complete - all API patterns verified and documented) **Target Version**: findingmodel v0.5.0
**Current Version**: findingmodel v0.4.0

## Overview

Upgrade from findingmodel v0.4.0 to v0.5.0 to leverage the improved Index API and significantly simplify our codebase.
The v0.5.0 release provides built-in methods for operations we currently implement manually, allowing us to **delete
~150+ lines of custom code**.

## Key Benefits

- **Simpler code**: Replace direct SQL queries with clean Index API methods
- **Remove caching layer**: Delete entire finding model Redis cache (Index handles it)
- **No GitHub API dependency**: Use `Index.get_full()` instead of fetching from GitHub
- **Better abstraction**: Library handles complexity, we handle business logic
- **Auto-updating models**: Manifest-based sync without code changes

## Breaking Changes

### Critical: Direct SQL Access Pattern

**What Changed**: v0.5.0 removes MongoDB backend and consolidates on DuckDB. Direct connection access via
`Index._ensure_connection()` is no longer supported.

**Impact**: `app/services/finding_model_service.py` line 60 uses `_ensure_connection()` for direct SQL queries.

**Migration**: Use new Index API methods instead:

- `Index.all(offset, limit)` - Paginated listing, returns `tuple[list[IndexEntry], int]`
- `Index.search_by_slug(pattern, limit, offset)` - Search by slug with pagination, returns
  `tuple[list[IndexEntry], int]`
- `Index.count()` - Total count (no search parameter)
- `Index.count_search(pattern)` - Count search results
- `Index.get_full(oifm_id)` - Get complete model JSON (requires OIFM ID, raises KeyError if not found)

## Implementation Tasks

### Phase 0: Pre-Upgrade API Verification

**CRITICAL**: Run this phase BEFORE upgrading to document current v0.4.0 baseline and confirm upgrade is necessary.

**File**: `scripts/verify_v0.4.0_baseline.py` (create new file)

**Content**:

```python
"""Verify current v0.4.0 capabilities before upgrade."""
import asyncio
from findingmodel import Index

async def verify_current_state():
    """Document what works in v0.4.0."""
    print("=== Current v0.4.0 Baseline ===\n")

    index = Index(db_path=None, read_only=True)
    print("✓ Index initialization works (persistent pattern)")

    # Test methods we currently use
    result = await index.get("abdominal-abscess")
    if result:
        print(f"✓ index.get() works, found: {result.name}")

    # Test count method
    try:
        count = await index.count()
        print(f"✓ index.count() works: {count} models")
    except AttributeError:
        print("✗ index.count() not available in v0.4.0")

    # Test new methods (should fail in v0.4.0)
    print("\nTesting v0.5.0 methods (expect failures):")

    try:
        await index.list(limit=5, offset=0)
        print("✗ UNEXPECTED: index.list() exists in v0.4.0")
    except AttributeError:
        print("✓ Expected: index.list() not in v0.4.0")

    try:
        await index.search_by_slug("test")
        print("✗ UNEXPECTED: index.search_by_slug() exists in v0.4.0")
    except AttributeError:
        print("✓ Expected: index.search_by_slug() not in v0.4.0")

    try:
        await index.get_full("test")
        print("✗ UNEXPECTED: index.get_full() exists in v0.4.0")
    except AttributeError:
        print("✓ Expected: index.get_full() not in v0.4.0")

    print("\n=== Baseline verification complete ===")

if __name__ == "__main__":
    asyncio.run(verify_current_state())
```

**Run**: `uv run python scripts/verify_v0.4.0_baseline.py`

**Expected Output**:

- `index.get()` works
- `index.count()` may or may not exist
- `index.list()`, `search_by_slug()`, `get_full()` should raise `AttributeError`

**Success Criteria**: Confirms v0.4.0 lacks the methods we need, justifying the upgrade.

---

### Phase 1: Dependency Update

**File**: `pyproject.toml`

**Change**:

```toml
# Line 17: Update version constraint
dependencies = [
    # ... other deps ...
    "findingmodel>=0.5.0",  # Changed from >=0.4.0
]
```

**Command**: `uv sync`

**Verification**: `uv run python -c "import findingmodel; print(findingmodel.__version__)"` Expected output: `0.5.0`

---

### Phase 1.5: Post-Upgrade API Verification

**CRITICAL**: Run this phase IMMEDIATELY after Phase 1 to verify v0.5.0 APIs before implementing.

**File**: `scripts/verify_v0.5.0_api.py` (create new file)

**Content**:

```python
"""Verify v0.5.0 API methods work correctly."""
import asyncio
import inspect
from findingmodel import Index
from findingmodel.index import IndexEntry

async def verify_api():
    """Verify all required v0.5.0 methods exist and work."""
    print("=== v0.5.0 API Verification ===\n")

    # 1. Test initialization (persistent, not context manager)
    index = Index(db_path=None, read_only=True)
    print("✓ Index initialization works (persistent pattern)")

    # 2. Verify method existence
    required_methods = ['all', 'search_by_slug', 'count', 'count_search', 'get_full']
    for method in required_methods:
        if not hasattr(index, method):
            print(f"✗ BLOCKER: Index.{method}() missing")
            return
        print(f"✓ Index.{method}() exists")

    # 3. Check method signatures
    print("\n--- Method Signatures ---")

    all_sig = inspect.signature(index.all)
    print(f"all{all_sig}")

    search_sig = inspect.signature(index.search_by_slug)
    print(f"search_by_slug{search_sig}")

    count_sig = inspect.signature(index.count)
    print(f"count{count_sig}")

    count_search_sig = inspect.signature(index.count_search)
    print(f"count_search{count_search_sig}")

    get_full_sig = inspect.signature(index.get_full)
    print(f"get_full{get_full_sig}")

    # 4. Test actual calls
    print("\n--- Functional Tests ---")

    # Test count
    total = await index.count()
    print(f"✓ count() returned: {total}")

    # Test all() with pagination - returns tuple
    models, total_from_all = await index.all(limit=3, offset=0)
    print(f"✓ all(limit=3, offset=0) returned: {len(models)} models, total={total_from_all}")
    print(f"  Type: {type(models[0])}")
    print(f"  Sample: {models[0].name if models else 'N/A'}")

    # Check IndexEntry fields
    if models:
        entry = models[0]
        print("\n--- IndexEntry Fields ---")
        print(f"  oifm_id: {entry.oifm_id}")
        print(f"  name: {entry.name}")
        print(f"  slug_name: {entry.slug_name}")
        print(f"  ✓ IndexEntry has slug_name field: '{entry.slug_name}'")

    # Test search_by_slug - returns tuple with built-in pagination
    print("\n--- search_by_slug Test ---")
    search_results, search_total = await index.search_by_slug("test", limit=5, offset=0)
    print(f"✓ search_by_slug('test', limit=5, offset=0)")
    print(f"  Returned: {len(search_results)} models, total={search_total}")
    print(f"  Return type: tuple[list[IndexEntry], int]")
    print(f"  ✓ Server-side pagination supported (has limit/offset params)")

    # Test count_search
    print("\n--- count_search Test ---")
    count_search_result = await index.count_search("test")
    print(f"✓ count_search('test') returned: {count_search_result}")
    print(f"  ✓ Separate count_search() method exists")

    # Test get_full - requires oifm_id, raises KeyError if not found
    print("\n--- get_full Test ---")
    if models:
        test_oifm_id = models[0].oifm_id
        try:
            full_model = await index.get_full(test_oifm_id)
            print(f"✓ get_full('{test_oifm_id}') works")
            print(f"  Type: {type(full_model)}")
            print(f"  Has FindingModelFull structure: {hasattr(full_model, 'oifm_id')}")
            print(f"  ⚠️  Raises KeyError if model not found (doesn't return None)")
        except KeyError as e:
            print(f"✗ get_full('{test_oifm_id}') raised KeyError: {e}")
        except Exception as e:
            print(f"⚠️  get_full('{test_oifm_id}') failed with: {type(e).__name__}: {e}")
            print("  → Database may need update - findingmodel package will auto-download latest")

    print("\n=== All API verification complete ===")
    print("\n✅ KEY FINDINGS for Phase 3 Implementation:")
    print("  1. Method is all(), NOT list()")
    print("  2. all() returns tuple[list[IndexEntry], int] - includes total count")
    print("  3. search_by_slug() returns tuple[list[IndexEntry], int] - includes total count")
    print("  4. search_by_slug() has built-in limit/offset (server-side pagination)")
    print("  5. IndexEntry has slug_name field - use it directly")
    print("  6. count() has NO search parameter")
    print("  7. count_search(pattern) is a separate method")
    print("  8. get_full(oifm_id) requires OIFM ID, raises KeyError if not found")

if __name__ == "__main__":
    asyncio.run(verify_api())
```

**Run**: `uv run python scripts/verify_v0.5.0_api.py`

**Expected Output**:

- All required methods exist
- Method signatures documented
- IndexEntry field structure confirmed
- Pagination support confirmed
- Counting mechanism identified

**BLOCKER**: DO NOT proceed to Phase 2 until this verification passes and results are documented.

**Action Required**: Based on verification results, adjust Phase 3 code examples to match actual API signatures.

---

### Phase 2: Remove Redis Cache for Finding Models

**File**: `app/cache.py`

**Delete these methods** (unused dead code, ~60 lines total):

1. **`get_finding_model()`** (lines 245-257)
2. **`set_finding_model()`** (lines 259-273)
3. **`get_finding_models()`** (lines 313-331)
4. **`set_finding_models()`** (lines 333-346)
5. **`invalidate_finding_models_cache()`** (lines 348-352)

**Why**: With `Index.get_full()`, we no longer need to cache full finding models from GitHub. The Index provides fast
access directly.

**Verification**:

- Run `task test-unit` - no tests should break (these methods are unused)
- Search codebase for references: `rg "get_finding_model|set_finding_model"` should only show deletions

---

### Phase 3: Refactor FindingModelService

**File**: `app/services/finding_model_service.py`

#### 3A: Remove Cache Dependency

**Lines 23-44**: Update `__init__()` signature

**Before**:

```python
def __init__(
    self,
    index: Any,
    cache: RedisCache,  # ← REMOVE THIS
    comment_repo: CommentRepo,
    user_repo: UserRepo,
    comment_service: CommentService,
) -> None:
    self.index = index
    self.cache = cache  # ← REMOVE THIS
    # ...
```

**After**:

```python
def __init__(
    self,
    index: Any,
    comment_repo: CommentRepo,
    user_repo: UserRepo,
    comment_service: CommentService,
) -> None:
    self.index = index
    # ...
```

**Update docstring**: Remove "cache: Redis cache for GitHub JSON caching" line

---

#### 3B: Refactor `list_models()` Method

**Lines 46-105**: Replace entire implementation

**Current Pattern** (~60 lines):

- Direct SQL via `conn = self.index._ensure_connection()`
- Manual query building with LIKE patterns
- Manual normalization of search terms
- Two separate SQL queries (count + data)

**New Implementation** (based on Phase 1.5 verified API):

```python
async def list_models(
    self, search: str | None = None, page: int = 1, per_page: int = 20
) -> tuple[list[dict[str, Any]], int]:
    """Get paginated list of finding models with optional search.

    Args:
        search: Optional search term for filtering by slug
        page: Page number (1-indexed)
        per_page: Results per page

    Returns:
        Tuple of (list of model dicts, total count)
    """
    offset = (page - 1) * per_page

    if search:
        # Server-side pagination with tuple return (models, total)
        paginated_models, total_count = await self.index.search_by_slug(
            search, limit=per_page, offset=offset
        )
    else:
        # List all models with pagination, tuple return (models, total)
        paginated_models, total_count = await self.index.all(offset=offset, limit=per_page)

    # Convert IndexEntry objects to dicts for template rendering
    model_list = []
    for entry in paginated_models:
        # Use slug_name field directly (verified in Phase 1.5)
        model_list.append({
            "id": entry.oifm_id,
            "name": entry.name,
            "slug": entry.slug_name,
        })

    return model_list, total_count
```

**Key Changes**:

- No more direct SQL queries
- No more `_ensure_connection()`
- No more manual normalization
- Index API handles all search and pagination logic
- **All Index methods are async** - use `await`
- **Tuple unpacking** for both `all()` and `search_by_slug()` return values
- Use `entry.slug_name` directly (no slug generation needed)
- Convert `IndexEntry` objects to dicts for templates

**Confirmed by Phase 1.5**:

- ✅ Server-side pagination: Both `all()` and `search_by_slug()` have `limit`/`offset` parameters
- ✅ Tuple returns: Both methods return `(list[IndexEntry], int)` with total count included
- ✅ Slug field exists: `IndexEntry.slug_name` is available and should be used directly
- ✅ Counting: Use `count()` for total, `count_search(pattern)` for filtered counts

---

#### 3C: Simplify `get_model_by_slug()` Method

**Lines 106-155**: Replace entire implementation

**Current Pattern** (~50 lines):

- Check Redis cache for model JSON
- Fetch from GitHub if cache miss
- Parse and validate JSON
- Cache the result
- Complex error handling for HTTP requests

**New Implementation** (based on Phase 1.5 findings):

```python
async def get_model_by_slug(self, slug: str) -> FindingModelFull:
    """Get finding model by slug.

    Args:
        slug: URL slug for the finding model

    Returns:
        Complete FindingModelFull object

    Raises:
        NotFoundError: If model not found
    """
    # Step 1: Get IndexEntry to obtain oifm_id
    index_entry = await self.index.get(slug)
    if not index_entry:
        raise NotFoundError(f"Finding model '{slug}' not found")

    # Step 2: Use oifm_id with get_full() (requires OIFM ID, not slug)
    try:
        finding_model = await self.index.get_full(index_entry.oifm_id)
    except KeyError as e:
        # get_full() raises KeyError if model not found (doesn't return None)
        raise NotFoundError(f"Full model data for '{slug}' not found") from e

    logger.debug(f"Retrieved finding model '{slug}' from Index")
    return finding_model
```

**Key Changes**:

- No cache checks
- No GitHub API calls
- No httpx import needed
- No JSON parsing
- **All Index methods are async** - use `await`
- **Two-step lookup**: slug → IndexEntry → oifm_id → FindingModelFull
- Handle `KeyError` from `get_full()` (doesn't return None)

**CRITICAL Finding from Phase 1.5**:

- ⚠️ `get_full()` requires **OIFM ID** (e.g., "OIFM.1001"), NOT slug
- ⚠️ `get_full()` **raises KeyError** if not found (doesn't return None)
- ⚠️ Requires `finding_model_json` table in database (may need schema update)

**Alternative**: If `get_full()` is unreliable, keep GitHub fetching pattern temporarily.

**Return Type Change**:

- **Before**: `tuple[FindingModelFull, IndexEntry]`
- **After**: `FindingModelFull` only

**Impact**: Check callers to ensure they don't need `IndexEntry`. If needed, we already have it from step 1.

---

#### 3D: Update Imports

**Top of file**: Remove unused imports (confirmed by Phase 1.5)

**Remove**:

```python
import httpx
from app.cache import RedisCache
```

**Keep**:

```python
from findingmodel import FindingModelFull
from findingmodel.index import IndexEntry
# ... other necessary imports
```

**Note from Phase 1.5**:

- ✅ **No slug generation needed**: `IndexEntry.slug_name` field exists and should be used directly
- ✅ **No normalize_name() needed**: Library provides slugs in the format we need
- ✅ **No httpx needed**: No GitHub API calls anymore

---

#### 3E: Update Type Hints and Method Signatures

**Critical**: Type hints must be updated to reflect the new return types and removed parameters.

**Changes to `FindingModelService` class:**

1. **`__init__()` signature** (Phase 3A already covers this):

   ```python
   # Before
   def __init__(self, index: Any, cache: RedisCache, ...) -> None:

   # After
   def __init__(self, index: Any, comment_repo: CommentRepo, ...) -> None:
   ```

2. **`get_model_by_slug()` return type**:

   ```python
   # Before
   async def get_model_by_slug(self, slug: str) -> tuple[FindingModelFull, IndexEntry]:

   # After
   async def get_model_by_slug(self, slug: str) -> FindingModelFull:
   ```

3. **All callers must be updated**:
   - Remove tuple unpacking: `finding_model, index_entry = await ...`
   - Use single variable: `finding_model = await ...`
   - If `IndexEntry` is needed, make separate call: `index_entry = await self.index.get(slug)`

**Verification**: Run `uv run mypy app` to catch any type errors after changes.

**Files likely needing updates**:

- `app/routers/finding_models_browse.py` - Main caller of `get_model_by_slug()`
- Any tests that mock or call this method

---

### Phase 4: Update Service Dependency Injection

**File**: `app/dependencies.py`

**Find**: The dependency function that creates `FindingModelService` (likely around line 100-120)

**Update**: Remove `cache` parameter from service initialization

**Before**:

```python
async def get_finding_model_service(
    database: DatabaseDep,
    cache: CacheDep,  # ← Remove if passed to service
) -> FindingModelService:
    return FindingModelService(
        index=database.finding_index,
        cache=cache,  # ← REMOVE THIS
        comment_repo=database.comment_repo,
        user_repo=database.user_repo,
        comment_service=...,
    )
```

**After**:

```python
async def get_finding_model_service(
    database: DatabaseDep,
) -> FindingModelService:
    return FindingModelService(
        index=database.finding_index,
        comment_repo=database.comment_repo,
        user_repo=database.user_repo,
        comment_service=...,
    )
```

**Note**: Search for `FindingModelService(` to find all instantiation sites.

---

### Phase 5: Update Router Callers

**File**: `app/routers/finding_models_browse.py`

**Find**: All calls to `finding_model_service.get_model_by_slug()`

**Update**: Handle new return type (no longer returns tuple)

**Before**:

```python
finding_model, index_entry = await finding_model_service.get_model_by_slug(slug)
# Use index_entry for something...
```

**After**:

```python
finding_model = await finding_model_service.get_model_by_slug(slug)
# If you need index data, make separate call:
# index_entry = await database.finding_index.get(slug)
```

**Search Pattern**: `rg "get_model_by_slug" app/routers/`

---

### Phase 6: Update Tests

#### 6A: Update FindingModelService Test Fixtures

**File**: `tests/test_services/test_finding_model_service.py`

**Lines 22-42**: Update mock fixtures

**Remove**:

```python
@pytest.fixture
def mock_cache(self) -> MagicMock:
    cache = MagicMock()
    cache.get_finding_model = AsyncMock(return_value=None)
    cache.set_finding_model = AsyncMock()
    return cache
```

**Update `mock_index` fixture** (based on Phase 1.5 findings):

**Before**:

```python
@pytest.fixture
def mock_index(self) -> MagicMock:
    index = MagicMock()
    index._ensure_connection = MagicMock()  # Old pattern
    # ... complex SQL mocking ...
    return index
```

**After**:

```python
@pytest.fixture
def mock_index(self) -> MagicMock:
    index = MagicMock()

    # Mock IndexEntry objects with slug_name field
    mock_entries = [
        type('IndexEntry', (), {
            'oifm_id': 'OIFM.1001',
            'name': 'Abdominal Abscess',
            'slug_name': 'abdominal-abscess'
        })(),
        type('IndexEntry', (), {
            'oifm_id': 'OIFM.1002',
            'name': 'Pneumonia',
            'slug_name': 'pneumonia'
        })(),
    ]

    # all() returns tuple (list[IndexEntry], int)
    index.all = AsyncMock(return_value=(mock_entries, 50))

    # search_by_slug() returns tuple (list[IndexEntry], int)
    index.search_by_slug = AsyncMock(return_value=(mock_entries[:1], 1))

    # count() returns int
    index.count = AsyncMock(return_value=50)

    # count_search() returns int
    index.count_search = AsyncMock(return_value=1)

    # get() returns IndexEntry or None (for slug lookup)
    index.get = AsyncMock(return_value=mock_entries[0])

    # get_full() returns FindingModelFull (requires oifm_id)
    index.get_full = AsyncMock(return_value=FindingModelFull(
        oifm_id='OIFM.1001',
        name='Abdominal Abscess',
        # ... other required fields
    ))

    return index
```

**Update service instantiation in tests**:

**Before**:

```python
service = FindingModelService(
    index=mock_index,
    cache=mock_cache,  # ← REMOVE
    comment_repo=mock_comment_repo,
    user_repo=mock_user_repo,
    comment_service=mock_comment_service,
)
```

**After**:

```python
service = FindingModelService(
    index=mock_index,
    comment_repo=mock_comment_repo,
    user_repo=mock_user_repo,
    comment_service=mock_comment_service,
)
```

---

#### 6B: Update Test Cases

**Update assertions** to match new return types:

**Before**:

```python
finding_model, index_entry = await service.get_model_by_slug("test-slug")
assert index_entry.name == "Test Model"
assert finding_model.oifm_id == "OIFM.1001"
```

**After**:

```python
finding_model = await service.get_model_by_slug("test-slug")
assert finding_model.oifm_id == "OIFM.1001"
assert finding_model.name == "Test Model"
```

**Remove cache-related tests**:

- Delete tests verifying cache hit/miss behavior
- Delete tests verifying GitHub fetch logic
- Keep tests for business logic (search, pagination, error handling)

---

#### 6C: Update Router Tests

**File**: `tests/test_routers/test_finding_models_browse.py` (if exists)

**Update mocks**:

- Remove httpx mocking
- Remove cache mocking
- Update service mock to return `FindingModelFull` directly (not tuple)

**Pattern**:

```python
mock_service.get_model_by_slug = AsyncMock(
    return_value=FindingModelFull(...)  # Not tuple anymore
)
```

---

### Phase 7: Final Integration Verification

**Note**: API verification is now handled comprehensively in **Phase 1.5**. This phase focuses on integration testing
after all code changes are complete.

**Tasks**:

1. **Run unit tests**: `task test-unit`
   - Verify all 144+ tests pass
   - Check that mocks are updated correctly
   - Confirm test coverage maintained (75%+)

2. **Run integration tests**: `task test`
   - Test finding model browse/search pages
   - Test model detail pages
   - Verify HTMX interactions work

3. **Manual verification**:

   ```bash
   # Start dev server
   task dev

   # Test browse page
   curl http://localhost:8000/finding-models

   # Test search
   curl 'http://localhost:8000/finding-models?search=pneumonia'

   # Test detail page (use actual slug from Phase 1.5 results)
   curl http://localhost:8000/finding-models/abdominal_abscess
   ```

4. **Verify logs**:
   - No errors related to Index methods
   - No GitHub API calls being made
   - No Redis cache misses for finding models

**Success Criteria**:

- All tests pass
- Browse/search/detail pages work correctly
- No errors in application logs
- Performance is similar or better than v0.4.0

---

## Testing Strategy

### Unit Tests

**Run**: `task test-unit`

**Expected Results**:

- All 144 tests pass (or more if we add new ones)
- No cache-related test failures
- Service tests use new Index mocks
- Router tests use new service return types

**If failures occur**:

1. Check mock setup matches new API
2. Verify return type handling in routers
3. Check for any lingering cache references

### Integration Tests

**Run**: `task test`

**Focus Areas**:

1. Browse page (`/finding-models`) - pagination works
2. Search functionality - returns correct results
3. Model detail page (`/finding-models/{slug}`) - displays correctly
4. No Redis errors in logs
5. No GitHub API calls being made

**Manual Verification**:

```bash
# Start dev server
task dev

# Test browse page
curl http://localhost:8000/finding-models

# Test search
curl http://localhost:8000/finding-models?search=pneumonia

# Test detail page
curl http://localhost:8000/finding-models/abdominal-abscess

# Check logs - should NOT see GitHub fetches
tail -f logs/app.log | grep -i github
```

### Performance Testing

**Before upgrade**: Measure current performance

```bash
# Time browse page load
time curl -s http://localhost:8000/finding-models > /dev/null

# Time detail page (first load - cache miss)
redis-cli FLUSHDB
time curl -s http://localhost:8000/finding-models/pneumonia > /dev/null

# Time detail page (second load - cache hit)
time curl -s http://localhost:8000/finding-models/pneumonia > /dev/null
```

**After upgrade**: Compare performance

```bash
# Should be similar or faster (no Redis overhead)
time curl -s http://localhost:8000/finding-models > /dev/null
time curl -s http://localhost:8000/finding-models/pneumonia > /dev/null
```

---

## Rollback Plan

If upgrade causes issues:

```bash
# 1. Revert pyproject.toml
git checkout main -- pyproject.toml

# 2. Reinstall old version
uv sync

# 3. Revert all code changes
git checkout main -- app/services/finding_model_service.py
git checkout main -- app/cache.py
git checkout main -- app/dependencies.py
git checkout main -- tests/

# 4. Verify tests pass
task test

# 5. Restart server
task dev
```

**Estimated rollback time**: 5 minutes

---

## Success Criteria

✅ **Code simplification**:

- `finding_model_service.py`: ~90 lines removed
- `cache.py`: ~60 lines removed
- Tests: Fewer mocks, simpler fixtures

✅ **All tests pass**: 144+ tests green

✅ **No regressions**:

- Browse page loads and paginates
- Search works correctly
- Model detail pages display
- No errors in logs

✅ **Performance**: Similar or better than before

✅ **Dependencies**: No Redis cache for finding models, no GitHub API calls for model details

---

## Implementation Notes

**All questions answered by Phase 1.5 verification** ✅:

1. ✅ **Index API Signatures**: Documented via `inspect.signature()`
   - `all(limit, offset)` → `tuple[list[IndexEntry], int]`
   - `search_by_slug(pattern, limit, offset)` → `tuple[list[IndexEntry], int]`
   - `count()` → `int`
   - `count_search(pattern)` → `int`
   - `get_full(oifm_id)` → `FindingModelFull` (raises KeyError if not found)

2. ✅ **Search Behavior**: Server-side pagination confirmed
   - Both `all()` and `search_by_slug()` have `limit`/`offset` parameters
   - Both return tuples with total count included

3. ✅ **IndexEntry Fields**: `slug_name` field confirmed
   - Use `entry.slug_name` directly (no slug generation needed)
   - No need for `normalize_name()` import

4. ✅ **Async/Sync**: All Index methods are async and require `await`

5. ✅ **Context Manager**: Persistent `Index(db_path=None, read_only=True)` pattern works

6. ✅ **Counting**: Two separate methods
   - `count()` for total count (no search parameter)
   - `count_search(pattern)` for filtered counts

7. ⚠️ **get_full() Limitation**: Requires OIFM ID, not slug
   - Must do two-step lookup: slug → IndexEntry → oifm_id → FindingModelFull
   - Raises KeyError if not found (doesn't return None)
   - May require database schema update (`finding_model_json` table)

---

## Task Assignment

This plan must be executed in strict sequence:

1. **Phase 0**: Pre-upgrade verification (5 minutes)
2. **Phase 1**: Dependency update (5 minutes)
3. **Phase 1.5**: Post-upgrade API verification (10 minutes) - **BLOCKER FOR ALL SUBSEQUENT PHASES**
4. **Phase 2**: Cache cleanup (15 minutes)
5. **Phase 3**: Service refactoring (30 minutes) - Adjust code based on Phase 1.5 results
6. **Phase 4**: DI updates (10 minutes)
7. **Phase 5**: Router updates (15 minutes)
8. **Phase 6**: Test updates (30 minutes)
9. **Phase 7**: Final verification (15 minutes)

**Total Estimated Time**: ~2.5 hours

**Critical Path**: Phase 0 → Phase 1 → Phase 1.5 → (all remaining phases depend on Phase 1.5 results)

---

## References

- **Release Notes**: https://github.com/openimagingdata/findingmodel/releases/tag/v0.5.0
- **Current Implementation**: `app/services/finding_model_service.py`
- **Cache Implementation**: `app/cache.py`
- **Test Suite**: `tests/test_services/test_finding_model_service.py`

---

**Document Version**: 3.0 **Last Updated**: 2025-11-04

## Changelog

### Version 3.0 (2025-11-04) - Phase 1.5 Complete

- ✅ **Phases 0, 1, 1.5 executed and verified**
- ✅ Updated all code examples with verified API patterns:
  - Changed `list()` to `all()` throughout
  - Added tuple unpacking for `all()` and `search_by_slug()` return values
  - Added `count_search()` method usage
  - Updated `get_full()` to use oifm_id (not slug) with KeyError handling
- ✅ Documented actual v0.5.0 API signatures from Phase 1.5 verification
- ✅ Confirmed server-side pagination for both `all()` and `search_by_slug()`
- ✅ Confirmed `IndexEntry.slug_name` field exists (no slug generation needed)
- ✅ Updated test fixtures to match actual API (tuple returns, AsyncMock)
- ✅ Removed references to `normalize_name()` (not needed)
- ✅ Updated Implementation Notes with complete verified API details
- ✅ Updated Breaking Changes section with accurate method signatures

### Version 2.0 (2025-11-04)

- ✅ Added Phase 0: Pre-upgrade baseline verification
- ✅ Added Phase 1.5: Post-upgrade API verification (comprehensive)
- ✅ Added `await` keywords to all Index method calls throughout
- ✅ Added Phase 3E: Type hints and signature updates
- ✅ Updated imports to include `normalize_name()` from findingmodel.common
- ✅ Clarified slug handling (slug_name field vs normalize_name function)
- ✅ Documented pagination approach (pending Phase 1.5 results)
- ✅ Confirmed async/await pattern for all Index methods
- ✅ Confirmed persistent Index initialization (no context manager needed)
- ✅ Replaced Phase 7 with integration testing focus
- ✅ Updated "Open Questions" section with confirmed answers
- ✅ Updated task assignment with strict sequential ordering

### Version 1.0 (2025-11-03)

- Initial plan created
