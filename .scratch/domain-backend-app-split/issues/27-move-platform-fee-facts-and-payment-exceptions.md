Status: done

# Move Platform Fee Facts And Payment Exceptions

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move platform fee statements and payment exceptions into `trip_payments`. Internal Admin may review or orchestrate these records later, but the business facts must remain owned by Trip Payments.

## Acceptance criteria

- [x] Trip Payments owns platform fee statement facts.
- [x] Trip Payments owns payment exception records and review state.
- [x] Internal Admin does not duplicate or own the payment facts.
- [x] Existing fee and exception behavior remains backward compatible.
- [x] Tests cover fee statement creation, exception states, and staff review integration hooks.

## Blocked by

- `.scratch/domain-backend-app-split/issues/23-move-trip-payment-ledger-and-derived-state.md`
- `.scratch/domain-backend-app-split/issues/24-move-payment-attempts-and-provider-payments.md`

## Comments

- 2026-05-29 22:24:08 IST: Assigned to Ralph worker Banach (`019e74a8-f184-7cd0-98df-fa7c8b6328d5`) for autonomous implementation. Worker owns platform fee statement facts, payment exception records/review state, and staff integration hooks in `trip_payments`; Issue 25 owns seat holds and reservation rules in parallel.
- 2026-05-29 22:40:40 IST: Worker completion note: moved Platform Fee Statement aggregation/generation into `trip_payments.platform_fees`, moved Payment Exception creation/review/dispute services into `trip_payments.payment_exceptions`, and moved staff-facing fee statement and exception review serializers/views into `trip_payments` with legacy Organizer shims preserved. Internal Admin remains a thin staff surface and does not store duplicate payment facts. Added focused Trip Payments coverage for fee statement creation/calculation, internal-admin fee statement hooks, mismatched provider payment exceptions, late exception resolution, provider dispute exceptions, and legacy fee/exception API re-exports. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue27.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue27.sqlite3 .venv/bin/python -m pytest apps/api/trip_payments apps/api/internal_admin apps/api/tripos_api/tests.py -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue27.sqlite3 .venv/bin/python -m pytest apps/api/organizers/tests/test_api_workflows.py -k "internal_admin_manages_monthly_platform_fee_statements or payment_setup_status_does_not_expose_platform_fee_statement_management or provider_confirmation_creates_mismatched_payment_exceptions or provider_confirmation_creates_mismatched_exception_for_provider_payment_reference or late_provider_confirmation_with_insufficient_bookable_seats_creates_exception or provider_dispute_exception_does_not_create_refund_or_change_booking_state or owner_and_operator_can_resolve_late_confirmed_payment_exception or only_late_confirmed_payment_exceptions_support_booking_resolution or reservation_confirmation_records_amount_exception_without_booking_outcome or platform_fees_are_recorded_for_reservation_and_balance_provider_payments or manual_payments_do_not_create_platform_fees or provider_confirmation_rejects_test_mode_payment" -q`; `git diff --check`. Known follow-up: broader Internal Admin orchestration for these Trip Payments-owned facts remains for the later Internal Admin issue.
- 2026-05-29 22:42:43 IST: Orchestrator accepted together with Issue 25. Verified `trip_payments.platform_fees`, `trip_payments.payment_exceptions`, provider lifecycle exception calls, staff-facing Trip Payments serializers/views, Internal Admin hook behavior, and legacy platform fee/exception shims. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trip_payments apps/api/trip_bookings apps/api/trips apps/api/internal_admin apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py apps/api/organizers/tests/test_public_qr_manual_payment_submission.py -k 'seat_hold or bookable or provider_confirmation or payment_attempt or public_checkout or public_booking_readiness or public_booking_gate or manual_payment or late_provider_confirmation or reservation_confirmation or public_qr or platform_fee or payment_exception or mismatched or provider_dispute or internal_admin_manages_monthly_platform_fee_statements or payment_setup_status_does_not_expose_platform_fee_statement_management or operations_payment_exception or financial_ledger'`; `git diff --check`.
