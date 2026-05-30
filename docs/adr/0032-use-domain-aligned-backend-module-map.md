# Use a Domain-Aligned Backend Module Map

TripOS will organize the backend modular monolith around domain-owned modules rather than technical buckets such as read models, workflows, or generic settings.

Package names should follow the stabilized domain language in `CONTEXT.md`. When the product language says Organizer Profile, Organizer Media, Organizer Policies, Organizer Payments, Creative Setup, Trip Bookings, Trip Travelers, Trip Payments, Trip Operations, Public Discovery, or Internal Admin, the backend package should use that domain name in snake case. Legacy convenience names and technical shape names should not override the domain vocabulary.

The target top-level backend domains are:

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

Technical or shared modules are allowed only where unavoidable and must be named for a specific responsibility. Generic buckets such as `read_models`, `workflows`, `utils`, or broad `organizer_settings` packages should not become domain owners.

These domains are target Django apps, not merely packages inside the existing `organizers` app. The split is staged in ADR 0035, but the end state should make each domain visible as its own Django app. In this map, `organizers` keeps the Organizer aggregate/root basics rather than owning every organizer-adjacent workflow.

The map follows the glossary decisions in `CONTEXT.md`: Organizer Profile, Organizer Media, Organizer Policies, Team Access, Organizer Payments, Creative Setup, Trips, Trip Bookings, Trip Travelers, Trip Payments, Trip Operations, Public Discovery, and Internal Admin each own different business language and invariants.

This makes the codebase easier to navigate and safer to evolve as a modular monolith. The tradeoff is that cross-domain flows must be explicit instead of hidden in broad service modules.
