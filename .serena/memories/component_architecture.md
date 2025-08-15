# Component Architecture and Reuse Patterns

## Overview
The application uses a component-based architecture with reusable Jinja2 macros and templates for consistency and maintainability.

## Component Hierarchy

### 1. Display Components
```
templates/components/
├── finding_model_complete_display.html    # Full display + JSON accordion
├── finding_model_display.html             # Formatted display only
└── finding_model_creation/                # Multi-step workflow
    ├── step_base.html                      # Base template for all steps
    ├── step_1_enter_name.html
    ├── step_2_edit_description.html
    ├── step_3_review_similar.html
    ├── step_4_edit_attributes.html
    └── step_5_review_model.html
```

### 2. Macro Library
```
templates/macros/
├── json_accordion.html         # Flowbite JSON accordion with copy/download
├── form_validation.html        # Alpine.js form validation patterns
├── synonym_manager.html        # Interactive synonym management
├── app_components.html         # Application-specific components
├── flowbite_components.html    # Flowbite component wrappers
└── create_workflow_elements.html  # Workflow navigation elements
```

## Usage Patterns

### 1. Complete Model Display
```jinja
{# Use everywhere finding models need full display #}
{% set finding_model = session_data.final_model %}
{% include 'components/finding_model_complete_display.html' %}
```

### 2. JSON Accordion
```jinja
{% from 'macros/json_accordion.html' import json_accordion %}
{{ json_accordion(finding_model, "finding-model-json", "JSON Data") }}
```

Features:
- Proper Flowbite accordion styling
- Copy to clipboard functionality
- Download as JSON file
- Syntax highlighting for JSON

### 3. Synonym Management
```jinja
{% from 'macros/synonym_manager.html' import synonym_manager, synonym_data %}

<div x-data='{{ synonym_data(initial_synonyms) }}'>
  {{ synonym_manager() }}
  <input type="hidden" name="synonyms" x-model="synonymsJson">
</div>
```

Features:
- Alpine.js reactive management
- Visual badge display
- Add/remove functionality
- JSON serialization for forms

### 4. Form Validation
```jinja
{% from 'macros/form_validation.html' import validation_data, validated_input %}

<div x-data='{{ validation_data(initial_name="") }}'>
  {{ validated_input("name", "Finding Name", minlength=3, maxlength=200) }}
</div>
```

## Component Discovery Process

Before creating new components:

1. **Search existing components**:
   ```bash
   find templates/ -name "*.html" | grep -E "(display|card|list)"
   grep -r "accordion" templates/
   grep -r "badge" templates/macros/
   ```

2. **Check for similar functionality**:
   - `templates/components/` - Full page sections
   - `templates/macros/` - Reusable UI elements

3. **Reuse patterns**:
   ```jinja
   {# ✅ CORRECT: Reuse existing component #}
   {% include 'components/finding_model_display.html' %}
   
   {# ❌ WRONG: Recreating existing functionality #}
   <div class="bg-green-100 text-green-800 px-3 py-1 rounded">Success</div>
   ```

## Component Guidelines

### 1. Flowbite Compliance
- **Always use Flowbite components** from https://flowbite.com/docs/components/
- **Copy exact HTML structure** and CSS classes
- **Use data attributes** for component behavior
- **No custom CSS** or JavaScript

### 2. Alpine.js Integration
```javascript
// ✅ CORRECT: Reactive data binding
x-data='{
  items: ["item1", "item2"],
  get itemsJson() { return JSON.stringify(this.items); }
}'

// Use x-model for form submission
<input type="hidden" name="items" x-model="itemsJson">
```

### 3. Template Structure
```jinja
{# Component documentation #}
{# Purpose: Brief description
   Parameters:
   - param1: Description (required)
   - param2: Description (optional, default: "value")
#}
{% macro my_component(param1, param2="default") %}
  <!-- Flowbite-compliant HTML -->
  <div class="exact-flowbite-classes">
    {{ param1 }}
  </div>
{% endmacro %}
```

## Testing Components

### 1. Unit Testing
- Test macro parameter handling
- Verify HTML structure output
- Check default values

### 2. Integration Testing
- Test component interaction with Alpine.js
- Verify HTMX compatibility
- Test responsive behavior

### 3. Accessibility Testing
- ARIA attributes present
- Keyboard navigation works
- Screen reader compatibility

## Performance Considerations

1. **Component Caching**: Jinja2 caches compiled templates
2. **Minimal JavaScript**: Use Alpine.js declaratively
3. **CSS Efficiency**: Tailwind purges unused classes
4. **Template Inheritance**: Reduces duplication

## Migration Notes

After the refactoring:
- **Removed**: 5 old JSON API endpoints
- **Consolidated**: 40+ lines of duplicate markdown generation
- **Added**: Reusable helper functions
- **Improved**: Component consistency across workflow

The architecture now supports:
- Easy component discovery and reuse
- Consistent styling with Flowbite
- Reactive behavior with Alpine.js
- Maintainable template structure