from __future__ import annotations

from collections.abc import Callable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from trip_bookings.models import Booking
from trip_operations.activity import record_activity_log
from trip_operations.models import ActivityLog, Notification
from trip_travelers.models import TravelerSlot
from trip_travelers.readiness import (
    BookingConfirmationRequirements,
)
from trip_travelers.readiness import (
    confirmation_requirements_for_booking as readiness_confirmation_requirements_for_booking,
)
from trip_travelers.slots import (
    ACTIVE_BOOKING_STATES,
)
from trip_travelers.slots import (
    active_reserved_traveler_count as traveler_active_reserved_traveler_count,
)
from trip_travelers.slots import (
    available_seats as traveler_available_seats,
)
from trips.models import Trip


def active_reserved_traveler_count(trip: Trip) -> int:
    return traveler_active_reserved_traveler_count(trip)


def available_seats(trip: Trip) -> int:
    return traveler_available_seats(trip)


def required_amount_to_reserve_inr(booking: Booking) -> int:
    schedule = getattr(booking.trip, "payment_schedule", None)
    if schedule and schedule.balance_due_date and timezone.localdate() > schedule.balance_due_date:
        return booking.booking_total_inr
    return booking.booking_reservation_amount_inr


class BookingLifecycleWorkflow:
    def __init__(
        self,
        *,
        send_confirmation_notice: Callable[[Booking], list[Notification]] | None = None,
    ):
        self.send_confirmation_notice = send_confirmation_notice

    def confirmation_requirements_for_booking(
        self,
        booking: Booking,
    ) -> BookingConfirmationRequirements:
        return readiness_confirmation_requirements_for_booking(booking)

    def confirm_booking(self, booking: Booking) -> Booking:
        with transaction.atomic():
            booking = self._lock_booking_for_requirements(booking)
            self._require_booking_state(
                booking,
                {Booking.BookingState.RESERVED},
                "Only Reserved Bookings can be confirmed.",
            )

            requirements = self.confirmation_requirements_for_booking(booking)
            if not requirements.ready:
                raise ValidationError("Confirmation is blocked by unmet Confirmation Requirements.")

            booking.booking_state = Booking.BookingState.CONFIRMED
            booking.save(update_fields=["booking_state", "updated_at"])
            if self.send_confirmation_notice is not None:
                self.send_confirmation_notice(booking)
            return booking

    def unconfirm_booking(self, booking: Booking) -> Booking:
        with transaction.atomic():
            booking = self._lock_booking(booking)
            self._require_booking_state(
                booking,
                {Booking.BookingState.CONFIRMED},
                "Only Confirmed Bookings can be unconfirmed.",
            )

            booking.booking_state = Booking.BookingState.RESERVED
            booking.save(update_fields=["booking_state", "updated_at"])
            return booking

    def cancel_booking(
        self,
        booking: Booking,
        *,
        cancellation_reason: str,
        actor=None,
    ) -> Booking:
        cancellation_reason = self._require_reason(
            cancellation_reason,
            "Booking Cancellation requires Cancellation Reason.",
        )

        with transaction.atomic():
            booking = self._lock_booking(booking, prefetch_travelers=True)
            self._require_active_booking(
                booking,
                "Only Reserved or Confirmed Bookings can be cancelled.",
            )

            booking.booking_state = Booking.BookingState.CANCELLED
            booking.save(update_fields=["booking_state", "updated_at"])
            self._record_transition_activity(
                action=ActivityLog.Action.BOOKING_CANCELLED,
                booking=booking,
                actor=actor,
                metadata={"cancellation_reason": cancellation_reason},
            )
            return booking

    def _lock_booking(
        self,
        booking: Booking,
        *,
        prefetch_travelers: bool = False,
        prefetch_ledger: bool = False,
    ) -> Booking:
        queryset = Booking.objects.select_for_update().select_related(
            "trip",
            "trip__organizer",
            "trip__payment_schedule",
        )
        prefetches = []
        if prefetch_travelers:
            prefetches.append("traveler_slots__package")
        if prefetch_ledger:
            prefetches.append("ledger_entries")
        if prefetches:
            queryset = queryset.prefetch_related(*prefetches)
        return queryset.get(pk=booking.pk)

    def _lock_booking_for_requirements(self, booking: Booking) -> Booking:
        return (
            Booking.objects.select_for_update()
            .select_related("trip", "trip__payment_schedule")
            .prefetch_related(
                "traveler_slots__package",
                "traveler_slots__documents",
                "ledger_entries",
            )
            .get(pk=booking.pk)
        )

    def _require_booking_state(
        self,
        booking: Booking,
        allowed_states: set[str],
        message: str,
    ) -> None:
        if booking.booking_state not in allowed_states:
            raise ValidationError(message)

    def _require_active_booking(self, booking: Booking, message: str) -> None:
        self._require_booking_state(booking, ACTIVE_BOOKING_STATES, message)

    def _require_reason(self, reason: str, message: str) -> str:
        if not reason.strip():
            raise ValidationError(message)
        return reason

    def _record_transition_activity(
        self,
        *,
        action: str,
        booking: Booking,
        traveler_slot: TravelerSlot | None = None,
        actor=None,
        metadata: dict | None = None,
    ) -> ActivityLog:
        return record_activity_log(
            action=action,
            booking=booking,
            traveler_slot=traveler_slot,
            actor=actor,
            metadata=metadata or {},
        )


def confirmation_requirements_for_booking(booking: Booking) -> BookingConfirmationRequirements:
    return BookingLifecycleWorkflow().confirmation_requirements_for_booking(booking)


def confirm_booking(
    booking: Booking,
    *,
    send_confirmation_notice: Callable[[Booking], list[Notification]] | None = None,
) -> Booking:
    return BookingLifecycleWorkflow(
        send_confirmation_notice=send_confirmation_notice,
    ).confirm_booking(booking)


def unconfirm_booking(booking: Booking) -> Booking:
    return BookingLifecycleWorkflow().unconfirm_booking(booking)


def cancel_booking(
    booking: Booking,
    *,
    cancellation_reason: str,
    actor=None,
) -> Booking:
    return BookingLifecycleWorkflow().cancel_booking(
        booking,
        cancellation_reason=cancellation_reason,
        actor=actor,
    )
