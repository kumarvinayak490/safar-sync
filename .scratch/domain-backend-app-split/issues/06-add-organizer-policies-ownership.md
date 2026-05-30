Status: done

# Add Organizer Policies Ownership

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Create Organizer Policies as the owner of the organizer Privacy Policy, Refund Policy, and Cancellation Policy. These policies should be reusable by organizer pages and trip pages without becoming profile identity.

## Acceptance criteria

- [ ] Organizer Policies owns all three fixed organizer-level policy fields.
- [ ] Owner-only edit rules are enforced for policy changes.
- [ ] Operators can view policies but cannot edit them in v1.
- [ ] Organizer Profile publication checks read required policy readiness from Organizer Policies.
- [ ] Tests cover policy edits, role restrictions, and publication readiness integration.

## Blocked by

- `.scratch/domain-backend-app-split/issues/04-move-organizer-profile-identity.md`

## Comments

- 2026-05-29 19:34:03 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Organizer Policies; avoid Organizer Media and Team Access invitation code.
- 2026-05-29 19:43:03 IST: Orchestrator accepted Organizer Policies ownership. Verified combined policy/media state with `python3 -m ruff check apps/api`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py check`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/organizer_policies/tests.py apps/api/organizer_media/tests.py apps/api/organizer_profile/tests.py apps/api/team_access/tests.py apps/api/tripos_api/tests.py apps/api/internal_admin/tests.py`.
- 2026-05-29 19:39:40 IST: Worker completion note: added Organizer Policies ownership with a domain-owned `OrganizerPolicies` model/migration, owner-edit/operator-view API at `/api/organizers/<organizer_id>/policies/`, explicit role capabilities, and a reusable required policy readiness interface for Organizer Profile publication rules. Tests cover owner edits, operator view/edit restrictions, role capabilities, and missing-policy readiness. Checks: `python3 -m ruff check apps/api/organizer_policies apps/api/team_access/permissions.py apps/api/tripos_api/urls.py`, `.venv/bin/python apps/api/manage.py check`, `.venv/bin/python apps/api/manage.py makemigrations organizer_policies --check --dry-run`, and `DATABASE_URL=sqlite:////private/tmp/tripos-organizer-policies.sqlite3 .venv/bin/python -m pytest apps/api/organizer_policies/tests.py apps/api/team_access/tests.py apps/api/tripos_api/tests.py` passed. Broad `python3 -m ruff check apps/api` currently fails on an Organizer Media import-order change in `apps/api/organizers/urls.py`, which is outside this worker's scope.
