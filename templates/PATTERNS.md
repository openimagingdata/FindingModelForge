# Frontend UI Patterns - FindingModelForge

## Button Standards Reference

When creating buttons throughout the application, use the appropriate macro based on the button's purpose and element type.

| Button Type | Macro | Use Case |
|-------------|-------|----------|
| Navigation Link | `flowbite_button()` | Links to other pages (`<a>` element) |
| Form Submit | `action_button()` | Form submissions (`<button type="submit">`) |
| Action Trigger | `action_button()` | JavaScript actions, modals (`<button type="button">`) |
| Icon Only | `flowbite_icon_button()` | Compact actions in tables/cards |

### Macro Locations

- **`flowbite_button()`**: `templates/macros/flowbite_components.html` - Use for navigation links
- **`action_button()`**: `templates/macros/flowbite_components.html` - Use for form buttons and triggers
- **`flowbite_icon_button()`**: `templates/macros/flowbite_components.html` - Use for icon-only buttons
- **`submit_button()`**: `templates/macros/create_workflow_elements.html` - Special submit button with HTMX indicator (creation workflow only)
- **`back_button()`**: `templates/macros/create_workflow_elements.html` - Special back navigation button (creation workflow only)

### Usage Examples

```jinja
{# Navigation link #}
{% from "macros/flowbite_components.html" import flowbite_button %}
{{ flowbite_button("View Details", href="/finding-models/123", type="primary") }}

{# Form submit button #}
{% from "macros/flowbite_components.html" import action_button %}
<form>
    {{ action_button("Save Changes", type="success", button_type="submit") }}
</form>

{# HTMX action button #}
{{ action_button(
    "Delete",
    type="danger",
    size="sm",
    attributes='hx-post="/drafts/123/delete" hx-target="#result" hx-swap="outerHTML"'
) }}

{# Icon-only button #}
{% from "macros/flowbite_components.html" import flowbite_icon_button %}
{% set edit_icon %}<svg>...</svg>{% endset %}
{{ flowbite_icon_button(edit_icon, color="blue", title="Edit") }}
```

### Special Workflow Buttons

The creation workflow uses specialized button macros that include HTMX loading indicators:

```jinja
{# Submit button with loading state #}
{% from "macros/create_workflow_elements.html" import submit_button %}
{{ submit_button(text="Continue", loading_text="Processing...") }}

{# Back navigation button #}
{% from "macros/create_workflow_elements.html" import back_button %}
{{ back_button(step_number=1) }}
```

**Note**: These workflow-specific macros preserve the HTMX indicator pattern and should only be used in the creation workflow templates.

## Clickable Table Rows Pattern

When making entire table rows clickable for navigation, use HTMX attributes directly on the `<tr>` element. This is the
standard pattern used throughout the application.

### ✅ CORRECT Pattern (Using HTMX)

```html
<!-- Table with clickable rows using HTMX -->
<div class="relative overflow-x-auto shadow-md sm:rounded-lg">
  <table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
    <thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
      <tr>
        <th scope="col" class="px-6 py-3">Column 1</th>
        <th scope="col" class="px-6 py-3">Column 2</th>
      </tr>
    </thead>
    <tbody>
      {% for item in items %}
      <tr
        hx-get="/path/to/{{ item.id }}?from=context"
        hx-target="#main-content"
        hx-push-url="true"
        class="bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 cursor-pointer"
      >
        <td class="px-6 py-4 font-medium text-gray-900 whitespace-nowrap dark:text-white">{{ item.field1 }}</td>
        <td class="px-6 py-4">{{ item.field2 }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
```

### Key Requirements

1. **HTMX Attributes on `<tr>`**:
   - `hx-get="/path/to/resource"` - The URL to navigate to
   - `hx-target="#main-content"` - Target element for content swap
   - `hx-push-url="true"` - Update browser URL

2. **CSS Classes**:
   - `cursor-pointer` - Shows pointer cursor on hover
   - `hover:bg-gray-50 dark:hover:bg-gray-600` - Visual feedback on hover

3. **Target Container**:
   - Page must have a `<div id="main-content">` element
   - This is where HTMX will swap the content

4. **Context Parameters**:
   - Add query parameters like `?from=public` for breadcrumb context
   - Preserves navigation flow information

### ❌ INCORRECT Patterns to Avoid

```html
<!-- DON'T use Alpine.js @click -->
<tr @click="window.location.href = '/path'">
  <!-- DON'T use onclick -->
</tr>

<tr onclick="location.href='/path'">
  <!-- DON'T use separate Action column with links -->
  <td><a href="/path">View</a></td>
</tr>
```

### Examples in Codebase

- **Finding Models Table**: `templates/fragments/finding_models_list_content.html`
- **Public Drafts Table**: `templates/drafts_table.html`

### Why This Pattern?

1. **Consistency**: Same pattern across all tables
2. **HTMX Benefits**:
   - Partial page updates (no full page reload)
   - Browser history management
   - Better performance
3. **Accessibility**: Entire row is clickable, larger target area
4. **No JavaScript Required**: HTMX handles everything declaratively
