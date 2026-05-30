Status: ready-for-agent

# PRD: Domain-Aligned Backend Django App Split

## Problem Statement

The backend currently reads as one large Organizer-centered area even though the TripOS domain has clear separate concerns: Organizer Profile, Organizer Media, Organizer Policies, Team Access, Organizer Payments, Creative Setup, Trips, Trip Bookings, Trip Travelers, Trip Payments, Trip Operations, Public Discovery, and Internal Admin.

This makes the codebase harder to navigate and reason about. A developer opening the backend sees technical or legacy buckets before they see the product language. Concepts such as Public Discovery and Internal Admin should not appear owned by Organizer. Payments currently mixes organizer-level payment setup with trip-scoped booking payments. Trips currently risk becoming a catch-all for trip profile, booking, traveler, payment, and operations behavior.

The user wants separation of concerns to be treated as a high priority. The backend should be structured as a modular monolith with real domain-aligned Django apps. This must not imply microservices: TripOS remains one Django project, one backend process, one deployment unit, and one database unless a future decision changes that.

## Solution

Split the backend into real Django apps named after the domain language already agreed in the glossary and ADRs. Create all target Django apps now so the intended structure is visible immediately and new code has a correct destination.

The split should be staged carefully as an end-to-end migration program. The final state is full domain ownership: apps, behavior, APIs, tests, permissions, selectors, orchestration code, models, and future migrations live in the owning domain app. Do not rewrite historical migrations. Preserve production data safely. Database table renames are optional and should happen only through explicit safe migrations when the value is worth the operational risk.

The target apps are:

- `organizers`
- `organizer_profile`
- `organizer_media`
- `organizer_policies`
- `team_access`
- `organizer_payments`
- `creative_setup`
- `trips`
- `trip_bookings`
- `trip_travelers`
- `trip_payments`
- `trip_operations`
- `public_discovery`
- `internal_admin`

## User Stories

