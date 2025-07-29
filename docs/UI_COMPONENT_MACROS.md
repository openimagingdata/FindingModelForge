# Jinja2 Macros for FindingModelForge

This directory contains reusable Jinja2 macros that provide consistent UI components throughout the application. All macros follow Flowbite design patterns and include proper dark mode support.

## Usage

Import macros at the top of your template:

```jinja
{% from "macros/flowbite_components.html" import breadcrumb, action_button, flowbite_badge %}
{% from "macros/layout_components.html" import page_header %}
{% from "macros/app_components.html" import finding_model_card %}
```

## Available Components

### Core Flowbite Components (`flowbite_components.html`)

#### Buttons

- `flowbite_button(text, href, type, size, icon, icon_position, disabled, target_blank)` - Standard Flowbite button (link)
- `action_button(text, type, size, icon, icon_position, disabled, classes, attributes)` - Action button for forms/JS

#### Navigation

- `breadcrumb(items)` - Breadcrumb navigation with proper accessibility
- `nav_link(text, href, icon, active)` - Navigation link component

#### Badges & Alerts

- `flowbite_badge(text, color, size, pill, href)` - Standard badge component
- `alert(message, type, dismissible)` - Alert/notification component

#### Cards & Layout

- `flowbite_card(title, content, href, cta_text, cta_href, icon, shadow)` - Content card
- `flowbite_icon_list(items, icon)` - List with custom icons

#### Forms

- `form_input(name, type, label, placeholder, value, required, disabled, readonly, classes, attributes)` - Form input field
- `form_textarea(name, label, placeholder, value, rows, required, disabled, readonly, classes, attributes)` - Textarea field

#### User Interface

- `user_avatar(user, size, show_name)` - User avatar with fallback
- `dropdown_menu(items, trigger_content)` - Dropdown menu with Alpine.js
- `progress_indicator(steps, current_step)` - Multi-step progress indicator

### Layout Components (`layout_components.html`)

- `page_header(title, subtitle, actions)` - Standard page header with optional actions
- `section_divider(title)` - Section divider with title
- `container(content, max_width, padding)` - Responsive container wrapper

### App-Specific Components (`app_components.html`)

- `finding_model_card(model, show_actions)` - Finding model display card with metadata
- `user_profile_card(user)` - User profile information display

## Examples

### Breadcrumb Navigation

```jinja
{% set home_icon %}
    <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
        <path d="m19.707 9.293-2-2-7-7a1 1 0 0 0-1.414 0l-7 7-2 2a1 1 0 0 0 1.414 1.414L2 10.414V18a2 2 0 0 0 2 2h3a1 1 0 0 0 1-1v-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v4a1 1 0 0 0 1 1h3a2 2 0 0 0 2-2v-7.586l.293.293a1 1 0 0 0 1.414-1.414Z"/>
    </svg>
{% endset %}

{{ breadcrumb([
    {"text": "Home", "href": url_for('index'), "icon": home_icon},
    {"text": "Finding Models", "href": url_for('pages.finding_models_list')},
    {"text": "Current Model"}
]) }}
```

### Action Buttons

```jinja
<!-- Primary action button -->
{{ action_button("Save Changes", type="primary", attributes='@click="saveProfile()" :disabled="isSaving"') }}

<!-- Secondary button -->
{{ action_button("Cancel", type="secondary", attributes='@click="cancelEdit()"') }}
```

### Form Inputs

```jinja
{{ form_input("email", type="email", label="Email Address", placeholder="Enter your email", required=true) }}

{{ form_textarea("bio", label="Biography", placeholder="Tell us about yourself", rows=4) }}
```

### Badges

```jinja
{{ flowbite_badge("Active", color="green") }}
{{ flowbite_badge("Draft", color="yellow", pill=true) }}
```

## Best Practices

1. **Use appropriate macros**: Always prefer macros over inline HTML for repeated patterns
2. **Consistent styling**: Macros ensure consistent Flowbite styling and dark mode support
3. **Accessibility**: All macros include proper ARIA attributes and accessibility features
4. **Customization**: Use the `classes` and `attributes` parameters for component-specific customization
5. **Alpine.js integration**: Many macros support Alpine.js directives via the `attributes` parameter

## File Organization

- **`flowbite_components.html`**: Core UI components (buttons, badges, forms, etc.)
- **`layout_components.html`**: Layout and structural components
- **`app_components.html`**: Application-specific business components

Import only the macros you need to keep templates clean and maintainable.

## Migration Guide

When refactoring templates to use macros:

1. **Identify repeated patterns** - Look for similar HTML structures across templates
2. **Choose appropriate macros** - Use existing macros or create new ones for common patterns
3. **Update imports** - Add macro imports at the top of templates
4. **Test thoroughly** - Ensure Alpine.js functionality and styling remain intact
5. **Document new macros** - Update this README with any new macro additions
