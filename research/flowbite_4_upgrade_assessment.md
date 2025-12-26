# Flowbite 4.0 Upgrade Assessment

**Date:** December 2025
**Decision:** Deferred
**Status:** Complete

## Current Stack

- Flowbite: 3.1.2
- Tailwind CSS: 4.1.1
- Alpine.js: 3.14.1

## Flowbite 4.0 Changes

### Benefits

1. **Semantic Token Classes**
   - New classes like `bg-surface`, `text-on-surface`, `bg-brand`
   - ~50% reduction in HTML class verbosity
   - Better maintainability for theming

2. **CSS Variable Dark Mode**
   - Dark mode via CSS variables instead of `dark:` prefix classes
   - Single class set works for both modes
   - Cleaner HTML output

3. **Improved Component API**
   - More consistent patterns
   - Better TypeScript support

### Breaking Changes

1. **Tailwind CSS 4.0 Required**
   - We're on 4.1.1, so compatible

2. **Dark Mode Migration**
   - All `dark:` prefixed classes must be converted to CSS variable approach
   - Significant template changes required

## Migration Effort Analysis

### Scope

```
Files with dark: classes: 39
Total dark: occurrences: 401
```

**Affected files include:**
- All template files in `templates/`
- Component macros in `templates/macros/`
- Base layout and partials

### Effort Estimate

- **Template updates:** 39 files × ~30 min avg = ~20 hours
- **Testing:** All UI workflows need verification = ~8 hours
- **Bug fixes:** Estimate 20% rework = ~6 hours
- **Total:** ~34 hours (1 week of focused work)

## Risk Assessment

- **Low:** Tailwind 4.x compatibility already satisfied
- **Medium:** Dark mode visual regressions possible
- **Medium:** Flowbite component behavior changes

## Decision

**Deferred.** The effort-to-benefit ratio is unfavorable:
- Current setup works correctly
- No blocking issues with Flowbite 3.x
- 34+ hours of migration work for primarily cosmetic benefits

## Conditions to Revisit

1. Starting a major UI overhaul (can combine with migration)
2. Flowbite provides automated migration tooling
3. Flowbite 3.x reaches end-of-life or has security issues
4. Need for semantic theming system becomes a priority
