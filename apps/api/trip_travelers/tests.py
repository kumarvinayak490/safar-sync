from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from organizers.bookings.operations import cancel_traveler as legacy_cancel_traveler
from organizers.bookings.operations import (
    mark_traveler_attendance as legacy_mark_traveler_attendance,
)
from organizers.models import Organizer
from organizers.travelers.readiness import TravelerReadiness as LegacyTravelerReadiness
from organizers.travelers.readiness import (
    submit_traveler_document as legacy_submit_traveler_document,
)
from trip_bookings.intake import create_booking_from_intake, prepare_manual_booking_intake
from trip_bookings.models import Booking
from trip_operations.models import ActivityLog
from trip_travelers.check_in import mark_traveler_attendance
from trip_travelers.documents import (
    record_sensitive_traveler_document_download,
    sensitive_traveler_document_filenames,
    submit_traveler_document,
    traveler_document_state_summary,
)
from trip_travelers.models import TravelerDocument, TravelerSlot
from trip_travelers.readiness import (
    TravelerReadiness,
    confirmation_requirements_for_booking,
    traveler_portal_readiness_payload,
    update_emergency_contact,
    update_medical_disclosure,
    update_travel_logistics,
)
from trip_travelers.slots import (
    TravelerSlotIntakeInput,
    TravelerSlotWorkflow,
    active_reserved_traveler_count,
    available_seats,
    prepare_traveler_slots_intake,
    replace_traveler,
    update_traveler_identity_details,
)
from trips.models import Trip, TripPackage


@pytest.mark.django_db
def test_trip_travelers_prepares_slot_intake_and_validates_package_ownership():
    trip = create_trip_with_packages()
    other_trip = create_trip_with_packages(title="Garhwal Autumn")
    other_package = other_trip.packages.get(name="Base")

    prepared = prepare_traveler_slots_intake(
        trip=trip,
        traveler_slots=[
            TravelerSlotIntakeInput(
                package_id=trip.packages.get(name="Base").id,
                traveler_full_name="  Riya Shah  ",
                traveler_phone="  +919800000101  ",
                traveler_email="  riya@example.com  ",
            )
        ],
        missing_slots_field="traveler_slots",
        missing_slots_message="At least one Traveler Slot with a Package is required.",
        package_ownership_field="traveler_slots",
        package_ownership_message="Every Traveler Slot Package must belong to this Trip.",
        allow_traveler_identity=True,
    )

    assert prepared[0].position == 1
    assert prepared[0].traveler_full_name == "Riya Shah"
    assert prepared[0].traveler_phone == "+919800000101"

    with pytest.raises(ValidationError, match="Every Traveler Slot Package"):
        prepare_traveler_slots_intake(
            trip=trip,
            traveler_slots=[TravelerSlotIntakeInput(package_id=other_package.id)],
            missing_slots_field="traveler_slots",
            missing_slots_message="At least one Traveler Slot with a Package is required.",
            package_ownership_field="traveler_slots",
            package_ownership_message="Every Traveler Slot Package must belong to this Trip.",
            allow_traveler_identity=False,
        )


@pytest.mark.django_db
def test_trip_bookings_create_slots_through_trip_travelers_intake_interface():
    trip = create_trip_with_packages()

    intake = prepare_manual_booking_intake(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        traveler_slots=[
            TravelerSlotIntakeInput(package_id=trip.packages.get(name="Base").id),
            TravelerSlotIntakeInput(package_id=trip.packages.get(name="Plus").id),
        ],
    )
    booking = create_booking_from_intake(
        trip=trip,
        intake=intake,
        booking_state=Booking.BookingState.RESERVED,
    )

    assert booking.traveler_slot_count == 2
    assert booking.booking_total_inr == 92000
    assert list(
        booking.traveler_slots.order_by("position").values_list("position", "package__name")
    ) == [(1, "Base"), (2, "Plus")]
    assert active_reserved_traveler_count(trip) == 2
    assert available_seats(trip) == 10


