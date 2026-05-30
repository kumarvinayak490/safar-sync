from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from trip_bookings.models import Booking
from trip_travelers.models import TravelerSlot
from trip_travelers.slots import (
    PRE_PAYMENT_TRAVELER_IDENTITY_MESSAGE as PRE_PAYMENT_TRAVELER_IDENTITY_MESSAGE,
)
from trip_travelers.slots import (
    TravelerSlotIntake,
    TravelerSlotIntakeInput,
    create_traveler_slots_for_booking,
    prepare_traveler_slots_intake,
    reject_pre_payment_traveler_identity_details,
    replace_traveler_slots_for_booking,
)
from trips.models import Trip


@dataclass(frozen=True)
class BookingContactIntake:
    name: str
    phone: str
    email: str = ""


@dataclass(frozen=True)
class BookingIntake:
    contact: BookingContactIntake
    traveler_slots: tuple[TravelerSlotIntake, ...]

    @property
    def traveler_count(self) -> int:
        return len(self.traveler_slots)

    @property
    def package_ids(self) -> list[int]:
        return [slot.package.id for slot in self.traveler_slots]


def prepare_public_booking_intake(
    *,
    trip: Trip,
    booking_contact_name: str,
    booking_contact_phone: str,
    booking_contact_email: str = "",
    selected_package_id: int | None = None,
    traveler_count: int | None = None,
    traveler_slots: Sequence[TravelerSlotIntakeInput] | None = None,
    explicit_traveler_slots_supplied: bool = False,
    initial_data: Mapping | None = None,
) -> BookingIntake:
    reject_pre_payment_traveler_identity_details(initial_data)
    selected_slots = _selected_public_traveler_slots(
        selected_package_id=selected_package_id,
        traveler_count=traveler_count,
        traveler_slots=traveler_slots or (),
        explicit_traveler_slots_supplied=explicit_traveler_slots_supplied,
    )
    return prepare_booking_intake(
        trip=trip,
        booking_contact_name=booking_contact_name,
        booking_contact_phone=booking_contact_phone,
        booking_contact_email=booking_contact_email,
        traveler_slots=selected_slots,
        missing_slots_field="traveler_count",
        missing_slots_message=(
            "Traveler count and Package are required before reservation payment."
        ),
        package_ownership_field="package",
        package_ownership_message="Every selected Package must belong to this Trip.",
        allow_traveler_identity=False,
    )


def prepare_manual_booking_intake(
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
        allow_traveler_identity=False,
    )


def create_booking_from_intake(
    *,
    trip: Trip,
    intake: BookingIntake,
    booking_state: str = Booking.BookingState.DRAFT,
) -> Booking:
    with transaction.atomic():
        booking = Booking.objects.create(
            trip=trip,
            booking_state=booking_state,
            booking_contact_name=intake.contact.name,
            booking_contact_phone=intake.contact.phone,
            booking_contact_email=intake.contact.email,
        )
        create_traveler_slots_from_intake(booking=booking, intake=intake)
    return booking


def apply_booking_intake_to_booking(
    *,
    booking: Booking,
    intake: BookingIntake,
    replace_traveler_slots: bool = False,
) -> Booking:
    booking.booking_contact_name = intake.contact.name
    booking.booking_contact_phone = intake.contact.phone
    booking.booking_contact_email = intake.contact.email
    booking.save()

    if replace_traveler_slots:
        replace_traveler_slots_for_booking(
            booking=booking,
            traveler_slots=intake.traveler_slots,
        )
    elif not booking.traveler_slots.exists():
        create_traveler_slots_from_intake(booking=booking, intake=intake)
    return booking


def create_traveler_slots_from_intake(
    *,
    booking: Booking,
    intake: BookingIntake,
) -> list[TravelerSlot]:
    return create_traveler_slots_for_booking(
        booking=booking,
        traveler_slots=intake.traveler_slots,
    )


def prepare_booking_intake(
    *,
    trip: Trip,
    booking_contact_name: str,
    booking_contact_phone: str,
    booking_contact_email: str,
    traveler_slots: Sequence[TravelerSlotIntakeInput],
    missing_slots_field: str,
    missing_slots_message: str,
    package_ownership_field: str,
    package_ownership_message: str,
    allow_traveler_identity: bool,
) -> BookingIntake:
    contact = normalize_booking_contact(
        booking_contact_name=booking_contact_name,
        booking_contact_phone=booking_contact_phone,
        booking_contact_email=booking_contact_email,
    )
    prepared_slots = prepare_traveler_slots_intake(
        trip=trip,
        traveler_slots=traveler_slots,
        missing_slots_field=missing_slots_field,
        missing_slots_message=missing_slots_message,
        package_ownership_field=package_ownership_field,
        package_ownership_message=package_ownership_message,
        allow_traveler_identity=allow_traveler_identity,
    )

    return BookingIntake(contact=contact, traveler_slots=prepared_slots)


def normalize_booking_contact(
    *,
    booking_contact_name: str,
    booking_contact_phone: str,
    booking_contact_email: str = "",
) -> BookingContactIntake:
    name = _normalize_booking_contact_text(booking_contact_name)
    phone = _normalize_booking_contact_text(booking_contact_phone)
    email = _normalize_booking_contact_text(booking_contact_email)
    if not name or not phone:
        raise ValidationError({"booking_contact": "Booking Contact name and phone are required."})
    return BookingContactIntake(name=name, phone=phone, email=email)


def _selected_public_traveler_slots(
    *,
    selected_package_id: int | None,
    traveler_count: int | None,
    traveler_slots: Sequence[TravelerSlotIntakeInput],
    explicit_traveler_slots_supplied: bool,
) -> Sequence[TravelerSlotIntakeInput]:
    if selected_package_id is not None or traveler_count is not None:
        if selected_package_id is None:
            raise ValidationError({"package": "Select a Package before reservation payment."})
        if traveler_count is None:
            raise ValidationError(
                {"traveler_count": "Enter Traveler count before reservation payment."}
            )
        if traveler_slots:
            raise ValidationError(
                {"traveler_slots": "Use Traveler count and Package for public draft intake."}
            )
        return [TravelerSlotIntakeInput(package_id=selected_package_id)] * traveler_count

    if explicit_traveler_slots_supplied and not traveler_slots:
        raise ValidationError(
            {"traveler_slots": "At least one Traveler Slot with a Package is required."}
        )
    return traveler_slots


def _normalize_booking_contact_text(value: str | None) -> str:
    return (value or "").strip()
