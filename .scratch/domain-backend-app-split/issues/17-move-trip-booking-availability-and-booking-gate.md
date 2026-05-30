Status: done

# Move Trip Booking Availability And Booking Gate

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move booking availability and the public booking gate into `trips`, while keeping checkout and payment behavior outside Public Discovery. The gate should compose trip publication state with organizer payment readiness and availability.

## Acceptance criteria

- [ ] Trips owns booking availability and booking gate decisions.
- [ ] Organizer payment readiness is consumed from Organizer Payments.
- [ ] Public Discovery does not own booking gate or checkout behavior.
- [ ] Existing public booking gate behavior remains backward compatible.
- [ ] Tests cover unpublished trips, unavailable trips, missing payment setup, and open booking states.

## Blocked by

- `.scratch/domain-backend-app-split/issues/11-move-organizer-payment-setup-readiness.md`
- `.scratch/domain-backend-app-split/issues/16-move-trip-publication-readiness-and-public-trip-page.md`

## Comments

- 2026-05-29 20:49:37 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Trips booking availability and public booking gate; checkout/payment collection remains outside this slice.
- 2026-05-29 21:02:09 IST: Orchestrator accepted Trips booking availability and public booking gate ownership. Verified with `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trips/tests.py apps/api/organizers/tests/test_payment_method_readiness.py apps/api/organizer_payments/tests/test_manual_payment_instructions.py apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py -k 'public_booking or payment_method_readiness or manual_payment_instructions or public_trip'`.
- 2026-05-29 20:57:41 IST: Worker completion note: moved Public Booking Gate and Booking Availability helpers into `trips.booking_availability`, moved public booking payment-method readiness into `trips.payment_method_readiness`, updated Trips public serialization and provider checkout validation to consume the Trips-owned gate, and left `organizers.public_booking_gate`, `organizers.payments.public_booking_gate`, `organizers.payments.payment_method_readiness`, and `organizers.services.public_booking_readiness` as compatibility shims/facades. Added Trips-owned regression coverage for unpublished trips, closed Booking Availability, missing payment readiness, open manual-payment booking, sold-out derivation from reserved travelers, and legacy re-exports. Checks: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-issue17.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-issue17.sqlite3 .venv/bin/python -m pytest apps/api/trips/tests.py apps/api/organizers/tests/test_payment_method_readiness.py apps/api/organizer_payments/tests/test_manual_payment_instructions.py apps/api/tripos_api/tests.py`; `DATABASE_URL=sqlite:////private/tmp/tripos-issue17.sqlite3 .venv/bin/python -m pytest apps/api/organizers/tests/test_api_workflows.py -k 'public_trip_booking_readiness or public_trip_page or public_availability_bands or public_sold_out_band or sold_out_booking_availability or draft_booking_does_not_affect_available_seats or reserved_booking_affects_available_seats or seat_hold'`. Known follow-up: none for this issue; booking lifecycle, seat holds, traveler records, and payment collection remain in their existing owners for later issues.
