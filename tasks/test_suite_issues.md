# UI Test Suite Issues and HTMX OOB Error Fix

## Issue 1: HTMX Out-of-Band Swap Error in Creation Workflow

### Status: ✅ FIXED (November 6, 2025)

### Problem
When clicking "Make Public" from the creation workflow, an `htmx:oobErrorNoTarget` error occurs in the browser console. The operation completes successfully, but the error is visible to users and indicates a structural problem with our HTMX response handling.

### Root Cause
Located in `app/routers/drafts/workflows.py:75-96`, the `make_draft_public` endpoint performs a standard HTTP redirect:

```python
@router.post("/{draft_id}/make-public")
async def make_draft_public(
    draft_id: str,
    current_user: CurrentUserDep,
    draft_service: DraftServiceDep,
    cache: CacheDep,
) -> Response:
    """Make a draft public for review."""
    try:
        await draft_service.make_public_draft(draft_id, current_user.id)
        with contextlib.suppress(Exception):
            await cache.delete("public_drafts_list")

        # Redirect to the draft page
        return RedirectResponse(url=f"/drafts/{draft_id}", status_code=303)
```

The problem occurs because:

1. The redirect causes the browser to make a new GET request to `/drafts/{draft_id}`
2. The `HX-Current-URL` header does not persist through HTTP redirects
3. In `app/routers/drafts/views.py:148-170`, the `unified_draft_page` endpoint tries to detect if the request came from the creation workflow using `HX-Current-URL`:

```python
current_url = request.headers.get("HX-Current-URL", "")
from_creation = "create-finding-model" in current_url
```

4. Since the header is lost, `from_creation` is always `False`, so `include_oob` is set to `True`
5. The `build_htmx_response_with_oob` function in `app/routers/drafts/helpers.py:190-247` then includes OOB swaps for:
   - `#draft-mode-toggle-header` - does not exist in creation workflow page
   - `#page-title` - does not exist in creation workflow page
6. HTMX throws `htmx:oobErrorNoTarget` when it cannot find these elements to swap

### Solution Implemented
Used **query parameter approach** to preserve context through HTTP redirects:

**Changes Made:**
1. **`app/routers/drafts/workflows.py:92`** - Added `?from=creation&success=made_public` to redirect URL
2. **`app/routers/drafts/views.py:152-154, 170`** - Check query param instead of header, pass to template
3. **`templates/components/draft_preview_content.html:11-15`** - Context-aware success message

**Why Query Parameters:**
- Survive HTTP 303 redirects (unlike headers)
- Explicit and debuggable
- Work with browser back/forward buttons
- Standard web pattern

**Verification:**
- ✅ Manual browser test: No `htmx:oobErrorNoTarget` error in console
- ✅ Success message appears: "Draft made public successfully!"
- ✅ Status changes from "Draft" to "Public"
- ✅ Unit tests passing (547 tests)

**Bonus Feature Added:**
- Green success alert now appears after "Make Public" action
- Context-aware message text based on draft status
- Improves UX by providing clear confirmation

## Issue 2: Creation Workflow Test Quality Problems

### Problem
The main end-to-end test for the creation workflow explicitly avoids testing the submission functionality, which is the most critical part of the workflow.

### Specific Issues Found

#### 1. Incomplete End-to-End Test
In `tests/ui/test_creation_workflow.py:144`, the `test_complete_creation_workflow` test contains this comment:

```python
# Note: We're not testing the actual submission since it had HTMX errors in manual testing
# The workflow successfully creates the draft, makes it public, and shows it ready for submission
```

The test stops before testing submission, meaning **the most important user action is not covered by our main integration test**.

#### 2. Conditional Logic Allows Tests to Pass When Skipping Sections
In `tests/ui/test_creation_workflow.py:303`, the test contains conditional logic:

```python
if await edit_mode_btn.count() > 0:
    # Test edit → preview cycle using mode toggle buttons
    ...
```

This pattern allows tests to silently skip entire sections if expected elements don't exist, rather than failing and alerting us to problems.

#### 3. Unrealistic Timeouts for Mocked Operations
In `tests/ui/utils.py:461-494`, the `wait_for_ai_completion_and_swap` function uses a 60-second default timeout:

```python
async def wait_for_ai_completion_and_swap(
    page: Page, button_text_prefix: str, expected_element: str, timeout: int = 60000
) -> None:
    """Wait for AI button to complete processing and HTMX to swap new content."""
    await page.wait_for_function(
        f"""() => {{
            const buttons = Array.from(document.querySelectorAll('#main-content button'));
            ...
        }}""",
        timeout=timeout,  # 60 seconds
    )
```

Since our UI tests mock AI responses (via test user ID 999999), these operations should return nearly instantly. The 60-second timeout masks potential problems and makes tests unnecessarily slow.

### Impact
These issues mean:
1. **False confidence**: Tests pass but don't validate the complete workflow
2. **Silent failures**: Tests can skip broken sections without alerting developers
3. **Slow feedback**: Long timeouts hide performance issues
4. **Production risk**: The submission workflow that real users depend on is not covered by automated tests

### Recommendations

1. ✅ **Fix the HTMX OOB error** (Issue 1 above) - COMPLETE
2. **Remove conditional logic**: Tests should fail loudly when expected elements are missing
3. **Reduce timeouts for mocked operations**: Use shorter timeouts (e.g., 5 seconds) for operations that use mock data
4. **Complete the end-to-end test**: Update `test_complete_creation_workflow` to test "Make Public" action
5. **Add explicit assertions**: Replace conditional checks with explicit assertions about what should exist on the page
6. **Verify success message**: Assert that success alert appears and contains correct text
7. **Verify no console errors**: Check that `htmx:oobErrorNoTarget` does not appear in console

### Test Files Requiring Attention
- `tests/ui/test_creation_workflow.py` - Main workflow tests with incomplete coverage
- `tests/ui/utils.py` - Helper functions with unrealistic timeouts
- Any other tests using `if element.count() > 0:` pattern for conditional logic

### Required Test Assertions for "Make Public"

When updating `test_complete_creation_workflow`, the test MUST verify:

1. **No HTMX OOB Errors**:
   ```python
   # Check console for errors
   console_messages = await page.context.console_messages()
   htmx_errors = [msg for msg in console_messages if 'oobErrorNoTarget' in msg.text]
   assert len(htmx_errors) == 0, f"Found HTMX OOB errors: {htmx_errors}"
   ```

2. **Success Alert Appears**:
   ```python
   success_alert = page.locator("#success-alert")
   await expect(success_alert).to_be_visible()
   await expect(success_alert).to_contain_text("Draft made public successfully!")
   ```

3. **Status Changes to Public**:
   ```python
   status_text = page.locator("text=Status: Public")
   await expect(status_text).to_be_visible()
   ```

4. **Success Alert is Dismissible**:
   ```python
   close_button = success_alert.locator('[data-dismiss-target="#success-alert"]')
   await close_button.click()
   await expect(success_alert).not_to_be_visible()
   ```

5. **URL Contains Success Parameter** (optional verification):
   ```python
   assert "success=made_public" in page.url or "from=creation" in page.url
   ```
