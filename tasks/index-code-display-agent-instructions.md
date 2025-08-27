# Sub-Agent Instructions: Index Code Display Implementation

## Task Overview
Implement index code displays for finding models at three levels: model-level, attribute-level, and value-level (with hover popovers). Follow the plan in `tasks/index-code-display.md`.

## CRITICAL UI GUIDELINES - READ FIRST

### ⚠️ STRICT RULES - NO EXCEPTIONS ⚠️

1. **FLOWBITE ONLY**: Use ONLY official Flowbite components from https://flowbite.com/docs/
   - ✅ Copy exact HTML structure from Flowbite documentation
   - ❌ NO custom Tailwind class combinations
   - ❌ NO ad-hoc CSS classes
   - ❌ NO style attributes

2. **ALPINE.JS for Interactivity**:
   - ✅ Use Alpine.js directives (x-data, x-show, x-model, etc.)
   - ❌ NO custom JavaScript
   - ❌ NO onclick handlers
   - ❌ NO jQuery

3. **HTMX Compatibility**:
   - Ensure all components work with HTMX content swaps
   - Remember `initFlowbite()` is called after swaps in `src/js/main.js`

4. **Jinja2 Macros - DRY Principle**:
   - ✅ Create reusable macros in `templates/macros/app_components.html`
   - ✅ Look for opportunities to create new reusable components
   - ✅ Reuse existing macros where possible
   - ❌ NO duplicate code

## Your Specific Task

### Phase 1: Add Macros to `templates/macros/app_components.html`

Create three new macros:

1. **`index_code_badge(code)`**
   - Display format: Two lines (SYSTEM:CODE on top, display text below)
   - Use Flowbite badge styling, NOT custom Tailwind
   - Colors: Indigo theme (find appropriate Flowbite component)

2. **`index_codes_display(codes, title="Index Codes")`**
   - Wrapper for multiple index code badges
   - Include title section
   - Use Flowbite's flex/grid layouts

3. **`value_popover(value, attr_name)`**
   - Replace existing `attribute_value` macro
   - Use Flowbite's popover component with `data-popover-trigger="hover"`
   - Must follow exact Flowbite popover HTML structure
   - Include value description and index codes in popover content

### Phase 2: Update `templates/components/finding_model_display.html`

1. Import the new macros at the top
2. Add finding model index codes section (after description, around line 22)
3. Add attribute index codes within attribute cards (around line 88)
4. Replace `attribute_value` calls with `value_popover` (around line 110)

### Important Context Files to Review

Before implementing, review:
- `templates/CLAUDE.md` - Frontend development guidelines
- `templates/macros/flowbite_components.html` - Existing Flowbite macro patterns
- `templates/macros/app_components.html` - Current app-specific components
- `tests/data/abdominal_abscess.fm.json` - Sample data with index codes

### Popover Implementation Notes

For Flowbite popovers:
```html
<!-- Button trigger -->
<button data-popover-target="popover-id" data-popover-trigger="hover" type="button">
    <!-- Button content -->
</button>

<!-- Popover content -->
<div data-popover id="popover-id" role="tooltip" class="[Flowbite popover classes]">
    <!-- Content -->
    <div data-popper-arrow></div>
</div>
```

Use EXACT Flowbite classes from their documentation, not custom combinations.

### Component Reusability Opportunities

Consider if any of these could be useful elsewhere:
- Index code badge could be used in search results
- Popover pattern could be abstracted for other hover details
- Index codes display section could be a generic "coded values display"

### Testing Your Implementation

1. Test with sample data from `tests/data/` directory
2. Verify hover popovers work
3. Check dark mode (all Flowbite components should handle this)
4. Test HTMX content swaps still work
5. Ensure no console errors

## BOUNDARIES - STAY FOCUSED

✅ **DO**:
- Implement the three UI components as specified
- Update the finding model display template
- Create reusable Jinja2 macros
- Use only Flowbite components

❌ **DO NOT**:
- Modify backend code
- Change API endpoints
- Update database models
- Add new routes
- Modify tests (unless specifically for UI)
- Create new CSS files
- Add custom JavaScript
- Make changes outside the scope of index code display

If you think something outside the UI needs changing, STOP and ask for clarification rather than making the change.

## Verification Steps

After implementation:
1. The finding model page should display index codes at model level (if present)
2. Each attribute should show its index codes (if present)
3. Hovering over attribute values should show a popover with description and index codes
4. All styling should come from Flowbite components
5. No custom CSS or JavaScript should be added

## Resources

- Flowbite Documentation: https://flowbite.com/docs/
- Specifically review:
  - Badges: https://flowbite.com/docs/components/badge/
  - Popovers: https://flowbite.com/docs/components/popover/
  - Typography: https://flowbite.com/docs/typography/text/

Remember: When in doubt, check how existing components in the codebase handle similar patterns. Follow the established conventions exactly.
