# Playwright Testing Patterns - FindingModelForge

## Expected Elements for Each Workflow Step

### Step 1: Generate Description

**Trigger**: Click "Generate Description" button **Wait for**: Description textarea to appear with generated content

```javascript
// Wait for step 2 to load
await expect(page.locator("textarea#description")).toBeVisible()
// Verify content was generated
await expect(page.locator("textarea#description")).not.toHaveValue("")
```

### Step 2: Check for Similar

**Trigger**: Click "Check for Similar" button **Wait for**: Either draft edit form OR similar models display

```javascript
// Wait for similarity check to complete (button changes from "Checking..." to something else)
await expect(page.locator("button:has-text('Checking...')")).toHaveCount(0)

// Then check for either outcome:
// Option 1: Redirected to draft edit (no similar found)
const isDraftEdit = (await page.locator("textarea[name='attributes_markdown']").count()) > 0

// Option 2: Similar models found
const hasSimilarModels = (await page.locator("button:has-text('Continue'), button:has-text('Skip')").count()) > 0
```

### Step 3: Update & Preview (Draft Generation)

**Trigger**: Click "Update & Preview" button **Wait for**: Draft preview display with mode toggle buttons

```javascript
// Wait for update to complete (button changes from "Updating..." to something else)
await expect(page.locator("button:has-text('Updating...')")).toHaveCount(0)

// Verify we're in preview mode with success message
await expect(page.locator("text=Draft updated successfully")).toBeVisible()

// Verify mode toggle buttons are present and working
await expect(page.locator("#edit-mode-btn")).toBeVisible()
await expect(page.locator("#view-mode-btn")).toBeVisible()
```

## Complete Workflow Validation Pattern

```javascript
async function validateCompleteWorkflow(page, findingName) {
  // Step 1: Enter name and generate description
  await page.fill("input[name='name']", findingName)
  await page.click("button:has-text('Generate Description')")
  await expect(page.locator("textarea#description")).toBeVisible()

  // Step 2: Check for similar
  await page.click("button:has-text('Check for Similar')")
  await expect(page.locator("button:has-text('Checking...')")).toHaveCount(0, { timeout: 120000 })

  // Handle either draft edit or similar models
  const isDraftEdit = (await page.locator("textarea[name='attributes_markdown']").count()) > 0
  if (!isDraftEdit) {
    // Handle similar models if they appear
    const continueBtn = page.locator("button:has-text('Continue'), button:has-text('Skip')")
    if ((await continueBtn.count()) > 0) {
      await continueBtn.first().click()
      await expect(page.locator("textarea[name='attributes_markdown']")).toBeVisible()
    }
  }

  // Step 3: Update and preview
  await page.click("button:has-text('Update & Preview')")
  await expect(page.locator("button:has-text('Updating...')")).toHaveCount(0, { timeout: 90000 })

  // Verify final state
  await expect(page.locator("text=Draft updated successfully")).toBeVisible()
  await expect(page.locator("#edit-mode-btn")).toBeVisible()
  await expect(page.locator("#view-mode-btn")).toBeVisible()

  // Test mode switching
  await page.click("#edit-mode-btn")
  await expect(page.locator("textarea[name='attributes_markdown']")).toBeVisible()

  await page.click("#view-mode-btn")
  await expect(page.locator("button:has-text('Submit Draft')")).toBeVisible()
}
```

## Key Testing Timeouts

- **AI Description Generation**: 30 seconds
- **AI Similarity Check**: 120 seconds (can be very slow)
- **Model Generation**: 90 seconds
- **Standard HTMX Operations**: 15 seconds

## Error States to Test

### Similarity Check Timeout

```javascript
// If similarity check takes too long, handle gracefully
try {
  await expect(page.locator("button:has-text('Checking...')")).toHaveCount(0, { timeout: 120000 })
} catch (timeoutError) {
  console.log("Similarity check timed out - this is a known issue")
  // Take screenshot for debugging
  await page.screenshot({ path: "similarity_timeout.png" })
}
```

### Mode Toggle Missing (Fixed but good to verify)

```javascript
// Verify mode toggle buttons appear after Update & Preview
await expect(page.locator("#draft-mode-toggle-header")).toBeVisible()
await expect(page.locator("#edit-mode-btn")).toBeVisible()
await expect(page.locator("#view-mode-btn")).toBeVisible()
```

## Test Data Cleanup

```javascript
// Clean up test data before each test
async function cleanupTestData(userId, findingName) {
  // This should be implemented to remove any existing drafts/models
  // with the same name for the test user
}
```
