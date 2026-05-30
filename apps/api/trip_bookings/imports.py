from __future__ import annotations

import csv
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from io import StringIO

from django.core.exceptions import ValidationError
from django.db import transaction

from trip_bookings.intake import (
    BookingIntake,
    apply_booking_intake_to_booking,
    prepare_booking_intake,
)
from trip_bookings.models import Booking, BookingImport, BookingImportRow
from trip_payments.models import OpeningPaymentRecord
from trip_travelers.slots import TravelerSlotIntakeInput, active_reserved_traveler_count
from trips.models import Trip


@dataclass(frozen=True)
class BookingImportTravelerSlotInput:
    package_id: int
    traveler_full_name: str = ""
    traveler_phone: str = ""
    traveler_email: str = ""


@dataclass(frozen=True)
class BookingImportRowInput:
    booking_contact_name: str
    booking_contact_phone: str
    traveler_slots: list[BookingImportTravelerSlotInput]
    booking_contact_email: str = ""
    booking_id: int | None = None
    opening_payment_amount_inr: int = 0
    opening_payment_reference: str = ""
    opening_payment_note: str = ""


OpeningPaymentRecorder = Callable[..., OpeningPaymentRecord]
BookingReservationReadiness = Callable[[Booking], bool]


def parse_booking_import_upload(upload) -> dict:
    decoded = StringIO(upload.read().decode("utf-8-sig"))
    rows = []
    for csv_row in csv.DictReader(decoded):
        row = {
            "booking_contact_name": csv_row.get("booking_contact_name", ""),
            "booking_contact_phone": csv_row.get("booking_contact_phone", ""),
            "booking_contact_email": csv_row.get("booking_contact_email", ""),
            "traveler_slots": [
                {
                    "package": csv_row.get("package_id") or csv_row.get("package"),
                    "traveler_full_name": csv_row.get("traveler_full_name", ""),
                    "traveler_phone": csv_row.get("traveler_phone", ""),
                    "traveler_email": csv_row.get("traveler_email", ""),
                }
            ],
            "opening_payment_amount_inr": (csv_row.get("opening_payment_amount_inr") or 0),
            "opening_payment_reference": csv_row.get(
                "opening_payment_reference",
                "",
            ),
            "opening_payment_note": csv_row.get("opening_payment_note", ""),
        }
        if csv_row.get("booking_id"):
            row["booking_id"] = csv_row["booking_id"]
        rows.append(row)
    return {"rows": rows, "source_filename": upload.name}


def prepare_booking_import_intake(
    *,
    trip: Trip,
    booking_contact_name: str,
    booking_contact_phone: str,
    booking_contact_email: str = "",
    traveler_slots: Sequence[TravelerSlotIntakeInput] | None = None,
) -> BookingIntake:
    return prepare_booking_intake(
        trip=trip,
        booking_contact_name=booking_contact_name,
        booking_contact_phone=booking_contact_phone,
        booking_contact_email=booking_contact_email,
        traveler_slots=traveler_slots or (),
        missing_slots_field="traveler_slots",
        missing_slots_message="At least one Traveler Slot with a Package is required.",
        package_ownership_field="traveler_slots",
        package_ownership_message="Every Traveler Slot Package must belong to this Trip.",
        allow_traveler_identity=True,
    )


def create_booking_import(
    *,
    trip: Trip,
    rows: list[BookingImportRowInput],
    actor=None,
    source_filename: str = "",
    record_opening_payment: OpeningPaymentRecorder | None = None,
    reserve_booking: BookingReservationReadiness | None = None,
) -> BookingImport:
    record_opening_payment = record_opening_payment or record_import_opening_payment
    reserve_booking = reserve_booking or reserve_imported_booking_if_ready

    with transaction.atomic():
        trip = (
            Trip.objects.select_for_update()
            .select_related("organizer", "payment_schedule")
            .prefetch_related("packages")
            .get(pk=trip.pk)
        )
        booking_import = BookingImport.objects.create(
            trip=trip,
            submitted_by=actor if getattr(actor, "is_authenticated", False) else None,
            source_filename=source_filename,
        )

        counts = {
            BookingImportRow.Status.CREATED: 0,
            BookingImportRow.Status.UPDATED: 0,
            BookingImportRow.Status.SKIPPED: 0,
            BookingImportRow.Status.CONFLICT: 0,
        }
        for row_number, row in enumerate(rows, start=1):
            status, booking, conflict_code, message = _process_booking_import_row(
                booking_import=booking_import,
                trip=trip,
                row=row,
                row_number=row_number,
                actor=actor,
                record_opening_payment=record_opening_payment,
                reserve_booking=reserve_booking,
            )
            counts[status] += 1
            BookingImportRow.objects.create(
                booking_import=booking_import,
                booking=booking,
                row_number=row_number,
                status=status,
                conflict_code=conflict_code,
                message=message,
                payload=booking_import_row_payload(row),
            )

        booking_import.created_count = counts[BookingImportRow.Status.CREATED]
        booking_import.updated_count = counts[BookingImportRow.Status.UPDATED]
        booking_import.skipped_count = counts[BookingImportRow.Status.SKIPPED]
        booking_import.conflict_count = counts[BookingImportRow.Status.CONFLICT]
        booking_import.status = (
            BookingImport.Status.COMPLETED_WITH_CONFLICTS
            if booking_import.conflict_count
            else BookingImport.Status.COMPLETED
        )
        booking_import.save(
            update_fields=[
                "created_count",
                "updated_count",
                "skipped_count",
                "conflict_count",
                "status",
            ]
        )
        return booking_import


