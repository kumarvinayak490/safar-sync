Status: done

# Move Trip Notifications And Reminders

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move trip notifications, reminders, announcements, and communication scheduling into `trip_operations`. These workflows should coordinate with booking and traveler state without owning those records.

## Acceptance criteria

- [x] Trip Operations owns notifications, reminders, and announcements.
- [x] Notification targeting reads booking and traveler state through explicit interfaces.
- [x] Existing notification behavior remains backward compatible.
- [x] Tests cover reminder creation, announcement visibility, and state-based targeting.
- [x] Operations code does not mutate booking, traveler, or payment state directly unless through owning interfaces.

## Blocked by

- `.scratch/domain-backend-app-split/issues/28-move-trip-activity-log.md`

## Comments

- 2026-05-29 22:56:11 IST: Assigned to Ralph worker Leibniz (`019e74c6-0511-7e30-8800-a6d346dc8c37`) for autonomous implementation. Worker owns notifications, reminders, announcements, targeting, and communication scheduling in `trip_operations`; Issue 30 owns dashboards/exports in parallel.
- 2026-05-29 23:11:10 IST: Worker completion note: moved notification, reminder, announcement, balance-link delivery, idempotency, targeting, content rendering, and activity logging behavior into `trip_operations.notifications`; moved notification/reminder/announcement serializers into `trip_operations.serializers`; added explicit booking contact/candidate, traveler recipient, and payment notification-state interfaces in sibling domains. Legacy `organizers.services` and `organizers.serializers` notification/reminder imports remain as thin compatibility shims. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue29.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue29.sqlite3 .venv/bin/python -m pytest apps/api/trip_operations/tests.py -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue29.sqlite3 .venv/bin/python -m pytest apps/api/trip_operations/tests.py apps/api/trip_bookings/tests.py apps/api/trip_travelers/tests.py apps/api/trip_payments/tests.py apps/api/organizers/tests/test_api_workflows.py -k 'notification or reminder or announcement or balance_payment_link or acknowledgement or date_change_notice or cancellation_notice or reservation_acknowledgement or payment_acknowledgement or refund_acknowledgement' -q`; `git diff --check`. Known follow-up: legacy `organizers.services` remains a broad facade while later split issues continue moving dashboard/export and other non-notification compatibility surfaces.
- 2026-05-29 23:14:47 IST: Orchestrator accepted. Verified that Trip Operations owns notification/reminder/announcement behavior, target/state reads come through explicit `trip_bookings`, `trip_travelers`, and `trip_payments` helper interfaces, and legacy `organizers` imports are compatibility shims. Acceptance checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trip_operations/tests.py apps/api/trip_bookings/tests.py apps/api/trip_travelers/tests.py apps/api/trip_payments/tests.py apps/api/trips/tests.py apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py -k 'notification or reminder or announcement or operations_dashboard or trip_overview or operational_export or recent_activity or balance_payment_link or reservation_acknowledgement or confirmation_notice or manual_payment_acknowledgement or refund_acknowledgement or date_change_notice or cancellation_notice' -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trip_operations/tests.py -q`; `git diff --check`.
