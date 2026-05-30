from __future__ import annotations

from organizers.models import Organizer, OrganizerMembership
from team_access.permissions import get_active_membership

LOGIN_ROUTE = "/login"
ORGANIZER_HOME_ROUTE = "/home"
ORGANIZER_ONBOARDING_ROUTE = "/onboarding/organizer"


def session_onboarding_payload(user) -> dict:
    membership = get_active_membership(user)
    if membership is None:
        return {
            "state": "no_organizer",
            "next_route": ORGANIZER_ONBOARDING_ROUTE,
            "organizer": None,
            "trip_count": 0,
        }

    return organizer_ready_payload(membership)


def anonymous_onboarding_payload() -> dict:
    return {
        "state": "unauthenticated",
        "next_route": LOGIN_ROUTE,
        "organizer": None,
        "trip_count": 0,
    }


def organizer_ready_payload(membership: OrganizerMembership) -> dict:
    organizer: Organizer = membership.organizer
    return {
        "state": "organizer_ready",
        "next_route": ORGANIZER_HOME_ROUTE,
        "organizer": {
            "id": organizer.id,
            "name": organizer.name,
            "slug": organizer.slug,
            "membership_role": membership.role,
            "membership_label": membership.get_role_display(),
        },
        "trip_count": organizer.trips.count(),
    }
