from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from trip_bookings.intake import create_booking_from_intake, prepare_public_booking_intake
from trip_bookings.models import Booking
from trip_operations.activity import record_activity_log
from trip_operations.models import ActivityLog
from trip_payments.financial_ledger import (
    record_financial_ledger_event,
)
from trip_payments.models import ManualPayment
from trip_payments.reservation_rules import (
    ensure_bookable_capacity_for_qualifying_payment,
    reserve_booking_if_ready,
)
from trip_travelers.slots import reserve_pending_traveler_additions_if_ready
from trips.booking_availability import PublicBookingGateReason, public_booking_gate_decision
from trips.models import Trip


class PublicQrManualPaymentSubmissionBlocked(Exception):
    def __init__(self, detail: dict):
        self.detail = detail
        super().__init__(str(detail))


def create_public_qr_manual_payment_submission(
    *,
    trip: Trip,
    booking_contact_name: str,
    booking_contact_phone: str,
    payment_proof,
    booking_contact_email: str = "",
    selected_package_id: int | None = None,
    traveler_count: int | None = None,
    payment_reference: str = "",
    note: str = "",
    initial_data=None,
) -> ManualPayment:
    if not payment_proof:
        raise ValidationError("Traveler-submitted Manual Payments require Payment Proof.")

    with transaction.atomic():
        trip = (
            Trip.objects.select_for_update()
            .select_related("organizer", "payment_schedule")
            .prefetch_related("packages")
            .get(pk=trip.pk)
        )
        intake = prepare_public_booking_intake(
            trip=trip,
            booking_contact_name=booking_contact_name,
            booking_contact_phone=booking_contact_phone,
            booking_contact_email=booking_contact_email,
            selected_package_id=selected_package_id,
            traveler_count=traveler_count,
            initial_data=initial_data,
        )
        readiness = public_booking_gate_decision(
            trip,
            requested_seats=intake.traveler_count,
        )
        manual_method = readiness.payment_method_readiness.manual_method
        if (
            not manual_method.ready
            and readiness.reason_code
            == PublicBookingGateReason.PAYMENT_METHOD_READINESS_MISSING
        ):
            raise PublicQrManualPaymentSubmissionBlocked(
                {
                    "manual_payment_method": {
                        "blocker_code": manual_method.blocker_code,
                        "message": manual_method.message,
                    }
                }
            )
        if not readiness.ready:
            raise PublicQrManualPaymentSubmissionBlocked(
                {
                    "public_booking_gate": {
                        "reason_code": readiness.reason_code,
                        "message": readiness.message,
                    }
                }
            )
        if not manual_method.ready:
            raise PublicQrManualPaymentSubmissionBlocked(
                {
                    "manual_payment_method": {
                        "blocker_code": manual_method.blocker_code,
                        "message": manual_method.message,
                    }
                }
            )

        booking = create_booking_from_intake(
            trip=trip,
            intake=intake,
            booking_state=Booking.BookingState.DRAFT,
        )
        return ManualPayment.objects.create(
            booking=booking,
            source=ManualPayment.Source.TRAVELER_SUBMITTED,
            status=ManualPayment.Status.SUBMITTED,
            amount_inr=booking.booking_reservation_amount_inr,
            payment_reference=payment_reference,
            note=note,
            payment_proof=payment_proof,
            original_filename=getattr(payment_proof, "name", ""),
            content_type=getattr(payment_proof, "content_type", "") or "",
            file_size=getattr(payment_proof, "size", 0),
        )


def create_organizer_entered_manual_payment(
    *,
    booking: Booking,
    amount_inr: int,
    actor=None,
    payment_reference: str = "",
    note: str = "",
    payment_proof=None,
    send_payment_acknowledgement: bool = False,
) -> ManualPayment:
    with transaction.atomic():
        booking = _lock_booking_for_manual_payment(booking)
        if booking.booking_state in {
            Booking.BookingState.CANCELLED,
            Booking.BookingState.COMPLETED,
        }:
            raise ValidationError("Manual Payments cannot be recorded for inactive Bookings.")
        ensure_bookable_capacity_for_qualifying_payment(
            booking,
            incoming_amount_inr=amount_inr,
        )

        manual_payment = ManualPayment.objects.create(
            booking=booking,
            source=ManualPayment.Source.ORGANIZER_ENTERED,
            status=ManualPayment.Status.APPROVED,
            amount_inr=amount_inr,
            payment_reference=payment_reference,
            note=note,
            payment_proof=payment_proof,
            original_filename=getattr(payment_proof, "name", "") if payment_proof else "",
            content_type=getattr(payment_proof, "content_type", "") if payment_proof else "",
            file_size=getattr(payment_proof, "size", 0) if payment_proof else 0,
            approved_by=actor if getattr(actor, "is_authenticated", False) else None,
        )
        record_financial_ledger_event(manual_payment)
        reserve_booking_if_ready(booking)
        reserve_pending_traveler_additions_if_ready(booking, actor=actor)
        _send_manual_payment_acknowledgement(
            manual_payment,
            send=send_payment_acknowledgement,
        )
        return manual_payment


