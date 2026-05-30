Status: done

# Move Booking Access Links

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move booking access link ownership into `trip_bookings`. Access links should coordinate booking contact access and traveler completion flows without making Trip Travelers own booking access state.

## Acceptance criteria

- [x] Trip Bookings owns booking access link lifecycle and expiry.
- [x] Traveler completion flows can validate access through Trip Bookings.
- [x] Existing access link URLs and API behavior remain stable.
- [x] Tests cover link creation, expiry, invalid token handling, and traveler-flow access.
- [x] Linting reports no stale legacy booking access imports.

## Blocked by

- `.scratch/domain-backend-app-split/issues/18-move-trip-booking-lifecycle.md`

## Comments

- 2026-05-29 21:17:04 IST: Assigned to Ralph worker Descartes (`019e746b-80cf-7791-8688-3b269948c14c`) for autonomous implementation. Worker owns Booking Access Link lifecycle, expiry/token validation, revocation helpers, and traveler-flow access validation in `trip_bookings`; Issue 19 owns booking imports in parallel.
- 2026-05-29 21:27:05 IST: Worker completion note: moved Booking Access Link token digesting, issuance, revocation, active-token resolution, expiry checks, and Traveler Portal slot access validation into `trip_bookings.access_links`; legacy Organizer service/view/serializer paths now delegate to Trip Bookings while keeping existing `/api/portal/<token>/` and operations access-link API behavior stable. Added Trip Bookings tests for link creation, expiry window, invalid token handling, revoked tokens, and traveler-flow access scoping. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue20.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue20.sqlite3 .venv/bin/python -m pytest apps/api/trip_bookings/tests.py apps/api/organizers/tests/test_api_workflows.py -k "access_link or portal or balance_payment_link" -q`; `git diff --check`.
- 2026-05-29 21:31:55 IST: Orchestrator accepted together with Issue 19. Verified `trip_bookings.access_links`, access-link model behavior, legacy Organizer portal/API delegates, and shared Trip Bookings tests. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trip_bookings/tests.py apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py -k 'booking_import or access_link or portal or balance_payment_link or booking_contact_change or manual_booking or booking_lifecycle'`; `git diff --check`.
