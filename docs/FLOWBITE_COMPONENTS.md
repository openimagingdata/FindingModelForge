# Flowbite Components Reference

This document catalogs the working Flowbite components in the FindingModelForge codebase. **Always reference these patterns instead of creating custom implementations.** *Update this document when adding new Flowbite components*

## Accordion Components

### ✅ Working Example: JSON Data Accordion

**File:** `templates/finding_model_display.html` (lines 90-105)

```html
<div id="accordion-json" data-accordion="collapse"
     data-active-classes="bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
     data-inactive-classes="text-gray-500 dark:text-gray-400">
  <h2 id="accordion-json-heading-1">
    <button type="button"
            class="flex items-center justify-between w-full p-6 font-medium rtl:text-right text-gray-500 border-b border-gray-200 dark:border-gray-700 dark:text-gray-400 gap-3 hover:bg-gray-50 dark:hover:bg-gray-700 focus:ring-4 focus:ring-gray-200 dark:focus:ring-gray-800"
            data-accordion-target="#accordion-json-body-1"
            aria-expanded="false"
            aria-controls="accordion-json-body-1">
      <span class="text-lg font-semibold text-gray-900 dark:text-white">JSON Data</span>
      <svg data-accordion-icon class="w-3 h-3 rotate-180 shrink-0" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 10 6">
        <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5 5 1 1 5"/>
      </svg>
    </button>
  </h2>
  <div id="accordion-json-body-1" class="hidden" aria-labelledby="accordion-json-heading-1">
    <div class="p-6 border-b border-gray-200 dark:border-gray-700">
      <!-- Content here -->
    </div>
  </div>
</div>
```

**Key Pattern Elements:**

- Container has `data-accordion="collapse"`
- Button has `data-accordion-target="#target-id"`
- Content div has matching `id="target-id"`
- Icon has `data-accordion-icon` attribute
- Proper ARIA attributes for accessibility

## Initialization Patterns

### ✅ For Dynamic Content

**File:** `templates/create_finding_model.html` (lines 641-651)

```javascript
// Use the official initFlowbite function to initialize all components
// based on their data attributes
if (typeof initFlowbite === 'function') {
    initFlowbite();
} else if (window.initFlowbite) {
    window.initFlowbite();
} else {
    console.warn('initFlowbite function not found');
}
```

**When to Use:**

- After dynamically injecting HTML content
- After Alpine.js updates the DOM
- Use `this.$nextTick()` in Alpine.js to ensure DOM is updated first

## Common Anti-Patterns to Avoid

### ❌ Custom Toggle Functions

```javascript
// DON'T DO THIS
function toggleAccordion() {
    const content = document.getElementById('content');
    content.classList.toggle('hidden');
}
```

### ❌ Manual Icon Rotation

```javascript
// DON'T DO THIS
function rotateIcon() {
    const icon = document.getElementById('icon');
    icon.classList.toggle('rotate-180');
}
```

### ❌ Custom Event Handlers

```html
<!-- DON'T DO THIS -->
<button onclick="customToggle()">Toggle</button>
```

## Before Adding New Components

1. **Check Context7** for Flowbite documentation
2. **Search existing codebase** for similar working components
3. **Use data attributes** instead of custom JavaScript
4. **Test with `initFlowbite()`** for dynamic content

## Component Inventory

- ✅ **Accordion**: `finding_model_display.html`, `finding_model_full_display.html`
- 🔍 **Modal**: (Add when implemented)
- 🔍 **Dropdown**: (Add when implemented)
- 🔍 **Tabs**: (Add when implemented)
