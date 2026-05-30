Status: done

# Move Traveler Slots

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move traveler slot ownership into `trip_travelers`. Traveler slots represent the people attached to a booking and should remain separate from booking contact state and payment state.

## Acceptance criteria

- [x] Trip Travelers owns traveler slot records and traveler-level validation.
- [x] Booking lifecycle references traveler slots through explicit Trip Travelers interfaces.
- [x] Available seats and reserved traveler calculations remain correct.
- [x] Existing traveler slot APIs remain backward compatible.
- [x] Tests cover traveler slot creation, updates, capacity effects, and booking integration.

## Blocked by

- `.scratch/domain-backend-app-split/issues/18-move-trip-booking-lifecycle.md`

## Comments

- 2026-05-29 21:32:50 IST: Assigned to Ralph worker Aquinas (`019e7479-b107-7a90-abb0-ffe375b72011`) for autonomous implementation. Worker owns Traveler Slot behavior and validation in `trip_travelers`; Traveler Documents/readiness remain Issue 22, and Trip Payments ledger/reservation rules remain later slices.
- 2026-05-29 21:45:20 IST: Worker completion note: moved Traveler Slot intake, identity validation, capacity counts, booking amount/slot-count calculations, and traveler cancellation/replacement/addition/package-change behavior behind `trip_travelers.slots`. Trip Bookings lifecycle/import code now calls Trip Travelers slot interfaces, while legacy Organizer service and booking operation paths delegate to Trip Travelers and keep existing APIs/URLs stable. Traveler Documents, readiness payloads, portal document completion, and check-in remain in legacy readiness/operation paths for Issue 22; package-change ledger recording still uses the existing legacy payment ledger facade for later Trip Payments work. Checks: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue21.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue21.sqlite3 .venv/bin/python -m pytest apps/api/trip_travelers apps/api/trip_bookings -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue21.sqlite3 .venv/bin/python -m pytest apps/api/organizers/tests/test_api_workflows.py -k "traveler_slot or traveler_cancellation or traveler_replacement or traveler_addition or traveler_package or package_change or available_seats or capacity_derivation or manual_booking or booking_import" -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue21.sqlite3 .venv/bin/python -m pytest apps/api/tripos_api/tests.py -q`; `git diff --check`.
- 2026-05-29 21:47:16 IST: Orchestrator accepted. Verified `trip_travelers.slots`, Trip Bookings intake/lifecycle/import delegates, Booking model totals/counts, Trips booking availability, and legacy Organizer traveler operation facades. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trip_travelers apps/api/trip_bookings apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py -k 'traveler_slot or traveler_cancellation or traveler_replacement or traveler_addition or traveler_package or package_change or available_seats or capacity_derivation or manual_booking or booking_import or booking_lifecycle or access_link'`; `git diff --check`.
