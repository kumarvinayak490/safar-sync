from __future__ import annotations

from dataclasses import dataclass

from organizer_payments.manual_payment_instructions import (
    has_ready_manual_payment_instructions,
)
from organizer_payments.models import ProviderPaymentSetup
from organizer_payments.online_payment_readiness import (
    OnlinePaymentReadinessDecision,
    online_payment_readiness_for_organizer,
)
from organizers.models import Organizer
from trips.models import Trip


class PaymentMethod:
    PROVIDER_PAYMENTS = "provider_payments"
    QR_MANUAL_PAYMENTS = "qr_manual_payments"


class PaymentMethodReadinessBlocker:
    READY = "ready"
    ONLINE_PAYMENT_READINESS_BLOCKED = "online_payment_readiness_blocked"
    MANUAL_PAYMENT_INSTRUCTIONS_MISSING = "manual_payment_instructions_missing"
    MANUAL_PAYMENT_AVAILABILITY_CLOSED = "manual_payment_availability_closed"
    BOOKING_AVAILABILITY_CLOSED = "booking_availability_closed"
    INSUFFICIENT_CAPACITY = "insufficient_capacity"


PAYMENT_METHOD_BLOCKER_LABELS = {
    PaymentMethodReadinessBlocker.READY: "Ready",
    PaymentMethodReadinessBlocker.ONLINE_PAYMENT_READINESS_BLOCKED: (
        "Online Payment Readiness blocked"
    ),
    PaymentMethodReadinessBlocker.MANUAL_PAYMENT_INSTRUCTIONS_MISSING: (
        "Manual Payment Instructions missing"
    ),
    PaymentMethodReadinessBlocker.MANUAL_PAYMENT_AVAILABILITY_CLOSED: (
        "Manual Payment Availability closed"
    ),
    PaymentMethodReadinessBlocker.BOOKING_AVAILABILITY_CLOSED: "Booking Availability closed",
    PaymentMethodReadinessBlocker.INSUFFICIENT_CAPACITY: "Insufficient Bookable Seats",
}

PAYMENT_METHOD_MESSAGES = {
    PaymentMethodReadinessBlocker.READY: "This payment method is ready for public booking.",
    PaymentMethodReadinessBlocker.ONLINE_PAYMENT_READINESS_BLOCKED: (
        "Online payments require Online Payment Readiness before travelers can pay."
    ),
    PaymentMethodReadinessBlocker.MANUAL_PAYMENT_INSTRUCTIONS_MISSING: (
        "Manual Payments require Manual Payment Instructions before travelers can scan a "
        "Payment QR."
    ),
    PaymentMethodReadinessBlocker.MANUAL_PAYMENT_AVAILABILITY_CLOSED: (
        "Manual Payments require open Manual Payment Availability for this Trip."
    ),
    PaymentMethodReadinessBlocker.BOOKING_AVAILABILITY_CLOSED: (
        "Payment methods require open Booking Availability for this Trip."
    ),
    PaymentMethodReadinessBlocker.INSUFFICIENT_CAPACITY: (
        "Payment methods require enough Bookable Seats for this Booking."
    ),
}


@dataclass(frozen=True)
class ManualPaymentMethodReadinessFacts:
    manual_payment_instructions_present: bool = False
    manual_payment_availability_open: bool = False
    booking_availability_open: bool = False
    capacity_available: bool = False


@dataclass(frozen=True)
class PaymentMethodReadiness:
    id: str
    label: str
    method_type: str
    ready: bool
    blocker_code: str
    message: str
    action_label: str
    provider: str = ""
    provider_label: str = ""
    online_payment_readiness_ready: bool | None = None
    manual_payment_instructions_ready: bool | None = None
    manual_payment_availability_open: bool | None = None
    requires_review: bool = False

    @property
    def status_label(self) -> str:
        return "Ready" if self.ready else "Blocked"

    @property
    def blocker_label(self) -> str:
        return PAYMENT_METHOD_BLOCKER_LABELS.get(self.blocker_code, self.blocker_code)

    def to_payload(self) -> dict[str, bool | str | None]:
        return {
            "id": self.id,
            "label": self.label,
            "method_type": self.method_type,
            "ready": self.ready,
            "status_label": self.status_label,
            "blocker_code": self.blocker_code,
            "blocker_label": self.blocker_label,
            "message": self.message,
            "action_label": self.action_label,
            "provider": self.provider,
            "provider_label": self.provider_label,
            "online_payment_readiness_ready": self.online_payment_readiness_ready,
            "manual_payment_instructions_ready": self.manual_payment_instructions_ready,
            "manual_payment_availability_open": self.manual_payment_availability_open,
            "requires_review": self.requires_review,
        }


