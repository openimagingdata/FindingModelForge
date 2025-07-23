# Flowbite Macro Organization

## Overview

FindingModelForge uses a well-organized macro system to ensure consistent, reliable usage of Flowbite components throughout the application. All UI components are implemented as Jinja2 macros following Flowbite's data-attribute patterns.

## File Structure

```
templates/macros/
├── index.html              # Unified import file - use this for all imports
├── flowbite_components.html # Core Flowbite UI components
├── layout_components.html   # Layout and section components
└── app_components.html      # Application-specific components
```

## Import Pattern

**Always import from the unified index file:**

```jinja2
{% from 'macros/index.html' import flowbite_button, flowbite_card, hero_section %}
```

## Macro Categories

### Core Flowbite Components (`flowbite_components.html`)

These implement standard Flowbite UI components with proper data attributes:

- **`flowbite_button`** - Buttons with size, color, and icon support
- **`flowbite_card`** - Cards with optional headers, footers, and images
- **`flowbite_icon_list`** - Lists with icons and descriptions
- **`flowbite_alert`** - Dismissible alerts with icons
- **`flowbite_dropdown`** - Dropdown menus with proper toggle behavior
- **`flowbite_modal`** - Modal dialogs with backdrop and controls
- **`flowbite_badge`** - Status and category badges
- **`flowbite_avatar`** - User avatar with fallback initials

### Layout Components (`layout_components.html`)

These handle page structure and content organization:

- **`hero_section`** - Main hero sections with background and content
- **`content_section`** - Standard content sections with consistent spacing

### App-Specific Components (`app_components.html`)

These are tailored to FindingModelForge's domain:

- **`github_icon`** - GitHub logo SVG for OAuth integration
- **`finding_model_card`** - Specialized cards for finding model display
- **`type_badge`** - Domain-specific status badges

## Usage Guidelines

### 1. Always Use Flowbite Data Attributes

✅ **Correct:** Use Flowbite's built-in functionality
```jinja2
{{ flowbite_button("Login", "/login", "primary", "lg") }}
```

❌ **Wrong:** Custom JavaScript implementations
```html
<button onclick="customLogin()">Login</button>
```

### 2. Import from Unified Index

✅ **Correct:** Single import source
```jinja2
{% from 'macros/index.html' import flowbite_button, flowbite_card %}
```

❌ **Wrong:** Multiple import sources
```jinja2
{% from 'macros/flowbite_components.html' import flowbite_button %}
{% from 'macros/app_components.html' import github_icon %}
```

### 3. Use Consistent Parameters

All macros follow consistent parameter patterns:

- **`text`** - Display text/content
- **`url`** - Link destinations
- **`color`** - Theme colors (primary, secondary, success, danger, etc.)
- **`size`** - Component sizes (sm, md, lg, xl)
- **`icon`** - Optional icon content
- **`classes`** - Additional CSS classes

### 4. Dark Mode Support

All components include proper dark mode classes:
- Use `dark:` prefixed classes where appropriate
- Test components in both light and dark modes
- Ensure proper contrast and visibility

## Component Documentation

### Buttons

```jinja2
{{ flowbite_button(text, url, color="primary", size="md", icon=none, classes="") }}
```

**Parameters:**
- `text`: Button label
- `url`: Link destination
- `color`: Theme color (primary, secondary, success, etc.)
- `size`: Button size (sm, md, lg, xl)
- `icon`: Optional icon HTML
- `classes`: Additional CSS classes

**Examples:**
```jinja2
{{ flowbite_button("Save", "/save", "primary", "lg") }}
{{ flowbite_button("Login", "/auth/login", "dark", "lg", github_icon("w-5 h-5 mr-2")) }}
```

### Cards

```jinja2
{{ flowbite_card(title, content, footer=none, image=none, classes="") }}
```

**Parameters:**
- `title`: Card title
- `content`: Main card content
- `footer`: Optional footer content
- `image`: Optional image URL
- `classes`: Additional CSS classes

### Alerts

```jinja2
{{ flowbite_alert(message, type="info", dismissible=true, icon=none) }}
```

