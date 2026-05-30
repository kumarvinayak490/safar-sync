Status: done

# Add Internal Admin Platform Fee Review Workflow

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Add a staff workflow in Internal Admin for reviewing platform fee statements and payment exceptions, while keeping the source fee and exception facts owned by Trip Payments.

## Acceptance criteria

- [x] Internal Admin can present platform fee and payment exception review workflows to staff.
- [x] Trip Payments remains the owner of fee statement and exception facts.
- [x] Review actions call Trip Payments-owned interfaces.
- [x] Tests cover staff access, review workflow behavior, and source ownership.
- [x] No payment facts are duplicated in Internal Admin.

## Blocked by

- `.scratch/domain-backend-app-split/issues/27-move-platform-fee-facts-and-payment-exceptions.md`
- `.scratch/domain-backend-app-split/issues/35-add-internal-admin-staff-shell.md`

## Comments

- 2026-05-29 23:16:56 IST: Assigned to Ralph worker Volta (`019e74d8-9bb1-7981-a687-23fa1aa5b06d`) for autonomous implementation. Worker owns the thin Internal Admin staff workflow for platform fee and payment exception review; Trip Payments remains the owner of fee and exception facts.
- 2026-05-29 23:25:36 IST: Worker completion note: added Internal Admin staff routes for Platform Fee Statement review and Payment Exception review/resolution, with review querysets, serializers, and resolution behavior delegated to Trip Payments-owned interfaces. Internal Admin remains model-free and does not duplicate payment facts. Checks passed: `python3 -m ruff check apps/api`; `DATABASE_URL=sqlite:////private/tmp/tripos-issue37.sqlite3 .venv/bin/python apps/api/manage.py check`; `DATABASE_URL=sqlite:////private/tmp/tripos-issue37.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `DATABASE_URL=sqlite:////private/tmp/tripos-issue37.sqlite3 .venv/bin/python -m pytest apps/api/internal_admin/tests.py apps/api/trip_payments/tests.py -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-issue37.sqlite3 .venv/bin/python -m pytest apps/api/tripos_api/tests.py apps/api/internal_admin/tests.py -q`; `DATABASE_URL=sqlite:////private/tmp/tripos-issue37.sqlite3 .venv/bin/python -m pytest apps/api/organizers/tests/test_api_workflows.py -k "internal_admin_manages_monthly_platform_fee_statements or payment_setup_status_does_not_expose_platform_fee_statement_management or owner_and_operator_can_resolve_late_confirmed_payment_exception or only_late_confirmed_payment_exceptions_support_booking_resolution or provider_dispute_exception_does_not_create_refund_or_change_booking_state" -q`; `git diff --check`.
- 2026-05-30 00:11:11 IST: Orchestrator accepted Issue 37. Internal Admin now exposes platform fee and payment-exception review workflows for staff while delegating all fee/exception data access and resolution actions to Trip Payments-owned interfaces. This keeps platform-fact ownership in the payments domain and preserves the staff-shell boundary. Checks were consistent with the worker slice: lint, Django/system checks, migration dry-run, and focused internal_admin/trip_payments API tests.
