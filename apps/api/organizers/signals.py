from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from organizer_payments.setup_records import ensure_payment_setup_records
from organizers.models import Organizer
from trip_operations.notifications import send_manual_payment_acknowledgement
from trip_payments.models import ManualPayment


@receiver(post_save, sender=Organizer)
def create_payment_setup_records(sender, instance: Organizer, created: bool, **kwargs) -> None:
    if created:
        ensure_payment_setup_records(instance)


@receiver(post_save, sender=ManualPayment)
def send_created_manual_payment_acknowledgement(
    sender,
    instance: ManualPayment,
    created: bool,
    **kwargs,
) -> None:
    if created:
        send_manual_payment_acknowledgement(instance)
