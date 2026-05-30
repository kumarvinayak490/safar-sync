from __future__ import annotations

from django.db import models
from django.utils import timezone

from trip_bookings.models import Booking
from trip_payments.models import PaymentAttempt, SeatHold
from trip_travelers.slots import available_seats
from trips.models import Trip

__all__ = [
    "active_seat_hold_count",
    "active_seat_hold_count_for_payment_attempt",
    "active_seat_hold_queryset",
    "bookable_seats",
    "create_seat_hold_for_payment_attempt",
    "release_active_seat_holds_for_booking",
    "release_seat_hold_for_payment_attempt",
]


def active_seat_hold_queryset(trip: Trip, *, now=None):
    current_time = now or timezone.now()
    return SeatHold.objects.filter(
        trip=trip,
        released_at__isnull=True,
        expires_at__gt=current_time,
    )


def active_seat_hold_count(trip: Trip, *, now=None) -> int:
    total = active_seat_hold_queryset(trip, now=now).aggregate(total=models.Sum("seat_count"))[
        "total"
    ]
    return total or 0


def active_seat_hold_count_for_payment_attempt(
    payment_attempt: PaymentAttempt,
    *,
    trip: Trip,
    now=None,
) -> int:
    current_time = now or timezone.now()
    total = SeatHold.objects.filter(
        trip=trip,
        payment_attempt=payment_attempt,
        released_at__isnull=True,
        expires_at__gt=current_time,
    ).aggregate(total=models.Sum("seat_count"))["total"]
    return total or 0


def bookable_seats(
    trip: Trip,
    *,
    payment_attempt: PaymentAttempt | None = None,
    now=None,
) -> int:
    held_seats_for_payment_attempt = 0
    if payment_attempt is not None:
        held_seats_for_payment_attempt = active_seat_hold_count_for_payment_attempt(
            payment_attempt,
            trip=trip,
            now=now,
        )
    return max(
        available_seats(trip)
        - active_seat_hold_count(trip, now=now)
        + held_seats_for_payment_attempt,
        0,
    )


def create_seat_hold_for_payment_attempt(
    payment_attempt: PaymentAttempt,
    *,
    now=None,
) -> SeatHold:
    booking = payment_attempt.booking
    return SeatHold.objects.create(
        trip=booking.trip,
        booking=booking,
        payment_attempt=payment_attempt,
        seat_count=booking.traveler_slot_count,
        expires_at=_seat_hold_expiry(now=now),
    )


def release_active_seat_holds_for_booking(booking: Booking, *, now=None) -> int:
    current_time = now or timezone.now()
    return SeatHold.objects.filter(
        booking=booking,
        released_at__isnull=True,
        expires_at__gt=current_time,
    ).update(released_at=current_time)


def release_seat_hold_for_payment_attempt(payment_attempt: PaymentAttempt, *, now=None) -> int:
    current_time = now or timezone.now()
    return SeatHold.objects.filter(
        payment_attempt=payment_attempt,
        released_at__isnull=True,
    ).update(released_at=current_time)


def _seat_hold_expiry(*, now=None):
    current_time = now or timezone.now()
    from django.conf import settings

    hold_seconds = getattr(settings, "TRIPOS_SEAT_HOLD_SECONDS", 10 * 60)
    return current_time + timezone.timedelta(seconds=hold_seconds)
