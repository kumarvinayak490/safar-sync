Status: done

# Add Organizer Media Ownership

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Create Organizer Media as the owner of organizer-level media records, including uploads, captions, ordering, visibility, and reuse across organizer pages, public trip pages, and future creative generation.

## Acceptance criteria

- [ ] Organizer-level media records are owned by Organizer Media.
- [ ] Media visibility and ordering rules are represented in the domain model or service layer.
- [ ] Organizer Profile can display selected public organizer media without owning uploads.
- [ ] Existing media-related behavior remains backward compatible where present.
- [ ] Tests cover upload metadata, visibility, ordering, and profile display integration.

## Blocked by

- `.scratch/domain-backend-app-split/issues/04-move-organizer-profile-identity.md`

## Comments

- 2026-05-29 19:34:03 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Organizer Media; avoid Organizer Policies and Team Access invitation code.
- 2026-05-29 19:43:03 IST: Orchestrator accepted Organizer Media ownership. Verified combined policy/media state with `python3 -m ruff check apps/api`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py check`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/organizer_policies/tests.py apps/api/organizer_media/tests.py apps/api/organizer_profile/tests.py apps/api/team_access/tests.py apps/api/tripos_api/tests.py apps/api/internal_admin/tests.py`.
- 2026-05-29 19:40:48 IST: Worker completion note: added Organizer Media-owned upload records, metadata, visibility, ordering, validation, admin, API library view, and profile display composition for Public Organizer Media while leaving Trip Media untouched. Added focused Organizer Media tests covering upload metadata, visibility/order updates, profile display integration, permissions, validation, and legacy organizer API view re-export. Checks: `python3 -m ruff check apps/api`, `DATABASE_URL=sqlite:////private/tmp/tripos-organizer-media.sqlite3 .venv/bin/python apps/api/manage.py check`, `DATABASE_URL=sqlite:////private/tmp/tripos-organizer-media.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, `DATABASE_URL=sqlite:////private/tmp/tripos-organizer-media.sqlite3 .venv/bin/python -m pytest apps/api/organizer_media/tests.py apps/api/organizer_profile/tests.py`, and `DATABASE_URL=sqlite:////private/tmp/tripos-organizer-media.sqlite3 .venv/bin/python -m pytest apps/api/tripos_api/tests.py apps/api/organizer_media/tests.py` passed. Initial migration generation with the default local PostgreSQL settings succeeded but emitted the known sandbox connection warning during migration history checking.
