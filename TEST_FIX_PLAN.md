# Test Fix Plan - Finding Model Creation Workflow

**Status**: In Progress **Target**: Fix failing Playwright tests for the streamlined creation workflow **Original
Issue**: Tests still expect old 5-step workflow, but new workflow uses unified draft pattern

## Current Test Status

```
Initial Status: 15 failed, 8 passed (8/23)
After Profile Fixes: 8 failed, 15 passed (15/23)
Current Failures:
- test_create_to_edit_cycle - TimeoutError waiting for function
- test_multiple_edit_regenerate_cycles - AssertionError: text not found
- test_resume_submitted_draft - AssertionError: wrong count
- test_edit_mode_to_preview_mode_switching - AssertionError: not visible
- test_direct_preview_mode_access - AssertionError: not visible
- test_button_validation_for_draft_with_existing_model - TimeoutError
- test_button_enabled_for_draft_without_model - TimeoutError
- test_back_from_preview_prefills_form - TimeoutError waiting for selector
Target: All 23 tests passing
```

## Problem Analysis

### Root Cause Issues Identified

1. **Workflow Misunderstanding**: Tests expect old 5-step workflow, but app uses streamlined draft-based workflow
2. **HTMX Confusion**: Tests don't properly handle HTMX content swaps vs. page redirects
3. **Mode Toggle Logic**: Tests don't understand the new edit/view mode switching pattern
4. **Timing Issues**: Tests use blind waits instead of proper HTMX/Alpine.js ready states
5. **AI Operation Delays**: Slow `findingmodel.tools.find_similar_models` causes timeouts

### Current Reality - How It Actually Works

New streamlined workflow:

1. Step 1 → Step 2 → **HTMX Swap OR 303 Redirect**
   - If similar models found: HTMX swaps step 3 content into `#step-container`
   - If no similar models: 303 redirect to `/api/finding-models/drafts/{id}?mode=edit`
2. Draft Edit → Update & Preview → Draft View (HTMX swaps in `#step-container`)
3. "Update & Preview" button generates model AND switches to view mode
4. "Submit Draft" button submits (confirmation dialog)

## Test Categorization

### Category 1: Need Updates (Keep & Fix)

These test the right concepts but with wrong assumptions:

- `TestBasicCreationFlow::test_complete_creation_workflow` - Core workflow, needs HTMX swap fixes
- `TestSynonymManagement::test_synonym_persistence_across_steps` - Valid test, needs workflow updates
- `TestCreateToEditWorkflow::test_create_to_edit_cycle` - Good test, needs mode toggle understanding
- `TestResumeFlow::test_resume_submitted_draft` - Important test, needs state handling fixes

### Category 2: Replace Entirely

These are so flawed they should be rewritten:

- `TestMultipleEditCycles::test_multiple_edit_regenerate_cycles` - Confusing implementation
- `TestFormValidation` tests - Based on wrong Alpine.js assumptions
- `TestBackNavigation::test_back_from_preview_prefills_form` - Wrong navigation model

### Category 3: Remove (No Longer Needed)

These test obsolete functionality:

- Any tests expecting step 3-5 as separate pages
- Tests expecting traditional page navigation
- Tests checking for elements outside `#step-container` context

## Files Requiring Changes

### Priority 1: Core Creation Test

- **File**: `tests/ui/test_creation_workflow.py`
- **Test**: `TestBasicCreationFlow::test_complete_creation_workflow`
- **Status**: Currently failing with "Submit button not found"

### Priority 2: Related Creation Tests

- **File**: `tests/ui/test_creation_workflow.py`
- **Tests**:
  - `test_synonym_persistence_across_steps` - Update for new workflow
  - `test_create_to_edit_cycle` - Adapt for draft editing pattern
  - `test_multiple_edit_regenerate_cycles` - Update selectors
  - `test_resume_submitted_draft` - Should still work but verify

### Priority 3: Draft Management Tests

- **File**: `tests/ui/test_draft_management.py` (if exists)
- **Status**: May need creation if missing

## Detailed Changes Needed

### 1. Button Selector Updates

| Old Selector                              | New Selector                          | Context         |
| ----------------------------------------- | ------------------------------------- | --------------- |
| `button:has-text('Generate Final Model')` | `button:has-text('Update & Preview')` | Draft edit form |
| `button:has-text('Submit to Repository')` | `button:has-text('Submit Draft')`     | Draft preview   |
| `textarea[name='attributes_markdown']`    | Same, but on draft page               | Draft edit form |

### 2. Workflow Logic Changes

#### Before (test_complete_creation_workflow):

```python
# Step 1: Enter name
# Step 2: Check similar
# Step 3: Skip or handle similar
# Step 4: Edit attributes
# Step 5: Submit model
```

#### After (test_complete_creation_workflow):

