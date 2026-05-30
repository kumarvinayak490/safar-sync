# Use Separate Shell Modes for Organizer and Trip Workspaces

TripOS will use a hard mode switch between Organizer-level routes and private Trip workspace routes. Organizer routes show the Organizer shell with Home, Organizer Identity, Team Access, Payment Setup, and Trips. When a Trip is opened, the Organizer sidebar is hidden completely and the Trip workspace shell becomes the full product surface with Overview, Launch, Bookings, Payments, Travelers, Communications, and Exports.

Private Trip workspace URLs use `/operations/trips/{tripId}/{section}`. Opening a Trip from Trips or completing Trip creation lands on Trip Overview. The Trip workspace provides Back to Trips and Home as distinct exits, so users can return either to the Organizer-level Trip list or to Organizer Home.

Root-level Trip workspace routes such as `/overview`, `/launch`, `/bookings`, `/payments`, `/travelers`, `/communications`, and `/exports` are not product routes. They must not render selected-Trip pages or preserve query-string selected Trip state. Before real users depend on them, remove those root routes rather than maintaining compatibility redirects.

Selected Trip state exists only inside canonical Trip workspace routes. Organizer-level routes may show Trip lists and links into Trip workspaces, but they must not carry, infer, or fall back to a selected Trip.

The Trip workspace switcher preserves the active section when switching between Trips, so `/operations/trips/7/payments` switches to `/operations/trips/9/payments`. This keeps the user's task mode stable across Trips; if a future section becomes conditional and unsupported for the target Trip, the fallback is Trip Overview for that target Trip.

The Organizer-layer Trips route is the recovery path for choosing a Trip outside direct deep links. Zero-Trip states stay on `/trips` with Owner create actions or Operator waiting states; successful Trip creation opens `/operations/trips/{tripId}/overview`; Home exits to `/home`; Back to Trips exits to `/trips`; and TripOS does not remember a last selected Trip in local storage, session state, or query params.

Canonical Trip workspace routes are strict. `/operations/trips/{tripId}` redirects to `/operations/trips/{tripId}/overview`; invalid Trip ids, missing or inaccessible Trips, and invalid sections return 404 rather than falling back to another Trip or to Overview.

This favors clearer execution context over the convenience of always showing Organizer navigation. The decision prevents selected-Trip state from feeling global, avoids nested sidebars, and keeps Organizer setup separate from Trip operations.
