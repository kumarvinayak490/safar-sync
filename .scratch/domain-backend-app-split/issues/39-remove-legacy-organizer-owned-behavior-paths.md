Status: done

## Comments

- 2026-05-30T10:45:00+05:30 | Orchestrator assigned this issue to the split cleanup worker (me).
- 2026-05-30T22:15:00+05:30 | Completed cleanup pass for remaining legacy organizer-owned behavior paths and compatibility imports.

- Scope: remove remaining logic from legacy `organizers`-owned behavior paths while keeping compatibility imports intact.

# Remove Legacy Organizer-Owned Behavior Paths

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Remove or shrink legacy organizer-owned behavior paths after domain apps own the behavior. Any old paths that remain must be thin compatibility shims with no business logic and a documented removal reason.

## Acceptance criteria

- [x] Legacy organizer-owned behavior modules are removed or reduced to re-exports.
- [x] No broad backend `organizer_settings` owner remains (compat-only path only).
- [x] No generic `read_models`, `workflows`, `utils`, or preference junk-drawer module is introduced.
- [x] Remaining compatibility shims are documented and covered by smoke tests.
- [x] Linting, Django checks, and migration dry-run pass.

## Completion notes

- Completed compatibility-shim migration for:
  - Organizer Payments behavior under `organizer_payments` and legacy `organizers/payments/*` re-exports.
  - Trip Bookings operation path under `trip_bookings/operations` and legacy `organizers/bookings/*` re-exports.
  - Public trip/operations/traveler/trip-profile compatibility modules.
  - Added/updated import smoke checks in `apps/api/tripos_api/tests.py`.
  - Kept `organizers/organizer_settings` as compatibility-only re-export surface (no business owner role remains).
  - Trimmed remaining compatibility risk in legacy service shim where `change_trip_dates` was enforcing a stale published-lock check; lock enforcement now remains at domain/API boundaries.

## Verification

- `python3 -m ruff check apps/api`
- `DATABASE_URL=sqlite:////private/tmp/tripos-issue40.sqlite3 .venv/bin/python apps/api/manage.py check`
- `DATABASE_URL=sqlite:////private/tmp/tripos-issue40.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`
- `DATABASE_URL=sqlite:////private/tmp/tripos-issue40.sqlite3 .venv/bin/python -m pytest apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py -q`

## Blocked by

- `.scratch/domain-backend-app-split/issues/38-move-domain-tests-to-owning-apps.md`