```python
# Step 1: Enter name, generate description
# Step 2: Check similar -> REDIRECT to draft edit
# Draft Edit: Update & Preview -> Switch to view mode
# Draft View: Submit Draft -> Final state
```

### 3. URL Pattern Detection

#### Critical URL Changes:

- Old: Stays on `/create-finding-model` throughout
- New: Redirects to `/api/finding-models/drafts/{id}?mode=edit&created=true`

#### Detection Strategy:

```python
# After "Check for Similar" click, detect redirect
await wait_for_htmx_to_settle(page, timeout=60000)
current_url = page.url
if "/drafts/" in current_url:
    # We're on the unified draft page
    # Look for mode=edit and success banner
```

### 4. Element Visibility Changes

#### New Elements to Check:

- Success banner: `div:has-text('Draft created successfully')`
- Mode toggle buttons: `button:has-text('Edit')`, `button:has-text('Preview')`
- Draft status indicator: Status shown in draft info section

#### Removed Elements:

- Step 4 attributes textarea (directly on step page)
- Step 5 final display
- Traditional step navigation breadcrumbs

## Comprehensive Implementation Plan

### Phase 1: Fix Core Infrastructure (utils.py)

**Priority**: CRITICAL - Must do first

1. **Add mock for slow AI operations**:
   - Mock `findingmodel.tools.find_similar_models` with 2s delay instead of real operation
   - Add fixture `mock_ai_operations` for consistent mocking

2. **Improve HTMX wait helpers**:
   - Fix `wait_for_ai_completion_and_swap()` to handle all button states
   - Add `wait_for_draft_redirect()` helper for detecting 303 redirects
   - Add `wait_for_mode_switch()` for edit/view transitions
   - Add `wait_for_step_container_content()` for HTMX swaps

3. **Fix authentication pattern**:
   - Ensure all tests use `authenticated_page` fixture consistently
   - Never use `TEST_AUTH_USER_ID` env var - hardcode 999999
   - Add cleanup in fixture teardown

### Phase 2: Fix Core Creation Workflow Test

**Target**: `test_complete_creation_workflow`

**Updated Flow**:

```python
# Step 1: Enter name, generate description (HTMX swap)
# Step 2: Check similar → Detect outcome:
#   - If similar found: HTMX swaps step 3 into #step-container
#   - If no similar: 303 redirect to draft page
# Handle conditional routing properly
# Draft Edit: Use #step-container selectors (containerless content)
# Mode switching: Check toggle buttons only after model generation
# Submit: Handle confirmation dialog with page.on("dialog")
```

**Key Changes**:

- Remove all step 3-5 expectations
- Add conditional logic for similar models outcome
- Use correct selectors for containerless content
- Handle dialog properly for submission

### Phase 3: Fix Synonym Management Tests

**Targets**: `test_synonym_persistence_across_steps`, `test_synonym_removal`

**Changes**:

- Update to handle redirect to draft page
- Check synonyms persist in draft edit form
- Use correct badge selectors on draft page
- Remove step 4 as separate page expectations

### Phase 4: Fix Draft Management Tests

1. **Fix `TestUnifiedDraftPage`**:
   - Add proper Alpine.js initialization waits
   - Fix mode toggle button selectors
   - Handle containerless content correctly
   - Add proper HTMX swap detection

2. **Rewrite `TestFormValidation`**:
   - Test button disabled when no changes (with generated model)
   - Test button enabled when changes made
   - Test button always enabled for drafts without model
   - Use `wait_for_alpine_ready()` before checking button states

3. **Fix `TestBackNavigation`**:
   - Remove browser back button expectations
   - Test mode switching preserves form values
   - Use HTMX swaps, not page navigation
   - Verify form prefill after mode switch

### Phase 5: Add New Essential Tests

1. **Profile/My Forge Page Tests** (new file: `test_profile_workflow.py`):
   - Test draft grid display
   - Test edit/view/delete actions
   - Test submitted vs draft status display
   - Test pagination if many drafts

2. **HTMX Workflow Tests** (add to existing):
   - Test content stays in `#step-container`
   - Test URL updates via `HX-Push-Url` header
   - Verify no page reloads occur
   - Test Alpine.js initialization after swaps

3. **Draft Lifecycle Tests** (enhance existing):
   - Create → Edit → Generate → Submit flow
   - Resume from different states (draft vs submitted)
   - Autosave on step 4 GET request
   - Draft deletion restrictions

### Phase 6: Clean Up & Optimize

1. **Remove obsolete code**:
   - Delete tests for steps 3-5 as separate pages
   - Remove page navigation expectations
   - Clean up unused helper functions

2. **Add proper test markers**:

   ```python
   @pytest.mark.slow  # For tests taking >5s
   @pytest.mark.ui    # For all UI tests
   @pytest.mark.critical  # For must-pass tests
   ```

