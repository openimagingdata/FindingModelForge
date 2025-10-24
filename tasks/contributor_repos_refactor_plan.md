# Contributor Repository Refactor: Index + MongoDB Dual-Source Pattern

**Status**: 🟢 Ready to Implement (findingmodel 0.4.0 verified) **Created**: 2025-10-22 **Updated**: 2025-10-22
**Branch**: `feature/contributor-repos-refactor` **Goal**: Separate canonical contributors (Index) from draft
contributors (MongoDB) using Repository pattern

**🔑 Key Principle**: Never reference DuckDB in application code. The `Index` class from `findingmodel` abstracts the
storage backend.

## ✅ Verification Complete

**findingmodel 0.4.0 Upgrade Status**: ✅ COMPLETE

- ✅ Upgraded to findingmodel 0.4.0 (DuckDB-based Index)
- ✅ Fixed all imports: `from findingmodel import Index` (not `from findingmodel.index import Index`)
- ✅ Updated `Database.connect()` to use new `Index(db_path=None, read_only=True)` constructor
- ✅ Updated `_load_people_and_organizations()` to use `get_people()` and `get_organizations()`
- ✅ Updated `ensure_person_for_user()` to use `get_person()` and write to `draft_people` collection (temporary)
- ✅ All unit tests passing (144 tests, 6 skipped)

**Index API Confirmed**: All methods documented and verified in Block 1, deliverable 4.

---

## Problem Statement

### Current Architecture

- `Database` class uses in-memory dicts: `self.people`, `self.organizations`
- Loads from MongoDB via `finding_index.people_collection` on startup
- `ensure_person_for_user()` writes to MongoDB, treating Index as application data
- **Issue**: Index conceptually should be read-only canonical data, not writable application data

### Future Architecture (with Index backend change)

- **Index** (via `findingmodel` package): Read-only canonical contributors (backend: DuckDB in future, MongoDB
  currently)
- **MongoDB `draft_people`/`draft_organizations`**: Writable draft contributors not yet published
- **Need**: Dual-source lookup that checks both, writes only to MongoDB draft collections
- **Important**: Application code should never know about DuckDB - that's Index's internal implementation detail

---

## Solution Design

### Architecture

```
┌─────────────────────────────────────────┐
│     Application Layer                   │
│  (Routers, Services access via repos)   │
└─────────────┬───────────────────────────┘
              │
       ┌──────┴──────┐
       │  Repository │
       │   Pattern   │
       └──────┬──────┘
              │
    ┌─────────┴──────────┐
    │                    │
┌───▼────┐        ┌──────▼─────┐
│ Index  │        │  MongoDB   │
│ (read) │        │  (write)   │
│Canonical│        │draft_people│
│Abstract │        │draft_orgs  │
└────────┘        └────────────┘
   │
   └─ Hides backend (DuckDB/MongoDB)
```

### Repository Responsibilities

**PeopleRepo:**

- Lookup precedence: In-memory cache → Index (canonical) → MongoDB (drafts)
- **Index abstraction**: Never mention DuckDB - Index class hides the backend
- Write operations: Only to MongoDB `draft_people` collection (Index is read-only)
- Methods: `get_by_username()`, `ensure_for_user()`, `clear_cache()`

**OrganizationRepo:**

- Same pattern, keyed by organization code
- Methods: `get_by_code()`, `clear_cache()`

**Key Design Principle**: The application should never know about DuckDB. The `Index` class from `findingmodel` package
abstracts the storage backend. Our repos just read from Index (canonical) and write to MongoDB (drafts).

### Cache Strategy

- **In-memory** cache (not Redis) - matches current pattern
- Fast lookups (~1000x faster than Redis)
- Small dataset (< 1MB for thousands of contributors)
- Clear on Index reload when new version loads (Index handles backend transitions)

---

## Implementation Plan

### ✅ Block 1: Create Repository Infrastructure

