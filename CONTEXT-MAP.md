# TripOS Context Map

TripOS uses multi-context domain docs. Read this file first, then load the smallest set of context files needed for the work.

## Always Read

- [Shared Context](docs/contexts/shared/CONTEXT.md): product-wide language shared across organizer, trip, payments, discovery, and staff work.
- Relevant ADRs under [docs/adr](docs/adr/): architecture and trade-off decisions.

## Organizer Contexts

- [Organizers](docs/contexts/organizers/CONTEXT.md): Organizer root, onboarding, setup checklist, and organizer-level ownership.
- [Organizer Profile](docs/contexts/organizer_profile/CONTEXT.md): public organizer profile content, publication state, readiness, and organizer public page content ownership.
- [Organizer Media](docs/contexts/organizer_media/CONTEXT.md): organizer-level public media library and reuse.
- [Organizer Policies](docs/contexts/organizer_policies/CONTEXT.md): privacy, refund, and cancellation policies.
- [Team Access](docs/contexts/team_access/CONTEXT.md): memberships, invitations, roles, and ownership invariants.
- [Organizer Payments](docs/contexts/organizer_payments/CONTEXT.md): payment setup, connected provider account, provider authorization, payout and settlement readiness, manual payment instructions.
- [Creative Setup](docs/contexts/creative_setup/CONTEXT.md): organizer-level creative generation preferences.

## Trip Contexts

- [Trips](docs/contexts/trips/CONTEXT.md): Trip Profile, public trip page content, publication, packages, itinerary, confirmation requirements, booking availability, and capacity.
- [Trip Bookings](docs/contexts/trip_bookings/CONTEXT.md): booking lifecycle, manual bookings, booking imports, booking contact, booking access, and booking state.
- [Trip Travelers](docs/contexts/trip_travelers/CONTEXT.md): traveler slots, traveler identity details, traveler documents, readiness, check-in, and traveler-level changes.
- [Trip Payments](docs/contexts/trip_payments/CONTEXT.md): booking-connected payments, attempts, provider payments, manual payments, ledgers, refunds, platform fee facts, and payment exceptions.
- [Trip Operations](docs/contexts/trip_operations/CONTEXT.md): reminders, announcements, operational exports, activity log, and operational exception review.

## Public And Staff Contexts

- [Public Discovery](docs/contexts/public_discovery/CONTEXT.md): Public Discovery Catalog, Demand Pages, discovery SEO metadata, discovery routing, and listing rules.
- [Internal Admin](docs/contexts/internal_admin/CONTEXT.md): thin TripOS staff orchestration surface for module-owned support and configuration actions.

## Legacy Full Context

- [Root CONTEXT.md](CONTEXT.md) remains the full historical context while the focused contexts stabilize. Prefer the focused context files above for new work. Use the root file only when a term has not yet been copied into a focused context.

## Conflict Rules

- Use the most specific context for domain language.
- If a focused context and root `CONTEXT.md` disagree, prefer the focused context and update the stale file.
- ADRs record architecture and trade-off decisions; contexts record domain language.
- Do not introduce synonyms for terms explicitly listed in `_Avoid_`.
