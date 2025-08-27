# Finding Model Index Codes Display Implementation

## Overview

Add comprehensive index code displays at three levels in the finding model template to improve the visibility of semantic coding information. This enhancement will make it easier for users to understand the standardized medical terminology associated with finding models.

## Requirements

1. **Finding Model Level** - Display top-level index codes with two-line format showing system:code and display text
2. **Attribute Level** - Display attribute-specific index codes with same two-line format
3. **Value Level** - Create hover popovers for attribute values showing description and associated index codes

## Visual Design

### Index Code Badge Format
Each index code should display as a small badge with:
- Line 1: `SYSTEM:CODE` (monospace font)
- Line 2: Display text (regular font)
- Example:
  ```
  SNOMED:705057003
  Presence (property) (qualifier value)
  ```

### Color Scheme
- Indigo color palette for visibility
- Light mode: `bg-indigo-100` with `text-indigo-800`
- Dark mode: `bg-indigo-900` with `text-indigo-300`

## Implementation Details

### Phase 1: Create Index Code Display Components

**File: `templates/macros/app_components.html`**

Add three new macros:

1. **`index_code_badge(code)`** - Displays a single index code with two-line format
   - Parameters: `code` object with `system`, `code`, and `display` fields
   - Returns: Two-line badge HTML

2. **`index_codes_display(codes, title)`** - Displays a list of index codes
   - Parameters: `codes` array, optional `title` (default: "Index Codes")
   - Returns: Section with title and wrapped badges

3. **`value_popover(value, attr_name)`** - Replaces current `attribute_value` macro
   - Parameters: `value` object, `attr_name` for unique ID generation
   - Returns: Badge with Flowbite hover popover
   - Popover contains: value description and index codes

### Phase 2: Update Finding Model Display Template

**File: `templates/components/finding_model_display.html`**

Modifications needed:

1. **Import new macros** (line ~2):
   ```jinja
   {% from 'macros/app_components.html' import index_codes_display, value_popover %}
   ```

2. **Add finding model index codes** (after description, ~line 22):
   - Check if `finding_model.index_codes` exists and has items
   - Use `index_codes_display` macro with title "Finding Model Index Codes"

3. **Add attribute index codes** (within attribute card, after description, ~line 88):
   - Check if `attribute.index_codes` exists and has items
   - Use `index_codes_display` macro with title "Attribute Index Codes"

4. **Replace value display** (line ~110):
   - Replace `attribute_value` macro calls with `value_popover`
   - Pass `value` and `attribute.name` parameters

### Phase 3: Ensure Flowbite Compatibility

**Popover Implementation:**
- Use Flowbite's native popover with `data-popover-trigger="hover"`
- Include `data-popover-target` and matching `id` attributes
- Add `data-popper-arrow` for arrow positioning
- Ensure `initFlowbite()` is called after HTMX swaps

## Data Structure

### Index Code Object
```json
{
  "system": "SNOMED",           // Coding system (SNOMED, RADLEX, etc.)
  "code": "705057003",          // System-specific code
  "display": "Presence (property) (qualifier value)"  // Human-readable text
}
```

### Example Finding Model with Index Codes
```json
{
  "name": "abdominal abscess",
  "index_codes": [
    {
      "system": "SNOMED",
      "code": "44132006",
      "display": "Abdominal abscess (disorder)"
    }
  ],
  "attributes": [
    {
      "name": "presence",
      "index_codes": [
        {
          "system": "SNOMED",
          "code": "705057003",
          "display": "Presence (property) (qualifier value)"
        }
      ],
      "values": [
        {
          "name": "absent",
          "description": "Abdominal abscess is absent",
          "index_codes": [
            {
              "system": "RADLEX",
              "code": "RID28473",
              "display": "absent"
            },
            {
              "system": "SNOMED",
              "code": "2667000",
              "display": "Absent (qualifier value)"
            }
          ]
        }
      ]
    }
  ]
}
```

## Testing Checklist

- [ ] **Finding Model Level**
  - [ ] Index codes display when present
  - [ ] Correct two-line format
  - [ ] No display when index_codes is empty/missing

- [ ] **Attribute Level**
  - [ ] Index codes display within attribute cards
  - [ ] Proper spacing and alignment
  - [ ] Compatible with existing attribute metadata

- [ ] **Value Level Popovers**
  - [ ] Popover appears on hover
  - [ ] Shows value description when present
  - [ ] Lists all value index codes
  - [ ] Popover positioning works correctly
  - [ ] Arrow points to trigger element

- [ ] **Cross-cutting Concerns**
  - [ ] Dark mode compatibility
  - [ ] Mobile responsive design
  - [ ] HTMX content swap compatibility
  - [ ] No JavaScript console errors
  - [ ] Accessibility (ARIA attributes)

## Test Data Sources

Use existing test data files:
- `tests/data/abdominal_abscess.fm.json`
- `tests/data/coronary_artery_calcifications.fm.json`

These files contain comprehensive index code examples at all three levels.

## Success Criteria

1. Users can see index codes at a glance for finding models and attributes
2. Value-level details are available on demand via hover
3. Visual design is consistent with existing Flowbite components
4. No custom CSS or JavaScript required
5. Implementation follows established patterns in codebase

## Notes

- This feature enhances the medical coding visibility without cluttering the interface
- Hover popovers provide details-on-demand for value-level information
- Two-line badge format ensures readability while remaining compact
- Uses native Flowbite components to maintain consistency
