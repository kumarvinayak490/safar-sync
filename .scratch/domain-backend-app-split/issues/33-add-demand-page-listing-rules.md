Status: done

# Add Demand Page Listing Rules

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Add Demand Page listing rules in Public Discovery. A Demand Page can use manually selected or rule-selected relevant organizers and trips, but it must distribute demand only to published organizer and trip pages.

## Acceptance criteria

- [x] Public Discovery owns Demand Page listing rule behavior.
- [x] Listing rules only surface published Organizer Profiles and published Public Trip Pages.
- [x] Demand Pages do not own booking, checkout, payment, or trip operations.
- [x] Tests cover manual selection, rule selection, unpublished exclusion, and empty results.
- [x] Existing public trip and organizer URLs remain domain-owned.

## Blocked by

- `.scratch/domain-backend-app-split/issues/16-move-trip-publication-readiness-and-public-trip-page.md`
- `.scratch/domain-backend-app-split/issues/31-add-public-discovery-app-routing-shell.md`
- `.scratch/domain-backend-app-split/issues/32-add-demand-page-configuration-model.md`

## Comments

- 2026-05-30 00:15:07 IST: Assigned to Ralph worker Babbage (`019e750f-b2cf-72de-a0ce-88f7f6d1f7e0`) for Issue 33 listing rules ownership in `public_discovery`. Scope: manual/rule selection behavior and published-content filtering.
- 2026-05-30 00:18:42 IST: Orchestrator implemented Issue 33 manually as fallback after worker capacity limits. Added listing rule selectors in `public_discovery.selectors` using AND-semantics pattern matching over published organizers/trips while preserving manual selection composition. Added tests for rule-based selection, unpublished exclusion from rule results, and empty matched sets. Existing non-ownership checks remain in place through previous Issue 31 test coverage.
