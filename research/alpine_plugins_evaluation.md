# Alpine.js Plugins Evaluation

**Date:** December 2025
**Decision:** None needed
**Status:** Complete

## Context

Evaluated all 8 official Alpine.js plugins to determine if any would reduce custom code or improve our HTMX/Alpine/Flowbite stack.

## Plugins Evaluated

### Focus
**Purpose:** Trap focus within elements (modals, dropdowns)
**Our need:** None - Flowbite handles focus trapping for modals, dropdowns, and accordions
**Decision:** Skip

### Collapse
**Purpose:** Animate height transitions for collapsible elements
**Our need:** None - Flowbite accordions handle this
**Decision:** Skip

### Anchor
**Purpose:** Position floating elements relative to anchors
**Our need:** None - Flowbite handles dropdown/tooltip positioning
**Decision:** Skip

### Mask
**Purpose:** Format text inputs (phone numbers, dates, credit cards)
**Our need:** None - No formatted input fields in the application
**Decision:** Skip

### Sort
**Purpose:** Drag-and-drop reordering
**Our need:** None - No reorderable lists in the application
**Decision:** Skip

### Intersect
**Purpose:** React to elements entering/leaving viewport (lazy loading, infinite scroll)
**Our need:** None - No lazy loading or infinite scroll features
**Decision:** Skip

### Persist
**Purpose:** Persist Alpine state to localStorage
**Our need:** Minimal - Only dark mode uses localStorage (15 lines in main.js)
**Decision:** Skip - Not worth adding a dependency for one simple use case

### Morph
**Purpose:** Preserve Alpine state across DOM updates (intelligent diffing)
**Our need:** None - Server is source of truth; fresh state on each HTMX swap is correct
**Decision:** Skip

## Conclusion

Flowbite handles Focus/Collapse/Anchor functionality. No use cases exist for Mask/Sort/Intersect. Persist would add complexity for minimal benefit. Morph contradicts our server-side state architecture.

## Conditions to Revisit

- Adding phone/date/credit card input fields → Consider Mask
- Adding drag-and-drop reordering → Consider Sort
- Adding lazy loading or infinite scroll → Consider Intersect
