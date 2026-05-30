from __future__ import annotations

from collections.abc import Callable

from organizers.models import (
    Booking,
    TravelerSlot,
    TripPackage,
)
from trip_bookings.lifecycle import (
    BookingLifecycleWorkflow,
    confirmation_requirements_for_booking,
    required_amount_to_reserve_inr,
)
from trip_bookings.lifecycle import (
    cancel_booking as lifecycle_cancel_booking,
)
from trip_bookings.lifecycle import (
    confirm_booking as lifecycle_confirm_booking,
)
from trip_bookings.lifecycle import (
    unconfirm_booking as lifecycle_unconfirm_booking,
)
from trip_operations.models import Notification
from trip_travelers.check_in import (
    mark_traveler_attendance as travelers_mark_traveler_attendance,
)
from trip_travelers.slots import (
    ACTIVE_BOOKING_STATES,
    TravelerSlotWorkflow,
    active_reserved_traveler_count,
    available_seats,
)
from trip_travelers.slots import (
    add_traveler_to_booking as slots_add_traveler_to_booking,
)
from trip_travelers.slots import (
    cancel_traveler as slots_cancel_traveler,
)
from trip_travelers.slots import (
    change_traveler_package as slots_change_traveler_package,
)
from trip_travelers.slots import (
    replace_traveler as slots_replace_traveler,
)
from trip_travelers.slots import (
    reserve_pending_traveler_additions_if_ready as slots_reserve_pending_traveler_additions,
)

__all__ = (
    "ACTIVE_BOOKING_STATES",
    "BookingOperationsWorkflow",
    "active_reserved_traveler_count",
    "available_seats",
    "required_amount_to_reserve_inr",
    "confirmation_requirements_for_booking",
    "confirm_booking",
    "unconfirm_booking",
    "cancel_booking",
    "cancel_traveler",
    "replace_traveler",
    "add_traveler_to_booking",
    "reserve_pending_traveler_additions_if_ready",
    "change_traveler_package",
    "mark_traveler_attendance",
)


class BookingOperationsWorkflow(BookingLifecycleWorkflow):
    """Legacy combined workflow while callers move to domain modules."""

    def cancel_traveler(
        self,
        traveler_slot: TravelerSlot,
        *,
        cancellation_reason: str,
        actor=None,
    ) -> TravelerSlot:
        return TravelerSlotWorkflow().cancel_traveler(
            traveler_slot,
            cancellation_reason=cancellation_reason,
            actor=actor,
        )

    def replace_traveler(
        self,
        traveler_slot: TravelerSlot,
        *,
        traveler_full_name: str,
        traveler_phone: str,
        traveler_email: str = "",
        actor=None,
    ) -> TravelerSlot:
        return TravelerSlotWorkflow().replace_traveler(
            traveler_slot,
            traveler_full_name=traveler_full_name,
            traveler_phone=traveler_phone,
            traveler_email=traveler_email,
            actor=actor,
        )

    def add_traveler_to_booking(
        self,
        booking: Booking,
        *,
        package: TripPackage,
        traveler_full_name: str = "",
        traveler_phone: str = "",
        traveler_email: str = "",
        actor=None,
    ) -> TravelerSlot:
        return slots_add_traveler_to_booking(
            booking,
            package=package,
            traveler_full_name=traveler_full_name,
            traveler_phone=traveler_phone,
            traveler_email=traveler_email,
            actor=actor,
        )

    def reserve_pending_traveler_additions_if_ready(
        self,
        booking: Booking,
        *,
        actor=None,
    ) -> list[TravelerSlot]:
        return slots_reserve_pending_traveler_additions(
            booking,
            actor=actor,
        )

    def change_traveler_package(
        self,
        traveler_slot: TravelerSlot,
        *,
        package: TripPackage,
        actor=None,
    ) -> TravelerSlot:
        return slots_change_traveler_package(
            traveler_slot,
            package=package,
            actor=actor,
        )

    def mark_traveler_attendance(
        self,
        traveler_slot: TravelerSlot,
        *,
        attendance_state: str,
        actor=None,
    ) -> TravelerSlot:
        return travelers_mark_traveler_attendance(
            traveler_slot,
            attendance_state=attendance_state,
            actor=actor,
        )


def confirm_booking(
    booking: Booking,
    *,
    send_confirmation_notice: Callable[[Booking], list[Notification]] | None = None,
) -> Booking:
    return lifecycle_confirm_booking(
        booking,
        send_confirmation_notice=send_confirmation_notice,
    )


def unconfirm_booking(booking: Booking) -> Booking:
    return lifecycle_unconfirm_booking(booking)


def cancel_booking(
    booking: Booking,
    *,
    cancellation_reason: str,
    actor=None,
) -> Booking:
    return lifecycle_cancel_booking(
        booking,
        cancellation_reason=cancellation_reason,
        actor=actor,
    )


def cancel_traveler(
    traveler_slot: TravelerSlot,
    *,
    cancellation_reason: str,
    actor=None,
) -> TravelerSlot:
    return slots_cancel_traveler(
        traveler_slot,
        cancellation_reason=cancellation_reason,
        actor=actor,
    )


def replace_traveler(
    traveler_slot: TravelerSlot,
    *,
    traveler_full_name: str,
    traveler_phone: str,
    traveler_email: str = "",
    actor=None,
) -> TravelerSlot:
    return slots_replace_traveler(
        traveler_slot,
        traveler_full_name=traveler_full_name,
        traveler_phone=traveler_phone,
        traveler_email=traveler_email,
        actor=actor,
    )


def add_traveler_to_booking(
    booking: Booking,
    *,
    package: TripPackage,
    traveler_full_name: str = "",
    traveler_phone: str = "",
    traveler_email: str = "",
    actor=None,
) -> TravelerSlot:
    return slots_add_traveler_to_booking(
        booking,
        package=package,
        traveler_full_name=traveler_full_name,
        traveler_phone=traveler_phone,
        traveler_email=traveler_email,
        actor=actor,
    )


def reserve_pending_traveler_additions_if_ready(
    booking: Booking,
    *,
    actor=None,
) -> list[TravelerSlot]:
    return slots_reserve_pending_traveler_additions(
        booking,
        actor=actor,
    )


def change_traveler_package(
    traveler_slot: TravelerSlot,
    *,
    package: TripPackage,
    actor=None,
) -> TravelerSlot:
    return slots_change_traveler_package(
        traveler_slot,
        package=package,
        actor=actor,
    )


def mark_traveler_attendance(
    traveler_slot: TravelerSlot,
    *,
    attendance_state: str,
    actor=None,
) -> TravelerSlot:
    return travelers_mark_traveler_attendance(
        traveler_slot,
        attendance_state=attendance_state,
        actor=actor,
    )
