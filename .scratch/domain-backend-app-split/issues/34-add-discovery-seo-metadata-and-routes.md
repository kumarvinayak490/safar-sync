Status: done

# Add Discovery SEO Metadata And Routes

## Parent

`.scratch/domain-backend-app-split/PRD.md`

## What to build

Add Public Discovery SEO metadata and route behavior for Demand Pages. Demand Pages should be suitable for demand-led SEO pages such as route or destination demand pages, while still only distributing demand to published organizer/trip pages.

## Acceptance criteria

- [x] Public Discovery owns SEO metadata for Demand Pages.
- [x] Demand Page routes render the configured title and SEO copy through backend responses.
- [x] Metadata does not duplicate Organizer Profile or Public Trip Page source content.
- [x] Tests cover route resolution, metadata output, slug collisions, and unpublished demand pages.
- [x] Django checks, migration dry-run, and linting pass.

## Blocked by

- `.scratch/domain-backend-app-split/issues/32-add-demand-page-configuration-model.md`
- `.scratch/domain-backend-app-split/issues/33-add-demand-page-listing-rules.md`

## Comments

- 2026-05-30 00:16:18 IST: Orchestrator completed Issue 34 by extending public discovery demand-page tests and metadata assertions in `public_discovery` test coverage. Added SEO payload verification (`seo_title`, `seo_copy`) and slug collision enforcement coverage via normalized case-insensitive uniqueness in Demand Page creation. Route ownership and unpublished demand behavior remains covered by the existing Issue 31/33 tests.
