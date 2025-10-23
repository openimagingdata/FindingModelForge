# Contributor Repository Pattern

## Status: ✅ COMPLETE (October 22, 2025)

**Branch**: `feature/contributor-repos-refactor`

## Overview

Implemented Repository pattern to separate canonical contributors (Index) from draft contributors (MongoDB). This architectural change prepares for findingmodel's Index backend transition from MongoDB to DuckDB while maintaining clean abstraction boundaries.

## Architecture

### Dual-Source Repository Pattern

```
Application Code
    ↓
Repository Layer (PeopleRepo, OrganizationRepo)
    ↓
    ├── Index (read-only, canonical) - Abstracts backend (DuckDB in 0.4.0+)
    └── MongoDB (write, drafts) - draft_people, draft_organizations collections
```

### Key Principles

1. **Index Abstraction**: Application code NEVER mentions DuckDB. The `Index` class from `findingmodel` package abstracts the storage backend.
2. **Read-Only Index**: Index is canonical source, never written to. All writes go to MongoDB draft collections.
3. **Lazy Loading**: Index data loaded on first access, cached in-memory for O(1) lookups.
4. **Lookup Precedence**: Cache → Index (canonical) → MongoDB (drafts) → None

## Implementation

### Repository Classes

**Location**: `app/repositories/`

**PeopleRepo** (`app/repositories/people_repo.py`):
- Manages `Person` contributors
- Key method: `get_by_username(username: str) -> Person | None`
- Creates draft persons: `ensure_for_user(user: User) -> Person`
- Keyed by `github_username`

**OrganizationRepo** (`app/repositories/organization_repo.py`):
- Manages `Organization` contributors
- Key method: `get_by_code(code: str) -> Organization | None`
- Keyed by organization `code`

**Both Repos Share**:
- Internal dict cache: `_cache: dict[str, T]`
- Lazy loading flag: `_index_loaded: bool`
- Cache management: `clear_cache() -> None`
- Async patterns throughout

### Database Integration

**Location**: `app/database.py`

**Changes**:
- Removed: `self.people: dict[str, Person]` and `self.organizations: dict[str, Organization]`
- Added: `self.people_repo: PeopleRepo` and `self.org_repo: OrganizationRepo`
- Initialization in `connect()`:
  ```python
  self.people_repo = PeopleRepo(
      index=self.finding_index,
      draft_collection=self.db.draft_people
  )
  self.org_repo = OrganizationRepo(
      index=self.finding_index,
      draft_collection=self.db.draft_organizations
  )
  ```
- Simplified `ensure_person_for_user()` to delegate to `people_repo.ensure_for_user()`

### Usage Pattern

**Old (removed)**:
```python
author = database.people.get(username)  # Dict lookup
```

**New (current)**:
```python
author = await database.people_repo.get_by_username(username)  # Async repo call
```

**Files Updated**:
- `app/main.py:59` - Updated logging message
- `app/routers/drafts/helpers.py:351` - Updated author lookup with safety assertion
- `app/services/creation_service.py:176` - Updated author lookup with safety check

## Cache Strategy

**In-Memory Dict Cache** (not Redis):
- Fast O(1) lookups (~1000x faster than Redis)
- Small dataset (< 1MB for thousands of contributors)
- Cleared on Index reload: `await repo.clear_cache()`
- Lazy loading: Index data loaded only on first `get_by_username()` call

**Why Not Redis?**:
- Contributors dataset is small and rarely changes
- In-memory cache matches existing Database pattern
- No network overhead for every lookup
- Simpler code, fewer dependencies

## Testing

**Test Suite**: `tests/test_repositories/`

**PeopleRepo Tests** (11 tests, 100% coverage):
- Dual-source lookup (cache, Index, MongoDB)
- Precedence (Index beats MongoDB)
- User creation (writes to MongoDB only)
- Write isolation (verifies no Index writes)
- Cache behavior (lazy loading, clearing)

**OrganizationRepo Tests** (8 tests, 100% coverage):
- Dual-source lookup (cache, Index, MongoDB)
- Precedence (Index beats MongoDB)
- Cache behavior (lazy loading, clearing)

**Test Results**: 517/517 passing (100%), 6 skipped (pre-existing)

**Updated Test Files** (7 files):
- `tests/test_routers/test_generate_finding_model_json.py`
- `tests/test_finding_models_comprehensive.py`
- `tests/test_database_integration.py`
- `tests/test_public_draft_feature.py`
- `tests/test_resume_logic.py`
- `tests/test_services/test_creation_service.py`
- `tests/test_services/test_draft_service.py`

**Mock Pattern**:
```python
# Old (dict mock)
mock_database.people = {}
mock_database.people["user"] = mock_person

# New (async repo mock)
mock_database.people_repo = AsyncMock()
mock_database.people_repo.get_by_username = AsyncMock(return_value=mock_person)
```

## Migration Strategy

**Lazy Migration** (no data migration required):
- New `draft_people` and `draft_organizations` collections start empty
- Existing Index data remains canonical source
- As users interact, draft entries created as needed
- No risky upfront data migration

## Benefits

1. **Abstraction**: Application isolated from Index backend changes (MongoDB → DuckDB)
2. **Read-Only Canonical**: Index treated as immutable source of truth
3. **Write Isolation**: Clear separation between canonical (Index) and draft (MongoDB) data
4. **Performance**: O(1) in-memory cache for fast lookups
5. **Type Safety**: Full type hints, mypy clean
6. **Testability**: Pure unit tests with 100% coverage
7. **Maintainability**: Clear separation of concerns, repository pattern

## Future Considerations

**Index Updates**: When Index reloads with new data:
```python
await database.people_repo.clear_cache()
await database.org_repo.clear_cache()
```

**Cache Warming** (optional): Could pre-populate cache on startup if beneficial

**Redis Migration** (optional): Repository interface supports swapping cache backend later if needed

## Related Work

- **Blocks**: None (but prepares for findingmodel 0.4.0+ DuckDB backend)
- **Dependencies**: findingmodel 0.4.0+ (DuckDB-based Index)
- **Related Patterns**: Repository pattern, Dual-source lookup, Lazy loading

## Files Created/Modified

**Created**:
- `app/repositories/__init__.py`
- `app/repositories/people_repo.py`
- `app/repositories/organization_repo.py`
- `tests/test_repositories/__init__.py`
- `tests/test_repositories/test_people_repo.py`
- `tests/test_repositories/test_organization_repo.py`

**Modified**:
- `app/database.py` (removed dicts, added repos)
- `app/main.py` (updated logging)
- `app/routers/drafts/helpers.py` (updated author lookup)
- `app/services/creation_service.py` (updated author lookup)
- 7 test files (updated mocks to async repo pattern)

**Statistics**:
- Lines added: ~900
- Lines removed: ~150
- Net change: +750 lines (including comprehensive tests)
- Test coverage: 100% for repository modules

---

**Document Owner**: @talkasab
**Last Updated**: 2025-10-22