@pytest.mark.django_db
def test_traveler_identity_update_validation_is_trip_travelers_owned():
    booking = create_reserved_booking()
    traveler_slot = booking.traveler_slots.get()

    with pytest.raises(ValidationError, match="full name"):
        update_traveler_identity_details(
            traveler_slot,
            traveler_full_name=" ",
            traveler_phone="+919876543210",
        )
    with pytest.raises(ValidationError, match="phone number"):
        update_traveler_identity_details(
            traveler_slot,
            traveler_full_name="Asha Nair",
            traveler_phone=" ",
        )

    updated = update_traveler_identity_details(
        traveler_slot,
        traveler_full_name="Asha Nair",
        traveler_phone="+919876543210",
        traveler_email="asha@example.com",
    )

    assert updated.is_traveler is True
    assert updated.traveler_email == "asha@example.com"


@pytest.mark.django_db
def test_traveler_cancellation_releases_capacity_and_legacy_path_stays_compatible():
    booking = create_reserved_booking(capacity=1)
    traveler_slot = booking.traveler_slots.get()
    actor = get_user_model().objects.create_user(
        username="traveler-slot-operator@example.com",
        email="traveler-slot-operator@example.com",
        password="password",
    )

    assert available_seats(booking.trip) == 0

    legacy_cancel_traveler(
        traveler_slot,
        cancellation_reason="Traveler cannot join.",
        actor=actor,
    )

    traveler_slot.refresh_from_db()
    assert traveler_slot.traveler_state == TravelerSlot.TravelerState.CANCELLED
    assert available_seats(booking.trip) == 1
    assert ActivityLog.objects.filter(
        booking=booking,
        traveler_slot=traveler_slot,
        action=ActivityLog.Action.TRAVELER_CANCELLED,
        actor=actor,
    ).exists()


@pytest.mark.django_db
def test_traveler_replacement_preserves_reserved_capacity():
    booking = create_reserved_booking(capacity=1)
    original = booking.traveler_slots.get()
    original.traveler_full_name = "Original Traveler"
    original.traveler_phone = "+919800000111"
    original.save()

    replacement = replace_traveler(
        original,
        traveler_full_name="Replacement Traveler",
        traveler_phone="+919800000222",
    )

    original.refresh_from_db()
    assert original.traveler_state == TravelerSlot.TravelerState.REPLACED
    assert replacement.replaces_slot == original
    assert replacement.booked_package_price_inr == original.booked_package_price_inr
    assert active_reserved_traveler_count(booking.trip) == 1
    assert available_seats(booking.trip) == 0


@pytest.mark.django_db
def test_pending_traveler_addition_counts_capacity_only_after_reservation():
    booking = create_reserved_booking(capacity=2)
    package = booking.trip.packages.get(name="Plus")
    unpaid_workflow = TravelerSlotWorkflow(
        required_amount_to_reserve=lambda _booking: 100,
        collected_amount=lambda _booking: 0,
    )
    paid_workflow = TravelerSlotWorkflow(
        required_amount_to_reserve=lambda _booking: 100,
        collected_amount=lambda _booking: 100,
    )

    pending = unpaid_workflow.add_traveler_to_booking(booking, package=package)

    pending.refresh_from_db()
    assert pending.traveler_state == TravelerSlot.TravelerState.PENDING_ADDITION
    assert active_reserved_traveler_count(booking.trip) == 1
    assert available_seats(booking.trip) == 1

    reserved = paid_workflow.reserve_pending_traveler_additions_if_ready(booking)

    pending.refresh_from_db()
    assert reserved == [pending]
    assert pending.traveler_state == TravelerSlot.TravelerState.ACTIVE
    assert active_reserved_traveler_count(booking.trip) == 2
    assert available_seats(booking.trip) == 0


