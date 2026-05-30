from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO

from trip_bookings.models import Booking
from trip_operations.activity import record_activity_log
from trip_operations.models import ActivityLog
from trip_payments.financial_ledger import (
    BookingReconciliation,
    booking_reconciliation,
    booking_reconciliation_flags,
    derived_payment_state,
)
from trip_travelers.documents import (
    sensitive_traveler_document_filenames,
    traveler_document_state_summary,
)
from trip_travelers.models import TravelerSlot
from trips.models import Trip

OPERATIONAL_EXPORT_BASE_HEADERS = [
    "trip_id",
    "trip_title",
    "booking_id",
    "booking_state",
    "booking_contact_name",
    "booking_contact_phone",
    "booking_contact_email",
    "traveler_slot_id",
    "traveler_position",
    "traveler_name",
    "traveler_phone",
    "traveler_email",
    "traveler_state",
    "package_name",
    "booked_package_price_inr",
    "booked_reservation_amount_inr",
    "payment_state",
    "booking_total_inr",
    "effective_booking_total_inr",
    "collected_inr",
    "due_inr",
    "adjusted_inr",
    "refunded_inr",
    "refund_due_inr",
    "overdue_inr",
    "platform_fee_inr",
    "reconciliation_flags",
    "document_state",
    "document_states",
    "travel_arrival_details",
    "travel_departure_details",
    "travel_pickup_location",
    "travel_logistics_note",
    "rooming_notes",
    "emergency_contact_name",
    "emergency_contact_phone",
    "emergency_contact_relationship",
    "check_in_status",
    "checked_in",
    "no_show",
    "attendance_marked_at",
]

OPERATIONAL_EXPORT_SENSITIVE_TRAVELER_HEADERS = [
    "sensitive_medical_disclosure",
    "sensitive_medical_disclosure_submitted_at",
    "sensitive_traveler_document_files",
]

OPERATIONAL_EXPORT_SENSITIVE_PAYMENT_HEADERS = [
    "sensitive_provider_payment_references",
    "sensitive_manual_payment_references",
    "sensitive_payment_proof_files",
]


@dataclass(frozen=True)
class OperationalExport:
    csv_content: str
    filename: str
    row_count: int
    excluded_draft_booking_count: int


def generate_operational_export_csv(
    trip: Trip,
    *,
    actor=None,
    include_sensitive_traveler_information: bool = False,
    include_sensitive_payment_information: bool = False,
    include_draft_bookings: bool = False,
) -> OperationalExport:
    trip = (
        Trip.objects.select_related("organizer")
        .prefetch_related(
            "bookings__trip__payment_schedule",
            "bookings__traveler_slots__package",
            "bookings__traveler_slots__documents",
            "bookings__ledger_entries",
            "bookings__manual_payments",
            "bookings__provider_payments",
        )
        .get(pk=trip.pk)
    )
    bookings = list(trip.bookings.all())
    excluded_draft_booking_count = sum(
        1 for booking in bookings if booking.booking_state == Booking.BookingState.DRAFT
    )
    if not include_draft_bookings:
        bookings = [
            booking for booking in bookings if booking.booking_state != Booking.BookingState.DRAFT
        ]

    headers = list(OPERATIONAL_EXPORT_BASE_HEADERS)
    if include_sensitive_traveler_information:
        headers.extend(OPERATIONAL_EXPORT_SENSITIVE_TRAVELER_HEADERS)
    if include_sensitive_payment_information:
        headers.extend(OPERATIONAL_EXPORT_SENSITIVE_PAYMENT_HEADERS)

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    row_count = 0

    for booking in bookings:
        reconciliation = booking_reconciliation(booking)
        payment_state = derived_payment_state(booking)
        for traveler_slot in booking.traveler_slots.all():
            if traveler_slot.traveler_state != TravelerSlot.TravelerState.ACTIVE:
                continue
            row = operational_export_row(
                trip=trip,
                booking=booking,
                traveler_slot=traveler_slot,
                reconciliation=reconciliation,
                payment_state=payment_state,
                include_sensitive_traveler_information=include_sensitive_traveler_information,
                include_sensitive_payment_information=include_sensitive_payment_information,
            )
            writer.writerow(row)
            row_count += 1

    record_activity_log(
        action=ActivityLog.Action.OPERATIONAL_EXPORT_GENERATED,
        trip=trip,
        actor=actor,
        metadata={
            "format": "csv",
            "row_count": row_count,
            "include_sensitive_traveler_information": include_sensitive_traveler_information,
            "include_sensitive_payment_information": include_sensitive_payment_information,
            "include_draft_bookings": include_draft_bookings,
            "excluded_draft_booking_count": (
                0 if include_draft_bookings else excluded_draft_booking_count
            ),
        },
    )

    return OperationalExport(
        csv_content=output.getvalue(),
        filename=f"tripos-operational-export-trip-{trip.id}.csv",
        row_count=row_count,
        excluded_draft_booking_count=(
            0 if include_draft_bookings else excluded_draft_booking_count
        ),
    )


