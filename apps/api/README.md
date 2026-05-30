# TripOS API

Django DRF API for TripOS.

The repo-level setup and development commands are documented in `../../README.md` and `../../docs/development/local-development.md`.

## Domain Django Apps

TripOS is a single Django project, one backend process, and one database. The backend app skeleton follows the domain map from ADR 0035:

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

All target apps are registered in `tripos_api.settings` and included in package discovery. During the current skeleton stage, historical persisted model state remains on the existing `organizers` migration chain so Django does not create accidental app-split migrations.

Current migration order:

- Existing persisted records remain represented by `organizers.0001_initial` through `organizers.0043_organizer_identity_whatsapp_number`.
- New domain apps have migrations packages but no migration files yet.
- Future model-ownership moves should add explicit, staged migrations after the current `organizers` leaf and must not rewrite historical migrations.
- Move dependencies in domain order: organizer root and organizer-level apps first, then `trips`, then `trip_bookings`, `trip_travelers`, `trip_payments`, `trip_operations`, and finally composition/orchestration apps such as `public_discovery` and `internal_admin`.
