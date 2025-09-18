# UI Component Macros Reference (v1.3.0)

Comprehensive guide to reusable Jinja2 macros for consistent, Flowbite-compliant UI with Alpine.js interactivity. All
components updated for the new simplified URL structure introduced in v1.3.0.

**URL Changes**: All macros now use simplified URLs (`/create/*`, `/drafts/*`) instead of previous
`/api/finding-models/*` structure.

## How to import

```jinja
{% from "macros/flowbite_components.html" import breadcrumb, action_button, flowbite_badge %}
{% from "macros/layout_components.html" import hero_section, content_section, container %}
{% from "macros/app_components.html" import required_badge, type_badge, attribute_value %}
{% from "macros/creation_components.html" import creation_stepper, error_alert, success_alert %}
{% from "macros/create_workflow_elements.html" import htmx_form, input_field, textarea_field, navigation_buttons %}
{% from "macros/form_validation.html" import validation_data, validated_input, validated_textarea %}
{% from "macros/synonym_manager.html" import synonym_manager, synonym_data %}
{% from "macros/json_accordion.html" import json_accordion %}
{% from "macros/confirmation_modal.html" import confirmation_modal %}
{% from "macros/delete_draft_modal.html" import delete_draft_modal %}
{% from "macros/submit_draft_modal.html" import submit_draft_modal %}
{% from "macros/make_public_modal.html" import make_public_modal %}
{% from "macros/unified_form_data.html" import unified_form_data %}
```

## Core Flowbite Components (macros/flowbite_components.html)

- Buttons
  - flowbite_button(text, href="#", type="primary"|"secondary"|"success"|"warning"|"danger"|"dark",
    size="xs"|"sm"|"default"|"lg", icon=None, icon_position="left"|"right", disabled=False, target_blank=False)
  - action_button(text, type=..., size=..., icon=None, icon_position="left"|"right", disabled=False, classes="",
    attributes="")
- Badges & Cards
  - flowbite_badge(text, color="default"|"gray"|"red"|"green"|"yellow"|"indigo"|"purple"|"pink"|"blue",
    size="xs"|"sm"|"default", pill=False, href=None)
  - flowbite_card(title, content, href=None, cta_text=None, cta_href=None, icon=None,
    shadow="none"|"sm"|"default"|"md"|"lg")
  - flowbite_icon_list(items, icon=None)
- Alerts
  - alert(message, type="info"|"success"|"warning"|"error", dismissible=False)
- Navigation & Identity
  - breadcrumb(items=[{ text, href?, icon? }])
  - nav_link(text, href, icon=None, active=False)
  - user_avatar(user, size="sm"|"default"|"lg", show_name=False)
  - dropdown_menu(items=[{ text, href, target?, divider? }], trigger_content)
- Progress
  - progress_indicator(steps=[...], current_step=1)
- Forms
  - form_input(name, type="text", label=None, placeholder="", value="", required=False, disabled=False, readonly=False,
    classes="", attributes="")
  - form_textarea(name, label=None, placeholder="", value="", rows=3, required=False, disabled=False, readonly=False,
    classes="", attributes="")

Usage tip: Use attributes to pass Alpine.js directives (e.g., attributes='x-model="email"').

## Layout Components (macros/layout_components.html)

- hero_section(title, subtitle, description, cta_button, image_src=None, image_alt="", icon_src=None)
- content_section(cards=[safe_html...], max_width="6xl")
- two_column_layout(left_content, right_content, left_width="1/2", right_width="1/2")
- three_column_layout(columns=[safe_html...])
- container(content, max_width="7xl", padding="px-4 py-8")

## App-Specific Components (macros/app_components.html)

- Badges & Values
  - required_badge()
  - id_badge(id_value)
  - type_badge(type_value) # maps common types to colored badges
  - attribute_value(value) # renders a value as a badge, with tooltip when description present
- Contributors & Icons
  - contributor_avatar(contributor, size="sm"|"default"|"lg")
  - github_icon(classes="w-5 h-5")
  - checkmark_icon(color="green"|"blue"|"red"|"gray")
  - arrow_right_icon()

## Creation Workflow Components (macros/creation_components.html)

- creation_stepper(current_step=1) # Flowbite stepper for the 5-step create flow
- step_loading_indicator() # HTMX indicator overlay
- error_alert(error_message)
- success_alert(success_message)

## HTMX Form Elements (macros/create_workflow_elements.html)

- htmx_form(step_number, method="post", extra_classes="")
  - Block macro: wraps form contents and wires hx-post to /api/finding-models/create/step/{step_number}
  - Example:
    ```jinja
    {% call htmx_form(4) %}
      {{ input_field('name', 'Name', required=true) }}
      {{ navigation_buttons(back_step=3) }}
    {% endcall %}
    ```
