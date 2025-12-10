# Changelog

All notable changes to FindingModelForge are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

#### Service Layer Refactoring Phase 1 (December 2025)

- **Context dataclasses**: Services now return complete context objects (`PaginationContext`, `DraftViewContext`, `NameResolutionResult`) instead of raw data
- **Business logic migration**: Moved workflow logic from routers to services:
  - `CreationService.resolve_name_input()` - draft lookup and workflow routing
  - `DraftService.prepare_view_context()` - permission checks, mode resolution
  - `FindingModelService.prepare_list_context()` - pagination calculations
- **Validation consolidation**: Input validation at API boundary (Pydantic/FastAPI), sanitization in services
- **Duplicate code removal**: Deleted `fetch_draft_with_context()`, `check_draft_permissions()` from helpers.py
- **Service tests**: Added 9 unit tests for `DraftService.prepare_view_context()`

#### Unit Test Quality Fixes (December 2025)

- **Fixed real API calls**: Tests were calling actual OpenAI API - now properly mocked
- **Removed skipped tests**: Fixed 4 skipped tests, deleted 2 obsolete step-4 tests
- **Test performance**: `test_step_1_valid_name` reduced from 15s to 0.04s via mocking
- **API mocking requirement**: All external API calls (OpenAI, etc.) must be mocked in unit tests

#### UI Test Suite Performance and Quality Improvements (November 2025)

- **Test performance optimization**: UI test suite now runs in 2.5 minutes (down from 5+ minutes, 2x speedup)
- **Network wait elimination**: Removed 41 `wait_for_load_state("networkidle")` calls across all UI tests
- **AI API call removal**: Eliminated 18+ real AI API calls, replaced with production data templates
- **Test data improvements**: Created `generate_valid_generated_json()` utility using real `abdominal_abscess.fm.json`
  data
- **HTMX-aware testing**: Migrated 20 arbitrary timeouts to `wait_for_htmx_settled()` utility
- **Click utility migration**: Standardized 7 HTMX actions to use `click_and_wait_for_htmx()` pattern
- **Anti-pattern elimination**: Fixed 10 "Schrödinger's Tests" that could pass without testing anything
- **Database-driven testing**: Added proper cleanup/seeding patterns for deterministic test behavior
- **Comprehensive documentation**: Added "No Schrödinger's Tests" philosophy and UI anti-patterns guide

#### findingmodel v0.5.0 Upgrade (November 2025)

- **Index API breaking changes**: Updated from MongoDB to DuckDB-backed Index class
- **Lazy loading pattern**: Index data loaded once on first access, cached in-memory for performance
- **API method updates**: Migrated from `Index.people` to `Index.load_people()` async pattern
- **Cache abstraction**: Updated to use Index as canonical source, maintaining MongoDB for drafts
- **Test fixture updates**: All tests updated to use async Index initialization patterns
- **Zero breaking changes**: Application code abstracted from backend implementation details

### Fixed

#### HTMX OOB Error Resolution (November 2025)

- **Fixed `htmx:oobErrorNoTarget` console errors**: HTTP 303 redirects losing `HX-Current-URL` header
- **Query parameter approach**: `?from=creation&success=made_public` survives redirects where headers don't
- **Context-aware rendering**: Server checks query params instead of headers for OOB swap decisions
- **Success message improvements**: Added context-aware alerts for "Make Public" workflow
- **Files affected**: `app/routers/drafts/workflows.py`, `app/routers/drafts/views.py`,
  `templates/components/draft_preview_content.html`

#### Drafts Router Modularization (October 15, 2025)

- **Modular router architecture**: Split monolithic 866-line `app/routers/drafts.py` into focused module
- **New structure**: 6 files in `app/routers/drafts/` package (views, mutations, workflows, comments, helpers, **init**)
- **Helper extraction**: 11 helper functions extracted for unit testing (generate_finding_model_json, render functions,
  etc.)
- **Test coverage improvements**: Added 40 new unit tests (34 for helpers + 6 for generate_finding_model_json)
- **Zero breaking changes**: All URLs and APIs unchanged, 100% test pass rate maintained (492/492)
- **Improved maintainability**: Files now ~250 lines each vs 866-line monolith
- **Better testability**: Helpers can be unit tested independently of HTTP layer
- **Shared utilities**: Created `app/utils/forms.py` for parse_synonyms reuse across routers
- **Bug fixes**: Fixed missing success alert parameter and Flowbite modal rendering issues discovered during testing
- **Documentation**: Established modular router pattern guidelines in project_overview memory

