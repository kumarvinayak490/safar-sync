Status: done

# Stabilize Domain App Skeleton

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Normalize the backend into the agreed domain Django app skeleton so new work has a correct destination. This slice should create or repair the target app packages, register them in the Django project, make package discovery include them, and document the current migration order without moving business behavior yet.

## Acceptance criteria

- [ ] All target domain Django apps from the PRD are present, importable, and have app configs.
- [ ] The Django project starts with all target apps registered in one server and one database.
- [ ] Package discovery includes the new domain apps.
- [ ] Partially created app skeletons are normalized rather than duplicated.
- [ ] Django system checks pass.
- [ ] A migration dry-run shows only expected app skeleton state or no model changes.

## Blocked by

None - can start immediately

## Comments

- 2026-05-29 18:57:18 IST: Assigned to Ralph worker for autonomous implementation. Worker should normalize the existing partial domain app skeleton, keep edits scoped to issue 01, and report changed files plus checks run.
- 2026-05-29 19:10:06 IST: Orchestrator accepted the skeleton/app-wiring slice. Verified with `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `.venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `.venv/bin/python -m pytest apps/api/tripos_api/tests.py`. Migration dry-run reported no model changes; PostgreSQL history check emitted a sandbox/local connection warning only.
- 2026-05-29 19:08:02 IST: Worker completion note: registered all target domain Django apps, expanded package discovery, normalized the existing partial model split so historical persisted model state still belongs to the `organizers` migration chain, added domain-app smoke checks, and documented the current migration order. Checks: Django `check` passed, `makemigrations --check --dry-run` reported no changes, domain apps show no migrations yet, ruff passed, and the new smoke tests passed. Broader organizer/health regression run was 410 passed / 1 failed on existing `test_trip_date_change_sends_notice_without_financial_effect` trip profile lock behavior.