3. **Improve test performance**:
   - Mock all AI operations consistently
   - Use parallel test execution where possible
   - Run headed mode only for debugging (`PLAYWRIGHT_HEADLESS=false`)
   - Add `--lf` flag to rerun only failed tests

### Implementation Order & Timeline

1. **Day 1**: Fix utils.py infrastructure (2-3 hours)
2. **Day 1**: Fix `test_complete_creation_workflow` as proof (1 hour)
3. **Day 2**: Fix remaining creation workflow tests (3-4 hours)
4. **Day 2**: Fix draft management tests (2-3 hours)
5. **Day 3**: Add new profile page tests (2 hours)
6. **Day 3**: Clean up and optimize (1 hour)

## Key Testing Principles to Follow

### HTMX-Aware Testing

- **All workflow happens via content swaps** in `#step-container`
- **No page navigation** - URL changes via `HX-Push-Url` header only
- **303 redirects intercepted by HTMX** become content swaps
- **Check for swapped content**, not URL changes

### Proper Wait Strategies

- **Use HTMX/Alpine ready states**, not blind timeouts
- **Wait for specific elements** after operations
- **Check button state changes** to detect AI completion
- **Use `wait_for_function()` for complex conditions**

### Authentication Best Practices

- **Always use test-auth login** pattern
- **User ID is always 999999** (hardcoded in test-auth)
- **Clean up test data** before and after tests
- **Never use GitHub OAuth** in tests

### Mock Strategies

- **Mock slow AI operations** for speed and reliability
- **Use consistent 2s delay** for mocked operations
- **Mock at the function level**, not HTTP level
- **Return realistic data** from mocks

## Success Metrics

### Test Execution Metrics

- All 23 existing tests passing (after removals/replacements)
- No timeout errors (all operations complete within limits)
- Tests complete in <3 minutes total (headed: <5 minutes)
- Zero console errors about Flowbite/Alpine initialization
- Works in both headed and headless modes

### Code Quality Metrics

- 100% of tests use proper HTMX wait patterns
- 0 uses of `page.wait_for_timeout()` (blind waits)
- All AI operations properly mocked
- Consistent use of authenticated fixtures
- Proper cleanup of test data

### Coverage Goals

- Core creation workflow: 100% coverage
- Draft management: 100% coverage
- Profile page interactions: 80% coverage
- Error handling paths: 70% coverage
- Edge cases: 60% coverage

## Success Criteria Checklist

### Per-Test Success Criteria

- [ ] `test_complete_creation_workflow`: Completes full flow from name entry to submitted draft
- [ ] `test_synonym_persistence_across_steps`: Synonyms persist through redirect to draft page
- [ ] `test_navigation_authentication_required`: Auth required for both creation and draft pages
- [ ] `test_create_to_edit_cycle`: Can edit draft and regenerate model
- [ ] `test_multiple_edit_regenerate_cycles`: Multiple edit cycles work on draft page
- [ ] `test_resume_submitted_draft`: Resume works for submitted drafts
- [ ] Draft management tests: All mode switching and validation tests pass
- [ ] Profile page tests: Draft grid and actions work correctly

### Overall Success Criteria

- [ ] All UI tests passing (target: 25+ tests after additions)
- [ ] No timeout errors
- [ ] No element not found errors
- [ ] Tests complete in <3 minutes (headless)
- [ ] Tests work in both headless and headed modes
- [ ] No flaky tests (pass 10/10 runs)
- [ ] Clear test output and error messages

## Testing Commands

```bash
# Run single test in headed mode for debugging
PLAYWRIGHT_HEADLESS=false uv run pytest tests/ui/test_creation_workflow.py::TestBasicCreationFlow::test_complete_creation_workflow -v --no-cov -s

# Run all creation workflow tests
uv run pytest tests/ui/test_creation_workflow.py -v --no-cov

# Run all UI tests
task test-ui

# Run all UI tests in headed mode
task test-ui-headed
```

## Notes & Discoveries

### Key Insights

- ✅ Step 2 creates draft and redirects (303) when no similar models found
- ✅ Unified draft page handles both edit and view modes via query parameter
- ✅ "Update & Preview" button generates model AND switches to view mode
- ✅ HTMX handles mode switching with `HX-Push-Url` header
- ✅ Success banner appears on draft creation

### Current Debugging

- Server logs confirm redirect: `POST /api/finding-models/create/step/2 HTTP/1.1" 303 See Other`
- Target URL: `GET /api/finding-models/drafts/{id}?mode=edit&created=true HTTP/1.1" 200 OK`

### Potential Issues to Watch

- AI operation timeouts (especially similarity check and model generation)
- Race conditions between HTMX operations and URL changes
- Element visibility timing after mode switches

---

**Next Action**: Implement Phase 1 - Fix `test_complete_creation_workflow`

**Delete This File**: After all tests are passing and changes are committed
