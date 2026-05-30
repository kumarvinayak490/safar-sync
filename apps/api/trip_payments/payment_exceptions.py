from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from team_access.models import OrganizerMembership
from trip_bookings.models import Booking
from trip_operations.activity import actor_for_activity, record_activity_log
from trip_operations.models import ActivityLog
from trip_payments.models import PaymentAttempt, PaymentException, ProviderPayment, SeatHold
from trip_payments.seat_holds import bookable_seats as calculated_bookable_seats


def record_mismatched_provider_payment_exception(
    payment_attempt: PaymentAttempt,
    *,
    provider_payment_reference: str,
    confirmation: dict,
    mismatch_reasons: list[str],
    provider_payment: ProviderPayment | None = None,
) -> PaymentException:
    booking = payment_attempt.booking
    details = _provider_confirmation_exception_details(
        payment_attempt,
        confirmation=confirmation,
        mismatch_reasons=mismatch_reasons,
    )
    if provider_payment is not None:
        details["existing_provider_payment"] = {
            "id": provider_payment.id,
            "booking": provider_payment.booking_id,
            "payment_attempt": provider_payment.payment_attempt_id,
            "provider_payment_reference": provider_payment.provider_payment_reference,
        }
    linked_provider_payment = (
        provider_payment
        if provider_payment is not None and provider_payment.booking_id == booking.id
        else None
    )
    payment_exception, created = PaymentException.objects.get_or_create(
        exception_type=PaymentException.ExceptionType.MISMATCHED_PROVIDER_PAYMENT,
        provider=confirmation["provider"],
        provider_payment_reference=provider_payment_reference,
        defaults={
            "organizer": booking.trip.organizer,
            "trip": booking.trip,
            "booking": booking,
            "payment_attempt": payment_attempt,
            "provider_payment": linked_provider_payment,
            "amount_inr": confirmation["amount_inr"],
            "provider_attempt_reference": confirmation["provider_attempt_reference"],
            "mismatch_reasons": mismatch_reasons,
            "details": details,
        },
    )
    if created:
        _record_payment_exception_activity(
            action=ActivityLog.Action.PAYMENT_EXCEPTION_CREATED,
            booking=booking,
            metadata={
                "payment_exception_id": payment_exception.id,
                "exception_type": payment_exception.exception_type,
                "mismatch_reasons": mismatch_reasons,
                "provider_payment_reference": provider_payment_reference,
            },
        )
    return payment_exception


def record_late_confirmed_payment_exception(
    provider_payment: ProviderPayment,
    *,
    payment_attempt: PaymentAttempt,
) -> PaymentException:
    booking = provider_payment.booking
    seat_hold = (
        SeatHold.objects.filter(payment_attempt=payment_attempt)
        .only("expires_at", "released_at", "seat_count")
        .first()
    )
    details = {
        "reason": "seat_hold_expired_with_insufficient_bookable_seats",
        "requested_seats": booking.traveler_slot_count,
        "bookable_seats": calculated_bookable_seats(booking.trip),
        "seat_hold": {
            "expires_at": seat_hold.expires_at.isoformat() if seat_hold else None,
            "released_at": seat_hold.released_at.isoformat()
            if seat_hold and seat_hold.released_at
            else None,
            "seat_count": seat_hold.seat_count if seat_hold else 0,
        },
    }
    payment_exception, created = PaymentException.objects.get_or_create(
        exception_type=PaymentException.ExceptionType.LATE_CONFIRMED_PAYMENT,
        provider_payment=provider_payment,
        defaults={
            "organizer": booking.trip.organizer,
            "trip": booking.trip,
            "booking": booking,
            "payment_attempt": payment_attempt,
            "provider": provider_payment.provider,
            "amount_inr": provider_payment.amount_inr,
            "provider_attempt_reference": payment_attempt.provider_attempt_reference,
            "provider_payment_reference": provider_payment.provider_payment_reference,
            "details": details,
        },
    )
    if created:
        _record_payment_exception_activity(
            action=ActivityLog.Action.PAYMENT_EXCEPTION_CREATED,
            booking=booking,
            metadata={
                "payment_exception_id": payment_exception.id,
                "exception_type": payment_exception.exception_type,
                "provider_payment_id": provider_payment.id,
            },
        )
    return payment_exception