**Status**: ⬜ Not Started **Owner**: TBD **Files**: New files in `app/repositories/`

#### Current Abstraction Violations to Fix

**Problem**: We're currently violating the Index abstraction by accessing MongoDB-specific collections:

- `finding_index.people_collection.find()` (line 65)
- `finding_index.organizations_collection.find()` (line 70)
- `finding_index.people_collection.find_one()` (line 92)
- `finding_index.people_collection.insert_one()` (line 112) ⚠️ **Writing to Index!**

**Why this is bad**:

- We're treating Index as if it's MongoDB-specific
- We're **writing** to Index (should be read-only!)
- When Index moves to DuckDB backend, this all breaks

**Correct approach**:

- Read from `index.people` and `index.organizations` (if Index exposes these)
- NEVER write to Index - it's canonical data
- Write draft contributors to separate `draft_people`/`draft_organizations` collections

#### Deliverables

1. **`app/repositories/__init__.py`**

   ```python
   from .people_repo import PeopleRepo
   from .organization_repo import OrganizationRepo

   __all__ = ["PeopleRepo", "OrganizationRepo"]
   ```

2. **`app/repositories/people_repo.py`**

   ```python
   from typing import Any
   from motor.motor_asyncio import AsyncIOMotorCollection
   from findingmodel.contributor import Person
   from findingmodel.index import Index
   from app.models import User

   class PeopleRepo:
       """Repository for Person contributors with dual-source lookup.

       Reads from Index (canonical, backend-agnostic) and MongoDB (drafts).
       Never writes to Index - it's read-only canonical data.
       """

       def __init__(
           self,
           index: Index,
           draft_collection: AsyncIOMotorCollection[Any]
       ):
           self.index = index  # Read-only canonical source (abstracts backend)
           self.draft_people = draft_collection  # Writable drafts
           self._cache: dict[str, Person] = {}
           self._index_loaded = False  # Track if we've loaded from Index

       async def get_by_username(self, username: str) -> Person | None:
           """Get Person by github_username.

           Lookup order: cache → Index (canonical) → MongoDB (drafts) → None

           Note: Index class hides whether it's using DuckDB, MongoDB, or other backend.
           We call index.get_people() and cache the results.
           """
           # 1. Check cache
           if username in self._cache:
               return self._cache[username]

           # 2. Load from Index if not cached yet (canonical source, takes precedence)
           # Index provides get_people() -> list[Person]
           # We load into cache on first access for O(1) lookups
           if not self._index_loaded:
               await self._load_from_index()

           if username in self._cache:
               return self._cache[username]

           # 3. Check MongoDB (draft contributors not yet in Index)
           doc = await self.draft_people.find_one({"github_username": username})
           if doc:
               person = Person.model_validate(doc)
               self._cache[username] = person
               return person

           return None

       async def _load_from_index(self) -> None:
           """Load all people from Index into cache."""
           for person in self.index.get_people():
               self._cache[person.github_username] = person
           self._index_loaded = True

       async def ensure_for_user(self, user: User) -> Person:
           """Get or create Person for User.

           Writes only to MongoDB draft_people collection.
           Index is read-only - we never write to it.
           """
           # Check if exists in Index or drafts
           if person := await self.get_by_username(user.login):
               return person

           # Create new draft person (MongoDB only, never Index)
           person_data = {
               "github_username": user.login,
               "email": user.email or f"{user.login}@users.noreply.github.com",
               "name": user.name or user.login,
               "organization_code": "INDV",  # Individual by default
               "url": user.html_url,
           }
           await self.draft_people.insert_one(person_data)

           person = Person.model_validate(person_data)
           self._cache[user.login] = person
           return person

       async def clear_cache(self) -> None:
           """Clear cache (e.g., when Index reloads with new data)."""
           self._cache.clear()
           self._index_loaded = False  # Force reload from Index on next access
   ```