@pytest.mark.django_db
def test_traveler_document_submission_metadata_and_legacy_readiness_shim():
    booking = create_reserved_booking(requires_traveler_documents=True)
    traveler_slot = booking.traveler_slots.get()
    upload = SimpleUploadedFile(
        "passport.txt",
        b"identity document",
        content_type="text/plain",
    )

    document = submit_traveler_document(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        label="Passport",
        uploaded_file=upload,
    )

    assert legacy_submit_traveler_document is submit_traveler_document
    assert LegacyTravelerReadiness is TravelerReadiness
    assert document.document_state == TravelerDocument.DocumentState.SUBMITTED
    assert document.original_filename == "passport.txt"
    assert document.content_type == "text/plain"
    assert document.file_size == len(b"identity document")
    assert document.is_sensitive_traveler_information is True
    assert document.exclude_from_default_exports is True


@pytest.mark.django_db
def test_traveler_readiness_reports_complete_and_incomplete_states():
    booking = create_reserved_booking(
        requires_traveler_documents=True,
        requires_traveler_identity_details=True,
        requires_travel_logistics=True,
        requires_emergency_contact=True,
        requires_medical_disclosure=True,
    )
    traveler_slot = booking.traveler_slots.get()

    requirements = confirmation_requirements_for_booking(booking)

    assert requirements.ready is False
    assert {requirement.code for requirement in requirements.unmet_requirements} == {
        "traveler_documents",
        "travel_logistics",
        "emergency_contact",
        "medical_disclosure",
    }

    TravelerDocument.objects.create(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        label="Passport",
        document_state=TravelerDocument.DocumentState.APPROVED,
    )
    update_travel_logistics(
        traveler_slot,
        arrival_details="Arriving by train",
        departure_details="Departing by cab",
        pickup_location="Station",
        logistics_note="Vegetarian meal on arrival.",
    )
    update_emergency_contact(
        traveler_slot,
        emergency_contact_name="Maya Nair",
        emergency_contact_phone="+919800000333",
        emergency_contact_relationship="Sister",
    )
    update_medical_disclosure(traveler_slot, medical_disclosure="No known allergies.")
    traveler_slot.refresh_from_db()

    summary = TravelerReadiness().readiness_summary_for_traveler_slot(traveler_slot)
    ready_requirements = confirmation_requirements_for_booking(booking)

    assert summary.ready is True
    assert ready_requirements.ready is True
    assert ready_requirements.unmet_requirements == []


@pytest.mark.django_db
def test_traveler_portal_readiness_payload_tracks_traveler_tasks():
    booking = create_reserved_booking(
        requires_traveler_documents=True,
        requires_traveler_identity_details=True,
        requires_travel_logistics=True,
        requires_emergency_contact=True,
        requires_medical_disclosure=True,
    )
    traveler_slot = booking.traveler_slots.get()

    incomplete_payload = traveler_portal_readiness_payload(traveler_slot)

    assert incomplete_payload == {
        "documents_ready": False,
        "travel_logistics_ready": False,
        "emergency_contact_ready": False,
        "medical_disclosure_ready": False,
        "ready": False,
    }

    TravelerDocument.objects.create(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        label="Passport",
        document_state=TravelerDocument.DocumentState.APPROVED,
    )
    update_travel_logistics(
        traveler_slot,
        arrival_details="Flight UK 123",
        departure_details="Flight UK 456",
        pickup_location="Airport gate 2",
        logistics_note="Arrives early.",
    )
    update_emergency_contact(
        traveler_slot,
        emergency_contact_name="Rohan Shah",
        emergency_contact_phone="+919800000444",
        emergency_contact_relationship="Brother",
    )
    update_medical_disclosure(traveler_slot, medical_disclosure="Carries inhaler.")
    traveler_slot.refresh_from_db()

    assert traveler_portal_readiness_payload(traveler_slot)["ready"] is True


