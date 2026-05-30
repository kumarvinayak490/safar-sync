# Keep Internal Admin Thin

TripOS will keep Internal Admin as a thin staff-facing module for orchestrating module-owned support and configuration actions.

Internal Admin may provide workflows for staff-managed actions such as configuring Configured Demand Pages or managing Platform Fee Statements. The underlying business records remain owned by their source domains: Configured Demand Pages belong to Public Discovery, and Platform Fee facts come from Trip Payments.

Internal Admin does not own Organizer, Trip, Public Discovery, Booking, Traveler, Payment, or Trip Operation business state. It can coordinate and expose staff tools, but module-owned actions must keep their source-domain invariants.

This prevents staff tooling from becoming a shadow source of truth. The tradeoff is that Internal Admin workflows must call into module-owned services or APIs instead of directly mutating every record they display.