- submit_button(text="Continue", loading_text="Processing...", extra_classes="", disabled=False)
- back_button(step_number, text="← Back", extra_classes="")
- input_field(name, label, value="", type="text", placeholder="", required=False, extra_classes="")
- textarea_field(name, label, value="", rows=4, placeholder="", required=False, extra_classes="")
- navigation_buttons(back_step=None, back_text="← Back", submit_text="Continue", submit_loading="Processing...")
- status_indicator(success: bool, message: str)

## Alpine.js Validation (macros/form_validation.html)

- validation_data(initial_name='', initial_description='', initial_attributes='')
  - Returns an Alpine.js data object with computed validation states; bind via x-data="..."
- validation_component() # legacy alias of validation_data()
- validated_input(name, label, value="", type="text", placeholder="", required=False, minlength=None, maxlength=None,
  pattern=None, pattern_message=None, extra_classes="", show_counter=False)
- validated_textarea(name, label, value="", rows=4, placeholder="", required=False, minlength=None, maxlength=None,
  extra_classes="")

Example:

```jinja
<div x-data='{{ validation_data() | safe }}'>
  {{ validated_input('name', 'Name', required=true, minlength=3, maxlength=200) }}
  {{ validated_textarea('description', 'Description', required=true, minlength=10) }}
  {{ action_button('Save', type='primary', attributes=':disabled="!isFormValid()"') }}
  <input type="hidden" name="name" x-ref="name" :value="name">
  <input type="hidden" name="description" x-ref="description" :value="description">
</div>
```

## Synonym Manager (macros/synonym_manager.html)

- synonym_manager() # badges UI for synonyms with add/remove
- synonym_data(initial_synonyms) # Alpine.js data for synonyms state

Example:

```jinja
<div x-data='{{ synonym_data([]) | safe }}'>
  {{ synonym_manager() }}
</div>
```

## JSON Accordion (macros/json_accordion.html)

- json_accordion(finding_model, accordion_id="json-accordion", title="JSON Data")
  - Uses Flowbite accordion markup. Includes Download/Copy buttons wired to global helpers `downloadJSON` and
    `copyToClipboard` provided by `src/js/main.js` (approved shared utilities).

### Shared JS utilities

- The global functions `downloadJSON(content, filename)` and `copyToClipboard(content)` are defined in `src/js/main.js`
  and are approved for use by macros/components that need copy/download behavior. Do not add ad hoc JS—reuse these
  utilities.
- These utilities ship in the Vite bundle and are included via `templates/base.html`, so you don’t need to add extra
  script tags.

## Best practices

- Always prefer these macros over hand-rolled HTML for repeated patterns.
- Stick to Flowbite’s structure and classes; use Alpine.js for interactivity via attributes.
- Avoid custom JS/CSS; when needed, wire through attributes and established macros.
- Keep templates small: import only the macros you use.
- Use unified_form_data for complex forms combining validation and synonym management.
- Include appropriate deletion modals for destructive actions.

## Modal Components

### Base Modal (macros/confirmation_modal.html)

- confirmation_modal(modal_id, title="Confirm Action", message="Are you sure?", confirm_text="Confirm",
  cancel_text="Cancel", confirm_color="primary", icon_type="warning", hx_post=None, hx_target=None, hx_swap=None,
  extra_attributes="")
  - Reusable Flowbite confirmation modal component
  - Supports primary, green, and red color themes
  - Icons: warning, danger, info
  - Full HTMX integration for server-side actions
  - Customizable text, styling, and behavior

### Draft Management Modals

- delete_draft_modal(draft_id, hx_target=None, hx_swap=None, extra_attributes='')
  - Flowbite confirmation modal for draft deletion
  - Uses base confirmation_modal with warning icon and red styling
  - HTMX integration for seamless deletion workflow
  - Customizable targeting and swap behavior

- make_public_modal(draft_id, hx_target="#main-content", hx_swap="innerHTML")
  - Flowbite confirmation modal for making drafts public
  - Uses base confirmation_modal with info icon and blue styling
  - Posts to `/drafts/{id}/make-public` endpoint
  - Added September 2025 for public draft review feature

- submit_draft_modal(draft_id, hx_target="#main-content", hx_swap="innerHTML")
  - Flowbite confirmation modal for draft submission
  - Uses base confirmation_modal with info icon and green styling
  - HTMX POST to submit endpoint with automatic targeting
  - Warns user about draft locking after submission

## Unified Form Data (macros/unified_form_data.html)

- unified_form_data(initial_description="", initial_attributes="", initial_synonyms=[], has_no_generated_json=False)
  - Alpine.js reactive data object combining validation and synonym management
  - Includes computed properties for validation state (isValidDescription, isValidAttributes, canSubmit)
  - Change detection for text fields and synonyms array
  - Step-specific validation methods (canSubmitStep2 for creation, canSubmit for editing)
  - Synonym management methods (addSynonym, removeSynonym, getSynonymsJson)

