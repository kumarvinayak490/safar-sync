from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import QuerySet
from django.utils import timezone

from trip_bookings.models import Booking
from trips.models import Trip

AUTOMATIC_REMINDER_BOOKING_STATES = (
    Booking.BookingState.RESERVED,
    Booking.BookingState.CONFIRMED,
)

MANUAL_PAYMENT_REMINDER_BOOKING_STATES = (
    Booking.BookingState.RESERVED,
    Booking.BookingState.CONFIRMED,
    Booking.BookingState.COMPLETED,
)

MANUAL_REQUIREMENTS_REMINDER_BOOKING_STATES = (
    Booking.BookingState.RESERVED,
    Booking.BookingState.CONFIRMED,
)

ANNOUNCEMENT_BOOKING_STATES = (
    Booking.BookingState.RESERVED,
    Booking.BookingState.CONFIRMED,
)


@dataclass(frozen=True)
class BookingContactNotificationTarget:
    name: str
    phone: str
    email: str


def booking_contact_notification_target(booking: Booking) -> BookingContactNotificationTarget:
    return BookingContactNotificationTarget(
        name=booking.booking_contact_name,
        phone=booking.booking_contact_phone,
        email=booking.booking_contact_email,
    )


def booking_for_notification(booking: Booking) -> Booking:
    return _base_notification_queryset().get(pk=booking.pk)


def booking_for_reminder(booking: Booking) -> Booking:
    return (
        _base_notification_queryset()
        .select_related("trip__payment_schedule")
        .prefetch_related(
            "traveler_slots__package",
            "traveler_slots__documents",
            "ledger_entries",
        )
        .get(pk=booking.pk)
    )


def automatic_reminder_booking_queryset() -> QuerySet[Booking]:
    return (
        _base_notification_queryset()
        .select_related("trip__payment_schedule")
        .prefetch_related(
            "traveler_slots",
            "traveler_slots__documents",
            "ledger_entries",
        )
        .filter(booking_state__in=AUTOMATIC_REMINDER_BOOKING_STATES)
    )


def draft_recovery_reminder_candidates(*, now) -> QuerySet[Booking]:
    return (
        _base_notification_queryset()
        .filter(
            booking_state=Booking.BookingState.DRAFT,
            created_at__lte=now - timedelta(hours=20),
            created_at__gt=now - timedelta(hours=24),
            draft_expires_at__gt=now,
        )
        .order_by("id")
    )


def announcement_bookings_for_trip(trip: Trip) -> QuerySet[Booking]:
    return (
        _base_notification_queryset()
        .prefetch_related("traveler_slots")
        .filter(trip_id=trip.pk, booking_state__in=ANNOUNCEMENT_BOOKING_STATES)
        .order_by("id")
    )


def can_receive_manual_payment_reminder(booking: Booking) -> bool:
    return booking.booking_state in MANUAL_PAYMENT_REMINDER_BOOKING_STATES


def can_receive_manual_requirements_reminder(booking: Booking) -> bool:
    return booking.booking_state in MANUAL_REQUIREMENTS_REMINDER_BOOKING_STATES


def can_receive_active_traveler_notifications(booking: Booking) -> bool:
    return booking.booking_state in ANNOUNCEMENT_BOOKING_STATES


def is_cancelled_booking(booking: Booking) -> bool:
    return booking.booking_state == Booking.BookingState.CANCELLED


def booking_updated_local_date(booking: Booking) -> date:
    return timezone.localdate(booking.updated_at)


def _base_notification_queryset() -> QuerySet[Booking]:
    return Booking.objects.select_related("trip", "trip__organizer")
