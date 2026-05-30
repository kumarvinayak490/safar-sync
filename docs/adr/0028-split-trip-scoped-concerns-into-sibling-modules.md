# Split Trip-Scoped Concerns into Sibling Modules

TripOS will split trip-scoped backend concerns into sibling modules rather than placing every trip-related workflow inside the Trips module.

The Trips module owns the core sellable offering: Trip Profile, Packages, Itinerary, Confirmation Requirements, Booking Availability, Trip Profile Publication Readiness, Public Trip Page, and trip publication state.

Trip Bookings, Trip Travelers, Trip Payments, and Trip Operations remain separate trip-scoped domains. They all belong to a Trip, but each has its own rules, invariants, tests, and APIs:

- Trip Bookings owns reservation lifecycle, manual bookings, booking imports, booking state, access links, and booking contact coordination.
- Trip Travelers owns traveler slots, traveler identity details, traveler documents, traveler check-in, and traveler-level changes.
- Trip Payments owns booking-connected payments, payment attempts, manual payment review, provider payment matching, ledgers, refunds, and payment-origin exception facts.
- Trip Operations owns communications, reminders, announcements, operational exports, activity log, and the organizer review workflow for operational exceptions.

Trip Operations may show combined trip-running views over Trips, Trip Bookings, Trip Travelers, and Trip Payments. It does not own Booking State, Traveler records, Payment State, Financial Ledger, or Trip Profile content.

This keeps the modular monolith close to the business language while avoiding a single overgrown Trips package. The tradeoff is more explicit coordination across trip-scoped modules, especially where booking, traveler, and payment state must move together.
