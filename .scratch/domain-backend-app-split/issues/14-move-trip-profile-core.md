Status: done

# Move Trip Profile Core

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move Trip Profile core ownership into `trips`: organizer-owned trips, public trip content basics, trip status, capacity basics, and structured rich text handling. Trips should be a top-level sibling app, not nested inside organizer code.

## Acceptance criteria

- [ ] Trips owns trip profile core behavior and domain language.
- [ ] Organizer ownership is represented as `organizer_id` ownership, not package nesting.
- [ ] Structured rich text behavior remains compatible.
- [ ] Existing trip profile APIs continue to respond as before.
- [ ] Tests cover creating, reading, updating, and validating trip profile core data.

## Blocked by

- `.scratch/domain-backend-app-split/issues/01-stabilize-domain-app-skeleton.md`
- `.scratch/domain-backend-app-split/issues/02-add-compatibility-import-safety-net.md`
- `.scratch/domain-backend-app-split/issues/03-move-organizer-root-basics.md`

## Comments

- 2026-05-29 20:19:29 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Trips core/profile behavior and should not move itinerary/packages/media/publication readiness yet.
- 2026-05-29 20:29:00 IST: Orchestrator accepted Trips core/profile ownership. Verified with `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trips/tests.py apps/api/organizers/tests/test_trip_profile_description.py apps/api/tripos_api/tests.py`.
- 2026-05-29 20:27:39 IST: Worker completion note: moved Trip Rich Text and Published Trip Profile Lock behavior into the top-level `trips` app, added Trips-owned core selector and serializer surfaces for organizer-owned Trip Profile data, routed existing organizer API integration through the Trips selector/description serializer, and kept old organizer rich-text/lock import paths as thin compatibility shims. Added Trips-owned tests for create/read/update/validation coverage and compatibility re-exports. Checks: `python3 -m ruff check apps/api` passed; `.venv/bin/python apps/api/manage.py check` passed; `.venv/bin/python apps/api/manage.py makemigrations --check --dry-run` reported no model changes with the known local PostgreSQL sandbox connection warning; `env DATABASE_URL=sqlite:////private/tmp/tripos-issue14.sqlite3 .venv/bin/python -m pytest apps/api/trips/tests.py apps/api/organizers/tests/test_trip_profile_description.py apps/api/tripos_api/tests.py` passed with 16 tests. The same focused pytest command against local PostgreSQL was attempted in sandbox and escalated modes; sandbox mode was blocked from localhost, and escalated mode reached PostgreSQL but failed on local `tripos` password authentication.
