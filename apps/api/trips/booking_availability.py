from __future__ import annotations

from dataclasses import dataclass

from organizer_payments.models import ProviderPaymentSetup
from organizer_payments.online_payment_readiness import (
    OnlinePaymentReadinessDecision,
    online_payment_readiness_for_organizer,
)
from organizers.models import Organizer
from trip_payments.models import PaymentAttempt
from trip_payments.seat_holds import (
    active_seat_hold_count,
)
from trip_payments.seat_holds import (
    bookable_seats as calculated_bookable_seats,
)
from trip_travelers.slots import available_seats as traveler_available_seats
from trips.models import Trip
from trips.payment_method_readiness import (
    PaymentMethodReadinessDecision,
    payment_method_readiness_for_trip,
)

FEW_SEATS_LEFT_ABSOLUTE_THRESHOLD = 3
FEW_SEATS_LEFT_CAPACITY_RATIO = 0.2


class PublicBookingGateReason:
    READY = "ready"
    PUBLICATION_NOT_PUBLISHED = "publication_not_published"
    BOOKING_CLOSED = "booking_closed"
    PAYMENT_METHOD_READINESS_MISSING = "payment_method_readiness_missing"
    ONLINE_PAYMENT_READINESS_MISSING = "online_payment_readiness_missing"
    PROVIDER_PAYMENT_SETUP_INCOMPLETE = "provider_payment_setup_incomplete"
    SOLD_OUT = "sold_out"
    INSUFFICIENT_CAPACITY = "insufficient_capacity"


AVAILABILITY_BAND_LABELS = {
    "available": "Available",
    "few_seats_left": "Few seats left",
    "sold_out": "Sold out",
}

EFFECTIVE_BOOKING_AVAILABILITY_LABELS = {
    Trip.BookingAvailability.OPEN: "Open",
    Trip.BookingAvailability.CLOSED: "Closed",
    "sold_out": "Sold out",
}

PUBLIC_BOOKING_GATE_MESSAGES = {
    PublicBookingGateReason.READY: "Booking can start for this trip.",
    PublicBookingGateReason.PUBLICATION_NOT_PUBLISHED: "This Public Trip Page is not available.",
    PublicBookingGateReason.BOOKING_CLOSED: "Bookings opening soon.",
    PublicBookingGateReason.PAYMENT_METHOD_READINESS_MISSING: "Bookings opening soon.",
    PublicBookingGateReason.ONLINE_PAYMENT_READINESS_MISSING: "Bookings opening soon.",
    PublicBookingGateReason.PROVIDER_PAYMENT_SETUP_INCOMPLETE: "Bookings opening soon.",
    PublicBookingGateReason.SOLD_OUT: "Sold out.",
    PublicBookingGateReason.INSUFFICIENT_CAPACITY: ("Not enough Bookable Seats for this Booking."),
}


@dataclass(frozen=True)
class PublicBookingGateDecision:
    trip: Trip
    ready: bool
    reason_code: str
    requested_seats: int
    publication_ready: bool
    booking_availability_open: bool
    online_payment_readiness: OnlinePaymentReadinessDecision
    payment_method_readiness: PaymentMethodReadinessDecision
    online_payment_readiness_ready: bool
    payment_method_readiness_ready: bool
    provider_payment_setup_complete: bool
    capacity_available: bool
    available_seats: int
    active_seat_holds: int
    bookable_seats: int
    booking_availability: str
    booking_availability_label: str
    effective_booking_availability: str
    effective_booking_availability_label: str
    availability_band: str
    availability_band_label: str
    message: str

    @property
    def cta_enabled(self) -> bool:
        return self.ready

    @property
    def cta_state(self) -> str:
        return "enabled" if self.cta_enabled else "disabled"

    def to_payload(self) -> dict:
        return {
            "cta_enabled": self.cta_enabled,
            "cta_state": self.cta_state,
            "ready": self.ready,
            "reason_code": self.reason_code,
            "requested_seats": self.requested_seats,
            "publication_ready": self.publication_ready,
            "booking_availability_open": self.booking_availability_open,
            **self.payment_method_readiness.to_payload(),
            "online_payment_readiness_ready": self.online_payment_readiness_ready,
            **self.online_payment_readiness.to_payload(),
            "provider_payment_setup_complete": self.provider_payment_setup_complete,
            "capacity_available": self.capacity_available,
            "available_seats": self.available_seats,
            "active_seat_holds": self.active_seat_holds,
            "bookable_seats": self.bookable_seats,
            "booking_availability": self.booking_availability,
            "booking_availability_label": self.booking_availability_label,
            "effective_booking_availability": self.effective_booking_availability,
            "effective_booking_availability_label": self.effective_booking_availability_label,
            "availability_band": self.availability_band,
            "availability_band_label": self.availability_band_label,
            "message": self.message,
        }


