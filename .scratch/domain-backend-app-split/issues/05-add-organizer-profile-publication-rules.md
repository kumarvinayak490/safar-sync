Status: done

# Add Organizer Profile Publication Rules

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Add Organizer Profile publication ownership. Organizer Profile should own publication state and enforce that public description and required policies are present before publishing, while organizer media remains encouraged but not required.

## Acceptance criteria

- [ ] Organizer Profile has its own publication state separate from Trip publication.
- [ ] Publishing requires public description plus Privacy Policy, Refund Policy, and Cancellation Policy.
- [ ] Organizer public media is not required for publishing.
- [ ] Owners can publish; operators can view but cannot publish.
- [ ] Tests cover successful publication, missing required inputs, and role restrictions.

## Blocked by

- `.scratch/domain-backend-app-split/issues/04-move-organizer-profile-identity.md`
- `.scratch/domain-backend-app-split/issues/06-add-organizer-policies-ownership.md`

## Comments

- 2026-05-29 19:43:03 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Organizer Profile publication state/rules; media should be encouraged but not required.
- 2026-05-29 19:52:09 IST: Orchestrator accepted Organizer Profile publication rules. Verified with `python3 -m ruff check apps/api`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py check`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/organizer_profile/tests.py apps/api/organizer_policies/tests.py apps/api/organizer_media/tests.py apps/api/creative_setup/tests.py apps/api/team_access/tests.py apps/api/tripos_api/tests.py apps/api/internal_admin/tests.py`.
- 2026-05-29 19:50:21 IST: Worker completion note: added Organizer Profile-owned publication record with Public Organizer Description and Organizer Profile Publication State; added readiness rules requiring Public Organizer Description plus Privacy, Refund, and Cancellation policies; kept Public Organizer Media as an encouraged non-blocking signal; exposed profile publication/readiness through the existing organizer profile identity API; and enforced Owner publish/edit with Operator view-only access. Checks: `python3 -m ruff check apps/api`, `DATABASE_URL=sqlite:////private/tmp/tripos-organizer-profile-publication.sqlite3 .venv/bin/python apps/api/manage.py check`, `DATABASE_URL=sqlite:////private/tmp/tripos-organizer-profile-publication.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, `DATABASE_URL=sqlite:////private/tmp/tripos-organizer-profile-publication.sqlite3 .venv/bin/python -m pytest apps/api/organizer_profile/tests.py apps/api/organizer_policies/tests.py apps/api/organizer_media/tests.py apps/api/team_access/tests.py`, and `DATABASE_URL=sqlite:////private/tmp/tripos-organizer-profile-publication.sqlite3 .venv/bin/python -m pytest apps/api/organizers/tests/test_trip_profile_publication_readiness.py` passed.
