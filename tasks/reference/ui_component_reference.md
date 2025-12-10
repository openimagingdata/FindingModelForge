# UI Component Reference

This document provides a quick reference for all available macros and when to use them.

## Location: `templates/macros/flowbite_components.html`

### Buttons

#### `flowbite_button` - Navigation Links
**Use for**: Links that navigate to another page (renders `<a>` element)

```jinja
{% from "macros/flowbite_components.html" import flowbite_button %}

{{ flowbite_button(
    text="Create Model",
    href="/create/step/1",
    type="primary",           {# primary|secondary|success|warning|danger|dark #}
    size="default",           {# xs|sm|default|lg #}
    icon='<svg>...</svg>',    {# Optional SVG icon #}
    icon_position="left",     {# left|right #}
    disabled=false,
    target_blank=false
) }}
```

#### `action_button` - Form/JS Actions
**Use for**: Buttons that trigger actions (renders `<button type="button">`)

```jinja
{% from "macros/flowbite_components.html" import action_button %}

{{ action_button(
    text="Submit",
    type="primary",           {# primary|secondary|success|warning|danger|dark #}
    size="default",           {# xs|sm|default|lg #}
    icon='<svg>...</svg>',    {# Optional SVG icon #}
    icon_position="left",     {# left|right #}
    disabled=false,
    classes="",               {# Additional CSS classes #}
    attributes='hx-post="/api/action" hx-target="#result"'  {# HTMX or other attrs #}
) }}
```

#### `flowbite_icon_button` - Icon-Only Buttons
**Use for**: Compact icon buttons in tables/cards

```jinja
{% from "macros/flowbite_components.html" import flowbite_icon_button %}

{% set edit_icon %}
<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5"/>
</svg>
{% endset %}

{{ flowbite_icon_button(
    icon=edit_icon,
    color="primary",          {# blue|green|red|yellow|gray|primary #}
    size="default",           {# xs|sm|default|lg #}
    title="Edit",             {# Tooltip and aria-label #}
    href="/edit/123",         {# If provided, renders <a>, otherwise <button> #}
    attributes='data-modal-toggle="modal-id"'
) }}
```

### Badges

#### `flowbite_badge` - Status Indicators
**Use for**: Tags, status labels, counts

```jinja
{% from "macros/flowbite_components.html" import flowbite_badge %}

{{ flowbite_badge(
    text="Draft",
    color="yellow",           {# default|gray|red|green|yellow|indigo|purple|pink|blue #}
    size="default",           {# xs|sm|default #}
    pill=false,               {# true for rounded-full #}
    href="/filter/draft"      {# Optional: makes it a link #}
) }}
```

**Badge Color Reference**:
| Status | Color | Example |
|--------|-------|---------|
| Draft | `yellow` | Work in progress |
| Public | `blue` | Visible to others |
| Submitted | `green` | Locked/finalized |
| Error | `red` | Problem state |
| Info | `default`/`blue` | Informational |

### Alerts

#### `alert` - Inline Messages
**Use for**: Validation errors, success messages, warnings

```jinja
{% from "macros/flowbite_components.html" import alert %}

{{ alert(
    message="Profile saved successfully!",
    type="success",           {# info|success|warning|error #}
    dismissible=true          {# Adds Alpine.js close button #}
) }}
```

### Navigation

#### `breadcrumb` - Page Location
**Use for**: Navigation breadcrumbs