def is_provider_payment_setup_complete(organizer: Organizer) -> bool:
    try:
        setup = organizer.provider_payment_setup
    except ProviderPaymentSetup.DoesNotExist:
        return False

    return setup.is_complete


def available_seats(trip: Trip) -> int:
    return traveler_available_seats(trip)


def bookable_seats(trip: Trip) -> int:
    return calculated_bookable_seats(trip)


def effective_booking_availability(trip: Trip, *, seats_available: int | None = None) -> str:
    if seats_available is None:
        seats_available = available_seats(trip)
    if trip.booking_availability == Trip.BookingAvailability.OPEN and seats_available <= 0:
        return "sold_out"
    return trip.booking_availability


def public_availability_band(trip: Trip, *, seats_available: int | None = None) -> str:
    if seats_available is None:
        seats_available = available_seats(trip)
    if seats_available <= 0:
        return "sold_out"

    few_seats_threshold = max(
        FEW_SEATS_LEFT_ABSOLUTE_THRESHOLD,
        int(trip.capacity * FEW_SEATS_LEFT_CAPACITY_RATIO),
    )
    if seats_available <= few_seats_threshold:
        return "few_seats_left"

    return "available"


def public_booking_gate_decision(
    trip: Trip,
    *,
    requested_seats: int = 1,
    payment_attempt: PaymentAttempt | None = None,
    now=None,
) -> PublicBookingGateDecision:
    requested_seats = max(requested_seats, 1)
    seats_available = available_seats(trip)
    active_holds = active_seat_hold_count(trip, now=now)
    seats_bookable = calculated_bookable_seats(trip, payment_attempt=payment_attempt, now=now)
    publication_ready = trip.publication_state == Trip.PublicationState.PUBLISHED
    booking_availability_open = trip.booking_availability == Trip.BookingAvailability.OPEN
    online_payment_readiness = online_payment_readiness_for_organizer(trip.organizer)
    provider_payment_setup_complete = is_provider_payment_setup_complete(trip.organizer)
    capacity_available = seats_bookable >= requested_seats
    payment_method_readiness = payment_method_readiness_for_trip(
        trip,
        online_payment_readiness=online_payment_readiness,
        booking_availability_open=booking_availability_open,
        capacity_available=capacity_available,
    )
    effective_availability = effective_booking_availability(
        trip,
        seats_available=seats_bookable,
    )
    availability_band = public_availability_band(trip, seats_available=seats_bookable)
    reason_code = _reason_code(
        publication_ready=publication_ready,
        booking_availability_open=booking_availability_open,
        payment_method_readiness_ready=payment_method_readiness.ready,
        capacity_available=capacity_available,
        bookable_seats=seats_bookable,
    )

    return PublicBookingGateDecision(
        trip=trip,
        ready=reason_code == PublicBookingGateReason.READY,
        reason_code=reason_code,
        requested_seats=requested_seats,
        publication_ready=publication_ready,
        booking_availability_open=booking_availability_open,
        online_payment_readiness=online_payment_readiness,
        payment_method_readiness=payment_method_readiness,
        online_payment_readiness_ready=online_payment_readiness.ready,
        payment_method_readiness_ready=payment_method_readiness.ready,
        provider_payment_setup_complete=provider_payment_setup_complete,
        capacity_available=capacity_available,
        available_seats=seats_available,
        active_seat_holds=active_holds,
        bookable_seats=seats_bookable,
        booking_availability=trip.booking_availability,
        booking_availability_label=trip.get_booking_availability_display(),
        effective_booking_availability=effective_availability,
        effective_booking_availability_label=EFFECTIVE_BOOKING_AVAILABILITY_LABELS[
            effective_availability
        ],
        availability_band=availability_band,
        availability_band_label=AVAILABILITY_BAND_LABELS[availability_band],
        message=PUBLIC_BOOKING_GATE_MESSAGES[reason_code],
    )


def _reason_code(
    *,
    publication_ready: bool,
    booking_availability_open: bool,
    payment_method_readiness_ready: bool,
    capacity_available: bool,
    bookable_seats: int,
) -> str:
    if not publication_ready:
        return PublicBookingGateReason.PUBLICATION_NOT_PUBLISHED
    if not booking_availability_open:
        return PublicBookingGateReason.BOOKING_CLOSED
    if not capacity_available:
        if bookable_seats <= 0:
            return PublicBookingGateReason.SOLD_OUT
        return PublicBookingGateReason.INSUFFICIENT_CAPACITY
    if not payment_method_readiness_ready:
        return PublicBookingGateReason.PAYMENT_METHOD_READINESS_MISSING
    return PublicBookingGateReason.READY
