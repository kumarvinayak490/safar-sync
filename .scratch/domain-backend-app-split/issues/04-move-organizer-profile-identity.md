Status: done

# Move Organizer Profile Identity

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move public organizer identity behavior into `organizer_profile`: public name, logo, description, contact channel, and profile-facing serialization/API behavior. Keep Organizer root ownership separate from public organizer profile content.

## Acceptance criteria

- [ ] Organizer Profile owns public organizer identity behavior.
- [ ] Organizer root does not contain profile-specific business rules except transitional re-exports.
- [ ] Existing organizer profile API responses remain backward compatible.
- [ ] Tests cover public identity behavior through the stable domain/API surface.
- [ ] Django checks, migration dry-run, and linting pass.

## Blocked by

- `.scratch/domain-backend-app-split/issues/01-stabilize-domain-app-skeleton.md`
- `.scratch/domain-backend-app-split/issues/02-add-compatibility-import-safety-net.md`
- `.scratch/domain-backend-app-split/issues/03-move-organizer-root-basics.md`

## Comments

- 2026-05-29 19:23:09 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Organizer Profile identity behavior and should keep tests under Organizer Profile where possible.
- 2026-05-29 19:34:03 IST: Orchestrator accepted Organizer Profile identity ownership. Verified with `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `.venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/organizer_profile/tests.py apps/api/team_access/tests.py apps/api/tripos_api/tests.py apps/api/internal_admin/tests.py` after correcting the SQLite env var. The default PostgreSQL-backed run remains blocked by local sandbox/credential access.
- 2026-05-29 19:29:59 IST: Worker completion note: moved public organizer identity helpers, logo validation, fallback payloads, identity serialization, and the identity API view into `organizer_profile`; converted old Organizer Settings and flat Organizer Identity paths to thin re-export shims; left Organizer root display properties as transitional delegators to Organizer Profile; and added Organizer Profile tests for public identity behavior, legacy route response shape, logo validation, and compatibility imports. Checks: `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `.venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `.venv/bin/python -m pytest apps/api/organizer_profile/tests.py apps/api/tripos_api/tests.py -k 'not profile_identity_api'` passed. The full focused pytest command including the DB-backed API route test could not complete locally: sandboxed PostgreSQL access was blocked, and the approved rerun reached PostgreSQL but failed on local `tripos` password authentication.