1. As a backend engineer, I want the backend app names to match the TripOS domain language, so that I can find the right place for a change without reverse-engineering legacy buckets.
2. As a backend engineer, I want Organizer Profile to be separate from Organizer Settings, so that public organizer identity and trust content do not get mixed with private setup preferences.
3. As a backend engineer, I want Organizer Media to be its own app, so that organizer-level uploads, captions, ordering, visibility, and reuse are not buried inside profile code.
4. As a backend engineer, I want Organizer Policies to be its own app, so that privacy, refund, and cancellation policies can be reused by public organizer and trip surfaces without being treated as profile identity.
5. As a backend engineer, I want Team Access to be its own app, so that memberships, invitations, roles, and ownership invariants are handled as access-control concerns rather than settings preferences.
6. As a backend engineer, I want Organizer Payments to be its own app, so that provider authorization, payout readiness, settlement readiness, and manual payment instructions are not hidden under generic settings.
7. As a backend engineer, I want Creative Setup to be its own app, so that organizer-level creative generation preferences have a clear home without creating a generic Organizer Preferences drawer.
8. As a backend engineer, I want Trips to be its own app, so that trip profile, packages, itinerary, confirmation requirements, booking availability, publication readiness, and public trip page state are owned by the Trip domain.
9. As a backend engineer, I want Trip Bookings to be its own app, so that reservations, manual bookings, imports, booking state, access links, and booking contact coordination are managed together.
10. As a backend engineer, I want Trip Travelers to be its own app, so that traveler slots, traveler identity details, traveler documents, traveler check-in, and traveler-level changes are isolated from booking contact and payment concerns.
11. As a backend engineer, I want Trip Payments to be its own app, so that booking-connected payments, payment attempts, manual payment review, provider payment matching, ledgers, refunds, platform fee facts, and payment exceptions are managed together.
12. As a backend engineer, I want Trip Operations to be its own app, so that communications, reminders, announcements, operational exports, activity log, and operational exception review have a clear operational home.
13. As a backend engineer, I want Public Discovery to be its own app, so that Demand Pages, SEO metadata, discovery routing, and listing rules do not appear owned by Organizer or Trips.
14. As a backend engineer, I want Internal Admin to be its own app, so that staff tooling does not look like organizer-owned functionality.
15. As a backend engineer, I want Internal Admin to remain a thin orchestration layer, so that module-owned business state is not duplicated in staff tooling.
16. As a backend engineer, I want Public Discovery to compose published Organizer Profile and Public Trip Pages, so that discovery does not become the owner of booking, checkout, payment, or trip operations.
17. As a backend engineer, I want Public Trip Page content and publication state to remain owned by Trips, so that discovery routing cannot accidentally own booking behavior.
18. As a backend engineer, I want booking URLs and checkout behavior to remain owned by Trips, Trip Bookings, and Trip Payments, so that Public Discovery stays demand distribution only.
19. As a backend engineer, I want Organizer Settings to remain only a UI grouping, so that backend code does not drift into a broad settings module again.
20. As a backend engineer, I want `organizer_settings`-style code to be removed or reduced to compatibility shims, so that the codebase reflects the current domain model.
21. As a backend engineer, I want old imports to keep working during the transition, so that the app split can be performed safely without a flag-day rewrite.
22. As a backend engineer, I want compatibility imports to be thin re-exports only, so that old paths do not become second implementations.
23. As a backend engineer, I want existing API behavior to remain stable during the first split, so that frontend and worker behavior do not regress while code moves.
24. As a backend engineer, I want persisted models to end up owned by the correct domain apps, so that domain ownership is complete rather than cosmetic.
25. As a backend engineer, I want model and migration moves to be staged domain by domain, so that each migration can be tested and reviewed independently.
26. As a site reliability engineer, I want the app split to keep one deployment and one database, so that operational complexity does not increase while code ownership improves.
27. As a site reliability engineer, I want app wiring to be explicit, so that startup failures caused by missing app registration are caught immediately.
28. As a site reliability engineer, I want Django checks and migration dry-runs to pass after each stage, so that structural changes do not hide runtime or migration issues.
29. As a product engineer, I want new Organizer Profile work to land in the Organizer Profile app, so that public organizer content evolves in the right place.
30. As a product engineer, I want new Demand Page work to land in Public Discovery, so that SEO and demand routing are not coupled to Organizer or Trips.
31. As a product engineer, I want new payment setup work to land in Organizer Payments, so that organizer-level provider readiness stays separate from trip-level booking payments.
32. As a product engineer, I want new payment collection work to land in Trip Payments, so that booking ledger behavior stays near payment attempts and provider confirmations.
33. As a product engineer, I want new reminder and announcement work to land in Trip Operations, so that operational communications are not mixed into Trip Profile or Booking lifecycle code.
34. As a product engineer, I want new traveler readiness work to land in Trip Travelers, so that traveler documents and check-in do not get hidden inside Booking code.
35. As a product engineer, I want package, itinerary, confirmation requirement, and publication readiness work to land in Trips, so that the Trip Profile remains the source of public trip content.
36. As a TripOS maintainer, I want the docs to list the target apps and migration order, so that future agents finish the split rather than adding more code to legacy locations.
37. As a TripOS maintainer, I want tests to move with the domain they verify, so that test ownership mirrors code ownership.
38. As a TripOS maintainer, I want the entire migration to be documented as chainable stages, so that one agent can complete a stage and another agent can continue from the next stage.
39. As a TripOS maintainer, I want any remaining legacy paths to be documented, so that they are intentional compatibility shims rather than forgotten architecture debt.
40. As a future maintainer, I want ADRs to explain why real Django apps were chosen, so that the split is not mistaken for a microservice migration.

## Implementation Decisions

