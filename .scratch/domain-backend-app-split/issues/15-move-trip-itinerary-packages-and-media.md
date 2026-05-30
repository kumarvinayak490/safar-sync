Status: done

# Move Trip Itinerary, Packages, And Media

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move itinerary days, packages, trip media assets, and trip media ordering into `trips`. These concerns define the Trip Profile and Public Trip Page content, so they should not live under booking, traveler, or organizer modules.

## Acceptance criteria

- [ ] Trips owns itinerary, package, and trip media behavior.
- [ ] Trip media reuse and duplication behavior remains stable.
- [ ] Existing APIs for packages, itinerary days, and trip media remain backward compatible.
- [ ] Tests cover package ordering, itinerary validation, media reuse, and media display ordering.
- [ ] Django checks, migration dry-run, and linting pass.

## Blocked by

- `.scratch/domain-backend-app-split/issues/14-move-trip-profile-core.md`

## Comments

- 2026-05-29 20:29:00 IST: Assigned to Ralph worker for autonomous implementation. Worker owns Trips itinerary, packages, trip media, payment schedule, and confirmation requirement content; avoid publication rules and booking gate.
- 2026-05-29 20:40:48 IST: Orchestrator accepted Trips itinerary, packages, media, payment schedule, and confirmation requirements ownership. Verified with `python3 -m ruff check apps/api`, `.venv/bin/python apps/api/manage.py check`, `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run`, and `DATABASE_URL=sqlite:////private/tmp/tripos-ralph.sqlite3 .venv/bin/python -m pytest apps/api/trips/tests.py apps/api/organizers/tests/test_trip_profile_itinerary_days.py apps/api/organizers/tests/test_trip_profile_packages.py apps/api/organizers/tests/test_trip_profile_media_gallery.py apps/api/organizers/tests/test_trip_profile_payment_schedule.py apps/api/organizers/tests/test_trip_profile_confirmation_requirements.py apps/api/organizers/tests/test_trip_profile_duplicate.py apps/api/tripos_api/tests.py`.
- 2026-05-29 20:39:36 IST: Worker completion note: moved Trip Profile content behavior for Packages, Itinerary Days, Trip Media Gallery uploads/ordering, Payment Schedule sections, Confirmation Requirement sections, content activity snapshots/audit helpers, and Trip Duplicate media/package/itinerary reuse into the top-level `trips` app. Legacy `organizers.trip_profile.media` and `organizers.trip_profile.activity` now route to Trips-owned behavior, and the Organizer API surface continues to import Trips-owned serializers for backward-compatible endpoints. Added Trips-owned regression coverage for package ordering/readiness, itinerary validation, media upload/display ordering, ADR 0024 media asset reuse during Trip Duplicate, and legacy compatibility imports. Checks: `python3 -m ruff check apps/api` passed; `.venv/bin/python apps/api/manage.py check` passed; `env DATABASE_URL=sqlite:////private/tmp/tripos-issue15.sqlite3 .venv/bin/python apps/api/manage.py makemigrations --check --dry-run` passed with no changes detected; `env DATABASE_URL=sqlite:////private/tmp/tripos-issue15.sqlite3 .venv/bin/python -m pytest apps/api/trips/tests.py apps/api/organizers/tests/test_trip_profile_packages.py apps/api/organizers/tests/test_trip_profile_itinerary_days.py apps/api/organizers/tests/test_trip_profile_media_gallery.py apps/api/organizers/tests/test_trip_profile_duplicate.py apps/api/organizers/tests/test_trip_profile_payment_schedule.py apps/api/organizers/tests/test_trip_profile_confirmation_requirements.py` passed with 54 tests and 3 Python 3.14 deprecation warnings from Django auth decorators.
