from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from trip_bookings.lifecycle import (
    required_amount_to_reserve_inr as booking_required_amount_to_reserve_inr,
)
from trip_bookings.models import Booking
from trip_payments.financial_ledger import collected_ledger_amount_inr
from trip_payments.models import PaymentAttempt, ProviderPayment
from trip_payments.seat_holds import bookable_seats
from trips.models import Trip

__all__ = [
    "bookable_capacity_available_for_reservation",
    "collected_amount_qualifies_for_reservation",
    "ensure_bookable_capacity_for_qualifying_payment",
    "reserve_booking_if_ready",
]


def collected_amount_qualifies_for_reservation(
    booking: Booking,
    *,
    incoming_amount_inr: int = 0,
) -> bool:
    if booking.booking_state != Booking.BookingState.DRAFT:
        return False
    return (
        collected_ledger_amount_inr(booking) + incoming_amount_inr
    ) >= booking_required_amount_to_reserve_inr(booking)


def ensure_bookable_capacity_for_qualifying_payment(
    booking: Booking,
    *,
    incoming_amount_inr: int = 0,
    payment_attempt: PaymentAttempt | None = None,
    insufficient_capacity_message: str = (
        "Bookable Seats are no longer sufficient for this Booking."
    ),
) -> None:
    if not collected_amount_qualifies_for_reservation(
        booking,
        incoming_amount_inr=incoming_amount_inr,
    ):
        return

    trip = Trip.objects.select_for_update().get(pk=booking.trip_id)
    booking.trip = trip
    if bookable_capacity_available_for_reservation(
        booking,
        payment_attempt=payment_attempt,
    ):
        return

    raise ValidationError(insufficient_capacity_message)


def reserve_booking_if_ready(
    booking: Booking,
    *,
    payment_attempt: PaymentAttempt | None = None,
    provider_payment: ProviderPayment | None = None,
) -> bool:
    if booking.booking_state != Booking.BookingState.DRAFT:
        return False

    if collected_ledger_amount_inr(booking) < booking_required_amount_to_reserve_inr(booking):
        return False

    if not bookable_capacity_available_for_reservation(
        booking,
        payment_attempt=payment_attempt,
    ):
        raise ValidationError("Available Seats are no longer sufficient for this Booking.")

    with transaction.atomic():
        booking.booking_state = Booking.BookingState.RESERVED
        booking.save(update_fields=["booking_state", "updated_at"])
    _send_reservation_acknowledgement(booking, provider_payment=provider_payment)
    return True


def bookable_capacity_available_for_reservation(
    booking: Booking,
    *,
    payment_attempt: PaymentAttempt | None = None,
    now=None,
) -> bool:
    requested_seats = max(booking.traveler_slot_count, 1)
    return bookable_seats(
        booking.trip,
        payment_attempt=payment_attempt,
        now=now,
    ) >= requested_seats


def _send_reservation_acknowledgement(
    booking: Booking,
    *,
    provider_payment: ProviderPayment | None = None,
) -> None:
    from organizers.services import send_reservation_acknowledgement

    if provider_payment is None:
        send_reservation_acknowledgement(booking)
        return
    send_reservation_acknowledgement(booking, provider_payment=provider_payment)
