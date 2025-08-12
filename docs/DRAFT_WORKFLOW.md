# Finding Model Draft Workflow

This document outlines the draft creation and submission flow.

## Overview

- Drafts are created during the multi-step creation wizard (HTMX-driven). Autosave begins on Step 4.
- Draft data:
  - user_id, name
  - inputs: description, synonyms, attributes_markdown
  - generated_json (server-generated)
  - status: draft | submitted | under-review | added | declined
  - action_log: timestamp, user_id, action, details
- Submitting a draft locks further editing.
- Resuming a submitted name directs to the final display view.

## Caching

- Redis-backed cache is used for user and finding model data.
- Implementation always calls cache; if Redis is unavailable, calls are safe no-ops.

## UI/UX

- Flowbite components; Alpine.js for state.
- HTMX drives server-rendered fragments for transitions between steps.
- `components/finding_model_complete_display.html` renders model + JSON accordion.

## Dev Notes

- See tests for coverage of submit/resume flows and repositories.
- Vite asset helper `get_vite_asset_path` reads `static/.vite/manifest.json` with a safe fallback.
- Keep interactivity in Alpine/HTMX; avoid custom JS/CSS.
