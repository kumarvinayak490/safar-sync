from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.utils import timezone

from trip_bookings.models import Booking
from trip_travelers.models import TravelerSlot
from trip_travelers.readiness import BookingConfirmationRequirements


@dataclass(frozen=True)
class TravelerNotificationTarget:
    name: str
    phone: str
    email: str
    traveler_slot: TravelerSlot


def active_traveler_notification_targets(booking: Booking) -> list[TravelerNotificationTarget]:
    return [
        _traveler_target(traveler_slot)
        for traveler_slot in booking.traveler_slots.all()
        if _is_active_traveler(traveler_slot)
    ]


def missing_requirements_traveler_notification_targets(
    booking: Booking,
    requirements: BookingConfirmationRequirements,
) -> list[TravelerNotificationTarget]:
    traveler_slot_ids = {
        requirement.traveler_slot_id
        for requirement in requirements.unmet_requirements
        if requirement.traveler_slot_id is not None
    }
    return [
        _traveler_target(traveler_slot)
        for traveler_slot in booking.traveler_slots.all()
        if traveler_slot.id in traveler_slot_ids and _is_active_traveler(traveler_slot)
    ]


def addition_reserved_local_dates(booking: Booking) -> list[date]:
    return [
        timezone.localdate(traveler_slot.addition_reserved_at)
        for traveler_slot in booking.traveler_slots.all()
        if traveler_slot.addition_reserved_at is not None
    ]


def _traveler_target(traveler_slot: TravelerSlot) -> TravelerNotificationTarget:
    return TravelerNotificationTarget(
        name=traveler_slot.traveler_full_name,
        phone=traveler_slot.traveler_phone,
        email=traveler_slot.traveler_email,
        traveler_slot=traveler_slot,
    )


def _is_active_traveler(traveler_slot: TravelerSlot) -> bool:
    return (
        traveler_slot.is_traveler
        and traveler_slot.traveler_state == TravelerSlot.TravelerState.ACTIVE
    )