@dataclass(frozen=True)
class PaymentMethodReadinessDecision:
    provider_method: PaymentMethodReadiness
    manual_method: PaymentMethodReadiness

    @property
    def methods(self) -> tuple[PaymentMethodReadiness, PaymentMethodReadiness]:
        return (self.provider_method, self.manual_method)

    @property
    def ready(self) -> bool:
        return any(method.ready for method in self.methods)

    @property
    def ready_method_count(self) -> int:
        return sum(1 for method in self.methods if method.ready)

    @property
    def ready_method_ids(self) -> list[str]:
        return [method.id for method in self.methods if method.ready]

    @property
    def status_label(self) -> str:
        return "Ready" if self.ready else "Blocked"

    def to_payload(self) -> dict:
        return {
            "payment_method_readiness_ready": self.ready,
            "payment_method_readiness_status_label": self.status_label,
            "ready_payment_method_count": self.ready_method_count,
            "ready_payment_method_ids": self.ready_method_ids,
            "payment_methods": [method.to_payload() for method in self.methods],
            "provider_payment_method": self.provider_method.to_payload(),
            "manual_payment_method": self.manual_method.to_payload(),
        }


def payment_method_readiness_for_trip(
    trip: Trip,
    *,
    online_payment_readiness: OnlinePaymentReadinessDecision | None = None,
    manual_payment_facts: ManualPaymentMethodReadinessFacts | None = None,
    booking_availability_open: bool | None = None,
    capacity_available: bool | None = None,
) -> PaymentMethodReadinessDecision:
    if online_payment_readiness is None:
        online_payment_readiness = online_payment_readiness_for_organizer(trip.organizer)
    if booking_availability_open is None:
        booking_availability_open = trip.booking_availability == Trip.BookingAvailability.OPEN
    if capacity_available is None:
        capacity_available = False
    if manual_payment_facts is None:
        manual_payment_facts = ManualPaymentMethodReadinessFacts(
            manual_payment_instructions_present=has_ready_manual_payment_instructions(
                trip.organizer
            ),
            manual_payment_availability_open=(
                trip.manual_payment_availability == Trip.ManualPaymentAvailability.OPEN
            ),
            booking_availability_open=booking_availability_open,
            capacity_available=capacity_available,
        )

    return PaymentMethodReadinessDecision(
        provider_method=provider_payment_method_readiness(
            trip.organizer,
            online_payment_readiness=online_payment_readiness,
        ),
        manual_method=manual_payment_method_readiness(manual_payment_facts),
    )


def provider_payment_method_readiness(
    organizer: Organizer,
    *,
    online_payment_readiness: OnlinePaymentReadinessDecision | None = None,
) -> PaymentMethodReadiness:
    if online_payment_readiness is None:
        online_payment_readiness = online_payment_readiness_for_organizer(organizer)
    provider, provider_label = _provider_context(organizer)
    ready = online_payment_readiness.ready
    return PaymentMethodReadiness(
        id=PaymentMethod.PROVIDER_PAYMENTS,
        label="Online payments",
        method_type="provider_payment",
        ready=ready,
        blocker_code=(
            PaymentMethodReadinessBlocker.READY
            if ready
            else PaymentMethodReadinessBlocker.ONLINE_PAYMENT_READINESS_BLOCKED
        ),
        message=(
            "Online payments are ready for public booking."
            if ready
            else online_payment_readiness.message
        ),
        action_label="Pay online",
        provider=provider,
        provider_label=provider_label,
        online_payment_readiness_ready=ready,
        requires_review=False,
    )


def manual_payment_method_readiness(
    facts: ManualPaymentMethodReadinessFacts | None = None,
) -> PaymentMethodReadiness:
    if facts is None:
        facts = ManualPaymentMethodReadinessFacts()
    blocker_code = _manual_payment_blocker_code(facts)
    ready = blocker_code == PaymentMethodReadinessBlocker.READY
    return PaymentMethodReadiness(
        id=PaymentMethod.QR_MANUAL_PAYMENTS,
        label="Manual Payments",
        method_type="qr_manual_payment",
        ready=ready,
        blocker_code=blocker_code,
        message=PAYMENT_METHOD_MESSAGES[blocker_code],
        action_label="Scan QR code to pay",
        manual_payment_instructions_ready=facts.manual_payment_instructions_present,
        manual_payment_availability_open=facts.manual_payment_availability_open,
        requires_review=True,
    )


def _manual_payment_blocker_code(facts: ManualPaymentMethodReadinessFacts) -> str:
    if not facts.manual_payment_instructions_present:
        return PaymentMethodReadinessBlocker.MANUAL_PAYMENT_INSTRUCTIONS_MISSING
    if not facts.booking_availability_open:
        return PaymentMethodReadinessBlocker.BOOKING_AVAILABILITY_CLOSED
    if not facts.manual_payment_availability_open:
        return PaymentMethodReadinessBlocker.MANUAL_PAYMENT_AVAILABILITY_CLOSED
    if not facts.capacity_available:
        return PaymentMethodReadinessBlocker.INSUFFICIENT_CAPACITY
    return PaymentMethodReadinessBlocker.READY


def _provider_context(organizer: Organizer) -> tuple[str, str]:
    try:
        setup = organizer.provider_payment_setup
    except ProviderPaymentSetup.DoesNotExist:
        return ProviderPaymentSetup.Provider.RAZORPAY, "Razorpay"
    return setup.provider, setup.get_provider_display()
