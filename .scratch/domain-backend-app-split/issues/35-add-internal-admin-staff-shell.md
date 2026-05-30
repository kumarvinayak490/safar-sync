Status: done

# Add Internal Admin Staff Shell

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Add a thin Internal Admin staff shell for staff-facing orchestration. Internal Admin may initiate module-owned actions and compose staff views, but it must not become the owner of business state.

## Acceptance criteria

- [ ] Internal Admin exists as a thin staff orchestration app.
- [ ] Staff access rules are explicit and tested.
- [ ] Internal Admin does not duplicate module-owned business records.
- [ ] Existing staff/admin behavior remains stable where present.
- [ ] Tests cover staff-only access and non-staff rejection.

## Blocked by

- `.scratch/domain-backend-app-split/issues/01-stabilize-domain-app-skeleton.md`

## Comments

- 2026-05-29 19:10:06 IST: Assigned to Ralph worker for autonomous implementation. Worker owns the thin Internal Admin staff shell; avoid compatibility shim work and broad domain moves.
- 2026-05-29 19:16:14 IST: Orchestrator accepted the Internal Admin staff shell. Verified with `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `.venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `.venv/bin/python -m pytest apps/api/tripos_api/tests.py apps/api/internal_admin/tests.py`. Shell is model-free and staff-gated.
- 2026-05-29 19:12:18 IST: Worker completion note: added a thin `internal_admin` staff shell at `/api/internal-admin/` with explicit staff-only permission checks, no Internal Admin business models, and tests for staff access plus non-staff rejection. Left existing organizer-hosted staff endpoints in place for migration compatibility; orchestrator should verify and mark done.
- 2026-05-29 19:14:41 IST: Worker verification: `python3 -m ruff check apps/api`, `.venv/bin/python -m pytest apps/api/tripos_api/tests.py apps/api/internal_admin/tests.py`, `.venv/bin/python apps/api/manage.py check`, and `.venv/bin/python apps/api/manage.py makemigrations --check --dry-run`. Migration dry-run reported no changes, with the same local PostgreSQL sandbox connection warning seen in issue 01.
