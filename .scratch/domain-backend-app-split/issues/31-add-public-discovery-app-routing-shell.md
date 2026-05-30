Status: done

# Add Public Discovery App Routing Shell

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Add the Public Discovery routing shell for marketplace and discovery URLs. Public Discovery should own discovery routing and listing entry points, while composing published Organizer Profile and Public Trip Page content from their owning domains.

## Acceptance criteria

- [x] Public Discovery has route ownership for discovery entry points.
- [x] Public organizer and public trip content is composed from owning domains.
- [x] Booking URLs and checkout behavior remain outside Public Discovery.
- [x] Existing public routes continue to work where they already exist.
- [x] Route smoke tests cover discovery entry points and non-ownership of checkout.

## Blocked by

- `.scratch/domain-backend-app-split/issues/01-stabilize-domain-app-skeleton.md`
- `.scratch/domain-backend-app-split/issues/16-move-trip-publication-readiness-and-public-trip-page.md`

## Comments

- 2026-05-29 23:16:56 IST: Assigned to Ralph worker Lovelace (`019e74d8-5bb4-7080-9e0b-2aac8664e2a7`) for autonomous implementation. Worker owns the Public Discovery routing shell and discovery entry-point tests; booking, checkout, payment, and trip operations behavior must remain in owning domains.
- 2026-05-30 00:11:11 IST: Orchestrator accepted Issue 31. Public Discovery now owns discovery routing shell under `/api/public/` and composes published Organizer Profile/Media/Policies, plus Trips-owned Public Trip Page payloads, without taking booking/checkout/payment/operations ownership. Acceptance checks (per worker + orchestrator review) include Django check, migration dry-run, and discovery/trip route smoke slices. Known follow-up: full public discovery demand/page behavior continues in Issues 32-34.
