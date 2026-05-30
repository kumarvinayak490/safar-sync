from __future__ import annotations

from django.db.models import QuerySet

from trip_payments.models import PaymentException, PlatformFeeStatement
from trip_payments.payment_exceptions import (
    resolve_late_confirmed_payment_exception_as_staff,
)


def platform_fee_statement_review_queryset() -> QuerySet[PlatformFeeStatement]:
    return PlatformFeeStatement.objects.select_related("organizer").all()


def payment_exception_review_queryset() -> QuerySet[PaymentException]:
    return PaymentException.objects.select_related(
        "organizer",
        "trip",
        "booking",
        "payment_attempt",
        "provider_payment",
        "resolved_by",
    ).all()


def resolve_payment_exception_for_staff_review(
    payment_exception: PaymentException,
    *,
    actor,
    resolution_note: str = "",
) -> PaymentException:
    return resolve_late_confirmed_payment_exception_as_staff(
        payment_exception,
        actor=actor,
        resolution_note=resolution_note,
    )
