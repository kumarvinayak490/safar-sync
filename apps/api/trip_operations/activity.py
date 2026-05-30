from __future__ import annotations

from django.core.exceptions import ValidationError

from trip_bookings.models import Booking
from trip_operations.models import ActivityLog
from trip_travelers.models import TravelerDocument, TravelerSlot
from trips.models import Trip


def record_activity_log(
    *,
    action: str,
    booking: Booking | None = None,
    trip: Trip | None = None,
    traveler_slot: TravelerSlot | None = None,
    traveler_document: TravelerDocument | None = None,
    actor=None,
    metadata: dict | None = None,
) -> ActivityLog:
    booking, trip, traveler_slot = _resolve_activity_scope(
        booking=booking,
        trip=trip,
        traveler_slot=traveler_slot,
        traveler_document=traveler_document,
    )
    return ActivityLog.objects.create(
        organizer=trip.organizer,
        trip=trip,
        booking=booking,
        traveler_slot=traveler_slot,
        traveler_document=traveler_document,
        actor=actor_for_activity(actor),
        action=action,
        metadata=metadata or {},
    )


def actor_for_activity(actor):
    return actor if getattr(actor, "is_authenticated", False) else None


def _resolve_activity_scope(
    *,
    booking: Booking | None,
    trip: Trip | None,
    traveler_slot: TravelerSlot | None,
    traveler_document: TravelerDocument | None,
) -> tuple[Booking | None, Trip, TravelerSlot | None]:
    if traveler_document is not None and traveler_slot is None:
        traveler_slot = traveler_document.traveler_slot
    if traveler_slot is not None and booking is None:
        booking = traveler_slot.booking
    if booking is None and trip is None:
        raise ValidationError("Activity Log requires a Booking or Trip.")

    resolved_trip = booking.trip if booking is not None else trip
    if resolved_trip is None:
        raise ValidationError("Activity Log requires a Booking or Trip.")

    if trip is not None and resolved_trip.pk != trip.pk:
        raise ValidationError("Activity Log Booking must belong to the Trip.")
    if traveler_slot is not None and booking is not None and traveler_slot.booking_id != booking.id:
        raise ValidationError("Activity Log Traveler must belong to the Booking.")
    if (
        traveler_document is not None
        and traveler_slot is not None
        and traveler_document.traveler_slot_id != traveler_slot.id
    ):
        raise ValidationError("Activity Log Traveler Document must belong to the Traveler.")

    return booking, resolved_trip, traveler_slot
