Status: done

# Move Trip Operations Dashboards And Exports

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move operational dashboards, trip overview composition, and operational exports into `trip_operations`. These views may compose data from sibling domains but must not become owners of booking, traveler, payment, or trip profile state.

## Acceptance criteria

- [x] Trip Operations owns operational overview and export composition.
- [x] Dashboards compose sibling domain data through clear read interfaces.
- [x] Existing operations dashboard behavior remains backward compatible.
- [x] Tests cover dashboard summary values and export output shape.
- [x] Operations code does not duplicate source-of-truth business state.

## Blocked by

- `.scratch/domain-backend-app-split/issues/28-move-trip-activity-log.md`

## Comments

- 2026-05-29 22:56:11 IST: Assigned to Ralph worker Pascal (`019e74c6-51cf-7543-9c93-e32c66cd5703`) for autonomous implementation. Worker owns operations dashboards, trip overview composition, and operational exports in `trip_operations`; Issue 29 owns notifications/reminders in parallel.
- 2026-05-29 23:11:18 IST: Worker completion note: moved Operations Dashboard read models, Trip Overview composition, operational metrics, operational export generation, and operation-facing list/export serializers into `trip_operations`. Legacy `organizers.operations.dashboard`, `organizers.operations.trip_overview`, root `organizers.operations_dashboard`/`trip_overview`, `organizers.services.generate_operational_export_csv`, and legacy serializer imports now re-export Trip Operations owners. Added focused Trip Operations coverage for dashboard summary values, Trip Overview composition with recent activity, operational export output shape/sensitive columns/activity logging, and legacy compatibility. Checks: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue30.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue30.sqlite3 .venv/bin/python -m pytest apps/api/trip_operations/tests.py apps/api/trip_bookings/tests.py apps/api/trip_travelers/tests.py apps/api/trip_payments/tests.py apps/api/trips/tests.py apps/api/tripos_api/tests.py -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue30.sqlite3 .venv/bin/python -m pytest apps/api/organizers/tests/test_api_workflows.py -k "operations_dashboard or trip_overview or operational_export" -q`; `git diff --check`. Known follow-up: Issue 29 continues to own notification/reminder/announcement migration.
- 2026-05-29 23:14:47 IST: Orchestrator accepted. Verified dashboard, trip overview, metrics, exports, and operation-facing serializers are owned by `trip_operations`, with legacy `organizers` import paths reduced to shims and API views delegating into the new domain module. Acceptance checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trip_operations/tests.py apps/api/trip_bookings/tests.py apps/api/trip_travelers/tests.py apps/api/trip_payments/tests.py apps/api/trips/tests.py apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py -k 'notification or reminder or announcement or operations_dashboard or trip_overview or operational_export or recent_activity or balance_payment_link or reservation_acknowledgement or confirmation_notice or manual_payment_acknowledgement or refund_acknowledgement or date_change_notice or cancellation_notice' -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trip_operations/tests.py -q`; `git diff --check`.
