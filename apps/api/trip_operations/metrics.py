from __future__ import annotations

from dataclasses import dataclass

from trip_bookings.models import Booking
from trip_payments.financial_ledger import booking_reconciliation
from trip_payments.models import ManualPayment, PaymentAttempt
from trip_travelers.readiness import confirmation_requirements_for_booking
from trip_travelers.slots import active_reserved_traveler_count
from trips.booking_availability import (
    PublicBookingGateDecision,
    available_seats,
    public_booking_gate_decision,
)
from trips.models import Trip


@dataclass(frozen=True)
class OperationalMetrics:
    unpaid_bookings: int
    overdue_amount_inr: int
    pending_manual_payments: int
    pending_manual_payments_supported: bool
    missing_requirements: int
    missing_requirements_supported: bool
    available_seats: int
    reserved_travelers: int
    core_operational_booking_count: int
    booking_state_counts: dict[str, int]


PublicBookingReadiness = PublicBookingGateDecision


def public_booking_readiness(
    trip: Trip,
    *,
    requested_seats: int = 1,
    payment_attempt: PaymentAttempt | None = None,
    now=None,
) -> PublicBookingReadiness:
    return public_booking_gate_decision(
        trip,
        requested_seats=requested_seats,
        payment_attempt=payment_attempt,
        now=now,
    )


def core_operational_booking_count(trip: Trip) -> int:
    return trip.bookings.exclude(booking_state=Booking.BookingState.DRAFT).count()


def operational_metrics(trip: Trip) -> OperationalMetrics:
    bookings = (
        trip.bookings.select_related("trip", "trip__payment_schedule")
        .prefetch_related(
            "traveler_slots__package",
            "traveler_slots__documents",
            "ledger_entries",
            "manual_payments",
        )
        .all()
    )
    booking_state_counts = {state: 0 for state, _label in Booking.BookingState.choices}
    unpaid_bookings = 0
    overdue_amount = 0
    core_count = 0
    missing_requirements = 0
    pending_manual_payments = 0

    for booking in bookings:
        booking_state_counts[booking.booking_state] = (
            booking_state_counts.get(booking.booking_state, 0) + 1
        )
        if booking.booking_state == Booking.BookingState.DRAFT:
            continue

        core_count += 1
        if booking.booking_state == Booking.BookingState.CANCELLED:
            continue

        reconciliation = booking_reconciliation(booking)
        if reconciliation.collected_inr <= 0:
            unpaid_bookings += 1
        overdue_amount += reconciliation.overdue_inr
        requirements = confirmation_requirements_for_booking(booking)
        missing_requirements += len(requirements.unmet_requirements)
        pending_manual_payments += sum(
            1
            for manual_payment in booking.manual_payments.all()
            if manual_payment.status == ManualPayment.Status.SUBMITTED
        )

    return OperationalMetrics(
        unpaid_bookings=unpaid_bookings,
        overdue_amount_inr=overdue_amount,
        pending_manual_payments=pending_manual_payments,
        pending_manual_payments_supported=True,
        missing_requirements=missing_requirements,
        missing_requirements_supported=True,
        available_seats=available_seats(trip),
        reserved_travelers=active_reserved_traveler_count(trip),
        core_operational_booking_count=core_count,
        booking_state_counts=booking_state_counts,
    )
