Status: done

# Move Manual Payment Instructions

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move organizer-owned manual payment instructions into `organizer_payments`. These instructions are organizer-level setup content reused by public booking flows, not trip payment ledger records.

## Acceptance criteria

- [ ] Organizer Payments owns manual payment instruction configuration.
- [ ] Public booking flows can read manual payment instructions without owning them.
- [ ] Existing instruction update and display behavior remains backward compatible.
- [ ] Tests cover required fields, QR/proof metadata where present, and public-read integration.
- [ ] Linting catches no stale references to legacy payment instruction modules.

## Blocked by

- `.scratch/domain-backend-app-split/issues/11-move-organizer-payment-setup-readiness.md`

## Comments

- 2026-05-29 20:07:32 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Organizer Payments manual payment instructions; avoid trip payment ledger/manual payment review.
- 2026-05-29 20:19:29 IST: Orchestrator accepted manual payment instructions ownership. Verified with `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/organizer_payments/tests apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py apps/api/organizers/tests/test_payment_method_readiness.py -k 'provider_authorization or credential or provider_connection or manual_payment_instructions or payment_setup or online_payment_readiness or settlement_readiness or payment_method_readiness'`.
- 2026-05-29 20:17:59 IST: Worker completion note: moved Manual Payment Instructions payload, QR validation, serializer, and API view ownership into `organizer_payments`, leaving `organizers.payments.manual_payment_instructions` as a thin compatibility re-export. Updated payment setup/status, payment method readiness, services, public trip page serialization, and compatibility smoke coverage to read through the Organizer Payments domain interface while leaving manual payment proof submission/review and ledger behavior in their existing trip-payment paths for later issues. Checks: `python3 -m ruff check apps/api/organizer_payments apps/api/organizers apps/api/tripos_api/tests.py`; `.venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-issue13.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-issue13.sqlite3 .venv/bin/python -m pytest apps/api/organizer_payments/tests/test_manual_payment_instructions.py apps/api/organizers/tests/test_public_qr_manual_payment_submission.py apps/api/tripos_api/tests.py -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-issue13.sqlite3 .venv/bin/python -m pytest apps/api/organizers/tests/test_payment_method_readiness.py apps/api/organizer_payments/tests/test_online_payment_readiness.py -q`.
