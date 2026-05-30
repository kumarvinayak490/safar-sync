from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from trip_payments.financial_ledger import record_financial_ledger_event
from trip_payments.models import (
    BookingAdjustment,
    ManualPayment,
    OpeningPaymentRecord,
    ProviderPayment,
    RefundRecord,
)


@receiver(post_save, sender=ProviderPayment)
def create_provider_payment_ledger_entries(
    sender,
    instance: ProviderPayment,
    created: bool,
    **kwargs,
) -> None:
    record_financial_ledger_event(instance)


@receiver(post_save, sender=ManualPayment)
def create_manual_payment_ledger_entries(
    sender,
    instance: ManualPayment,
    created: bool,
    **kwargs,
) -> None:
    record_financial_ledger_event(instance)


@receiver(post_save, sender=OpeningPaymentRecord)
def create_opening_payment_record_ledger_entry(
    sender,
    instance: OpeningPaymentRecord,
    created: bool,
    **kwargs,
) -> None:
    record_financial_ledger_event(instance)


@receiver(post_save, sender=BookingAdjustment)
def create_booking_adjustment_ledger_entry(
    sender,
    instance: BookingAdjustment,
    created: bool,
    **kwargs,
) -> None:
    record_financial_ledger_event(instance)


@receiver(post_save, sender=RefundRecord)
def create_refund_record_ledger_entry(
    sender,
    instance: RefundRecord,
    created: bool,
    **kwargs,
) -> None:
    record_financial_ledger_event(instance)
