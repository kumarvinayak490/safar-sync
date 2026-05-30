from __future__ import annotations

from trips.models import Trip

LOCKED_TRIP_PROFILE_STATES = {
    Trip.PublicationState.PUBLISHED,
    Trip.PublicationState.ARCHIVED,
}


def is_trip_profile_locked(trip: Trip) -> bool:
    return trip.publication_state in LOCKED_TRIP_PROFILE_STATES


def published_trip_profile_lock_message(subject: str) -> str:
    return f"Published Trip Profile Lock prevents {subject} edits."