#### Comment System Refactor - Centralized Service Layer (September 30, 2025)

- **Created CommentService**: Centralized all comment logic (validation, rate limiting, persistence) into shared service
- **Eliminated code duplication**: Removed duplicate rate limiting checks from routers
- **Service layer delegation**: DraftService and FindingModelService now delegate to CommentService
- **Architecture cleanup**: Routers are thin HTTP handlers, business logic in services
- **Single source of truth**: Rate limiting now only in CommentService, not duplicated in routers
- **Maintained test coverage**: All 491 tests passing with 79.50% coverage

### Added

#### Public Draft Review Feature (September 17, 2025)

- **New draft status**: Added `DraftStatus.PUBLIC` enum value for community review stage
- **Public drafts table**: New `/drafts` endpoint displaying all public drafts for review
- **Make public functionality**: POST `/drafts/{id}/make-public` endpoint with owner validation
- **Enhanced permissions**: Public and submitted drafts viewable by all, editable by owner
- **Redis caching**: 5-minute TTL cache for public drafts list with proper invalidation
- **Denormalized author fields**: Added `author_username` and `author_name` to drafts
- **UI test improvements**: Fixed seed_draft() to generate valid JSON for public/submitted drafts
- **Bug fixes**: Fixed database query to allow editing both "draft" and "public" statuses
- **Test coverage**: Added comprehensive tests for public draft editing permissions

#### Comment System Implementation (September 2025)

- **Complete comment system** for finding models and drafts with single-level replies
- **Data models and repository layer**: Comment, CommentThread, UserCommentEntry models with MongoDB operations
- **Service layer integration**: Comment helpers and finding model/draft service methods
- **HTMX-powered UI components**: Dynamic comment threads with Alpine.js form validation
- **Rate limiting**: 3 comments per minute per user with 429 status enforcement
- **Report functionality**: Users can report inappropriate comments with double-report prevention
- **User comment index**: Track user comment history for profile features
- **Authentication requirements**: Only authenticated users can comment
- **Draft restrictions**: Comments only allowed on submitted drafts (not draft status)
- **Testing coverage**: 17 UI tests + 8 rate limiting tests + 43 repository tests all passing

#### Comment System Features

- **Single-level threading**: Comments can have replies, but replies cannot have replies
- **Character validation**: 1-2000 character limit with real-time counter
- **Empty state handling**: Different messages for authenticated vs anonymous users
- **Chronological ordering**: Oldest-first display for natural discussion flow
- **User attribution**: GitHub avatars and usernames displayed with comments
- **Timestamp display**: Raw UTC timestamps (humanization planned for future)
- **Report system**: Flag inappropriate content for moderation
- **Rate limiting enforcement**: Prevents spam with per-user limits

#### Comment System Architecture

- **Separate collection**: `comment_threads` collection for clean separation from content
- **Polymorphic references**: `reference_type` and `reference_id` for models and drafts
- **Atomic operations**: MongoDB atomic updates for thread creation and comment addition
- **Lazy thread creation**: Threads created on first comment to avoid empty documents
- **Indexed lookups**: Compound index on (reference_type, reference_id) for performance
- **Moderation support**: `reported_count` index for finding flagged content

### Changed

#### Router Refactoring (September 2025)

- **Enhanced routers with comment endpoints**:
  - `finding_models_browse.py`: Added `/finding-models/{slug}/comments` and report endpoints
  - `drafts.py`: Added `/drafts/{id}/comments` and report endpoints with draft validation
- **Service layer updates**:
  - `finding_model_service.py`: Integrated comment thread retrieval
  - `draft_service.py`: Added draft ownership validation for comments
  - `comment_helpers.py`: Created for rate limiting and blacklist checking

#### Three-Level Index Code Display System

- **Complete index code display functionality** implemented across model, attribute, and value levels (August 27, 2025)
- **New Flowbite-based components** in `templates/macros/app_components.html`:
  - `index_code_badge(code)` - Two-line badge format with system:code and display text
  - `index_codes_display(codes, title)` - Section display with title and multiple badges
  - `value_popover(value, attr_name)` - Hover popovers showing value descriptions and codes
