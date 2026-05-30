Status: done

# Add Creative Setup Ownership

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Create Creative Setup as the owner of organizer-level creative generation preferences: LLM/model choice, brand tone, default style, logo usage, and poster defaults. Do not let this become a generic organizer preferences module.

## Acceptance criteria

- [ ] Creative Setup owns only organizer-level creative preferences.
- [ ] Trip-specific generated assets remain out of scope for this app.
- [ ] No generic backend Organizer Settings or Organizer Preferences owner is introduced.
- [ ] Existing settings-like behavior is either moved here or documented as intentionally out of scope.
- [ ] Tests cover reading and updating creative setup through the stable backend surface.

## Blocked by

- `.scratch/domain-backend-app-split/issues/04-move-organizer-profile-identity.md`

## Comments

- 2026-05-29 19:43:03 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Creative Setup only; generated trip-scoped assets remain out of scope.
- 2026-05-29 19:52:09 IST: Orchestrator accepted Creative Setup ownership. Verified with `python3 -m ruff check apps/api`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py check`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/organizer_profile/tests.py apps/api/organizer_policies/tests.py apps/api/organizer_media/tests.py apps/api/creative_setup/tests.py apps/api/team_access/tests.py apps/api/tripos_api/tests.py apps/api/internal_admin/tests.py`.
- 2026-05-29 19:48:40 IST: Worker completion note: added Creative Setup as the domain owner for organizer-level creative generation preferences with a one-to-one setup record, stable read/update API, owner/operator access rules, and focused tests. Generated posters and trip-specific creative assets remain out of scope and are documented in the Creative Setup README. Checks: `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `DATABASE_URL=sqlite:////private/tmp/tripos-creative-setup.sqlite3 .venv/bin/python -m pytest apps/api/creative_setup/tests.py apps/api/team_access/tests.py apps/api/tripos_api/tests.py`, and `DATABASE_URL=sqlite:////private/tmp/tripos-creative-setup.sqlite3 .venv/bin/python apps/api/manage.py makemigrations creative_setup --check --dry-run` passed. Full all-app migration dry-run is blocked by a parallel Organizer Profile pending migration (`organizer_profile/migrations/0001_initial.py`) outside this worker scope.
