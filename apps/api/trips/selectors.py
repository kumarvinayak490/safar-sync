from __future__ import annotations

from django.shortcuts import get_object_or_404

from trips.models import Trip

TRIP_PROFILE_CORE_SELECT_RELATED = ("organizer", "payment_schedule")
TRIP_PROFILE_CORE_PREFETCH_RELATED = (
    "packages",
    "itinerary_days",
    "media_items__asset",
)


def trip_profile_core_queryset():
    return Trip.objects.select_related(*TRIP_PROFILE_CORE_SELECT_RELATED).prefetch_related(
        *TRIP_PROFILE_CORE_PREFETCH_RELATED
    )


def get_trip_profile_for_organizer_id(*, organizer_id: int, trip_id: int) -> Trip:
    return get_object_or_404(
        trip_profile_core_queryset(),
        pk=trip_id,
        organizer_id=organizer_id,
    )
