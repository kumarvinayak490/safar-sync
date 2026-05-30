Status: done

# Move Payment Attempts And Provider Payments

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move payment attempts, provider payment records, provider adapters, and provider webhook payment lifecycle behavior into `trip_payments`. Organizer Payments should own provider setup; Trip Payments should own booking-connected payment facts.

## Acceptance criteria

- [x] Trip Payments owns booking-connected payment attempts and provider payments.
- [x] Organizer Payments remains the source for provider setup and credentials.
- [x] Provider webhook behavior preserves idempotency and existing external behavior.
- [x] Existing public QR/manual payment submission and provider payment APIs remain stable.
- [x] Tests cover provider success, failure, duplicate webhook, and booking ledger integration.

## Blocked by

- `.scratch/domain-backend-app-split/issues/12-move-provider-authorization-and-credentials.md`
- `.scratch/domain-backend-app-split/issues/23-move-trip-payment-ledger-and-derived-state.md`

## Comments

- 2026-05-29 22:03:21 IST: Assigned to Ralph worker Singer (`019e7495-96a0-70e3-9dec-b45b477073b1`) for autonomous implementation. Worker owns provider payment attempts, provider payments, adapters, checkout/webhook lifecycle, and provider-payment API compatibility in `trip_payments`; Issue 26 owns manual review/refund/adjustment workflows in parallel.
- 2026-05-29 22:18:56 IST: Worker completion note: moved booking-connected provider checkout adapters, Payment Attempt/Provider Payment lifecycle, Razorpay webhook processing, and provider API call sites into `trip_payments`; split OAuth provider authorization adapters into `organizer_payments`; preserved legacy `organizers.provider_*` and `organizers.payments.provider_*` import paths as thin shims. Added Trip Payments coverage for browser checkout success/failure, duplicate webhook idempotency, provider ledger entries, legacy provider confirmation API compatibility, and public QR manual payment submission stability. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue24.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue24.sqlite3 .venv/bin/python -m pytest apps/api/trip_payments -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue24.sqlite3 .venv/bin/python -m pytest apps/api/trip_bookings -q`; focused Organizer Payments provider authorization/connection pytest; focused legacy provider/API compatibility pytest; `git diff --check`.
- 2026-05-29 22:23:11 IST: Orchestrator accepted together with Issue 26. Verified `trip_payments.provider_adapters`, `trip_payments.provider_payment_lifecycle`, `trip_payments.provider_webhooks`, Organizer Payments provider adapter split, legacy provider shims, public QR stability, and provider payment ledger integration. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trip_payments apps/api/trip_bookings apps/api/organizer_payments/tests/test_provider_authorization_and_credentials.py apps/api/organizer_payments/tests/test_provider_connection_tests.py apps/api/organizers/tests/test_api_workflows.py apps/api/organizers/tests/test_public_qr_manual_payment_submission.py -k 'provider or payment_attempt or checkout or webhook or qr or manual_payment or refund or adjustment or financial_ledger or payment_state or booking_reconciliation or reconciliation_flags or platform_fee or package_change or public_qr'`; `git diff --check`.
