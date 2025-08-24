# Frontend/UI Development Guide - FindingModelForge

⚠️ **CRITICAL**: ALWAYS use Flowbite components and Alpine.js. NEVER create custom CSS or JavaScript.

## Golden Rules

1. ✅ **Check Flowbite docs FIRST**: https://flowbite.com/docs/
2. ✅ **Use exact HTML structure** from Flowbite examples
3. ✅ **Use Alpine.js for interactivity** - `x-data`, `x-model`, computed properties
4. ❌ **NO custom CSS classes** - Use Tailwind utilities only
5. ❌ **NO custom JavaScript** - Use Alpine.js declaratively

## Template Structure

```
templates/
├── base.html                 # Base layout with Tailwind/Alpine setup
├── components/               # Reusable component templates
│   ├── drafts/              # Draft action results (save, submit, delete)
│   ├── finding_model_creation/  # Multi-step workflow components
│   ├── finding_model_display.html    # Model display component
│   └── finding_model_complete_display.html  # Full display with JSON
├── macros/                  # Jinja2 macros for reusability
│   ├── flowbite_components.html  # Flowbite component wrappers
│   ├── json_accordion.html       # JSON display accordion
│   ├── synonym_manager.html      # Synonym management
│   └── form_validation.html      # Form validation patterns
└── *.html                   # Page templates

```

## Component Usage Patterns

### 1. Always Check for Existing Components

```bash
# Before creating anything new, search for existing components:
grep -r "accordion" templates/
grep -r "badge" templates/macros/
find templates/ -name "*display*"
```

### 2. Reuse Existing Components

```jinja
{# ✅ CORRECT: Reuse existing component #}
{% include 'components/finding_model_display.html' %}

{# ✅ CORRECT: Use existing macro #}
{% from "macros/flowbite_components.html" import alert, badge %}
{{ alert("Success!", type="success") }}

{# ❌ WRONG: Creating duplicate functionality #}
<div class="bg-green-100 text-green-800 rounded">Success!</div>
```

### 3. Flowbite Component Examples

```html
<!-- ✅ CORRECT: Official Flowbite button -->
<button
  type="button"
  class="text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 me-2 mb-2 dark:bg-blue-600 dark:hover:bg-blue-700 focus:outline-none dark:focus:ring-blue-800"
>
  Default
</button>

<!-- ❌ WRONG: Custom button styling -->
<button class="my-custom-button">Click me</button>

<!-- ✅ CORRECT: Flowbite accordion -->
<div id="accordion-collapse" data-accordion="collapse">
  <h2 id="accordion-collapse-heading-1">
    <button
      type="button"
      class="flex items-center justify-between w-full p-5 font-medium rtl:text-right text-gray-500 border border-b-0 border-gray-200 rounded-t-xl focus:ring-4 focus:ring-gray-200 dark:focus:ring-gray-800 dark:border-gray-700 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 gap-3"
      data-accordion-target="#accordion-collapse-body-1"
      aria-expanded="true"
      aria-controls="accordion-collapse-body-1"
    >
      <span>Section Title</span>
      <svg data-accordion-icon class="w-3 h-3 rotate-180 shrink-0" aria-hidden="true">
        <!-- SVG path -->
      </svg>
    </button>
  </h2>
  <div id="accordion-collapse-body-1" class="hidden" aria-labelledby="accordion-collapse-heading-1">
    <div class="p-5 border border-b-0 border-gray-200 dark:border-gray-700 dark:bg-gray-900">
      <!-- Content -->
    </div>
  </div>
</div>

<!-- ❌ WRONG: Custom accordion -->
<div onclick="toggleAccordion()">Click to expand</div>
```

## Alpine.js Patterns

### 1. Reactive Data Binding

```html
<!-- ✅ CORRECT: Alpine.js reactive form -->
<div
  x-data='{
  name: "",
  description: "",
  synonyms: [],
  get isValid() {
    return this.name.length >= 3 && this.description.length > 0;
  },
  get synonymsJson() {
    return JSON.stringify(this.synonyms);
  }
}'
>
  <input type="text" x-model="name" />
  <textarea x-model="description"></textarea>
  <input type="hidden" name="synonyms" x-model="synonymsJson" />
  <button :disabled="!isValid">Submit</button>
</div>

<!-- ❌ WRONG: Manual DOM manipulation -->
<script>
  document.getElementById("form").addEventListener("submit", function () {
    // Manual validation
  })
</script>
```

### 2. Component State Management

```html
<!-- ✅ CORRECT: Computed properties for derived state -->
<div
  x-data='{
  items: [],
  newItem: "",
  get itemCount() { return this.items.length; },
  get hasItems() { return this.items.length > 0; },
  addItem() {
    if (this.newItem) {
      this.items.push(this.newItem);
      this.newItem = "";
    }
  }
}'
>
  <span x-text="itemCount"></span> items
  <div x-show="hasItems">
    <!-- Show items -->
  </div>
</div>
```

### 3. HTMX Integration

```html
<!-- Alpine.js works seamlessly with HTMX -->
<form hx-post="/api/save" hx-target="#result" x-data='{ draft_id: "{{ session_data.draft_id or "" }}" }'>
  <input type="hidden" name="draft_id" x-model="draft_id" />
  <!-- Form fields -->
</form>
```

## Jinja2 Macro Best Practices

### 1. Creating Reusable Macros

