Status: done

# Move Trip Payment Ledger And Derived State

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move the financial ledger and payment-derived booking state into `trip_payments`. Payment state should continue to be derived from ledger facts rather than duplicated into booking lifecycle code.

## Acceptance criteria

- [x] Trip Payments owns ledger entries and payment-derived state calculations.
- [x] Trip Bookings does not duplicate payment state.
- [x] Existing booking payment summaries remain backward compatible.
- [x] Tests cover ledger entries, due/paid/overdue derived state, and booking integration.
- [x] Payment regression tests pass.

## Blocked by

- `.scratch/domain-backend-app-split/issues/18-move-trip-booking-lifecycle.md`
- `.scratch/domain-backend-app-split/issues/21-move-traveler-slots.md`

## Comments

- 2026-05-29 21:47:49 IST: Assigned to Ralph worker Ohm (`019e7487-abe4-7163-b1d4-beb4a8d1ed88`) for autonomous implementation. Worker owns Trip Payment ledger behavior and payment-derived state in `trip_payments`; Traveler Documents/readiness work runs in parallel under Issue 22.
- 2026-05-29 22:00:36 IST: Worker completion note: moved Financial Ledger implementation, payment-derived reconciliation/state helpers, booking payment summaries, and ledger signal receivers into `trip_payments`; legacy `organizers.financial_ledger` and `organizers.payments.financial_ledger` now re-export the Trip Payments implementation. Trip Bookings keeps only a compatibility property for collected provider payment amount, delegated to Trip Payments, and legacy Organizer serializers/read models delegate reconciliation payloads, flags, and summaries to Trip Payments. Added focused Trip Payments tests for supported ledger entries, due/paid/overdue/refund-derived states, provider/platform fee totals, package-change ledger entries, booking integration, and legacy summary/flag compatibility. Checks: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue23.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue23.sqlite3 .venv/bin/python -m pytest apps/api/trip_payments apps/api/trip_bookings apps/api/trip_travelers apps/api/tripos_api/tests.py -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue23.sqlite3 .venv/bin/python -m pytest apps/api/organizers/tests/test_api_workflows.py -k "financial_ledger or payment_state or booking_reconciliation or reconciliation_flags or platform_fee or provider_fee_and_net_settlement or package_change or operations_api_records_adjustments_and_refunds or operations_booking_detail_exposes_financial_ledger" -q`; `git diff --check`. Known follow-up: provider payment attempt/callback/reservation behavior and manual review/refund workflow ownership remain in later issues 24-26.
- 2026-05-29 22:02:22 IST: Orchestrator accepted together with Issue 22. Verified `trip_payments.financial_ledger`, signal registration, legacy financial-ledger re-export shims, payment summary/reconciliation compatibility, and cross-domain confirmation readiness integration. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trip_travelers apps/api/trip_payments apps/api/trip_bookings apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py apps/api/organizers/tests/test_trip_profile_confirmation_requirements.py -k 'traveler_document or traveler_readiness or readiness or check_in or no_show or confirmation_requirements or financial_ledger or payment_state or booking_reconciliation or reconciliation_flags or platform_fee or provider_fee_and_net_settlement or package_change or operations_api_records_adjustments_and_refunds or operations_booking_detail_exposes_financial_ledger or booking_lifecycle or manual_booking or booking_import'`; `git diff --check`.
