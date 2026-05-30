Status: done

# Move Booking Imports

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move booking import sessions and import row behavior into `trip_bookings`. Imported rows should create or update booking lifecycle records without owning traveler readiness or payment ledger state.

## Acceptance criteria

- [x] Trip Bookings owns booking import records and import workflow behavior.
- [x] Import validation preserves existing accepted and rejected row behavior.
- [x] Imported booking creation continues to integrate with traveler and payment domains through explicit interfaces.
- [x] Existing import APIs remain backward compatible.
- [x] Tests cover valid imports, invalid rows, and import result summaries.

## Blocked by

- `.scratch/domain-backend-app-split/issues/18-move-trip-booking-lifecycle.md`

## Comments

- 2026-05-29 21:17:04 IST: Assigned to Ralph worker Bernoulli (`019e746b-44d8-76a2-99d0-9e186f1ed5d2`) for autonomous implementation. Worker owns Booking Import sessions/rows/parsing/validation/result summaries in `trip_bookings`; Issue 20 owns access links in parallel.
- 2026-05-29 21:29:45 IST: Worker completion note: moved Booking Import row inputs, intake preparation, import session processing, CSV upload parsing, opening payment recording, and import result serializers into `trip_bookings`; legacy Organizer service, intake, serializer, and view paths now delegate to the Trip Bookings-owned implementation while preserving the existing operations booking-import endpoint. Added Trip Bookings tests for valid imports, invalid/skipped/conflicted rows, result summaries, and CSV API compatibility. Checks: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue19.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue19.sqlite3 .venv/bin/python -m pytest apps/api/trip_bookings/tests.py apps/api/organizers/tests/test_api_workflows.py -k booking_import -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue19.sqlite3 .venv/bin/python -m pytest apps/api/trip_bookings/tests.py -q`; `git diff --check`. Known follow-up: imported opening payments still use the existing legacy financial-ledger/reservation acknowledgement facade until the scheduled Trip Payments ledger and captured-payment reservation issues move those owners.
- 2026-05-29 21:31:55 IST: Orchestrator accepted together with Issue 20. Verified `trip_bookings.imports`, `trip_bookings.serializers`, legacy Organizer import facades, and shared Trip Bookings tests. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trip_bookings/tests.py apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py -k 'booking_import or access_link or portal or balance_payment_link or booking_contact_change or manual_booking or booking_lifecycle'`; `git diff --check`.
