Status: done

# Move Organizer Payment Setup Readiness

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move organizer-level payment setup readiness into `organizer_payments`. This app should own whether an organizer is ready to collect payments, including connected provider account readiness and payout readiness signals.

## Acceptance criteria

- [ ] Organizer Payments owns payment setup readiness calculations.
- [ ] Trip and booking code reads organizer payment readiness through a clear domain interface.
- [ ] Payment setup behavior is no longer hidden under generic settings.
- [ ] Existing readiness API behavior remains backward compatible.
- [ ] Tests cover ready, not-ready, and partially configured payment setup states.

## Blocked by

- `.scratch/domain-backend-app-split/issues/01-stabilize-domain-app-skeleton.md`
- `.scratch/domain-backend-app-split/issues/02-add-compatibility-import-safety-net.md`
- `.scratch/domain-backend-app-split/issues/03-move-organizer-root-basics.md`

## Comments

- 2026-05-29 19:52:09 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Organizer Payment Setup readiness and should not move provider credentials or manual payment instructions yet.
- 2026-05-29 20:07:32 IST: Orchestrator accepted Organizer Payment Setup readiness. Verified with `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/team_access/tests.py apps/api/organizer_payments/tests/test_online_payment_readiness.py apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py -k 'invitation or team_access or last_owner or payment_setup or online_payment_readiness or settlement_readiness'`.
- 2026-05-29 20:05:49 IST: Worker completion note: moved Online Payment Readiness, Payment Setup readiness, Connected Provider Account readiness mutations, and Payment Setup record creation into `organizer_payments`, leaving legacy `organizers` and `organizers.payments` paths as thin compatibility imports. Updated API/operations/trip payment call sites to read organizer payment readiness through `organizer_payments`, moved focused readiness tests under `organizer_payments`, and kept provider authorization/credentials plus manual payment instructions in their existing owners for later issues. Checks: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `.venv/bin/python apps/api/manage.py makemigrations --check --dry-run` (no changes detected; local PostgreSQL sandbox warning only); `DATABASE_URL=sqlite:////private/tmp/tripos-safar-sync-test.sqlite3 .venv/bin/python -m pytest apps/api/organizer_payments/tests/test_online_payment_readiness.py apps/api/tripos_api/tests.py`; `DATABASE_URL=sqlite:////private/tmp/tripos-safar-sync-test.sqlite3 .venv/bin/python -m pytest apps/api/organizers/tests/test_api_workflows.py -k 'payment_setup or online_payment_readiness or settlement_readiness'`. PostgreSQL-backed focused pytest was attempted after sandbox approval but local `tripos` password authentication failed, so DB-backed pytest verification used the SQLite override.