- **Three-level integration** in `templates/components/finding_model_display.html`:
  - **Model level**: Top-level index codes displayed with "Codes" heading using indigo styling
  - **Attribute level**: Attribute-specific codes shown within each attribute section
  - **Value level**: Interactive hover popovers on value buttons showing detailed code information
- **Accessibility features**: Proper ARIA attributes, role="tooltip", and keyboard navigation support
- **Visual consistency**: Unified indigo color scheme and two-line badge format across all levels
- **Comprehensive test coverage**: 7 Playwright tests integrated into existing UI test infrastructure covering all three
  levels

### Fixed

#### Playwright Test Infrastructure

- **Fixed multiple technical issues** in initial test implementation:
  - Regex compilation errors (`/font-mono/` → `re.compile(r'.*\\bfont-mono\\b.*')`)
  - Playwright selector syntax (`page.locator().first()` → `page.locator().first`)
  - Strict mode violations with more specific selectors (`.font-mono` for SNOMED badges)
- **Established proper testing patterns** following UI test conventions with console error collection and verification

## [1.3.0] - 2025-08-25

### Added

#### URL Simplification Implementation

- **Simplified URL structure** - Clean, user-friendly URLs for creation and draft management
- **Router refactoring completion** - Extracted monolithic routers into focused, single-responsibility modules
- **Service layer architecture** - Complete separation of business logic from HTTP concerns

#### Router Architecture Overhaul

- **Router file organization**:
  - `app/routers/creation.py` - Creation workflow (was `finding_models_creation.py`)
  - `app/routers/drafts.py` - Draft management (was `finding_models_drafts.py`)
  - `app/routers/finding_models_browse.py` - Browse/detail functionality (unchanged)
  - `app/routers/home.py`, `auth_pages.py`, `profile.py` - Simple page routers
- **Service layer implementation**:
  - `app/services/creation_service.py` - AI generation and workflow logic
  - `app/services/draft_service.py` - Draft CRUD operations
  - `app/services/finding_model_service.py` - Model browsing and caching
  - `app/utils/slug.py` - URL slug generation utilities

#### URL Structure Modernization

**New simplified URLs**:

```
Creation Workflow:
  /create/step/1, /create/step/2, /create/step/3
  /create/restart, /create/resume

Draft Management:
  /drafts/{id}, /drafts/{id}/submit, /drafts/{id}/delete
  /drafts/{id}/update-and-redirect

Browse (unchanged):
  /finding-models, /finding-models/{slug}
```

**Old URLs removed**:

```
/api/finding-models/create/* → /create/*
/api/finding-models/drafts/* → /drafts/*
```

### Changed

#### Comprehensive Template Updates

- **14 template files updated** with new URL structure
- **HTMX patterns preserved** - All content swapping and form submissions working
- **Template consistency** - Updated all `hx-post`, `hx-get`, form actions, and navigation links

#### FastAPI Router Architecture

- **Prefix-based routing** - Clean separation using `app.include_router(router, prefix="/create")`
- **Route path optimization** - Routes define relative paths, prefixes added at registration
- **Service integration** - All business logic moved to injectable service classes

#### Testing Infrastructure Updates

- **URL test updates** - All test URLs updated to new structure
- **Coverage maintenance** - 78.39% router coverage maintained
- **UI test compatibility** - Playwright tests working with new URLs

### Fixed

#### Planning Process Improvements

- **Critical planning rule added** - Prevention of unilateral plan changes
- **Documentation synchronization** - All docs updated to reflect new architecture

#### Development Workflow

- **Live server verification** - New URLs confirmed working in development
- **Redirect URL fixes** - All `RedirectResponse` URLs updated throughout routers
- **Import path updates** - All module imports updated for renamed files

### Technical Details

#### Router Extraction Metrics

- **Code reduction achieved**:
  - `pages.py`: 539 → 49 lines (91% reduction)
  - `finding_models.py`: 1037 → 0 lines (100% reduction, file removed)
  - Total: 1000+ lines extracted into focused routers
- **Service layer**: 3 services with 62 comprehensive tests
- **Test coverage**: 144 tests passing (84.69% overall coverage)

#### Architecture Quality

- **Single responsibility principle** - Each router handles one concern
- **DRY principle achieved** - Eliminated code duplication via services and utilities
- **Clean separation** - Routers handle HTTP, services handle business logic
- **Type safety maintained** - Complete type hints throughout refactored code

