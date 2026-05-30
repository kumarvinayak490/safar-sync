from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from trip_operations.activity import actor_for_activity, record_activity_log
from trip_operations.models import ActivityLog
from trip_travelers.models import TravelerSlot
from trip_travelers.slots import ACTIVE_BOOKING_STATES

__all__ = (
    "TravelerCheckInWorkflow",
    "mark_traveler_attendance",
)


class TravelerCheckInWorkflow:
    def mark_traveler_attendance(
        self,
        traveler_slot: TravelerSlot,
        *,
        attendance_state: str,
        actor=None,
    ) -> TravelerSlot:
        if attendance_state not in {
            TravelerSlot.AttendanceState.CHECKED_IN,
            TravelerSlot.AttendanceState.NO_SHOW,
        }:
            raise ValidationError("Unsupported Traveler attendance state.")

        with transaction.atomic():
            traveler_slot = self._lock_traveler_slot(traveler_slot)
            booking = traveler_slot.booking
            self._require_active_booking(
                booking,
                "Traveler Check-In and No-Show are available only for Reserved or Confirmed "
                "Bookings.",
            )
            if not traveler_slot.is_traveler:
                raise ValidationError("Traveler attendance requires Traveler Identity Details.")

            prior_state = traveler_slot.attendance_state
            traveler_slot.attendance_state = attendance_state
            traveler_slot.attendance_marked_at = timezone.now()
            traveler_slot.attendance_marked_by = actor_for_activity(actor)
            traveler_slot.save(
                update_fields=[
                    "attendance_state",
                    "attendance_marked_at",
                    "attendance_marked_by",
                    "updated_at",
                ]
            )
            self._record_attendance_activity(
                action=(
                    ActivityLog.Action.TRAVELER_CHECKED_IN
                    if attendance_state == TravelerSlot.AttendanceState.CHECKED_IN
                    else ActivityLog.Action.TRAVELER_MARKED_NO_SHOW
                ),
                traveler_slot=traveler_slot,
                actor=actor,
                metadata={
                    "attendance_state": attendance_state,
                    "prior_attendance_state": prior_state,
                    "booking_state": booking.booking_state,
                },
            )
            return traveler_slot

    def _lock_traveler_slot(self, traveler_slot: TravelerSlot) -> TravelerSlot:
        return (
            TravelerSlot.objects.select_for_update()
            .select_related("booking", "booking__trip", "booking__trip__organizer", "package")
            .get(pk=traveler_slot.pk)
        )

    def _require_active_booking(self, booking, message: str) -> None:
        if booking.booking_state not in ACTIVE_BOOKING_STATES:
            raise ValidationError(message)

    def _record_attendance_activity(
        self,
        *,
        action: str,
        traveler_slot: TravelerSlot,
        actor=None,
        metadata: dict | None = None,
    ) -> ActivityLog:
        booking = traveler_slot.booking
        return record_activity_log(
            action=action,
            booking=booking,
            traveler_slot=traveler_slot,
            actor=actor,
            metadata=metadata or {},
        )


def mark_traveler_attendance(
    traveler_slot: TravelerSlot,
    *,
    attendance_state: str,
    actor=None,
) -> TravelerSlot:
    return TravelerCheckInWorkflow().mark_traveler_attendance(
        traveler_slot,
        attendance_state=attendance_state,
        actor=actor,
    )
