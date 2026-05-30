from __future__ import annotations

from django.db.models import QuerySet

from trip_operations.models import ActivityLog
from trip_operations.serializers import activity_actor_email
from trips.models import Trip


def activity_log_timeline_for_trip(trip: Trip) -> QuerySet[ActivityLog]:
    return (
        ActivityLog.objects.filter(trip=trip)
        .select_related("actor")
        .order_by("-occurred_at", "-id")
    )


def activity_log_item_payload(activity_log: ActivityLog) -> dict:
    return {
        "id": activity_log.id,
        "action": activity_log.action,
        "action_label": activity_log.get_action_display(),
        "booking_id": activity_log.booking_id,
        "traveler_slot_id": activity_log.traveler_slot_id,
        "actor_email": activity_actor_email(activity_log),
        "occurred_at": activity_log.occurred_at,
        "metadata": activity_log.metadata,
    }


def recent_activity_payload(trip: Trip, *, limit: int = 6) -> list[dict]:
    return [
        activity_log_item_payload(activity_log)
        for activity_log in activity_log_timeline_for_trip(trip)[:limit]
    ]