3. **`app/repositories/organization_repo.py`**

   ```python
   from typing import Any
   from motor.motor_asyncio import AsyncIOMotorCollection
   from findingmodel.contributor import Organization
   from findingmodel.index import Index

   class OrganizationRepo:
       """Repository for Organization contributors with dual-source lookup."""

       def __init__(
           self,
           index: Index,
           draft_collection: AsyncIOMotorCollection[Any]
       ):
           self.index = index  # Read-only canonical source
           self.draft_organizations = draft_collection  # Writable drafts
           self._cache: dict[str, Organization] = {}
           self._index_loaded = False  # Track if we've loaded from Index

       async def get_by_code(self, code: str) -> Organization | None:
           """Get Organization by code.

           Lookup order: cache → Index (canonical) → MongoDB (drafts) → None
           """
           # 1. Check cache
           if code in self._cache:
               return self._cache[code]

           # 2. Load from Index if not cached yet (canonical source)
           # Index provides get_organizations() -> list[Organization]
           if not self._index_loaded:
               await self._load_from_index()

           if code in self._cache:
               return self._cache[code]

           # 3. Check MongoDB (draft organizations not yet in Index)
           doc = await self.draft_organizations.find_one({"code": code})
           if doc:
               org = Organization.model_validate(doc)
               self._cache[code] = org
               return org

           return None

       async def _load_from_index(self) -> None:
           """Load all organizations from Index into cache."""
           for org in self.index.get_organizations():
               self._cache[org.code] = org
           self._index_loaded = True

       async def clear_cache(self) -> None:
           """Clear cache (e.g., when Index reloads with new data)."""
           self._cache.clear()
           self._index_loaded = False  # Force reload from Index on next access
   ```

4. **✅ CONFIRMED: Index API (v0.4.0 - DuckDB-based)**

   **Status**: ✅ Verified with findingmodel 0.4.0

   **The `Index` class (actually `DuckDBIndex`) provides:**
   - **Import**: `from findingmodel import Index` (exports `DuckDBIndex` as `Index`)
   - **Constructor**: `Index(db_path: str | Path | None = None, *, read_only: bool = True)`
     - `db_path=None` uses default location from findingmodel package
     - `read_only=True` enforces read-only access (perfect for our use case)
   - **People methods**:
     - `get_people() → list[Person]` - Returns all people
     - `get_person(github_username: str) → Person | None` - Get single person by username
     - `count_people() → int` - Count total people
   - **Organization methods**:
     - `get_organizations() → list[Organization]` - Returns all organizations
     - `get_organization(code: str) → Organization | None` - Get single org by code
     - `count_organizations() → int` - Count total organizations
   - **Index methods**:
     - `get(identifier: str) → IndexEntry | None` - Get finding model by ID
     - `contains(identifier: str) → bool` - Check if finding model exists
     - `search(query: str, *, limit: int = 10) → list[IndexEntry]` - Search finding models

   **Our approach**: Load these into our repository's internal dict cache:

   ```python
   # In PeopleRepo.__init__ or lazy-load method
   async def _load_from_index(self) -> None:
       """Load people from Index into cache."""
       for person in self.index.get_people():
           self._cache[person.github_username] = person
   ```

   **Why not use dict directly?**
   - Index returns lists (not dicts keyed by username/code)
   - We need fast O(1) username/code lookups
   - Our cache provides this with merged Index + MongoDB data

   **Lazy-loading pattern:**
   - Don't load Index data until first `get_by_username()` call
   - Use `_index_loaded` flag to track if we've loaded
   - This avoids blocking startup with Index loading
   - `clear_cache()` resets flag to force reload when Index updates

   **Key Change from 0.3.x**:
   - ❌ OLD: `Index(client=motor_client, db_name="...")` - MongoDB-backed
   - ✅ NEW: `Index(db_path=None, read_only=True)` - DuckDB-backed
   - ❌ OLD: Had `.people_collection`, `.organizations_collection` (MongoDB)
   - ✅ NEW: Has `.get_people()`, `.get_organizations()` (DuckDB abstraction)

