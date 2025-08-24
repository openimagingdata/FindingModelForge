# Changelog

All notable changes to FindingModelForge are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

---

## Contributors

- Development and testing improvements
- Comprehensive documentation updates
- Router endpoint consolidation and optimization
