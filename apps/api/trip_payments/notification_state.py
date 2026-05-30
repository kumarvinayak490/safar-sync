from __future__ import annotations

from trip_bookings.models import Booking
from trip_payments.financial_ledger import BookingReconciliation, booking_reconciliation
from trip_payments.models import ManualPayment, ProviderPayment


def booking_reconciliation_for_notification(booking: Booking) -> BookingReconciliation:
    return booking_reconciliation(booking)


def current_balance_due_for_notification_inr(booking: Booking) -> int:
    return booking_reconciliation_for_notification(booking).due_inr


def provider_payment_for_notification(provider_payment: ProviderPayment) -> ProviderPayment:
    return ProviderPayment.objects.select_related(
        "booking",
        "booking__trip",
        "booking__trip__organizer",
    ).get(pk=provider_payment.pk)


def manual_payment_for_notification(manual_payment: ManualPayment) -> ManualPayment:
    return ManualPayment.objects.select_related(
        "booking",
        "booking__trip",
        "booking__trip__organizer",
    ).get(pk=manual_payment.pk)


def should_send_manual_payment_acknowledgement(
    manual_payment: ManualPayment,
    *,
    send: bool | None,
) -> bool:
    if manual_payment.status != ManualPayment.Status.APPROVED:
        return False
    if send is not None:
        return send
    return manual_payment.source == ManualPayment.Source.TRAVELER_SUBMITTED