#### URL Verification

- **Development server testing**:
  - New URLs return 401 (authenticated endpoints working)
  - Old URLs return 404 (properly removed)
  - All functionality preserved with simplified structure

### Migration Notes

#### For Developers

1. **URL updates**: Any external references to `/api/finding-models/create/*` or `/api/finding-models/drafts/*` need
   updating
2. **Import changes**: Router imports now use shorter names (`creation`, `drafts`)
3. **Service injection**: New services available for dependency injection

#### For Users

- **No breaking changes**: All functionality works identically with cleaner URLs
- **Better UX**: Shorter, more memorable URLs for creation and draft management
- **Preserved workflows**: All existing user workflows continue working

### Added

#### Finding Models Display System Complete Overhaul

- **Public browseable finding models library** with comprehensive search, navigation, and responsive UI
- **Advanced HTMX patterns** implemented:
  - `hx-history-elt="true"` configuration on `#main-content` prevents CSS-in-JS conflicts
  - Conditional Out-of-Band (OOB) breadcrumb swaps prevent duplicate breadcrumbs on initial page load
  - Template-based browser history restoration for clean breadcrumb and title updates
- **Server-side search and pagination** with 500ms debounced search input for optimal UX
- **Dynamic page title system**:
  - Context-aware titles: "Finding Models", "Search: {query}", "{model} - Finding Model Forge"
  - Automatic HTMX title updates using `<title>` tags in fragment responses
  - Proper title restoration during browser history navigation
- **Smart caching optimization** with Redis layer for GitHub API finding models data and graceful fallback
- **SEO-friendly implementation** with clean URL structure, proper meta tags, and search indexing support

#### Comprehensive Testing Infrastructure

- **100% test success rate achieved** - All 40 tests passing (22 unit + 18 UI tests)
- **Complete Unit Test Suite**:
  - Fixed 7 failing unit tests by updating route paths from singular to plural (/finding-model/ → /finding-models/)
  - Fixed async mocking issues using AsyncMock for cache operations instead of MagicMock
  - Removed 4 obsolete partial route tests referencing non-existent endpoints
  - Added 5 new unit tests for search, pagination, HTMX headers, and dynamic titles
- **Comprehensive Playwright UI Test Suite**:
  - 18 end-to-end tests covering all finding models navigation scenarios
  - TestFindingModelsListPage (5 tests): page loading, search functionality, debounce verification, pagination, empty
    results
  - TestFindingModelsDetailNavigation (4 tests): HTMX navigation, direct access, breadcrumb links, 404 handling
  - TestFindingModelsHistoryNavigation (4 tests): browser back/forward, title/breadcrumb restoration
  - TestFindingModelsDynamicFeatures (5 tests): dynamic titles, state preservation, HTMX configuration verification
- **Playwright MCP-driven development** - Used real browser automation to understand actual site behavior before writing
  tests
- **Robust test patterns**:
  - Fixed function signature issues (ignore_patterns → allowed_patterns)
  - Fixed import issues (tests.ui.helpers → tests.ui.utils)
  - Fixed Playwright expect syntax (string expects → proper assertions)
  - Used specific breadcrumb selector (`nav[aria-label='Breadcrumb']`) instead of generic selectors

### Fixed

#### Submit Draft Modal Implementation

- **Fixed htmx:targetError** - Submit Draft button now correctly targets `#main-content` instead of non-existent
  `#draft-content`
- **Replaced browser confirmation with Flowbite modal** - Consistent UI using proper modal components instead of
  `hx-confirm`
- **Created reusable modal system**:
  - `templates/macros/confirmation_modal.html` - Base modal component with customizable parameters
  - `templates/macros/submit_draft_modal.html` - Green submit confirmation modal
  - Refactored `templates/macros/delete_draft_modal.html` to use base component
- **Updated draft preview templates** - All draft display components now use consistent modal patterns
- **Comprehensive test coverage**:
  - 4 unit tests for modal HTML generation and HTMX attributes
  - 4 UI tests for complete Submit/Delete modal workflows including accessibility
  - Tests verify modal appearance, button functionality, and proper HTMX targeting

#### Code Quality Improvements

- **Linting fixes** - Resolved all style and formatting issues in test files
- **Import organization** - Consistent import ordering across test modules
- **Unused variable cleanup** - Removed dead code from UI tests

