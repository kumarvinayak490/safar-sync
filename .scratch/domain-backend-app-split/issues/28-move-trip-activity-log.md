Status: done

# Move Trip Activity Log

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move trip activity log ownership into `trip_operations`. Activity log entries may describe events from bookings, travelers, and payments, but Trip Operations owns the operational timeline view.

## Acceptance criteria

- [x] Trip Operations owns activity log records and timeline behavior.
- [x] Booking, traveler, and payment domains can emit activity without becoming operations owners.
- [x] Existing activity log API behavior remains backward compatible.
- [x] Tests cover activity emitted from booking, traveler, and payment events.
- [x] Django checks, migration dry-run, and linting pass.

## Blocked by

- `.scratch/domain-backend-app-split/issues/18-move-trip-booking-lifecycle.md`
- `.scratch/domain-backend-app-split/issues/21-move-traveler-slots.md`
- `.scratch/domain-backend-app-split/issues/23-move-trip-payment-ledger-and-derived-state.md`

## Comments

- 2026-05-29 22:43:52 IST: Assigned to Ralph worker Hume (`019e74ba-a7d6-74e1-b709-19165ce14cab`) for autonomous implementation. Worker owns Activity Log emission/timeline behavior in `trip_operations`; notifications/reminders and dashboards/exports remain blocked for Issues 29 and 30.
- 2026-05-29 22:53:09 IST: Worker completion note: moved Activity Log emission, actor normalization, serializer ownership, and recent timeline payload behavior into `trip_operations.activity`, `trip_operations.serializers`, and `trip_operations.timeline`. Booking, Trip Travelers, Trip Payments, and Trip Profile activity emitters now call the Trip Operations interface while preserving existing model/table identity and legacy Organizer service/serializer imports as thin shims. Added focused Trip Operations tests for scope resolution, legacy service/serializer compatibility, and timeline ordering, plus Trip Payments coverage for sensitive Manual Payment activity. Checks: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue28.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue28.sqlite3 .venv/bin/python -m pytest apps/api/trip_operations/tests.py apps/api/trip_bookings/tests.py apps/api/trip_travelers/tests.py apps/api/trip_payments/tests.py apps/api/tripos_api/tests.py -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue28.sqlite3 .venv/bin/python -m pytest apps/api/organizers/tests/test_api_workflows.py apps/api/organizers/tests/test_trip_profile_activity_log.py apps/api/organizers/tests/test_trip_profile_publication_readiness.py -k "trip_overview or payment_proof_download_records_sensitive_payment_activity_log or booking_adjustment_requires_adjustment_reason_and_records_ledger_activity or traveler_cancellation_releases_capacity_without_ledger_entries or booking_cancellation_releases_all_capacity_without_ledger_entries or refund_record_requires_refund_reason_and_resolves_refund_due or operations_api_records_adjustments_and_refunds or sensitive_traveler_document_download_records_activity_log or activity_log" -q`; `git diff --check`. Known follow-up: Notification/reminder/announcement ownership and dashboard/export composition remain intentionally untouched for Issues 29 and 30.
- 2026-05-29 22:55:24 IST: Orchestrator accepted. Verified `trip_operations.activity`, `trip_operations.serializers`, `trip_operations.timeline`, booking/traveler/payment/trip emitters, legacy Organizer service/serializer shims, and activity timeline compatibility. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trip_operations/tests.py apps/api/trip_bookings/tests.py apps/api/trip_travelers/tests.py apps/api/trip_payments/tests.py apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py apps/api/organizers/tests/test_trip_profile_activity_log.py apps/api/organizers/tests/test_trip_profile_publication_readiness.py -k 'activity_log or trip_overview or payment_proof_download_records_sensitive_payment_activity_log or booking_adjustment_requires_adjustment_reason_and_records_ledger_activity or traveler_cancellation_releases_capacity_without_ledger_entries or booking_cancellation_releases_all_capacity_without_ledger_entries or refund_record_requires_refund_reason_and_resolves_refund_due or operations_api_records_adjustments_and_refunds or sensitive_traveler_document_download_records_activity_log or booking_lifecycle or traveler or manual_payment or payment_exception'`; `git diff --check`.