- Use real Django apps as the target structure, not only plain Python packages.
- Different Django apps remain part of one modular monolith: no separate servers, no network calls between domains, no separate deployment units, and no separate databases.
- Create all target Django apps now, even if some begin thin or empty.
- Register all target apps with the Django project so app ownership is visible immediately.
- Keep `organizers` as the Organizer root app and legacy integration point during the first pass, but do not treat it as owner of every organizer-adjacent workflow.
- Move behavior into domain apps before moving persisted models when that reduces risk, but the final target includes domain-owned models.
- Move models and future migrations into the owning domain apps through staged, explicit migrations.
- Do not rewrite historical migrations.
- Preserve existing data throughout the migration.
- Preserve existing database table names by default. Rename tables only when there is a specific value and the rename is handled through explicit safe migrations.
- Keep existing API behavior stable while code moves.
- Use compatibility imports for old paths during the migration.
- Compatibility imports must only re-export new domain-owned behavior.
- Do not create broad technical buckets such as `read_models`, `workflows`, generic `utils`, broad `organizer_settings`, or generic `organizer_preferences`.
- Organizer Profile owns public organizer name, logo, description, contact channel, publication state, and organizer public page content.
- Organizer Media owns organizer-level uploads, captions, ordering, visibility, and reuse.
- Organizer Policies owns Organizer Privacy Policy, Organizer Refund Policy, and Organizer Cancellation Policy.
- Team Access owns organizer memberships, invitations, roles, and ownership invariants.
- Organizer Payments owns Payment Setup, provider authorization, connected provider account readiness, payout readiness, settlement readiness, and manual payment instructions.
- Creative Setup owns organizer-level creative generation preferences only. Generated posters and trip-specific creative assets remain trip-scoped.
- Trips owns Trip Profile, Packages, Itinerary, Confirmation Requirements, Booking Availability, Trip Profile Publication Readiness, Public Trip Page content, and trip publication state.
- Trip Bookings owns reservation lifecycle, manual bookings, booking imports, booking state, booking access links, and booking contact coordination.
- Trip Travelers owns traveler slots, traveler identity details, traveler documents, traveler check-in, and traveler-level changes.
- Trip Payments owns booking-connected payments, payment attempts, manual payment review, provider payment matching, ledgers, refunds, platform fee facts, and payment exceptions.
- Trip Operations owns reminders, announcements, operational exports, activity log, and operational exception review.
- Public Discovery owns Demand Pages, Discovery SEO Metadata, Discovery Routing, and Discovery Listing Rules.
- Public Discovery composes Published Organizer Profile and published Public Trip Pages but does not own their source content, booking rules, checkout, payments, or trip operations.
- Internal Admin owns staff-facing orchestration workflows only. Module-owned records remain owned by their source domains.
- Internal Admin can provide staff workflows for Configured Demand Pages and Platform Fee Statements, but the source business facts stay in Public Discovery and Trip Payments.
- Organizer Settings remains a UI grouping only, not a backend domain.
- The migration must include a staged checklist with entry criteria, exit criteria, verification, and handoff notes for each stage.

## Testing Decisions

- Tests should verify external behavior and domain invariants, not import-path implementation details.
- A good test exercises the public interface of a domain app and proves that the app preserves the behavior expected by callers.
- Run Django system checks after app registration to catch startup, app config, signal, and settings issues.
- Run migration dry-runs after each stage to ensure migration operations are expected and controlled.
- Run linting after import moves to catch stale imports and unused compatibility paths.
- Run the existing organizer backend suite as regression coverage during the split.
- Prioritize tests around Organizer Payments and Trip Payments because payment behavior carries the highest operational risk.
- Prioritize tests around Trips, Trip Bookings, and Trip Travelers because booking capacity, traveler readiness, and public booking gates cross domain lines.
- Prioritize tests around Public Discovery when Demand Pages, discovery routing, or listing rules are introduced.
- Prioritize tests around Team Access because ownership invariants and role permissions are security-sensitive.
- Preserve existing tests for payment readiness, public booking gate, manual payment instructions, provider connection tests, trip profile publication readiness, trip profile media, packages, itinerary days, confirmation requirements, and public QR manual payment submission.
- Move tests to the domain app they verify as behavior moves.
- Add smoke tests that import every new Django app and confirm the Django project starts with all target apps registered.
- Add regression tests for old compatibility imports where they are expected to remain temporarily.
- Do not add tests that merely assert a function lives in a specific file path; tests should assert behavior and stable domain interfaces.

## Out of Scope

- Splitting TripOS into microservices.
- Creating separate servers, deployments, databases, queues, or network APIs between the domain apps.
- Rewriting historical migrations.
- Renaming database tables without an explicit safe migration and a clear reason.
- Treating a stage as complete without documenting what remains for the next stage.
- Changing public API behavior unless required to preserve functionality during the move.
- Building new marketplace checkout, split settlement, reviews, or platform-owned trip fulfillment.
- Building Demand Page UI beyond the domain app structure and migration plan.
- Building Organizer Profile, Organizer Media, Organizer Policies, or Creative Setup product features beyond the structural split unless already present.
- Introducing a generic Organizer Preferences backend module.
- Keeping Organizer Settings as a backend owner.

## Further Notes

- ADR 0035 supersedes ADR 0034 and establishes real domain Django apps as the target.
- ADR 0033 still applies: the migration must be incremental and avoid reckless flag-day database changes.
- ADR 0032 defines the domain-aligned backend module map and naming rule.
- ADR 0027, ADR 0028, ADR 0029, ADR 0030, and ADR 0031 define key ownership boundaries that this PRD must respect.
- The implementation should favor deep modules with small, stable interfaces. Moving files without creating clearer ownership is not enough.
- The goal is to document and execute the migration as chainable stages until full domain ownership is complete.
