# Keep Organizer Settings as a UI Grouping

TripOS will keep Organizer Settings as a user-interface grouping, not as a broad backend domain module.

Organizer Settings may link to module-owned setup areas such as Creative Setup, Team Access, Organizer Payments, Organizer Profile, Organizer Media, and Organizer Policies. Those modules own their own records, rules, permissions, and invariants.

TripOS will not introduce a generic Organizer Preferences backend module in the first version. Creative Setup is the only concrete organizer-level preference domain for now. A generic preferences module can be introduced later only when multiple low-risk preferences share rules and lifecycle.

This prevents a backend `organizer_settings` area from becoming a catch-all for unrelated organizer concerns. The tradeoff is that the UI may still present a familiar Settings section while the backend routes actions to narrower domain modules.