def record_provider_dispute_exception(
    provider_payment: ProviderPayment,
    *,
    provider_event_type: str,
    provider_dispute_reference: str,
    amount_inr: int | None = None,
    details: dict | None = None,
) -> PaymentException:
    with transaction.atomic():
        provider_payment = (
            ProviderPayment.objects.select_for_update()
            .select_related(
                "booking",
                "booking__trip",
                "booking__trip__organizer",
                "payment_attempt",
            )
            .get(pk=provider_payment.pk)
        )
        provider_event_type = provider_event_type.strip()
        provider_dispute_reference = provider_dispute_reference.strip()
        if provider_event_type not in PaymentException.ProviderEventType.values:
            raise ValidationError("Provider Dispute Exception requires dispute or chargeback.")
        if not provider_dispute_reference:
            raise ValidationError("Provider Dispute Exception requires dispute reference.")
        dispute_amount_inr = amount_inr if amount_inr is not None else provider_payment.amount_inr
        if dispute_amount_inr <= 0:
            raise ValidationError("Provider Dispute Exception amount must be positive.")

        booking = provider_payment.booking
        payment_exception, created = PaymentException.objects.get_or_create(
            exception_type=PaymentException.ExceptionType.PROVIDER_DISPUTE,
            provider_payment=provider_payment,
            defaults={
                "organizer": booking.trip.organizer,
                "trip": booking.trip,
                "booking": booking,
                "payment_attempt": provider_payment.payment_attempt,
                "provider": provider_payment.provider,
                "amount_inr": dispute_amount_inr,
                "provider_attempt_reference": (
                    provider_payment.payment_attempt.provider_attempt_reference
                ),
                "provider_payment_reference": provider_payment.provider_payment_reference,
                "provider_event_type": provider_event_type,
                "provider_dispute_reference": provider_dispute_reference,
                "details": details or {},
            },
        )
        if created:
            _record_payment_exception_activity(
                action=ActivityLog.Action.PAYMENT_EXCEPTION_CREATED,
                booking=booking,
                metadata={
                    "payment_exception_id": payment_exception.id,
                    "exception_type": payment_exception.exception_type,
                    "provider_payment_id": provider_payment.id,
                    "provider_event_type": provider_event_type,
                    "provider_dispute_reference": provider_dispute_reference,
                },
            )
        return payment_exception


def resolve_late_confirmed_payment_exception(
    payment_exception: PaymentException,
    *,
    actor,
    resolution_note: str = "",
) -> PaymentException:
    if not _actor_can_use_operator_workflow_for_booking(actor, payment_exception.booking):
        raise ValidationError(
            "Owner or Operator access is required to resolve this Payment Exception."
        )
    return _resolve_late_confirmed_payment_exception(
        payment_exception,
        actor=actor,
        resolution_note=resolution_note,
    )


def resolve_late_confirmed_payment_exception_as_staff(
    payment_exception: PaymentException,
    *,
    actor,
    resolution_note: str = "",
) -> PaymentException:
    if not _actor_can_use_internal_admin_review(actor):
        raise ValidationError("Internal TripOS staff access is required.")
    return _resolve_late_confirmed_payment_exception(
        payment_exception,
        actor=actor,
        resolution_note=resolution_note,
    )


def _resolve_late_confirmed_payment_exception(
    payment_exception: PaymentException,
    *,
    actor,
    resolution_note: str = "",
) -> PaymentException:
    with transaction.atomic():
        payment_exception = (
            PaymentException.objects.select_for_update()
            .select_related("booking", "booking__trip")
            .get(pk=payment_exception.pk)
        )
        if (
            payment_exception.exception_type
            != PaymentException.ExceptionType.LATE_CONFIRMED_PAYMENT
        ):
            raise ValidationError(
                "Only Late Confirmed Payment Exceptions support booking operations resolution."
            )
        if payment_exception.status == PaymentException.Status.BOOKING_OPERATIONS_RESOLVED:
            return payment_exception

        payment_exception.status = PaymentException.Status.BOOKING_OPERATIONS_RESOLVED
        payment_exception.resolution_note = resolution_note.strip()
        payment_exception.resolved_by = actor_for_activity(actor)
        payment_exception.resolved_at = timezone.now()
        payment_exception.save(
            update_fields=[
                "status",
                "resolution_note",
                "resolved_by",
                "resolved_at",
                "updated_at",
            ]
        )
        _record_payment_exception_activity(
            action=ActivityLog.Action.PAYMENT_EXCEPTION_RESOLVED,
            booking=payment_exception.booking,
            actor=actor,
            metadata={
                "payment_exception_id": payment_exception.id,
                "exception_type": payment_exception.exception_type,
                "resolution_note": payment_exception.resolution_note,
            },
        )
        return payment_exception


def _provider_confirmation_exception_details(
    payment_attempt: PaymentAttempt,
    *,
    confirmation: dict,
    mismatch_reasons: list[str],
) -> dict:
    return {
        "mismatch_reasons": mismatch_reasons,
        "expected": {
            "payment_attempt": payment_attempt.id,
            "booking": payment_attempt.booking_id,
            "provider": payment_attempt.provider,
            "purpose": payment_attempt.purpose,
            "provider_attempt_reference": payment_attempt.provider_attempt_reference,
            "amount_inr": payment_attempt.amount_inr,
        },
        "reported": {
            "payment_attempt": confirmation["payment_attempt_id"],
            "booking": confirmation["booking_id"],
            "provider": confirmation["provider"],
            "purpose": confirmation["purpose"],
            "provider_attempt_reference": confirmation["provider_attempt_reference"],
            "amount_inr": confirmation["amount_inr"],
        },
    }


def _actor_can_use_operator_workflow_for_booking(actor, booking: Booking) -> bool:
    if not getattr(actor, "is_authenticated", False):
        return False
    return OrganizerMembership.objects.filter(
        organizer_id=booking.trip.organizer_id,
        user=actor,
        role__in=[
            OrganizerMembership.Role.OWNER,
            OrganizerMembership.Role.OPERATOR,
        ],
    ).exists()


def _actor_can_use_internal_admin_review(actor) -> bool:
    return bool(
        getattr(actor, "is_authenticated", False)
        and getattr(actor, "is_staff", False)
    )


def _record_payment_exception_activity(
    *,
    action: str,
    booking: Booking,
    actor=None,
    metadata: dict | None = None,
) -> ActivityLog:
    return record_activity_log(
        action=action,
        booking=booking,
        actor=actor,
        metadata=metadata or {},
    )
