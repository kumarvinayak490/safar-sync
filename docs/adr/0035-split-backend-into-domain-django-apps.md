# Split Backend into Domain Django Apps

TripOS will split the backend modular monolith into real domain-aligned Django apps.

Different Django apps do not mean separate servers, separate deployments, network calls between domains, or separate databases. TripOS remains one Django project, one backend process, one deployment unit, and one database unless a future ADR deliberately changes that.

The target Django apps follow the domain module map:

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

The split will be staged. The final state is full domain ownership: apps, behavior, APIs, tests, permissions, selectors, orchestration code, models, and future migrations live in the owning domain app.

Historical migrations should not be rewritten. Existing data must be preserved. Database table names should be preserved by default and renamed only when there is a specific value, with explicit safe migrations.

Compatibility imports may remain during the transition. They should only re-export module-owned behavior and must not become a second implementation.

This supersedes ADR 0034 because separation of concerns is more important than avoiding Django app churn. The tradeoff is more migration and settings work now, but the resulting structure makes domain ownership visible in the codebase instead of hiding it inside one large Django app.