def create_traveler_submitted_manual_payment(
    *,
    booking: Booking,
    amount_inr: int,
    payment_proof,
    payment_reference: str = "",
    note: str = "",
) -> ManualPayment:
    if not payment_proof:
        raise ValidationError("Traveler-submitted Manual Payments require Payment Proof.")

    with transaction.atomic():
        booking = _lock_booking_for_manual_payment(booking)
        if booking.booking_state in {
            Booking.BookingState.CANCELLED,
            Booking.BookingState.COMPLETED,
        }:
            raise ValidationError("Manual Payments cannot be submitted for inactive Bookings.")

        return ManualPayment.objects.create(
            booking=booking,
            source=ManualPayment.Source.TRAVELER_SUBMITTED,
            status=ManualPayment.Status.SUBMITTED,
            amount_inr=amount_inr,
            payment_reference=payment_reference,
            note=note,
            payment_proof=payment_proof,
            original_filename=getattr(payment_proof, "name", ""),
            content_type=getattr(payment_proof, "content_type", "") or "",
            file_size=getattr(payment_proof, "size", 0),
        )


def approve_manual_payment(
    *,
    manual_payment: ManualPayment,
    actor=None,
) -> ManualPayment:
    with transaction.atomic():
        manual_payment = (
            ManualPayment.objects.select_for_update()
            .select_related("booking", "booking__trip", "booking__trip__payment_schedule")
            .prefetch_related("booking__traveler_slots__package", "booking__ledger_entries")
            .get(pk=manual_payment.pk)
        )
        if manual_payment.status != ManualPayment.Status.SUBMITTED:
            raise ValidationError("Only Submitted Manual Payments can be approved.")
        if (
            manual_payment.source == ManualPayment.Source.TRAVELER_SUBMITTED
            and not manual_payment.payment_proof
        ):
            raise ValidationError("Traveler-submitted Manual Payments require Payment Proof.")
        ensure_bookable_capacity_for_qualifying_payment(
            manual_payment.booking,
            incoming_amount_inr=manual_payment.amount_inr,
        )

        manual_payment.status = ManualPayment.Status.APPROVED
        manual_payment.approved_by = actor if getattr(actor, "is_authenticated", False) else None
        manual_payment.approved_at = timezone.now()
        manual_payment.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )
        record_financial_ledger_event(manual_payment)
        reserve_booking_if_ready(manual_payment.booking)
        reserve_pending_traveler_additions_if_ready(manual_payment.booking, actor=actor)
        _send_manual_payment_acknowledgement(manual_payment)
        return manual_payment


def reject_manual_payment(
    *,
    manual_payment: ManualPayment,
    actor=None,
    rejection_reason: str = "",
) -> ManualPayment:
    with transaction.atomic():
        manual_payment = (
            ManualPayment.objects.select_for_update()
            .select_related("booking", "booking__trip")
            .get(pk=manual_payment.pk)
        )
        if manual_payment.status != ManualPayment.Status.SUBMITTED:
            raise ValidationError("Only Submitted Manual Payments can be rejected.")

        note = rejection_reason.strip()
        if note:
            existing_note = manual_payment.note.strip()
            manual_payment.note = (
                f"{existing_note}\n\nRejection Reason: {note}"
                if existing_note
                else f"Rejection Reason: {note}"
            )
        manual_payment.status = ManualPayment.Status.REJECTED
        manual_payment.approved_by = actor if getattr(actor, "is_authenticated", False) else None
        manual_payment.approved_at = timezone.now()
        manual_payment.save(
            update_fields=[
                "status",
                "note",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )
        return manual_payment


def record_sensitive_payment_information_download(
    manual_payment: ManualPayment,
    *,
    actor=None,
) -> ActivityLog:
    return record_activity_log(
        action=ActivityLog.Action.SENSITIVE_PAYMENT_INFORMATION_DOWNLOAD,
        booking=manual_payment.booking,
        actor=actor,
        metadata={
            "manual_payment": manual_payment.id,
            "source": manual_payment.source,
            "status": manual_payment.status,
            "is_sensitive_payment_information": manual_payment.is_sensitive_payment_information,
            "exclude_from_default_exports": manual_payment.exclude_from_default_exports,
        },
    )


def _lock_booking_for_manual_payment(booking: Booking) -> Booking:
    return (
        Booking.objects.select_for_update()
        .select_related("trip", "trip__payment_schedule")
        .prefetch_related("traveler_slots__package", "ledger_entries")
        .get(pk=booking.pk)
    )


def _send_manual_payment_acknowledgement(
    manual_payment: ManualPayment,
    *,
    send: bool | None = None,
):
    from organizers.services import send_manual_payment_acknowledgement

    return send_manual_payment_acknowledgement(manual_payment, send=send)
