from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from team_access.models import OrganizerMembership
from trip_bookings.models import Booking
from trip_operations.activity import actor_for_activity, record_activity_log
from trip_operations.models import ActivityLog
from trip_payments.financial_ledger import record_financial_ledger_event
from trip_payments.models import BookingAdjustment, RefundRecord


def create_booking_adjustment(
    *,
    booking: Booking,
    amount_inr: int,
    adjustment_reason: str,
    actor=None,
) -> BookingAdjustment:
    with transaction.atomic():
        booking = _lock_booking_for_payment_correction(booking)
        booking_adjustment = BookingAdjustment.objects.create(
            booking=booking,
            amount_inr=amount_inr,
            adjustment_reason=adjustment_reason,
                recorded_by=actor_for_activity(actor),
        )
        record_financial_ledger_event(booking_adjustment)
        _record_payment_activity(
            action=ActivityLog.Action.BOOKING_ADJUSTMENT_RECORDED,
            booking=booking,
            actor=actor,
            metadata={
                "booking_adjustment_id": booking_adjustment.id,
                "amount_inr": booking_adjustment.amount_inr,
                "adjustment_reason": booking_adjustment.adjustment_reason,
            },
        )
        return booking_adjustment


def create_refund_record(
    *,
    booking: Booking,
    amount_inr: int,
    refund_reason: str,
    actor=None,
    refund_reference: str = "",
    send_acknowledgement: bool = False,
) -> RefundRecord:
    with transaction.atomic():
        booking = _lock_booking_for_payment_correction(booking)
        if not _actor_is_owner_for_booking(actor, booking):
            raise ValidationError("Only Owners can create Refund Records in the MVP.")
        refund_record = RefundRecord.objects.create(
            booking=booking,
            amount_inr=amount_inr,
            refund_reason=refund_reason,
            refund_reference=refund_reference,
                recorded_by=actor_for_activity(actor),
        )
        record_financial_ledger_event(refund_record)
        _record_payment_activity(
            action=ActivityLog.Action.REFUND_RECORD_RECORDED,
            booking=booking,
            actor=actor,
            metadata={
                "refund_record_id": refund_record.id,
                "amount_inr": refund_record.amount_inr,
                "refund_reference": refund_record.refund_reference,
                "refund_reason": refund_record.refund_reason,
            },
        )
        _send_refund_acknowledgement(
            booking=booking,
            amount_inr=refund_record.amount_inr,
            refund_reference=refund_record.refund_reference or f"refund-record:{refund_record.id}",
            refund_reason=refund_record.refund_reason,
            send=send_acknowledgement,
        )
        return refund_record


def _lock_booking_for_payment_correction(booking: Booking) -> Booking:
    return (
        Booking.objects.select_for_update()
        .select_related("trip", "trip__payment_schedule")
        .prefetch_related("traveler_slots__package", "ledger_entries")
        .get(pk=booking.pk)
    )


def _actor_is_owner_for_booking(actor, booking: Booking) -> bool:
    if not getattr(actor, "is_authenticated", False):
        return False
    return OrganizerMembership.objects.filter(
        organizer_id=booking.trip.organizer_id,
        user=actor,
        role=OrganizerMembership.Role.OWNER,
    ).exists()


def _record_payment_activity(
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


def _send_refund_acknowledgement(
    *,
    booking: Booking,
    amount_inr: int,
    refund_reference: str,
    refund_reason: str = "",
    send: bool = False,
):
    from organizers.services import send_refund_acknowledgement

    return send_refund_acknowledgement(
        booking=booking,
        amount_inr=amount_inr,
        refund_reference=refund_reference,
        refund_reason=refund_reason,
        send=send,
    )
