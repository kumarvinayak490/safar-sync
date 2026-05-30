Status: done

# Move Domain Tests To Owning Apps

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Move tests to the domain app whose behavior they verify. The test suite should mirror domain ownership and continue to assert behavior through stable APIs and domain interfaces, not specific implementation paths.

## Acceptance criteria

- [x] Tests for Organizer Profile, Media, Policies, Team Access, Organizer Payments, Creative Setup, Trips, Trip Bookings, Trip Travelers, Trip Payments, Trip Operations, Public Discovery, and Internal Admin live with the owning apps.
- [x] Tests assert behavior and invariants rather than file locations.
- [x] Compatibility import smoke tests remain only where temporary compatibility is expected.
- [x] The existing backend regression suite passes or any pre-existing failures are clearly documented.
- [x] Test ownership gaps are documented for follow-up only if they cannot be resolved in this slice.

## Result

- Trip-related profile/confirmation/packages/media/itinerary/payment-schedule/publication-readiness/activity-log tests were moved from `organizers/tests/` to `trips/tests/`.
- `test_public_qr_manual_payment_submission.py` was moved from `organizers/tests/` to `trip_bookings/tests/`.
- Cross-domain imports were aligned where practical:
  - `trips.publication_readiness`, `trips.rich_text`, `trips.duplication`
  - `trip_bookings.lifecycle`
  - `trip_bookings.confirmation` helpers
  - `trip_travelers.readiness`
  - `organizer_payments.setup_records`
- Validation status: local targeted test execution could not complete due to unavailable PostgreSQL (`connection to server at localhost:5432 failed`), so behavioral verification is pending in a DB-ready environment.

## Blocked by

- Domain move issues `.scratch/domain-backend-app-split/issues/03-move-organizer-root-basics.md` through `.scratch/domain-backend-app-split/issues/37-add-internal-admin-platform-fee-review-workflow.md`
