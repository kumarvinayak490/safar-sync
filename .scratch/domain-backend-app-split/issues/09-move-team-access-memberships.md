Status: done

# Move Team Access Memberships

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move organizer membership ownership into `team_access`. Membership roles, active/inactive state, ownership relationship, and access checks should live with Team Access rather than Organizer Settings or Organizer root code.

## Acceptance criteria

- [ ] Team Access owns organizer membership behavior and invariants.
- [ ] Existing membership APIs and permission checks keep their external behavior.
- [ ] Organizer root references memberships through Team Access interfaces.
- [ ] Tests cover membership creation, role visibility, and access checks.
- [ ] Django checks, migration dry-run, and linting pass.

## Blocked by

- `.scratch/domain-backend-app-split/issues/01-stabilize-domain-app-skeleton.md`
- `.scratch/domain-backend-app-split/issues/02-add-compatibility-import-safety-net.md`
- `.scratch/domain-backend-app-split/issues/03-move-organizer-root-basics.md`

## Comments

- 2026-05-29 19:23:09 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Team Access membership behavior and should avoid Organizer Profile identity code.
- 2026-05-29 19:34:03 IST: Orchestrator accepted Team Access membership ownership. Verified with `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `.venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/organizer_profile/tests.py apps/api/team_access/tests.py apps/api/tripos_api/tests.py apps/api/internal_admin/tests.py`. Invitations remain intentionally in scope for issue 10.
- 2026-05-29 19:32:16 IST: Worker completion note: moved Team Access membership creation, payload, role visibility, and active-user access checks behind `team_access` interfaces; kept old `organizers.permissions` membership imports working through re-exports; routed organizer onboarding/dashboard/payment read models through Team Access permissions; and added focused Team Access membership tests. Checks: `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `env DATABASE_URL=sqlite:////private/tmp/tripos-team-access-check.sqlite .venv/bin/python apps/api/manage.py check`, `env DATABASE_URL=sqlite:////private/tmp/tripos-team-access-check.sqlite .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, `env DATABASE_URL=sqlite:////private/tmp/tripos-team-access-tests.sqlite .venv/bin/python -m pytest apps/api/team_access/tests.py apps/api/tripos_api/tests.py`, and `env DATABASE_URL=sqlite:////private/tmp/tripos-team-access-workflows.sqlite .venv/bin/python -m pytest apps/api/organizers/tests/test_api_workflows.py -k "team_access or role_resolution or operations_dashboard"` passed. Default Postgres-backed pytest was attempted in sandbox and escalated mode, but local Postgres rejected the configured `tripos` credentials; default migration dry-run reported no model changes with the known sandbox Postgres connection warning.