## [1.2.0] - 2025-08-20

### Major UI Testing Infrastructure Overhaul

#### Playwright Test Suite Complete Rewrite

- **Fixed all Playwright UI tests** - Complete rewrite of browser automation testing infrastructure
- **24/24 tests now passing** - Creation workflow (8), Draft management (8), Profile workflow (8)
- **Unified container architecture** - All HTMX workflows use `#main-content` container for consistency
- **AI operation mocking** - Test user ID 999999 bypasses all AI operations with realistic mock responses
- **HTMX-aware testing patterns** - Proper content swap detection instead of browser navigation
- **Alpine.js integration fixes** - Simplified testing without over-complicated framework waits

#### Container ID Unification

- **Unified `#main-content` containers** across all workflows - eliminates HTMX target mismatches
- **Updated templates**:
  - `templates/create_finding_model_htmx.html` - changed from `#step-container` to `#main-content`
  - `templates/draft_unified.html` - changed from `#draft-content` to `#main-content`
  - `templates/components/draft_mode_toggle_header.html` - unified HTMX target references
- **Router context detection** - all endpoints now use `#main-content` consistently
- **Test selector updates** - all UI tests updated to use unified container pattern

#### Comprehensive AI Mocking System

- **User ID-based AI bypass** - Test user 999999 uses mock responses instead of real AI operations
- **Three endpoint mock integration**:
  - `process_step_1()` - Mock description generation with 2-second realistic delay
  - `process_step_2()` - Mock similarity detection with instant "no similar found" response
  - `update_draft_and_redirect()` - Mock model generation with structured FindingModelBase creation
- **Realistic mock data** - Generated responses match actual AI output structure and content
- **Performance optimization** - Tests complete in ~120 seconds instead of 5+ minutes

#### Browser Testing Infrastructure

- **Playwright MCP integration** - Direct browser automation for debugging and verification
- **Test utilities enhancement** - Updated `tests/ui/utils.py` with proper HTMX and Alpine.js helpers
- **Authentication streamlining** - Consistent test-auth pattern for all UI tests
- **Error handling improvements** - Better console error detection and reporting

### Testing Improvements

#### UI Test Coverage

- **Creation Workflow Tests** (8/8 passing):
  - Complete creation flow from name entry to draft submission
  - Synonym management across HTMX content swaps
  - Draft editing and regeneration cycles
  - Resume functionality for draft and submitted states
- **Draft Management Tests** (8/8 passing):
  - Edit/Preview mode switching with unified container
  - Form validation with Alpine.js reactive buttons
  - Model reuse vs regeneration logic testing
  - Form persistence across mode switches
- **Profile Workflow Tests** (8/8 passing):
  - Draft grid display and navigation
  - Edit/View/Delete actions from profile page
  - Status indicators and user isolation

#### Test Infrastructure

- **HTMX testing patterns** - Proper content swap detection instead of URL navigation
- **Alpine.js testing simplification** - Direct element state checking without framework complexity
- **Mock data factories** - Realistic test data creation via MongoDB MCP integration
- **Background server management** - Automated dev server handling for continuous testing

### Frontend Architecture Improvements

#### HTMX Workflow Consistency

- **Single container pattern** - All dynamic content swaps into `#main-content`
- **URL synchronization** - HTMX `HX-Push-Url` headers maintain browser history
- **Mode switching reliability** - Edit/Preview toggles work seamlessly across workflows
- **Error handling** - Better HTMX error detection and user feedback

#### Alpine.js Integration Fixes

- **Simplified reactivity** - Removed unnecessary Alpine.js initialization waits
- **Form validation optimization** - Direct button state checking without framework delays
- **Component initialization** - Proper Alpine.js tree initialization after HTMX swaps

### Workflow Transition Completion

#### 5-Step to 3-Step + Draft Workflow Migration

- **Removed obsolete 5-step workflow remnants** - Complete cleanup of old step 4 and step 5 components
- **Type-safe step validation** - Implemented `StepNumber` annotated type with Pydantic validation (steps 1-3 only)
- **Template cleanup**:
  - Deleted `templates/components/finding_model_creation/step_4_edit_attributes.html`
  - Deleted `templates/components/finding_model_creation/step_5_review_model.html`
- **Router modernization** - GET `/create/step/{step_number}` now enforces 1-3 constraint with 422 validation errors
- **Test suite updates** - Fixed 5 failing tests, updated expectations for new workflow patterns