```jinja
{% from "macros/flowbite_components.html" import breadcrumb %}

{% set home_icon %}
<svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
    <path d="m19.707 9.293-2-2-7-7a1 1 0 0 0-1.414 0l-7 7-2 2a1 1 0 0 0 1.414 1.414L2 10.414V18a2 2 0 0 0 2 2h3a1 1 0 0 0 1-1v-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v4a1 1 0 0 0 1 1h3a2 2 0 0 0 2-2v-7.586l.293.293a1 1 0 0 0 1.414-1.414Z"/>
</svg>
{% endset %}

{{ breadcrumb([
    {"text": "Home", "href": url_for('index'), "icon": home_icon},
    {"text": "Models", "href": url_for('finding_models')},
    {"text": "Pulmonary Nodule"}  {# Last item is current page, no href #}
]) }}

{# HTMX-enabled breadcrumb items #}
{{ breadcrumb([
    {"text": "Home", "href": "/", "icon": home_icon,
     "hx_get": "/api/home", "hx_target": "#main-content", "hx_push_url": "/"},
    {"text": "Current Page"}
]) }}
```

### Cards

#### `flowbite_card` - Content Blocks
**Use for**: Feature cards, information sections

```jinja
{% from "macros/flowbite_components.html" import flowbite_card %}

{% set card_content %}
<p>Card body content here...</p>
{% endset %}

{{ flowbite_card(
    title="What is a Finding Model?",
    content=card_content,
    href="/learn-more",           {# Optional: make title linkable #}
    cta_text="Learn More",        {# Optional call-to-action #}
    cta_href="/docs",
    icon='<svg>...</svg>',        {# Optional header icon #}
    shadow="sm"                   {# none|sm|default|md|lg #}
) }}
```

### Lists

#### `flowbite_icon_list` - Bulleted Lists
**Use for**: Feature lists, checklists

```jinja
{% from "macros/flowbite_components.html" import flowbite_icon_list %}

{{ flowbite_icon_list([
    "First feature",
    "Second feature",
    "Third feature"
]) }}
```

### Form Components

#### `form_input` - Text Inputs (non-Alpine)
**Use for**: Simple forms without reactive validation

```jinja
{% from "macros/flowbite_components.html" import form_input %}

{{ form_input(
    name="email",
    type="email",
    label="Email Address",
    placeholder="you@example.com",
    value=user.email,
    required=true,
    disabled=false,
    readonly=false,
    classes="",
    attributes=""
) }}
```

#### `form_textarea` - Multiline Text (non-Alpine)
**Use for**: Simple textarea without reactive validation

```jinja
{% from "macros/flowbite_components.html" import form_textarea %}

{{ form_textarea(
    name="description",
    label="Description",
    placeholder="Enter description...",
    value=model.description,
    rows=4,
    required=true
) }}
```

---

## Location: `templates/macros/form_validation.html`

### Validated Form Components (with Alpine.js)

#### `validation_data` - Alpine.js Form State
**Use for**: Setting up reactive form validation

```jinja
{% from "macros/form_validation.html" import validation_data %}

<div x-data='{{ validation_data(
    initial_name="",
    initial_description="",
    initial_attributes="",
    has_no_generated_json=false
) }}'>
    {# Form content with x-model bindings #}
    <button :disabled="!canSubmit">Submit</button>
</div>
```

**Provides computed properties**:
- `isNameValid` - name 3-200 chars
- `isDescriptionValid` - description 10-1000 chars
- `isAttributesValid` - attributes 20+ chars
- `hasChanges` - any field changed from original
- `canSubmit` - all valid AND (changes OR fresh draft)
- `isFormValid()` - method alias for button bindings

#### `validated_input` - Input with Validation State
```jinja
{% from "macros/form_validation.html" import validated_input %}

{{ validated_input(
    name="name",
    label="Finding Name",
    value=model.name,
    type="text",
    placeholder="e.g., Pulmonary Nodule",
    required=true,
    minlength=3,
    maxlength=200
) }}
```

#### `validated_textarea` - Textarea with Validation
```jinja
{% from "macros/form_validation.html" import validated_textarea %}

{{ validated_textarea(
    name="description",
    label="Description",
    value=model.description,
    rows=4,
    placeholder="Describe the finding...",
    required=true,
    minlength=10,
    maxlength=1000
) }}
```

---

## Location: `templates/macros/unified_form_data.html`

#### `unified_form_data` - Complete Draft Form State
**Use for**: Draft editing forms with description, attributes, synonyms