**Parameters:**
- `message`: Alert text
- `type`: Alert type (info, success, warning, danger)
- `dismissible`: Whether alert can be dismissed
- `icon`: Optional icon HTML

## Development Workflow

### Adding New Components

1. **Determine Category**: Core Flowbite, Layout, or App-specific
2. **Add to Appropriate File**: Place macro in correct category file
3. **Export in Index**: Add to `macros/index.html` exports
4. **Follow Patterns**: Use consistent parameter naming and data attributes
5. **Test Both Modes**: Verify light and dark mode appearance
6. **Document Usage**: Add examples to this guide

### Updating Components

1. **Maintain Compatibility**: Keep existing parameter names
2. **Update All Files**: Macro definition and index exports
3. **Test Extensively**: Check all pages using the component
4. **Update Documentation**: Reflect any parameter changes

### Debugging Issues

1. **Check Import Path**: Ensure importing from `macros/index.html`
2. **Verify Exports**: Confirm macro is exported in index file
3. **Data Attributes**: Ensure Flowbite data attributes are correct
4. **JavaScript**: Use `initFlowbite()` for dynamic content
5. **Console Errors**: Check browser console for Flowbite errors

## Best Practices

### Performance
- Import only needed macros to reduce template size
- Use consistent parameter defaults to reduce template complexity
- Cache frequently used macro combinations

### Maintainability
- Keep macros focused and single-purpose
- Use descriptive parameter names
- Include comprehensive documentation
- Test components in isolation

### Accessibility
- Include proper ARIA attributes in macro definitions
- Ensure keyboard navigation works with Flowbite components
- Test with screen readers
- Maintain proper color contrast ratios

### Security
- Always escape user content in macro parameters
- Use `url_for()` for internal links
- Validate optional parameters properly
- Avoid inline JavaScript in macro definitions

## Migration Notes

### From Old Structure

The macro system was reorganized for better maintainability:

**Old (Disorganized):**
```
templates/macros/
├── ui_components.html    # Mixed components
└── badge_macros.html     # Overlapping functionality
```

**New (Organized):**
```
templates/macros/
├── index.html              # Unified imports
├── flowbite_components.html # Core UI
├── layout_components.html   # Layouts
└── app_components.html      # App-specific
```

### Update Required

All templates must update their imports:

**Before:**
```jinja2
{% from 'macros/ui_components.html' import flowbite_button %}
{% from 'macros/badge_macros.html' import type_badge %}
```

**After:**
```jinja2
{% from 'macros/index.html' import flowbite_button, type_badge %}
```

## Troubleshooting

### Common Issues

**1. Import Errors**
```
UndefinedError: the template 'macros/index.html' does not export 'macro_name'
```
- Check that macro is defined in appropriate category file
- Verify macro is exported in `macros/index.html`
- Ensure macro name matches exactly (case-sensitive)

**2. Flowbite Not Working**
```
Components not responding to clicks/interactions
```
- Check that data attributes are correct (`data-modal-target`, etc.)
- Ensure Flowbite JavaScript is loaded
- Call `initFlowbite()` for dynamically added content

**3. Dark Mode Issues**
```
Components not displaying properly in dark mode
```
- Add `dark:` prefixed classes to macro definitions
- Test components in both light and dark modes
- Check color contrast and visibility

### Getting Help

1. **Check Documentation**: Review component examples in this file
2. **Inspect Existing**: Look at working components in other templates
3. **Browser Console**: Check for JavaScript errors
4. **Flowbite Docs**: Reference official Flowbite documentation
5. **Context7**: Use Context7 tool for up-to-date Flowbite patterns

## Future Enhancements

### Planned Improvements

1. **Component Library**: Build comprehensive component showcase page
2. **Automated Testing**: Add tests for macro rendering and functionality
3. **Documentation Generation**: Auto-generate component docs from macros
4. **Performance Optimization**: Implement macro caching strategies
5. **Accessibility Audit**: Comprehensive a11y review of all components

### Contributing

When adding new macros:

1. Follow the established patterns and naming conventions
2. Include comprehensive parameter documentation
3. Test in both light and dark modes
4. Add usage examples to this documentation
5. Consider accessibility and performance implications