#### Backend Architecture Improvements

- **Enhanced type safety** - `StepNumber = Annotated[int, Path(ge=1, le=3)]` provides validation at FastAPI/Pydantic
  level
- **Improved error handling** - Step validation now returns proper 422 errors with clear messages instead of 500 errors
- **Redirect testing patterns** - Updated tests to properly handle 303 redirects to draft endpoints
- **Clean separation** - Clear distinction between creation steps (1-3) and draft management system

#### Test Infrastructure Fixes

- **Fixed test failures** - Resolved 5 critical test failures from workflow transition:
  - `test_render_step_template_valid_steps` - Updated to test steps 1-3 only
  - `test_get_creation_step_valid_steps` - Fixed step validation expectations
  - `test_get_creation_step_invalid_step` - Updated for 422 validation errors
  - `test_process_step_1_resume_existing_draft` - Fixed redirect handling
  - `test_step1_resumes_submitted_draft_to_draft_view` - Updated for draft view mode
- **Test cleanup** - Removed obsolete `tests/test_step4_and_drafts.py` file
- **Mock improvements** - Added proper `get_draft` mocking for redirect targets

### Developer Experience

#### Testing Workflow

- **Fast test execution** - UI tests complete in ~2 minutes with full coverage
- **Debugging capabilities** - Playwright MCP allows real-time browser inspection
- **Reliable CI/CD** - No more flaky tests, consistent pass rates
- **Clear test output** - Simplified assertions and better error messages

#### Development Tools

- **Background server management** - `task dev` with logging to `test.log`
- **MongoDB MCP integration** - Direct database inspection and test data management
- **Browser automation** - Playwright MCP for UI debugging and verification

## [1.1.0] - 2025-08-19

### Major Improvements

#### Draft Management System Overhaul

- **Complete draft lifecycle implementation** with autosave, resume, submit, and delete functionality
- **Unified draft page pattern** - single endpoint handling both edit and view modes via `?mode=` parameter
- **Session adoption pattern** - automatic recovery of draft state when sessions are lost
- **Action logging** - comprehensive audit trail for all draft operations
- **User-scoped draft isolation** - one editable draft per (user_id, name) combination

#### Router Endpoint Consolidation

- **Removed 3 obsolete endpoints** (256 lines) superseded by unified approach:
  - `POST /drafts/{draft_id}/update` - replaced by step 4 autosave
  - `GET /drafts/{draft_id}/preview` - replaced by unified draft page with `?mode=view`
  - `GET /drafts/{draft_id}/view` - replaced by unified draft page with `?mode=view`
- **Added missing decorator** for `/drafts/{draft_id}/update-and-redirect` endpoint
- **Streamlined workflow routing** with better step transitions and error handling

#### Comprehensive Testing Suite

- **Added 18 new unit tests** improving finding_models.py coverage from 49% to 71%
- **Four test priority categories**:
  1. Critical Happy Path Tests (4 tests) - core workflow scenarios
  2. Draft State Transitions (5 tests) - save, submit, delete, resume operations
  3. Error Handling & Edge Cases (5 tests) - validation failures and edge cases
  4. Access Control & Validation (4 tests) - security and permission checks
- **Fixed all failing tests** - session handling, ObjectId validation, assertion improvements
- **Enhanced test patterns** - better mocking, realistic data, comprehensive assertions

### Backend Changes

#### API Endpoints

- **Modified**: `GET /api/finding-models/drafts/{draft_id}` - now supports `?mode=edit|view` parameter
- **Enhanced**: `POST /api/finding-models/create/step/4` - improved autosave on GET requests
- **Fixed**: `POST /api/finding-models/drafts/{draft_id}/update-and-redirect` - added proper router decorator
- **Improved**: Step 2 processing - better error handling and assertion validation

#### Database & Repository Layer

- **Enhanced DraftRepo methods**:
  - `save_draft()` - robust upsert logic with action logging
  - `find_editable_by_name()` - case-insensitive draft lookup
  - `submit()` - status transition with validation
  - `delete_draft()` - secure deletion with ownership checks
- **Session management improvements** - better draft adoption and state recovery

#### Models & Validation

- **Enhanced FindingModelDraft** - comprehensive action logging and status management
- **Improved session handling** - draft_id persistence and status tracking
- **Better error handling** - specific exceptions for validation failures

