Status: done

# Move Team Access Invitations And Owner Rules

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move organizer invitation flows and owner invariants into `team_access`. This includes invitation tokens, accepted/expired states, invite permissions, and rules that protect organizer ownership.

## Acceptance criteria

- [ ] Team Access owns invitation lifecycle behavior.
- [ ] Owner-only and operator-visible rules are enforced consistently.
- [ ] Ownership invariants cannot be bypassed through old organizer-owned paths.
- [ ] Existing invitation APIs remain backward compatible.
- [ ] Tests cover invitation creation, acceptance, expiry, and owner protection.

## Blocked by

- `.scratch/domain-backend-app-split/issues/09-move-team-access-memberships.md`

## Comments

- 2026-05-29 19:52:09 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Team Access invitations and owner protection rules.
- 2026-05-29 20:07:32 IST: Orchestrator accepted Team Access invitations and owner rules. Verified with `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/team_access/tests.py apps/api/organizer_payments/tests/test_online_payment_readiness.py apps/api/tripos_api/tests.py apps/api/organizers/tests/test_api_workflows.py -k 'invitation or team_access or last_owner or payment_setup or online_payment_readiness or settlement_readiness'`.
- 2026-05-29 20:00:07 IST: Worker completion note: moved Organizer Invitation lifecycle behavior into `team_access.invitations`, kept legacy organizer invitation imports as thin re-exports, routed legacy Organizer API serializers/views through Team Access, moved invitation admin ownership beside memberships, and added Team Access coverage for invitation creation, acceptance, duplicate membership/pending invite checks, expiry, revocation, compatibility imports, and last-owner protection through old model imports. Checks: `python3 -m ruff check apps/api`; `.venv/bin/python apps/api/manage.py check`; `.venv/bin/python apps/api/manage.py makemigrations --check --dry-run` (reported no model changes with the known sandbox PostgreSQL connection warning); `env DATABASE_URL=sqlite:////private/tmp/tripos-team-access-issue10-check.sqlite .venv/bin/python apps/api/manage.py check`; `env DATABASE_URL=sqlite:////private/tmp/tripos-team-access-issue10-migrations.sqlite .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`; `env DATABASE_URL=sqlite:////private/tmp/tripos-team-access-issue10-tests.sqlite .venv/bin/python -m pytest apps/api/team_access/tests.py apps/api/tripos_api/tests.py`; and `env DATABASE_URL=sqlite:////private/tmp/tripos-team-access-issue10-workflows.sqlite .venv/bin/python -m pytest apps/api/organizers/tests/test_api_workflows.py -k "invitation or team_access or last_owner"` passed.
