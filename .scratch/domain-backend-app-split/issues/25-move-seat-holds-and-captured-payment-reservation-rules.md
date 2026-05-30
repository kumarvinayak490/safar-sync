Status: done

# Move Seat Holds And Captured-Payment Reservation Rules

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move seat holds and captured-payment reservation rules into `trip_payments`, while preserving the rule that public seats are reserved only after captured provider payments.

## Acceptance criteria

- [x] Trip Payments owns seat hold lifecycle and expiry.
- [x] Captured provider payment remains the reservation trigger for public booking seats.
- [x] Booking availability reads confirmed reservation effects correctly.
- [x] Existing seat hold and reservation behavior remains stable.
- [x] Tests cover hold creation, expiry, captured payment confirmation, and capacity impact.

## Blocked by

- `.scratch/domain-backend-app-split/issues/17-move-trip-booking-availability-and-booking-gate.md`
- `.scratch/domain-backend-app-split/issues/24-move-payment-attempts-and-provider-payments.md`

## Comments

- 2026-05-29 22:24:08 IST: Assigned to Ralph worker Huygens (`019e74a8-9ddf-70d2-8560-c4f10a92d25e`) for autonomous implementation. Worker owns seat holds, bookable-seat calculations, expiry/release behavior, and captured-payment/manual qualifying reservation rules in `trip_payments`; Issue 27 owns platform fee facts and payment exception review state in parallel.
- 2026-05-29 22:38:56 IST: Worker completion note: moved Seat Hold lifecycle, expiry/release helpers, Bookable Seats pressure, and qualifying payment reservation checks into `trip_payments`; kept `organizers.seat_holds`, `organizers.payments.seat_holds`, and legacy service APIs as thin compatibility paths; updated Trips booking availability, provider payment confirmation, manual payment approval, and booking import reservation calls to consume Trip Payments-owned interfaces. Added focused Trip Payments and Trips coverage for hold creation, expiry, release, captured-provider reservation, manual-payment reservation, late expired hold capacity exceptions, booking gate integration, and legacy import compatibility. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue25.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue25-domain.sqlite3 .venv/bin/python -m pytest apps/api/trip_payments apps/api/trip_bookings apps/api/trips -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph-issue25-pytest.sqlite3 .venv/bin/python -m pytest apps/api/trip_payments apps/api/trip_bookings apps/api/trips apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py -k 'seat_hold or bookable or provider_confirmation or payment_attempt or public_checkout or public_booking_readiness or public_booking_gate or manual_payment or late_provider_confirmation or reservation_confirmation or public_qr' -q`; `git diff --check`. Known follow-up: none for Issue 25; Issue 27 remains responsible for platform fee facts/payment exception review ownership.
- 2026-05-29 22:42:43 IST: Orchestrator accepted together with Issue 27. Verified `trip_payments.seat_holds`, `trip_payments.reservation_rules`, provider/manual/import reservation call sites, Trips booking availability, and legacy seat-hold shims. Checks passed: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trip_payments apps/api/trip_bookings apps/api/trips apps/api/internal_admin apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py apps/api/organizers/tests/test_public_qr_manual_payment_submission.py -k 'seat_hold or bookable or provider_confirmation or payment_attempt or public_checkout or public_booking_readiness or public_booking_gate or manual_payment or late_provider_confirmation or reservation_confirmation or public_qr or platform_fee or payment_exception or mismatched or provider_dispute or internal_admin_manages_monthly_platform_fee_statements or payment_setup_status_does_not_expose_platform_fee_statement_management or operations_payment_exception or financial_ledger'`; `git diff --check`.
