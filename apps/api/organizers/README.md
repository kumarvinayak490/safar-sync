# Organizer Root Boundary

The Organizer app remains the Organizer root app and the historical migration
anchor while the backend moves to real domain Django apps. Treat this package
as the Organizer aggregate root plus Django/DRF integration, not as the owner of
every organizer-adjacent workflow.

## Root-Owned Surface

Keep only Organizer root and framework integration modules at the app root:

- `models.py` owns the `Organizer` root model and compatibility imports for
  records that have not received explicit app-move migrations yet. Do not add
  new organizer-adjacent models here unless they are Organizer aggregate basics.
- `serializers.py`, `views.py`, and `urls.py` own the current DRF integration
  surface. They may compose target domain apps, but they should not become the
  domain owner for those workflows.
- `admin.py`, `permissions.py`, and `signals.py` own Django framework integration.
- `services.py` is the remaining legacy service facade. New behavior should move
  into the domain app that owns the concept, then be re-exported only when old
  call sites need it.

## Compatibility-Only Root Modules

These flat root modules are compatibility import paths from older
organizer-owned names. Keep them as thin re-exports only:

- `booking_intake.py`
- `booking_operations_workflow.py`
- `financial_ledger.py`
- `online_payment_readiness.py` -> `organizer_payments.online_payment_readiness`
- `operations_dashboard.py`
- `organizer_identity.py` -> `organizer_profile.identity`
- `organizer_invitations.py`
- `payment_setup_guidance.py`
- `payment_setup_readiness.py` -> `organizer_payments.payment_setup_readiness`
- `platform_fees.py`
- `provider_adapters.py`
- `provider_authorization.py` -> `organizer_payments.provider_authorization`
- `provider_connection_tests.py` -> `organizer_payments.provider_connection_tests`
- `provider_credentials.py` -> `organizer_payments.provider_credentials`
- `provider_payment_lifecycle.py`
- `provider_webhooks.py`
- `public_booking_gate.py`
- `seat_holds.py`
- `session_onboarding.py`
- `traveler_readiness.py`
- `trip_overview.py`
- `trip_profile_activity.py`
- `trip_profile_lock.py`
- `trip_profile_publication_readiness.py`
- `rich_text.py` is a compatibility import path for historical migrations. New code should
  use `trip_profile/rich_text.py`.

## Transitional In-App Packages

The legacy in-app packages below still contain behavior that will move in later
domain slices. They are transitional homes, not Organizer root ownership:

- `bookings/` -> `trip_bookings`
- `operations/` -> `trip_operations`
- `organizer_settings/` -> compatibility-only for moved Organizer Profile
  identity behavior, and later `creative_setup` or another specific
  organizer-level domain app
- `onboarding/` -> Organizer root onboarding integration
- `payments/` -> `organizer_payments` or `trip_payments`, depending on whether
  the behavior is organizer-level setup or booking-connected payment collection.
  Online Payment Readiness, Payment Setup readiness, and Connected Provider
  Account readiness, Provider Authorization, Sensitive Provider Credential
  storage, and Provider Connection Tests are compatibility imports for
  `organizer_payments`.
- `team_access/` -> `team_access`
- `travelers/` -> `trip_travelers`
- `trip_profile/` -> `trips`
- `tests/` -> the domain app whose behavior the test verifies

Avoid adding new `read_models` or `workflows` packages. Those names describe code shape,
not the TripOS module that owns the behavior.