```jinja
{# macros/my_component.html #}

{# Purpose: Display a status badge
   Parameters:
   - text: Badge text (required)
   - color: Tailwind color name (default: "blue")
   - size: Size variant "sm", "md", "lg" (default: "md")
#}
{% macro status_badge(text, color="blue", size="md") %}
  {% set size_classes = {
    "sm": "text-xs px-2.5 py-0.5",
    "md": "text-sm px-3 py-1",
    "lg": "text-base px-4 py-1.5"
  } %}
  <span class="bg-{{ color }}-100 text-{{ color }}-800 {{ size_classes[size] }} font-medium rounded dark:bg-{{ color }}-900 dark:text-{{ color }}-300">
    {{ text }}
  </span>
{% endmacro %}
```

### 2. Using Macros

```jinja
{% from "macros/my_component.html" import status_badge %}

{{ status_badge("Active", color="green") }}
{{ status_badge("Pending", color="yellow", size="sm") }}
```

## Available Reusable Components

### Display Components

- `components/finding_model_display.html` - Basic model display
- `components/finding_model_complete_display.html` - Full display with JSON
- `components/drafts/*.html` - Draft action result messages

### Workflow Components

- `components/finding_model_creation/step_*.html` - Creation workflow steps
- `components/finding_model_creation/stepper.html` - Progress indicator

### Macros

#### flowbite_components.html

- `alert(message, type)` - Alert messages
- `badge(text, color)` - Status badges
- `button(text, type, size)` - Buttons

#### json_accordion.html

- `json_accordion(data, id, title)` - Collapsible JSON display with copy/download

#### synonym_manager.html

- `synonym_manager()` - Interactive synonym management
- `synonym_data(initial_synonyms)` - Alpine.js data initialization

#### form_validation.html

- `validation_data(...)` - Form validation state
- `validated_input(...)` - Input with validation
- `validated_textarea(...)` - Textarea with validation

## HTMX Patterns

### 1. Multi-Step Workflow

```html
<!-- Step container for HTMX swapping -->
<div id="step-container">
  <!-- Step content gets swapped here -->
</div>

<!-- Step template -->
<form hx-post="/api/step/{{ next_step }}" hx-target="#step-container" hx-swap="innerHTML">
  <!-- Step content -->
</form>
```

### 2. Component Reinitialization

```javascript
// In src/js/main.js - reinitialize after HTMX swaps
document.addEventListener("htmx:afterSwap", function (event) {
  initFlowbite() // Reinitialize Flowbite components
  if (window.Alpine && event.detail.elt) {
    Alpine.initTree(event.detail.elt) // Process Alpine.js
  }
})
```

## Tailwind CSS Guidelines

### 1. Use Utility Classes

```html
<!-- ✅ CORRECT: Tailwind utilities -->
<div class="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-md dark:bg-gray-800">
  <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">Title</h2>
</div>

<!-- ❌ WRONG: Custom CSS -->
<div class="my-container">
  <h2 class="my-title">Title</h2>
</div>
```

### 2. Dark Mode Support

Always include dark mode variants:

```html
<div class="bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100">
  <!-- Content -->
</div>
```

### 3. Responsive Design

Use responsive prefixes:

```html
<div class="w-full md:w-1/2 lg:w-1/3 px-4">
  <!-- Responsive column -->
</div>
```

## Component Development Process

### Before Creating New Components

1. **Search existing components**

   ```bash
   find templates/ -name "*.html" | xargs grep -l "similar-functionality"
   ```

2. **Check Flowbite docs**
   - Visit https://flowbite.com/docs/
   - Find the exact component needed
   - Copy the official HTML structure

3. **Check existing macros**

   ```bash
   ls templates/macros/
   ```

4. **Consider extending existing components**
   - Can you add parameters to an existing macro?
   - Can you compose existing components?

### Creating New Components

If you must create a new component:

1. **Use Flowbite as base**
   - Start with Flowbite HTML structure
   - Use exact Flowbite CSS classes
   - Add Alpine.js for interactivity

2. **Create as macro for reusability**

   ```jinja
   {# templates/macros/new_component.html #}
   {% macro component_name(param1, param2="default") %}
     <!-- Flowbite-based HTML -->
   {% endmacro %}
   ```

3. **Document parameters**

   ```jinja
   {# Purpose: What this does
      Parameters:
      - param1: Description (required)
      - param2: Description (optional, default: "value")
   #}
   ```

4. **Test dark mode and responsiveness**

## Common Pitfalls to Avoid

1. ❌ **Creating custom validation JavaScript**
   - Use Alpine.js computed properties instead

2. ❌ **Writing onclick handlers**
   - Use Alpine.js `@click` directives

3. ❌ **Making custom modals or dropdowns**
   - Use Flowbite's data-attribute driven components

4. ❌ **Using jQuery or vanilla JS for DOM manipulation**
   - Alpine.js handles reactivity automatically

5. ❌ **Creating custom CSS classes**
   - Compose Tailwind utilities instead

## Testing UI Components

### Visual Testing

1. Check in light and dark modes
2. Test on mobile, tablet, desktop sizes
3. Verify Flowbite components initialize
4. Test Alpine.js reactivity

### Accessibility

1. Use semantic HTML
2. Include ARIA attributes
3. Test keyboard navigation
4. Verify screen reader compatibility

## Quick Reference

### Find Flowbite Component

```bash
# Search Flowbite docs for component type
open https://flowbite.com/docs/
```

### Check Alpine.js Syntax

```bash
# Alpine.js documentation
open https://alpinejs.dev/directives/[directive-name]
```

### Test Template Rendering

```bash
# Run dev server and check
task dev
open http://localhost:8000/[page-route]
```

### Rebuild CSS

```bash
# After changing Tailwind classes
npm run build:css
# or
npm run watch:css  # For development
```

## Resources

- **Flowbite Components**: https://flowbite.com/docs/
- **Alpine.js Docs**: https://alpinejs.dev/
- **Tailwind CSS**: https://tailwindcss.com/docs
- **Jinja2 Templates**: https://jinja.palletsprojects.com/