@pytest.mark.django_db
def test_sensitive_traveler_document_filename_helpers_and_download_activity():
    booking = create_reserved_booking()
    traveler_slot = booking.traveler_slots.get()
    actor = get_user_model().objects.create_user(
        username="document-download@example.com",
        email="document-download@example.com",
        password="password",
    )
    identity_document = TravelerDocument.objects.create(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        label="Passport",
        document_state=TravelerDocument.DocumentState.APPROVED,
        file=SimpleUploadedFile("passport.txt", b"identity", content_type="text/plain"),
        original_filename="passport-original.txt",
    )
    TravelerDocument.objects.create(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.ELIGIBILITY,
        label="Permit",
        document_state=TravelerDocument.DocumentState.SUBMITTED,
        file=SimpleUploadedFile("permit.txt", b"permit", content_type="text/plain"),
    )

    state_summary = traveler_document_state_summary(traveler_slot)
    record_sensitive_traveler_document_download(document=identity_document, actor=actor)

    assert state_summary.document_state == TravelerDocument.DocumentState.SUBMITTED
    assert "Passport:identity:approved" in state_summary.document_states
    assert sensitive_traveler_document_filenames(traveler_slot) == ["passport-original.txt"]
    assert ActivityLog.objects.filter(
        booking=booking,
        traveler_slot=traveler_slot,
        traveler_document=identity_document,
        actor=actor,
        action=ActivityLog.Action.SENSITIVE_TRAVELER_INFORMATION_DOWNLOAD,
    ).exists()


@pytest.mark.django_db
def test_traveler_check_in_and_no_show_are_trip_travelers_owned_with_legacy_shim():
    booking = create_reserved_booking()
    traveler_slot = booking.traveler_slots.get()
    actor = get_user_model().objects.create_user(
        username="check-in-operator@example.com",
        email="check-in-operator@example.com",
        password="password",
    )

    checked_in = mark_traveler_attendance(
        traveler_slot,
        attendance_state=TravelerSlot.AttendanceState.CHECKED_IN,
        actor=actor,
    )
    no_show = legacy_mark_traveler_attendance(
        traveler_slot,
        attendance_state=TravelerSlot.AttendanceState.NO_SHOW,
        actor=actor,
    )

    assert checked_in.attendance_state == TravelerSlot.AttendanceState.CHECKED_IN
    assert no_show.attendance_state == TravelerSlot.AttendanceState.NO_SHOW
    assert booking.ledger_entries.count() == 0
    assert ActivityLog.objects.filter(
        booking=booking,
        traveler_slot=traveler_slot,
        actor=actor,
        action=ActivityLog.Action.TRAVELER_CHECKED_IN,
        metadata__prior_attendance_state=TravelerSlot.AttendanceState.NOT_MARKED,
    ).exists()
    assert ActivityLog.objects.filter(
        booking=booking,
        traveler_slot=traveler_slot,
        actor=actor,
        action=ActivityLog.Action.TRAVELER_MARKED_NO_SHOW,
        metadata__prior_attendance_state=TravelerSlot.AttendanceState.CHECKED_IN,
    ).exists()


def create_trip_with_packages(
    *,
    title: str = "Spiti Summer",
    capacity: int = 12,
    **trip_kwargs,
) -> Trip:
    organizer = Organizer.objects.create(name=f"{title} Collective")
    trip = Trip.objects.create(
        organizer=organizer,
        title=title,
        start_date=date(2026, 7, 10),
        end_date=date(2026, 7, 16),
        capacity=capacity,
        **trip_kwargs,
    )
    TripPackage.objects.create(
        trip=trip,
        name="Base",
        price_inr=40000,
        reservation_amount_inr=10000,
        position=1,
    )
    TripPackage.objects.create(
        trip=trip,
        name="Plus",
        price_inr=52000,
        reservation_amount_inr=12000,
        position=2,
    )
    return trip


def create_reserved_booking(*, capacity: int = 12, **trip_kwargs) -> Booking:
    trip = create_trip_with_packages(capacity=capacity, **trip_kwargs)
    package = trip.packages.get(name="Base")
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(
        booking=booking,
        package=package,
        position=1,
        traveler_full_name="Asha Nair",
        traveler_phone="+919876543210",
    )
    return booking