---

### ✅ Block 2: Update Database Class

**Status**: ⬜ Not Started **Owner**: TBD **Files**: `app/database.py`

#### Changes Required

1. **Add imports**:

   ```python
   from .repositories import PeopleRepo, OrganizationRepo
   ```

2. **Modify `Database.__init__`** (lines 34-42):

   ```python
   def __init__(self) -> None:
       self.client: AsyncIOMotorClient[Any] | None = None
       self.db: AsyncIOMotorDatabase[Any] | None = None
       self.user_repo: UserRepo | None = None
       self.draft_repo: DraftRepo | None = None
       self.comment_repo: CommentRepo | None = None
       self.finding_index: Index | None = None
       self.people_repo: PeopleRepo | None = None        # NEW
       self.org_repo: OrganizationRepo | None = None     # NEW
       # REMOVE: self.people and self.organizations dicts
   ```

3. **Modify `Database.connect()`** (lines 44-60):

   ```python
   async def connect(self) -> None:
       """Connect to MongoDB."""
       self.client = AsyncIOMotorClient(settings.mongodb_uri)
       self.db = self.client[settings.mongodb_db]
       self.user_repo = UserRepo(self.db)
       self.draft_repo = DraftRepo(self.db)
       self.comment_repo = CommentRepo(self.db)

       # Initialize finding index
       self.finding_index = Index(client=self.client, db_name=settings.mongodb_db)

       # Initialize contributor repositories
       # NOTE: Index abstracts the backend - could be DuckDB, MongoDB, etc.
       # We just read from it, never write to it.
       self.people_repo = PeopleRepo(
           index=self.finding_index,  # Read-only canonical source
           draft_collection=self.db.draft_people  # Writable drafts
       )
       self.org_repo = OrganizationRepo(
           index=self.finding_index,
           draft_collection=self.db.draft_organizations
       )

       # Create indices for comment threads
       comment_threads = self.db.comment_threads
       await comment_threads.create_index([("reference_type", 1), ("reference_id", 1)], unique=True)
       await comment_threads.create_index([("reported_count", -1)])

       # REMOVE: await self._load_people_and_organizations()
   ```

4. **Replace `ensure_person_for_user()`** (lines 75-119):

   ```python
   async def ensure_person_for_user(self, user: "User") -> Person:
       """Create or get a Person for a User.

       Args:
           user: User object to create/get Person for

       Returns:
           Person object (existing or newly created)
       """
       if not self.people_repo:
           raise RuntimeError("People repository not initialized")

       return await self.people_repo.ensure_for_user(user)
   ```

5. **Update `disconnect()`** (lines 121-128):

   ```python
   async def disconnect(self) -> None:
       """Disconnect from MongoDB."""
       if self.client:
           self.client.close()
       self.user_repo = None
       self.draft_repo = None
       self.comment_repo = None
       self.finding_index = None
       self.people_repo = None    # NEW
       self.org_repo = None       # NEW
   ```

6. **DELETE** `_load_people_and_organizations()` method (lines 62-73)

---

### ✅ Block 3: Update Application Code

**Status**: ⬜ Not Started **Owner**: TBD **Files**: 3 files accessing `db.people`

#### Changes Required

1. **`app/main.py:59`** - Update logging:

   ```python
   # OLD:
   logger.info(f"Loaded {len(database.people)} people and {len(database.organizations)} organizations into memory")

   # NEW:
   logger.info(f"Initialized contributor repositories (people_repo, org_repo)")
   ```

2. **`app/routers/drafts/helpers.py:350`** - Update author lookup:

   ```python
   # OLD:
   author = database.people.get(current_user.login)

   # NEW:
   author = await database.people_repo.get_by_username(current_user.login)
   ```

   **Note**: Function signature must change to `async` if not already!

