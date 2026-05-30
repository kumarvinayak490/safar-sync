Status: done

# Move Trip Booking Lifecycle

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move reservation and booking lifecycle behavior into `trip_bookings`: booking creation, manual bookings, booking state, booking contact coordination, and cancellation-related lifecycle transitions that are not payment ledger facts.

## Acceptance criteria

- [x] Trip Bookings owns booking lifecycle behavior.
- [x] Booking state remains distinct from traveler records and payment state.
- [x] Existing booking APIs remain backward compatible.
- [x] Tests cover manual booking creation, booking state transitions, and booking contact behavior.
- [x] Django checks, migration dry-run, and linting pass.

## Blocked by

- `.scratch/domain-backend-app-split/issues/17-move-trip-booking-availability-and-booking-gate.md`

## Comments

- 2026-05-29 21:02:09 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Trip Bookings lifecycle; booking imports/access links/travelers/payments remain later slices.
- 2026-05-29 21:12:12 IST: Worker completion note: moved Booking lifecycle intake and state transitions into `trip_bookings.intake` and `trip_bookings.lifecycle`; legacy Organizer booking intake/operations paths now delegate lifecycle behavior while keeping Booking Import and Traveler operations in their current owners for later issues. Updated Organizer API facades and Trips/payment helpers to consume Trip Bookings-owned lifecycle helpers, and added Trip Bookings tests for manual booking creation, confirm/unconfirm/cancel guards, cancellation activity, and Booking Contact access-link revocation. Checks: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-issue18.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-issue18.sqlite3 .venv/bin/python -m pytest apps/api/trip_bookings/tests.py apps/api/tripos_api/tests.py -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-issue18.sqlite3 .venv/bin/python -m pytest apps/api/organizers/tests/test_api_workflows.py -k 'manual_booking or confirm_booking or unconfirm_booking or cancel_booking or booking_contact_change' -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-issue18.sqlite3 .venv/bin/python -m pytest apps/api/organizers/tests/test_public_qr_manual_payment_submission.py apps/api/trips/tests.py -q`. Known follow-up: Booking Import and Traveler Slot lifecycle remain in legacy Organizer paths for issues 19 and 21-22.
- 2026-05-29 21:14:00 IST: Additional broad regression attempt `DATABASE_URL=sqlite:////private/tmp/tripos-issue18.sqlite3 .venv/bin/python -m pytest apps/api/organizers/tests/test_api_workflows.py -q` ran 306 tests with 305 passing and 1 failing in `test_trip_date_change_sends_notice_without_financial_effect` because Trip Profile Lock blocks Trip Date edits. That failure is outside this Booking lifecycle slice and was not changed here.
- 2026-05-29 21:16:27 IST: Orchestrator accepted. Verified Issue 18 scope around `trip_bookings.intake`, `trip_bookings.lifecycle`, legacy compatibility facades, Trip booking gate/payment helpers, and TripOS compatibility tests. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trip_bookings/tests.py apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py apps/api/organizers/tests/test_public_qr_manual_payment_submission.py apps/api/trips/tests.py -k 'manual_booking or booking_lifecycle or booking_cancel or booking_confirm or booking_unconfirm or public_booking or booking_access or trip_profile_core'`; `git diff --check`.
