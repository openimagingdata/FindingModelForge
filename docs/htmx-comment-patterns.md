# HTMX Patterns for Comment System

## Core HTMX Attributes

### Comment Section Container

```html
<!-- Main comment thread container -->
<div id="comment-thread-finding_model-{{ oifm_id }}"
     class="comments-section">
    <!-- Comments content here -->
</div>
```

### Add Comment Form

```html
<form hx-post="/finding-models/{{ slug }}/comments"
      hx-target="#comment-thread-finding_model-{{ oifm_id }}"
      hx-swap="outerHTML"
      hx-trigger="submit">
    <input type="hidden" name="parent_comment_id" value="">
    <textarea name="content" 
              x-model="commentText"
              maxlength="2000"></textarea>
    <button type="submit" 
            :disabled="!commentText.trim() || commentText.length > 2000">
        Comment
    </button>
</form>
```

### Reply Form Pattern

```html
<!-- Hidden reply form template -->
<template x-if="replyingTo === '{{ comment.id }}'">
    <form hx-post="/finding-models/{{ slug }}/comments"
          hx-target="#comment-thread-finding_model-{{ oifm_id }}"
          hx-swap="outerHTML">
        <input type="hidden" name="parent_comment_id" value="{{ comment.id }}">
        <textarea name="content"></textarea>
        <button type="submit">Post Reply</button>
        <button type="button" @click="replyingTo = null">Cancel</button>
    </form>
</template>
```

### Report Comment

```html
<button hx-post="/finding-models/{{ slug }}/comments/{{ comment.id }}/report"
        hx-target="#alert-container"
        hx-swap="beforeend"
        hx-confirm="Report this comment as inappropriate?">
    Report ⚑
</button>
```

## Alpine.js Integration

### Comment Form State

```html
<div x-data="{
    commentText: '',
    replyingTo: null,
    get charCount() { return this.commentText.length },
    get canSubmit() { 
        return this.commentText.trim().length > 0 && 
               this.commentText.length <= 2000 
    }
}">
    <!-- Form content -->
    <span x-text="charCount + '/2000'"></span>
</div>
```

## Response Patterns

### Success Response (Full Thread Swap)

```python
# In router endpoint
async def add_comment(...):
    # Add comment to thread
    updated_thread = await comment_repo.add_comment(...)
    
    # Return entire comment section HTML
    return templates.TemplateResponse(
        "components/comment_thread.html",
        {
            "thread": updated_thread,
            "reference_type": "finding_model",
            "reference_id": oifm_id,
            "current_user": user,
        }
    )
```

### Error/Alert Response

```python
# For report endpoint
async def report_comment(...):
    try:
        await comment_repo.report_comment(...)
        alert_html = '''
        <div class="alert alert-success" role="alert">
            Comment reported. Thank you for helping maintain our community standards.
        </div>
        '''
    except Exception as e:
        alert_html = '''
        <div class="alert alert-danger" role="alert">
            Failed to report comment. Please try again.
        </div>
        '''
    return HTMLResponse(alert_html)
```

## Rate Limiting Response

```python
# When rate limited
if not rate_limit_ok:
    return HTMLResponse(
        '''
        <div class="alert alert-warning" role="alert">
            You can only post 3 comments per minute. Please wait before commenting again.
        </div>
        ''',
        status_code=429
    )
```

## Loading States

```html
<!-- Show spinner during request -->
<form hx-post="/finding-models/{{ slug }}/comments"
      hx-indicator="#comment-spinner">
    <!-- form content -->
</form>

<div id="comment-spinner" class="htmx-indicator">
    <div class="spinner-border" role="status">
        <span class="visually-hidden">Loading...</span>
    </div>
</div>
```

## Best Practices

1. **Always use outerHTML swap** for comment thread updates to replace entire section
2. **Use unique IDs** combining reference type and ID to avoid conflicts
3. **Preserve form state** with Alpine.js during HTMX swaps
4. **Show loading indicators** for better UX during async operations
5. **Use hx-confirm** for destructive actions like reporting
6. **Return proper HTTP status codes** (429 for rate limit, 403 for forbidden)

## Error Handling

```html
<!-- Global error handler -->
<div hx-on::htmx:response-error="
    if (event.detail.xhr.status === 429) {
        alert('Rate limit exceeded. Please wait a moment before commenting again.');
    } else if (event.detail.xhr.status === 403) {
        alert('You are not allowed to perform this action.');
    } else {
        alert('An error occurred. Please try again.');
    }
">
    <!-- Comment section content -->
</div>
```

## Testing HTMX Comments

```python
# In Playwright tests
async def test_add_comment():
    # Fill comment form
    await page.fill('textarea[name="content"]', 'Test comment')
    
    # Submit and wait for HTMX swap
    await page.click('button:has-text("Comment")')
    await wait_for_htmx_swap(page, '.comment-item:has-text("Test comment")')
    
    # Verify comment appears
    await expect(page.locator('.comment-item')).to_contain_text('Test comment')
```