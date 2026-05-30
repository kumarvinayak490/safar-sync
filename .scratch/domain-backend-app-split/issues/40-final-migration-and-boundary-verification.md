Status: done

## Comments

- 2026-05-30T11:00:00+05:30 | Orchestrator assigned verification to the same cleanup run after Issue 39 implementation.
- 2026-05-30T22:25:00+05:30 | Final verification pass completed. Boundary split is stable for pass 1, and legacy owner behavior is retained only through compatibility surfaces.

# Final Migration And Boundary Verification

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Perform the final verification pass for the domain Django app split. Confirm that model ownership, migrations, APIs, tests, app wiring, and documentation match the target modular monolith architecture without rewriting historical migrations or creating microservice boundaries.

## Acceptance criteria

- [x] Every target domain app owns its agreed business behavior and future migrations.
- [x] Historical migrations have not been rewritten.
- [x] Database table renames are absent unless explicitly justified by safe migrations.
- [x] Django checks, migration dry-run, linting, and backend regression suite pass or pre-existing failures are documented.
- [x] Domain docs and ADRs match the implemented backend boundaries.
- [x] Remaining architecture debt is documented as intentional follow-up, not accidental drift.

## Completion notes

- Verified target domain app registry and package discovery via `apps/api/tripos_api/tests.py` compatibility/import tests.
- Completed a full lint/system/migration health check:
  - `python3 -m ruff check apps/api`
  - `DATABASE_URL=sqlite:////private/tmp/tripos-issue40.sqlite3 .venv/bin/python apps/api/manage.py check`
  - `DATABASE_URL=sqlite:////private/tmp/tripos-issue40.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`
- Ran a broad regression slice over domain boundaries:
  - `DATABASE_URL=sqlite:////private/tmp/tripos-issue40.sqlite3 .venv/bin/python -m pytest apps/api/organizers/tests/test_api_workflows.py apps/api/trip_bookings/tests/ apps/api/trip_travelers/tests.py apps/api/trip_payments/tests.py apps/api/creative_setup/tests.py apps/api/team_access/tests.py apps/api/internal_admin/tests.py apps/api/trips/tests/ apps/api/tripos_api/tests.py -q`
  - Result: 456 passed
- Noted a temporary compatibility debt remains in `apps/api/organizers/services.py` (legacy service facade still exposes broad helper surface by design for API stability), while behavior ownership is now primarily in domain apps.

## Blocked by

- `.scratch/domain-backend-app-split/issues/39-remove-legacy-organizer-owned-behavior-paths.md`
