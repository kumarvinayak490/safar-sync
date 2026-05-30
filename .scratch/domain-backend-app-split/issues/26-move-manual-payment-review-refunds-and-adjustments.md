Status: done

# Move Manual Payment Review, Refunds, And Adjustments

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move manual payment review, refund records, and booking payment adjustments into `trip_payments`. These are payment facts and corrections, not booking lifecycle state.

## Acceptance criteria

- [x] Trip Payments owns manual payment review records and transitions.
- [x] Trip Payments owns refund records and payment adjustments.
- [x] Existing manual payment and refund APIs remain backward compatible.
- [x] Tests cover review approval/rejection, refunds, adjustments, and ledger effects.
- [x] Payment regression tests pass.

## Blocked by

- `.scratch/domain-backend-app-split/issues/23-move-trip-payment-ledger-and-derived-state.md`

## Comments

- 2026-05-29 22:03:21 IST: Assigned to Ralph worker Aristotle (`019e7495-dc38-7df0-9014-9153d79d4a0a`) for autonomous implementation. Worker owns manual payment review, refunds, adjustments, and ledger effects in `trip_payments`; Issue 24 owns provider payment attempts/webhooks in parallel.
- 2026-05-29 22:20:13 IST: Worker completion note: moved manual payment submission/review transitions, booking payment adjustments, refund records, payment-proof download activity, and their ledger/activity effects into `trip_payments`; legacy Organizer services, serializers, and views now delegate to or re-export Trip Payments implementations while preserving existing URLs. Added Trip Payments coverage for manual approval/rejection, adjustment/refund ledger effects, activity logs, owner-only refund records, and legacy API class compatibility. Checks: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue26.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue26.sqlite3 .venv/bin/python -m pytest apps/api/trip_payments -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue26.sqlite3 .venv/bin/python -m pytest apps/api/trip_bookings -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue26.sqlite3 .venv/bin/python -m pytest apps/api/organizers/tests/test_api_workflows.py apps/api/organizers/tests/test_public_qr_manual_payment_submission.py -k "manual_payment or adjustment or refund or operations_api_records_adjustments_and_refunds" -q`. Known follow-up: manual payment reservation still calls the existing reservation acknowledgement/capacity helpers pending the later seat-hold/reservation-rule split.
- 2026-05-29 22:23:11 IST: Orchestrator accepted together with Issue 24. Verified `trip_payments.manual_review`, `trip_payments.adjustments`, Trip Payments manual/refund serializers/views, legacy Organizer service/view/serializer delegates, payment proof download activity, and ledger effects. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trip_payments apps/api/trip_bookings apps/api/organizer_payments/tests/test_provider_authorization_and_credentials.py apps/api/organizer_payments/tests/test_provider_connection_tests.py apps/api/organizers/tests/test_api_workflows.py apps/api/organizers/tests/test_public_qr_manual_payment_submission.py -k 'provider or payment_attempt or checkout or webhook or qr or manual_payment or refund or adjustment or financial_ledger or payment_state or booking_reconciliation or reconciliation_flags or platform_fee or package_change or public_qr'`; `git diff --check`.