```jinja
{% from "macros/unified_form_data.html" import unified_form_data %}

<div x-data='{{ unified_form_data(
    initial_description=draft.inputs.description,
    initial_attributes=draft.inputs.attributes_markdown,
    initial_synonyms=draft.inputs.synonyms or [],
    has_no_generated_json=(not draft.generated_json)
) }}'>
    {# Form with description, attributes, synonyms #}
</div>
```

**Provides**:
- All validation from `validation_data`
- Synonym management (`addSynonym()`, `removeSynonym()`, `getSynonymsJson()`)
- Change tracking for synonyms (`synonymsChanged`)

---

## Location: `templates/macros/create_workflow_elements.html`

### Workflow-Specific Components

#### `htmx_form` - HTMX Form Wrapper
```jinja
{% from "macros/create_workflow_elements.html" import htmx_form %}

{% call htmx_form(step_number=2) %}
    {# Form content #}
{% endcall %}
```

#### `submit_button` - Submit with Loading Indicator
```jinja
{% from "macros/create_workflow_elements.html" import submit_button %}

{{ submit_button(
    text="Generate Description",
    loading_text="Generating...",
    disabled=false
) }}
```

#### `back_button` - HTMX Back Navigation
```jinja
{% from "macros/create_workflow_elements.html" import back_button %}

{{ back_button(
    step_number=1,
    text="← Back"
) }}
```

#### `status_indicator` - Availability Check Result
```jinja
{% from "macros/create_workflow_elements.html" import status_indicator %}

{{ status_indicator(
    success=name_available,
    message="Name is available" if name_available else "Name already exists"
) }}
```

---

## Location: `templates/macros/synonym_manager.html`

#### `synonym_manager` - Interactive Synonym Editor
**Use for**: Managing synonym lists in forms

```jinja
{% from "macros/synonym_manager.html" import synonym_manager %}

{# Must be inside x-data with synonym state #}
{{ synonym_manager() }}
```

---

## Location: `templates/macros/confirmation_modal.html`

#### `confirmation_modal` - Flowbite Confirmation Dialog
```jinja
{% from "macros/confirmation_modal.html" import confirmation_modal %}

{{ confirmation_modal(
    modal_id="delete-modal-123",
    title="Delete Draft",
    message="Are you sure? This cannot be undone.",
    confirm_text="Yes, delete",
    cancel_text="Cancel",
    confirm_color="red",          {# primary|blue|green|red #}
    icon_type="danger",           {# warning|danger|info #}
    hx_post="/drafts/123/delete",
    hx_target="#draft-card-123",
    hx_swap="delete",
    extra_attributes=""
) }}
```

---

## Location: `templates/macros/json_accordion.html`

#### `json_accordion` - Collapsible JSON Display
**Use for**: Showing JSON data with copy/download

```jinja
{% from "macros/json_accordion.html" import json_accordion %}

{{ json_accordion(
    data=finding_model,           {# Dict or JSON-serializable object #}
    id="model-json",              {# Unique ID for accordion #}
    title="JSON Data"             {# Accordion header text #}
) }}
```

---

## Decision Tree: Which Macro to Use?

### Buttons
```
Need a link to another page?
  → flowbite_button (renders <a>)

Need a form submit or JS action?
  → action_button (renders <button type="button">)

Need icon-only in tight space?
  → flowbite_icon_button

Need submit with HTMX loading indicator?
  → submit_button (from create_workflow_elements.html)
```

### Forms
```
Simple form, no reactive validation?
  → form_input / form_textarea (from flowbite_components.html)

Need Alpine.js validation state?
  → validated_input / validated_textarea (from form_validation.html)

Draft editing with synonyms?
  → unified_form_data (from unified_form_data.html)
```

### Status Display
```
Small inline status tag?
  → flowbite_badge

Alert/message box?
  → alert

Validation result indicator?
  → status_indicator (from create_workflow_elements.html)
```
