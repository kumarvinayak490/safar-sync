# Keep Trips as a Top-Level Domain Module

TripOS will keep Trips as a top-level domain module in the modular monolith rather than nesting trip behavior under the Organizer module.

An Organizer owns Trips commercially and authorizes Users to act on them. The Trip domain owns the lifecycle for each sellable scheduled offering: Trip Profile, Packages, Itinerary, Confirmation Requirements, Booking Availability, Public Trip Page, Bookings, Travelers, Payments, readiness, activity, and operations.

Organizer-level modules may link to or summarize Trips, and the product UI may show Trips inside the Organizer workspace. That UI containment does not make Trips part of Organizer Settings, Organizer Profile, Organizer Media, Organizer Policies, Organizer Payments, or Team Access.

This favors clear operational ownership as TripOS grows. The tradeoff is more explicit cross-module relationships between Organizers and Trips, but it avoids turning Organizer into a catch-all container for trip operations.