def operational_export_row(
    *,
    trip: Trip,
    booking: Booking,
    traveler_slot: TravelerSlot,
    reconciliation: BookingReconciliation,
    payment_state: str,
    include_sensitive_traveler_information: bool,
    include_sensitive_payment_information: bool,
) -> dict[str, str | int | bool]:
    document_state, document_states = _traveler_document_state_summary(traveler_slot)
    row: dict[str, str | int | bool] = {
        "trip_id": trip.id,
        "trip_title": trip.title,
        "booking_id": booking.id,
        "booking_state": booking.booking_state,
        "booking_contact_name": booking.booking_contact_name,
        "booking_contact_phone": booking.booking_contact_phone,
        "booking_contact_email": booking.booking_contact_email,
        "traveler_slot_id": traveler_slot.id,
        "traveler_position": traveler_slot.position,
        "traveler_name": traveler_slot.traveler_full_name,
        "traveler_phone": traveler_slot.traveler_phone,
        "traveler_email": traveler_slot.traveler_email,
        "traveler_state": traveler_slot.traveler_state,
        "package_name": traveler_slot.package.name,
        "booked_package_price_inr": traveler_slot.booked_package_price_inr,
        "booked_reservation_amount_inr": traveler_slot.booked_reservation_amount_inr,
        "payment_state": payment_state,
        "booking_total_inr": reconciliation.booking_total_inr,
        "effective_booking_total_inr": reconciliation.effective_booking_total_inr,
        "collected_inr": reconciliation.collected_inr,
        "due_inr": reconciliation.due_inr,
        "adjusted_inr": reconciliation.adjusted_inr,
        "refunded_inr": reconciliation.refunded_inr,
        "refund_due_inr": reconciliation.refund_due_inr,
        "overdue_inr": reconciliation.overdue_inr,
        "platform_fee_inr": reconciliation.platform_fee_inr,
        "reconciliation_flags": _reconciliation_flags(reconciliation),
        "document_state": document_state,
        "document_states": document_states,
        "travel_arrival_details": traveler_slot.arrival_details,
        "travel_departure_details": traveler_slot.departure_details,
        "travel_pickup_location": traveler_slot.pickup_location,
        "travel_logistics_note": traveler_slot.logistics_note,
        "rooming_notes": traveler_slot.rooming_notes,
        "emergency_contact_name": traveler_slot.emergency_contact_name,
        "emergency_contact_phone": traveler_slot.emergency_contact_phone,
        "emergency_contact_relationship": traveler_slot.emergency_contact_relationship,
        "check_in_status": traveler_slot.attendance_state,
        "checked_in": traveler_slot.attendance_state == TravelerSlot.AttendanceState.CHECKED_IN,
        "no_show": traveler_slot.attendance_state == TravelerSlot.AttendanceState.NO_SHOW,
        "attendance_marked_at": traveler_slot.attendance_marked_at.isoformat()
        if traveler_slot.attendance_marked_at
        else "",
    }
    if include_sensitive_traveler_information:
        row.update(
            {
                "sensitive_medical_disclosure": traveler_slot.medical_disclosure,
                "sensitive_medical_disclosure_submitted_at": (
                    traveler_slot.medical_disclosure_submitted_at.isoformat()
                    if traveler_slot.medical_disclosure_submitted_at
                    else ""
                ),
                "sensitive_traveler_document_files": _sensitive_document_files(traveler_slot),
            }
        )
    if include_sensitive_payment_information:
        row.update(
            {
                "sensitive_provider_payment_references": _provider_payment_references(booking),
                "sensitive_manual_payment_references": _manual_payment_references(booking),
                "sensitive_payment_proof_files": _payment_proof_files(booking),
            }
        )
    return row


def _traveler_document_state_summary(traveler_slot: TravelerSlot) -> tuple[str, str]:
    summary = traveler_document_state_summary(traveler_slot)
    return summary.document_state, summary.document_states


def _reconciliation_flags(reconciliation: BookingReconciliation) -> str:
    return "; ".join(booking_reconciliation_flags(reconciliation))


def _sensitive_document_files(traveler_slot: TravelerSlot) -> str:
    return "; ".join(sensitive_traveler_document_filenames(traveler_slot))


def _provider_payment_references(booking: Booking) -> str:
    return "; ".join(
        payment.provider_payment_reference for payment in booking.provider_payments.all()
    )


def _manual_payment_references(booking: Booking) -> str:
    return "; ".join(
        payment.payment_reference
        for payment in booking.manual_payments.all()
        if payment.payment_reference
    )


def _payment_proof_files(booking: Booking) -> str:
    values = []
    for payment in booking.manual_payments.all():
        if payment.payment_proof:
            values.append(
                payment.original_filename or payment.payment_proof.name.rsplit("/", 1)[-1]
            )
    return "; ".join(values)