3. **`app/services/creation_service.py:174`** - Update author lookup:

   ```python
   # OLD:
   author = self.database.people.get(user.login)

   # NEW:
   author = await self.database.people_repo.get_by_username(user.login)
   ```

**Important**: Calls to `ensure_person_for_user()` don't need changes (interface stays the same).

---

### ✅ Block 4: Update Test Infrastructure

**Status**: ⬜ Not Started **Owner**: TBD **Files**: Multiple test files

#### Test Files Requiring Updates

1. **`tests/conftest.py`**
   - Update fixtures to mock repos instead of dicts
   - Add `mock_people_repo` and `mock_org_repo` fixtures

2. **`tests/test_database_integration.py`**
   - Lines 77-78, 141-150: Replace `db.people`/`db.organizations` dict assertions
   - Update to check repo cache or call repo methods

3. **`tests/test_finding_models_comprehensive.py`**
   - Lines 77-80: Replace `db.people = {}` with `db.people_repo = Mock(spec=PeopleRepo)`
   - Lines 1215-1216: Update mock to use `get_by_username()`

4. **`tests/test_public_draft_feature.py`**
   - Line 96: Replace `db.people = {}` with repo mock

5. **`tests/test_resume_logic.py`**
   - Lines 32-33: Replace dict mocks with repo mocks

6. **`tests/test_routers/test_generate_finding_model_json.py`**
   - Lines 48, 147, 237, 296, 355: Replace `db.people.get()` with `db.people_repo.get_by_username()`

7. **`tests/test_services/test_creation_service.py`**
   - Lines 31, 36: Replace dict mock with repo mock

8. **`tests/test_services/test_draft_service.py`**
   - Line 44: Replace `db.people = {}` with repo mock

#### Mock Pattern

```python
# OLD pattern
mock_db.people = {}
mock_db.people["testuser"] = mock_person

# NEW pattern
mock_people_repo = Mock(spec=PeopleRepo)
mock_people_repo.get_by_username = AsyncMock(return_value=mock_person)
mock_db.people_repo = mock_people_repo
```

---

### ✅ Block 5: Add Repository Tests

**Status**: ⬜ Not Started **Owner**: TBD **Files**: New test files

#### Test Files to Create

1. **`tests/test_repositories/__init__.py`** (empty)

2. **`tests/test_repositories/test_people_repo.py`**

   **Test scenarios**:
   - `test_get_by_username_from_cache` - Cache hit returns immediately
   - `test_get_by_username_from_duckdb` - DuckDB lookup works, caches result
   - `test_get_by_username_from_mongodb` - MongoDB lookup works, caches result
   - `test_get_by_username_precedence` - DuckDB beats MongoDB if both exist
   - `test_get_by_username_not_found` - Returns None if not in any source
   - `test_ensure_for_user_existing` - Returns existing person
   - `test_ensure_for_user_creates_new` - Creates in MongoDB, caches
   - `test_ensure_for_user_never_writes_duckdb` - Verify no DuckDB writes
   - `test_clear_cache` - Cache clearing works

3. **`tests/test_repositories/test_organization_repo.py`**

   **Test scenarios**:
   - Similar pattern to PeopleRepo tests
   - `test_get_by_code_from_cache`
   - `test_get_by_code_from_duckdb`
   - `test_get_by_code_from_mongodb`
   - `test_get_by_code_precedence`
   - `test_get_by_code_not_found`
   - `test_clear_cache`

#### Test Fixture Setup

```python
@pytest.fixture
async def people_repo(mock_duckdb_index, mongodb_collection):
    """Create PeopleRepo with mocked sources."""
    return PeopleRepo(
        duckdb_index=mock_duckdb_index,
        draft_collection=mongodb_collection
    )
```

---

## Migration Strategy

### Handling Existing Data

