Status: done

# Add Demand Page Configuration Model

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Add configured Demand Page ownership to `public_discovery`: slug, title, SEO copy, demand pattern, publication state if needed, and selected or rule-selected relevant organizers/trips. This is staff/admin configured in v1.

## Acceptance criteria

- [x] Public Discovery owns Demand Page configuration records.
- [x] Demand Page configuration supports slug, title, SEO copy, and demand pattern.
- [x] Demand Pages can reference relevant published organizers and trips without owning their content.
- [x] Configuration validation prevents invalid slugs and unusable demand pages.
- [x] Tests cover creation, validation, and published content composition.

## Blocked by

- `.scratch/domain-backend-app-split/issues/31-add-public-discovery-app-routing-shell.md`

## Comments

- 2026-05-30 00:11:36 IST: Assigned to Ralph worker Ada (`019e74da-1234-4abf-9d67-f2a6ef123456`) for autonomous implementation of Demand Page configuration model ownership in Public Discovery. Worker should keep behavior in `public_discovery` and leave listing/SEO to follow-up issues.
- 2026-05-30 18:10:05 IST: Orchestrator accepted Issue 32. Added `DemandPage` in `apps/api/public_discovery/models.py`, demand-page selectors/visibility composition in `public_discovery/selectors.py`, shell payload wiring in `public_discovery/serializers.py` and `views.py`, and dedicated tests for validation, discoverability, and composition. Added migration `0001_demand_page.py`. Scope remains on model/configuration ownership; listing rules and SEO behavior remain in Issues 33 and 34.
