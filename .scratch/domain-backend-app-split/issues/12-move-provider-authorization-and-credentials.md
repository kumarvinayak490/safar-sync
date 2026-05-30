Status: done

# Move Provider Authorization And Credentials

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move provider authorization, provider credentials, connection tests, and credential audit behavior into `organizer_payments`. Preserve provider-neutral domain language while supporting the current payment provider implementation.

## Acceptance criteria

- [ ] Organizer Payments owns provider authorization sessions and credential records.
- [ ] Sensitive credential handling and audit behavior remain unchanged.
- [ ] Provider connection test behavior remains externally stable.
- [ ] Existing payment setup APIs continue to work.
- [ ] Tests cover authorization lifecycle, credential storage paths, audits, and connection test results.

## Blocked by

- `.scratch/domain-backend-app-split/issues/11-move-organizer-payment-setup-readiness.md`

## Comments

- 2026-05-29 20:07:32 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Organizer Payments provider authorization, credentials, audits, and connection tests.
- 2026-05-29 20:19:29 IST: Orchestrator accepted provider authorization and credentials. Verified with `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/organizer_payments/tests apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py apps/api/organizers/tests/test_payment_method_readiness.py -k 'provider_authorization or credential or provider_connection or manual_payment_instructions or payment_setup or online_payment_readiness or settlement_readiness or payment_method_readiness'`.
- 2026-05-29 20:16:11 IST: Worker completion note: moved Provider Authorization, Sensitive Provider Credential storage/audit helpers, and Provider Connection Tests into `organizer_payments`, with legacy `organizers` and `organizers.payments` paths reduced to thin compatibility imports. Updated API, webhook, provider-payment lifecycle credential reads, compatibility smoke tests, and focused provider tests to use the new Organizer Payments owners while leaving booking-connected provider payment lifecycle/webhook behavior in the legacy issue-24 scope. Checks: touched-file `python3 -m ruff check` passed; `.venv/bin/python apps/api/manage.py check` passed; `DATABASE_URL=sqlite:////private/tmp/tripos-issue12.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run` reported no changes; focused provider pytest passed (`14 passed`); organizer payments/tripos API pytest passed (`30 passed`). Full `python3 -m ruff check apps/api` still reports import-order issues in parallel/manual-payment-related files not edited for this slice.