### Draft Management Integration Example

```jinja
{# Complete draft editing form with validation and deletion modal #}
<div x-data='{{ unified_form_data(draft.inputs.description, draft.inputs.attributes_markdown, draft.inputs.synonyms, not draft.generated_json) | safe }}'>
  {{ validated_textarea('description', 'Description', required=true, minlength=10, maxlength=1000) }}
  {{ synonym_manager() }}
  {{ validated_textarea('attributes_markdown', 'Attributes', required=true, minlength=20) }}

  <div class="flex gap-4">
    {{ action_button('Save Changes', type='primary', attributes=':disabled="!canSubmit"') }}
    {{ action_button('Delete Draft', type='danger', attributes='data-modal-target="delete-draft-modal-' + draft.id + '" data-modal-toggle="delete-draft-modal-' + draft.id + '"') }}
  </div>

  {# Hidden fields for form submission #}
  <input type="hidden" name="description" x-model="description">
  <input type="hidden" name="attributes_markdown" x-model="attributes_markdown">
  <input type="hidden" name="synonyms" x-model="getSynonymsJson()">
</div>

{# Include deletion confirmation modal #}
{{ delete_draft_modal(draft.id, hx_target="#main-content", hx_swap="innerHTML") }}
```

## Comment System Components (templates/components/comment_thread.html)

### Comment Thread Component

The comment thread component provides a complete discussion system for finding models and drafts:

```jinja
{% include 'components/comment_thread.html' %}
```

**Context Variables Required:**

- `thread` - CommentThread object containing all comments
- `reference_type` - Either "finding_model" or "draft"
- `reference_id` - The oifm_id for models or draft ID
- `slug_or_id` - URL identifier for HTMX endpoints
- `current_user` - Current authenticated user (or None)

**Features:**

- **Authentication-aware UI** - Different messages for logged-in vs anonymous users
- **Single-level replies** - Comments can have replies, but replies cannot
- **Character counting** - Real-time validation with Alpine.js (1-2000 chars)
- **Dynamic updates** - HTMX-powered comment submission without page reload
- **Report functionality** - Flag inappropriate content with one-click reporting
- **Rate limiting** - Enforced server-side with user-friendly error messages
- **Chronological display** - Oldest-first ordering for natural discussion flow

### Comment Display Structure

Each comment includes:

- User avatar (GitHub profile image)
- Username and timestamp
- Comment content (plain text, markdown support planned)
- Reply button (hover to show)
- Report button (if not already reported by user)
- Indented replies below parent comment

### Alpine.js Integration

The comment forms use Alpine.js for:

- Character counting: `x-text="contentLength + '/2000'"`
- Submit button state: `:disabled="!content || content.length > 2000"`
- Reply form toggling: `x-show="showReplyForm"`
- Form reset on cancel: `@click="content = ''; showReplyForm = false"`

### HTMX Patterns

Comment submission uses HTMX for seamless updates:

```html
<form
  hx-post="/finding-models/{{ slug_or_id }}/comments"
  hx-target="#comment-thread-{{ reference_type }}-{{ reference_id }}"
  hx-swap="outerHTML"
></form>
```

Report buttons use self-replacing pattern:

```html
<button hx-post="/finding-models/{{ slug_or_id }}/comments/{{ comment.id }}/report" hx-swap="outerHTML"></button>
```

### Usage Examples

**In Finding Model Detail Page:**

```jinja
{% include 'components/comment_thread.html' with
    thread=comment_thread,
    reference_type="finding_model",
    reference_id=model.oifm_id,
    slug_or_id=model.slug,
    current_user=current_user
%}
```

**In Draft View Page:**

```jinja
{% if draft.status != "draft" %}
  {% include 'components/comment_thread.html' with
      thread=comment_thread,
      reference_type="draft",
      reference_id=draft.id,
      slug_or_id=draft.id,
      current_user=current_user
  %}
{% endif %}
```

### Styling Classes

The component uses Flowbite classes throughout:

- Cards: `bg-white dark:bg-gray-800 rounded-lg p-4`
- Avatars: `w-8 h-8 rounded-full`
- Buttons: `text-blue-600 hover:text-blue-700`
- Forms: `border-gray-300 dark:border-gray-600 rounded-lg`
- Alerts: `bg-red-50 dark:bg-red-900 text-red-600`

### Server Response Patterns

The comment endpoints return:

- **Success**: Updated comment thread HTML fragment
- **Rate limit (429)**: Error alert HTML with message
- **Validation error (400)**: Error alert HTML with details
- **Authentication required (401)**: Redirect or error message