**Current state**:

- People/organizations exist in MongoDB via `finding_index.people_collection`
- These are mixed with canonical Index data

**Migration approach**: **Lazy Migration**

1. Don't migrate data upfront
2. New `draft_people` collection starts empty
3. As users interact with the app, create entries in `draft_people` as needed
4. Eventually deprecate writes to `finding_index.people_collection`

**Benefits**:

- No risky data migration step
- Gradual transition
- Can run both systems in parallel temporarily

---

## Success Criteria

### Functional Requirements

- ✅ All existing tests pass (144 tests)
- ✅ Dual-source lookup works correctly (DuckDB → MongoDB precedence)
- ✅ Writes only go to MongoDB, never DuckDB (read-only enforced)
- ✅ Cache improves performance (sub-millisecond lookups)
- ✅ `ensure_person_for_user()` creates draft contributors correctly

### Non-Functional Requirements

- ✅ Type hints throughout, `mypy` clean
- ✅ No breaking changes to existing API contracts
- ✅ Clear separation of concerns (canonical vs draft data)
- ✅ Maintainable repository pattern following existing conventions

### Test Coverage

- ✅ New repository unit tests (18+ tests)
- ✅ Integration tests updated for new architecture
- ✅ All mocks properly updated

---

## Rollout Plan

### Phase 1: Implementation

1. Complete Blocks 1-3 (new repos, update Database class, update app code)
2. Run unit tests to verify basic functionality
3. Update test infrastructure (Block 4)
4. Verify all existing tests pass

### Phase 2: Testing

1. Add new repository tests (Block 5)
2. Run full test suite (`task test`)
3. Manual testing of draft creation workflow
4. Verify contributor display works correctly

### Phase 3: Deployment

1. Merge to `dev` branch
2. Deploy to staging environment
3. Verify DuckDB read-only constraint (when DuckDB is implemented)
4. Deploy to production

---

## Notes & Open Questions

### Design Decisions

- ✅ **Abstraction layer**: Use Index class, never reference DuckDB directly
- ✅ **Cache strategy**: In-memory (not Redis) - matches current pattern, simpler
- ✅ **Lookup precedence**: Index (canonical) before MongoDB (drafts) - canonical source wins
- ✅ **Write isolation**: MongoDB only - Index is read-only
- ✅ **Migration**: Lazy creation - no risky upfront data migration

### Critical Requirements

- 🔴 **NEVER mention DuckDB** in application code - that's Index's internal detail
- 🔴 **NEVER write to Index** - it's read-only canonical data
- ✅ **Index API confirmed**: `get_people() → list[Person]` and `get_organizations() → list[Organization]`

### Future Considerations

- **Index updates**: When new Index version loads (with updated backend), call `clear_cache()` on repos
- **Cache warming**: Could pre-populate cache from Index on startup if beneficial
- **Redis migration**: Repository interface supports swapping cache backend later if needed

### Related Work

- Blocked by: None (but should verify Index API first)
- Blocks: Future `findingmodel` package upgrade to DuckDB backend
- Related to: Index class abstraction from `findingmodel` package

---

## Progress Tracking

| Block                         | Status         | Owner | Completion Date | Notes |
| ----------------------------- | -------------- | ----- | --------------- | ----- |
| 1. Repository Infrastructure  | ⬜ Not Started | TBD   | -               | -     |
| 2. Database Class Update      | ⬜ Not Started | TBD   | -               | -     |
| 3. Application Code Update    | ⬜ Not Started | TBD   | -               | -     |
| 4. Test Infrastructure Update | ⬜ Not Started | TBD   | -               | -     |
| 5. Repository Tests           | ⬜ Not Started | TBD   | -               | -     |

**Legend**: ⬜ Not Started | 🟡 In Progress | ✅ Complete | ❌ Blocked

---

**Last Updated**: 2025-10-22 **Document Owner**: @talkasab
