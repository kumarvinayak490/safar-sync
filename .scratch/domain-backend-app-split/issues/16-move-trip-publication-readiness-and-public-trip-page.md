Status: done

# Move Trip Publication Readiness And Public Trip Page

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move Trip Profile publication readiness and Public Trip Page content ownership into `trips`. Public Discovery may route to published trip pages later, but Trips must own the content and publication state.

## Acceptance criteria

- [ ] Trips owns trip publication state and readiness checks.
- [ ] Public Trip Page content is sourced from Trips-owned structures.
- [ ] Publication rules continue to require payment and content readiness where applicable.
- [ ] Existing public trip page behavior remains stable.
- [ ] Tests cover readiness failures, successful publication, and public trip serialization.

## Blocked by

- `.scratch/domain-backend-app-split/issues/14-move-trip-profile-core.md`
- `.scratch/domain-backend-app-split/issues/15-move-trip-itinerary-packages-and-media.md`

## Comments

- 2026-05-29 20:40:48 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Trips publication readiness and Public Trip Page content; avoid booking gate/availability.
- 2026-05-29 20:49:37 IST: Orchestrator accepted Trips publication readiness and Public Trip Page content. Verified with `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trips/tests.py apps/api/organizers/tests/test_trip_profile_publication_readiness.py apps/api/organizers/tests/test_trip_profile_media_gallery.py apps/api/organizer_payments/tests/test_manual_payment_instructions.py apps/api/tripos_api/tests.py`.
- 2026-05-29 20:48:10 IST: Worker completion note: moved Trip Profile Publication Readiness into `trips.publication_readiness`, moved the Public Trip Page serializer into the Trips serializer surface while preserving the existing legacy Organizer API response, and moved public trip page publish activity logging into `trips.activity`. Legacy organizer import paths now re-export the Trips-owned helpers. Added Trips-owned regression tests for readiness blockers, successful publication readiness, public trip serialization from Trips-owned content, public/private media filtering, and compatibility re-exports. Checks: `python3 -m ruff check apps/api` passed; `.venv/bin/python apps/api/manage.py check` passed; `env DATABASE_URL=sqlite:////private/tmp/tripos-issue16.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run` passed with no changes detected; `env DATABASE_URL=sqlite:////private/tmp/tripos-issue16.sqlite3 .venv/bin/python -m pytest apps/api/trips/tests.py apps/api/organizers/tests/test_trip_profile_publication_readiness.py apps/api/organizers/tests/test_trip_profile_media_gallery.py apps/api/organizer_payments/tests/test_manual_payment_instructions.py apps/api/tripos_api/tests.py` passed with 40 tests and 3 Python 3.14 deprecation warnings from Django auth decorators. Known follow-up: Public Trip Page serialization still composes the existing legacy public booking gate/readiness helper for backward-compatible payload fields; issue 17 owns moving/gating that booking behavior.
