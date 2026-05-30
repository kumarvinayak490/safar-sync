Status: done

# Add Internal Admin Demand Page Workflow

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Add a staff workflow in Internal Admin for configuring Demand Pages, while keeping Demand Page records and rules owned by Public Discovery.

## Acceptance criteria

- [x] Internal Admin can initiate Demand Page configuration for staff users.
- [x] Public Discovery remains the owner of Demand Page records and validation.
- [x] Staff workflow preserves Demand Page listing and SEO rules.
- [x] Tests cover staff create/update flows and non-staff rejection.
- [x] No Demand Page business state is duplicated in Internal Admin.

## Blocked by

- `.scratch/domain-backend-app-split/issues/32-add-demand-page-configuration-model.md`
- `.scratch/domain-backend-app-split/issues/35-add-internal-admin-staff-shell.md`

## Comments

- 2026-05-30 23:58:00 IST: Orchestrator marked Issue 36 done. Implemented Internal Admin demand page workflow against public-discovery-owned Demand Pages. Added staff-only shell coverage and demand-page CRUD/readback checks in `apps/api/internal_admin/tests.py`; kept validation and listing logic in `apps/api/public_discovery`.
- Verification run:
  - `pytest apps/api/public_discovery/tests.py apps/api/internal_admin/tests.py -q`
  - `ruff check apps/api/public_discovery/tests.py apps/api/public_discovery/models.py apps/api/public_discovery/selectors.py apps/api/internal_admin/tests.py apps/api/internal_admin/views.py`
  - `python apps/api/manage.py check`
  - `python apps/api/manage.py makemigrations --check --dry-run`
