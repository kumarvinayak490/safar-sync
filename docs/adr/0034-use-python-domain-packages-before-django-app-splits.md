# Use Python Domain Packages Before Django App Splits

Status: Superseded by [ADR 0035](0035-split-backend-into-domain-django-apps.md).

TripOS will introduce the target backend domains as plain Python packages before splitting them into separate Django apps.

For the current refactor, the existing Django app boundary remains stable. Domain ownership should move through package structure, imports, services, selectors, policies, and tests while models, migrations, app labels, content types, admin registration, and settings remain stable.

The existing `organizers` package remains the Django integration app. It owns Organizer aggregate/root basics plus framework integration such as `models.py`, `views.py`, `urls.py`, `admin.py`, and migrations. Domain packages inside it carry business behavior for profile, media, policies, team access, payments, creative setup, trips, bookings, travelers, trip payments, trip operations, public discovery, and internal admin.

Splitting a domain into its own Django app may be considered later when the package boundary has proven stable and the operational benefit outweighs the migration cost.

This avoids framework churn during the architecture cleanup. The tradeoff is that one Django app may temporarily contain multiple domain packages, but those packages can still express clear modular-monolith boundaries.
