# Technology Decisions

Decisions about our technology stack. For detailed research, see `research/` folder.

## Frontend

### Alpine.js Plugins (December 2025)
**Decision:** None needed.
- Focus/Collapse/Anchor → Flowbite already handles these
- Mask/Sort/Intersect/Persist → No use cases in our application
- See `research/alpine_plugins_evaluation.md` for full analysis

### Flowbite 4.0 Upgrade (December 2025)
**Decision:** Deferred.
- High effort: 401 `dark:` class occurrences across 39 files need migration
- Low benefit: Current Flowbite 3.1.2 + Tailwind 4.1.1 setup works well
- Revisit when: Starting major UI overhaul or Flowbite provides migration tooling
- See `research/flowbite_4_upgrade_assessment.md` for full analysis

### Alpine-morph Extension (December 2025)
**Decision:** Not needed.
- Our server-side state pattern is correct
- Server provides fresh state via Jinja2 → HTMX swaps → Alpine.initTree() reinitializes
- No client state preservation needed across swaps

## Backend

(No decisions documented yet)
