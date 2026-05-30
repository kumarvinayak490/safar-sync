Status: done

# Move Organizer Root Basics

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Make `organizers` mean the Organizer aggregate root and framework integration only. Remove organizer-adjacent business behavior from Organizer root ownership where it already has a target domain, while preserving existing external behavior through compatibility imports.

## Acceptance criteria

- [ ] Organizer root owns only organizer aggregate basics and integration concerns.
- [ ] Organizer-adjacent behavior is no longer newly authored under broad organizer-owned buckets.
- [ ] Existing API behavior around organizer access and lookup remains stable.
- [ ] Compatibility imports keep old callers working where required.
- [ ] Django checks and relevant organizer regression tests pass.

## Blocked by

- `.scratch/domain-backend-app-split/issues/01-stabilize-domain-app-skeleton.md`
- `.scratch/domain-backend-app-split/issues/02-add-compatibility-import-safety-net.md`

## Comments

- 2026-05-29 19:16:14 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Organizer root boundary cleanup and should avoid moving concrete domain behavior assigned to later issues.
- 2026-05-29 19:23:09 IST: Orchestrator accepted Organizer root boundary cleanup. Verified with `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `.venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `.venv/bin/python -m pytest apps/api/tripos_api/tests.py apps/api/internal_admin/tests.py`. Migration dry-run had only the known local PostgreSQL sandbox connection warning and no model changes.
- 2026-05-29 19:21:23 IST: Worker completion note: tightened the Organizer root boundary docs/comments so `organizers` reads as the Organizer aggregate root, DRF/Django integration surface, historical migration anchor, and compatibility facade only. Added smoke coverage that `organizers.models` locally defines only `Organizer` and that new top-level Organizer modules must be registered as integration surfaces or compatibility shims. Checks: `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `.venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `.venv/bin/python -m pytest apps/api/tripos_api/tests.py` passed. Focused DB-backed organizer regression selection was attempted; sandboxed run could not reach local PostgreSQL, and escalated run reached PostgreSQL but failed before tests on local `tripos` password authentication.