### Frontend Changes

#### Template Updates

- **Updated draft_editor.html** - replaced removed `/preview` endpoint with unified approach
- **Enhanced form handling** - better draft_id persistence and mode switching
- **Improved JavaScript** - updated URL detection for unified endpoint pattern

#### Component Architecture

- **New draft management components**:
  - `templates/components/draft_edit_form.html` - comprehensive draft editing
  - `templates/components/draft_preview.html` - preview mode display
  - `templates/draft_unified.html` - unified edit/view page template
- **Enhanced macros**:
  - `macros/delete_draft_modal.html` - confirmation modal for draft deletion
  - `macros/unified_form_data.html` - shared form data management

### Testing Improvements

#### Unit Test Coverage

- **tests/test_finding_models_comprehensive.py** - new comprehensive test suite
- **71% coverage** for finding_models.py (up from 49%)
- **70 passing tests, 4 skipped, 0 failing** - all critical paths covered

#### Test Infrastructure

- **Better session mocking** - proper cookie handling for authenticated requests
- **Realistic test data** - valid MongoDB ObjectIds and appropriate field lengths
- **Improved assertions** - less brittle tests with better error messages
- **Enhanced fixtures** - comprehensive mock setup for database and cache

#### Test Patterns

- **Priority-based test organization** - clear categorization by importance
- **Comprehensive scenarios** - happy path, error cases, edge conditions
- **Integration readiness** - tests designed for both unit and integration testing

### Documentation Updates

#### Enhanced Guides

- **Updated app/CLAUDE.md** - new endpoint patterns and unified draft approach
- **Enhanced tests/CLAUDE.md** - comprehensive testing patterns and examples
- **Improved templates/CLAUDE.md** - updated component usage patterns

#### Memory System Updates

- **Serena memory updates** - current state of draft management and testing patterns
- **Workflow documentation** - complete draft lifecycle and session management
- **Testing best practices** - patterns for router testing and mock usage

### Developer Experience

#### Code Quality

- **Type safety improvements** - better type hints throughout router code
- **Error handling enhancements** - specific exceptions and better error messages
- **Code organization** - cleaner endpoint structure and better separation of concerns

#### Debugging & Monitoring

- **Enhanced logging** - better draft operation tracking
- **Improved error messages** - more specific validation failures
- **Session debugging** - better state recovery and adoption patterns

## Previous Releases

### [1.0.0] - Previous Release

- See git history for previous changes before this comprehensive overhaul

---

## Migration Notes

### From Previous Draft System

If upgrading from a previous version:

1. **Database Migration**: Existing drafts will continue to work with the new unified endpoint
2. **Frontend Updates**: Any custom templates referencing removed endpoints need updating:
   - Replace `/drafts/{id}/preview` with `/drafts/{id}?mode=view`
   - Replace `/drafts/{id}/update` with step 4 autosave workflow
3. **Testing**: New test patterns provide better coverage - consider updating existing tests

### API Breaking Changes

- **Removed endpoints** (deprecated, no longer functional):
  - `POST /api/finding-models/drafts/{draft_id}/update`
  - `GET /api/finding-models/drafts/{draft_id}/preview`
  - `GET /api/finding-models/drafts/{draft_id}/view`

### New Features Available

- **Unified draft editing** - single endpoint for all draft operations
- **Automatic draft recovery** - sessions can recover from drafts seamlessly
- **Enhanced testing** - comprehensive test coverage for all router functionality
- **Better error handling** - more specific error messages and validation

## [0.5.0] - 2025-08-30

### Added

- **URL Simplification**: Clean, user-friendly URLs replacing API prefixes
- **Router Refactoring**: Modular, focused routers with single responsibilities
- **Service Layer**: Complete separation of business logic from HTTP concerns
- **Three-Level Index Code Display**: Enhanced code navigation with hover popovers
- **Comprehensive Testing**: Playwright tests for UI workflows

### Changed

- **Router organization**: Split monolithic routers into focused modules
- **URL structure**: Removed `/api/finding-models/` prefix for cleaner URLs
- **Draft workflow**: Unified draft management with session adoption
- **Testing infrastructure**: Enhanced with priority-based test organization

---

## Contributors

- Development and testing improvements
- Comprehensive documentation updates
- Router endpoint consolidation and optimization