def record_import_opening_payment(
    *,
    booking: Booking,
    booking_import: BookingImport,
    amount_inr: int,
    payment_reference: str = "",
    note: str = "",
    actor=None,
) -> OpeningPaymentRecord:
    opening_payment_record = OpeningPaymentRecord.objects.create(
        booking=booking,
        booking_import=booking_import,
        amount_inr=amount_inr,
        payment_reference=payment_reference,
        note=note,
        recorded_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    _record_opening_payment_ledger_event(opening_payment_record)
    return opening_payment_record


def reserve_imported_booking_if_ready(booking: Booking) -> bool:
    from trip_payments.reservation_rules import reserve_booking_if_ready

    return reserve_booking_if_ready(booking)


def booking_import_row_payload(row: BookingImportRowInput) -> dict:
    return {
        "booking_id": row.booking_id,
        "booking_contact_name": row.booking_contact_name,
        "booking_contact_phone": row.booking_contact_phone,
        "booking_contact_email": row.booking_contact_email,
        "traveler_slots": [
            {
                "package_id": slot.package_id,
                "traveler_full_name": slot.traveler_full_name,
                "traveler_phone": slot.traveler_phone,
                "traveler_email": slot.traveler_email,
            }
            for slot in row.traveler_slots
        ],
        "opening_payment_amount_inr": row.opening_payment_amount_inr,
        "opening_payment_reference": row.opening_payment_reference,
    }


def _process_booking_import_row(
    *,
    booking_import: BookingImport,
    trip: Trip,
    row: BookingImportRowInput,
    row_number: int,
    actor=None,
    record_opening_payment: OpeningPaymentRecorder,
    reserve_booking: BookingReservationReadiness,
) -> tuple[str, Booking | None, str, str]:
    if not row.traveler_slots:
        return (
            BookingImportRow.Status.SKIPPED,
            None,
            "missing_traveler_slots",
            "At least one Traveler Slot with a Package is required.",
        )
    if not row.booking_contact_name.strip() or not row.booking_contact_phone.strip():
        return (
            BookingImportRow.Status.SKIPPED,
            None,
            "missing_booking_contact",
            "Booking Contact name and phone are required.",
        )

    try:
        with transaction.atomic():
            booking, created = _create_or_update_import_booking(
                trip=trip,
                row=row,
            )
            if row.opening_payment_amount_inr > 0:
                record_opening_payment(
                    booking=booking,
                    booking_import=booking_import,
                    amount_inr=row.opening_payment_amount_inr,
                    payment_reference=row.opening_payment_reference,
                    note=row.opening_payment_note,
                    actor=actor,
                )

            reserve_booking(booking)
            booking.refresh_from_db()
            status = BookingImportRow.Status.CREATED if created else BookingImportRow.Status.UPDATED
            message = (
                "Booking Import row created a Booking."
                if created
                else "Booking Import row updated a Booking."
            )
            return status, booking, "", message
    except ValidationError as exc:
        message = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
        conflict_code = (
            "capacity_conflict" if "Available Seats" in message else "validation_conflict"
        )
        return BookingImportRow.Status.CONFLICT, None, conflict_code, message
    except Booking.DoesNotExist:
        return (
            BookingImportRow.Status.CONFLICT,
            None,
            "missing_booking",
            "Imported Booking was not found for this Trip.",
        )


def _create_or_update_import_booking(
    *,
    trip: Trip,
    row: BookingImportRowInput,
) -> tuple[Booking, bool]:
    intake = prepare_booking_import_intake(
        trip=trip,
        booking_contact_name=row.booking_contact_name,
        booking_contact_phone=row.booking_contact_phone,
        booking_contact_email=row.booking_contact_email,
        traveler_slots=[
            TravelerSlotIntakeInput(
                package_id=slot.package_id,
                traveler_full_name=slot.traveler_full_name,
                traveler_phone=slot.traveler_phone,
                traveler_email=slot.traveler_email,
            )
            for slot in row.traveler_slots
        ],
    )

    if row.booking_id is not None:
        booking = (
            Booking.objects.select_for_update()
            .select_related("trip", "trip__payment_schedule")
            .get(pk=row.booking_id)
        )
        if booking.trip_id != trip.id:
            raise ValidationError("Imported Booking must belong to the Booking Import Trip.")
        if booking.booking_state in {
            Booking.BookingState.CONFIRMED,
            Booking.BookingState.CANCELLED,
            Booking.BookingState.COMPLETED,
        }:
            raise ValidationError("Booking Import can update only Draft or Reserved Bookings.")
        created = False
    else:
        booking = Booking(trip=trip, booking_state=Booking.BookingState.DRAFT)
        created = True

    apply_booking_intake_to_booking(
        booking=booking,
        intake=intake,
        replace_traveler_slots=not created,
    )
    if (
        booking.booking_state == Booking.BookingState.RESERVED
        and active_reserved_traveler_count(trip) > trip.capacity
    ):
        raise ValidationError("Available Seats are no longer sufficient for this Booking.")
    return booking, created


def _record_opening_payment_ledger_event(
    opening_payment_record: OpeningPaymentRecord,
) -> None:
    from trip_payments.financial_ledger import record_financial_ledger_event

    record_financial_ledger_event(opening_payment_record)
