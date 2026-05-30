Status: done

# Move Traveler Documents And Readiness

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move traveler documents, traveler check-in, and traveler readiness behavior into `trip_travelers`. These are traveler-level operational facts, not booking contact fields.

## Acceptance criteria

- [x] Trip Travelers owns traveler document records and readiness checks.
- [x] Traveler readiness integrates with trip operations views without being owned by operations.
- [x] Existing traveler document and readiness APIs remain backward compatible.
- [x] Tests cover document upload metadata, readiness complete/incomplete states, and check-in behavior.
- [x] Django checks, migration dry-run, and linting pass.

## Blocked by

- `.scratch/domain-backend-app-split/issues/21-move-traveler-slots.md`

## Comments

- 2026-05-29 21:47:49 IST: Assigned to Ralph worker Dalton (`019e7487-64e8-7613-9b3c-c777bd7eda78`) for autonomous implementation. Worker owns Traveler Documents, readiness payloads, sensitive document helpers, and check-in/no-show behavior in `trip_travelers`; Trip Payments ledger work runs in parallel under Issue 23.
- 2026-05-29 21:59:07 IST: Worker completion note: moved Traveler Document submission/review/state summaries, Traveler Readiness confirmation and portal payloads, sensitive document filename/download logging helpers, and Traveler Check-In/No-Show behavior into `trip_travelers`. Legacy Organizer readiness and booking operation paths now delegate to Trip Travelers, and existing organizer/traveler portal document/readiness/check-in URLs remain compatible. Added focused Trip Travelers tests for document metadata, readiness complete/incomplete states, portal readiness, sensitive filename handling/download logging, and check-in/no-show compatibility. Checks: Issue 22 ruff target set passed; full `python3 -m ruff check apps/api` is still blocked by parallel Trip Payments import/line-length findings in `apps/api/organizers/payments/provider_payment_lifecycle.py` and `apps/api/trip_payments/tests.py`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue22.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue22.sqlite3 .venv/bin/python -m pytest apps/api/trip_travelers apps/api/trip_bookings apps/api/tripos_api/tests.py -q`; focused legacy organizer traveler document/readiness/check-in pytest passed for `apps/api/organizers/tests/test_api_workflows.py` and `apps/api/organizers/tests/test_trip_profile_confirmation_requirements.py`.
- 2026-05-29 22:02:22 IST: Orchestrator accepted together with Issue 23. Verified `trip_travelers.documents`, `trip_travelers.readiness`, `trip_travelers.check_in`, legacy Organizer readiness/operation shims, and confirmation/portal compatibility paths. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trip_travelers apps/api/trip_payments apps/api/trip_bookings apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py apps/api/organizers/tests/test_trip_profile_confirmation_requirements.py -k 'traveler_document or traveler_readiness or readiness or check_in or no_show or confirmation_requirements or financial_ledger or payment_state or booking_reconciliation or reconciliation_flags or platform_fee or provider_fee_and_net_settlement or package_change or operations_api_records_adjustments_and_refunds or operations_booking_detail_exposes_financial_ledger or booking_lifecycle or manual_booking or booking_import'`; `git diff --check`.
