Status: done

# Add Compatibility Import Safety Net

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Add a temporary compatibility layer that lets old organizer-owned import paths continue to resolve while behavior moves into domain apps. The compatibility layer must only re-export domain-owned behavior and must make remaining legacy paths visible as intentional transition debt.

## Acceptance criteria

- [ ] Existing public backend imports continue to work during the app split.
- [ ] Compatibility modules contain no duplicate business logic.
- [ ] Compatibility modules clearly point callers toward the owning domain app.
- [ ] Tests or import smoke checks cover the compatibility paths expected to survive temporarily.
- [ ] Linting does not report stale or unused compatibility imports introduced by this slice.

## Blocked by

- `.scratch/domain-backend-app-split/issues/01-stabilize-domain-app-skeleton.md`

## Comments

- 2026-05-29 19:10:06 IST: Assigned to Ralph worker for autonomous implementation. Worker owns temporary compatibility import safety net and related smoke tests; avoid Internal Admin staff shell files except where shared import checks require them.
- 2026-05-29 19:16:14 IST: Orchestrator accepted compatibility import safety net. Verified with `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `.venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `.venv/bin/python -m pytest apps/api/tripos_api/tests.py apps/api/internal_admin/tests.py`. Compatibility shims are thin re-exports; some still point at transitional `organizers.*` packages until later domain move issues complete.
- 2026-05-29 19:13:59 IST: Worker completion note: added thin legacy organizer compatibility modules that re-export the current transitional owners, added smoke coverage for those flat legacy module imports and `organizers.models` domain-model re-exports, and left issue status unchanged for orchestrator verification. Checks: `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `.venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `.venv/bin/python -m pytest apps/api/tripos_api/tests.py`. Migration dry-run reported no model changes and only the existing local PostgreSQL sandbox connection warning.
