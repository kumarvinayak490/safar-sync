from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.utils import timezone
from rest_framework.test import APIClient

from organizers.models import Organizer
from team_access.models import OrganizerMembership
from trip_bookings.access_links import (
    issue_booking_access_link,
    issue_traveler_access_link,
    resolve_active_access_link,
    traveler_slot_for_access_link,
)
from trip_bookings.imports import (
    BookingImportRowInput,
    BookingImportTravelerSlotInput,
    create_booking_import,
)
from trip_bookings.intake import (
    TravelerSlotIntakeInput,
    create_booking_from_intake,
    prepare_manual_booking_intake,
)
from trip_bookings.lifecycle import (
    BookingLifecycleWorkflow,
    cancel_booking,
    confirm_booking,
    unconfirm_booking,
)
from trip_bookings.models import Booking, BookingAccessLink, BookingImport, BookingImportRow
from trip_operations.models import ActivityLog
from trip_payments.models import LedgerEntry, OpeningPaymentRecord
from trip_travelers.models import TravelerSlot
from trips.models import Trip, TripPackage


@pytest.mark.django_db
def test_trip_bookings_manual_booking_creation_normalizes_contact_and_creates_slots():
    trip = create_trip_with_packages()

    intake = prepare_manual_booking_intake(
        trip=trip,
        booking_contact_name="  Asha Nair  ",
        booking_contact_phone="  +919876543210  ",
        booking_contact_email="  asha@example.com  ",
        traveler_slots=[
            TravelerSlotIntakeInput(package_id=trip.packages.get(name="Base").id),
            TravelerSlotIntakeInput(package_id=trip.packages.get(name="Plus").id),
        ],
    )
    booking = create_booking_from_intake(
        trip=trip,
        intake=intake,
        booking_state=Booking.BookingState.DRAFT,
    )

    assert booking.booking_contact_name == "Asha Nair"
    assert booking.booking_contact_phone == "+919876543210"
    assert booking.booking_contact_email == "asha@example.com"
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert list(
        booking.traveler_slots.order_by("position").values_list(
            "position",
            "package__name",
            "traveler_full_name",
        )
    ) == [(1, "Base", ""), (2, "Plus", "")]


@pytest.mark.django_db
def test_trip_bookings_booking_state_transitions_are_lifecycle_owned():
    booking = create_reserved_booking()

    confirmed = confirm_booking(booking)
    assert confirmed.booking_state == Booking.BookingState.CONFIRMED

    unconfirmed = unconfirm_booking(confirmed)
    assert unconfirmed.booking_state == Booking.BookingState.RESERVED

    with pytest.raises(ValidationError, match="Booking Cancellation requires Cancellation Reason"):
        cancel_booking(unconfirmed, cancellation_reason="")

    actor = get_user_model().objects.create_user(
        username="operator@example.com",
        email="operator@example.com",
        password="password",
    )
    cancelled = cancel_booking(
        unconfirmed,
        cancellation_reason="Traveler cannot join.",
        actor=actor,
    )

    assert cancelled.booking_state == Booking.BookingState.CANCELLED
    activity = ActivityLog.objects.get(
        booking=cancelled,
        action=ActivityLog.Action.BOOKING_CANCELLED,
    )
    assert activity.actor == actor
    assert activity.metadata == {"cancellation_reason": "Traveler cannot join."}


@pytest.mark.django_db
def test_trip_bookings_booking_lifecycle_state_guards_remain_distinct_from_payment_state():
    booking = create_reserved_booking()
    booking.booking_state = Booking.BookingState.DRAFT
    booking.save(update_fields=["booking_state", "updated_at"])

    with pytest.raises(ValidationError, match="Only Reserved Bookings can be confirmed"):
        BookingLifecycleWorkflow().confirm_booking(booking)

    booking.booking_state = Booking.BookingState.CANCELLED
    booking.save(update_fields=["booking_state", "updated_at"])

    with pytest.raises(ValidationError, match="Only Confirmed Bookings can be unconfirmed"):
        BookingLifecycleWorkflow().unconfirm_booking(booking)


@pytest.mark.django_db
def test_booking_contact_change_revokes_booking_level_access_links_only():
    booking = create_reserved_booking()
    booking_link = BookingAccessLink.objects.create(
        booking=booking,
        scope=BookingAccessLink.Scope.BOOKING,
        token_digest="booking-link-digest",
    )
    traveler_link = BookingAccessLink.objects.create(
        booking=booking,
        traveler_slot=booking.traveler_slots.get(),
        scope=BookingAccessLink.Scope.TRAVELER,
        token_digest="traveler-link-digest",
    )

    booking.booking_contact_name = "New Coordinator"
    booking.booking_contact_phone = "+918888888888"
    booking.save(update_fields=["booking_contact_name", "booking_contact_phone", "updated_at"])

    booking_link.refresh_from_db()
    traveler_link.refresh_from_db()
    assert booking_link.revoked_at is not None
    assert traveler_link.revoked_at is None


@pytest.mark.django_db
def test_trip_bookings_booking_import_creates_booking_and_result_summary(monkeypatch):
    monkeypatch.setattr(
        "organizers.services.send_reservation_acknowledgement",
        lambda *args, **kwargs: [],
    )
    trip = create_trip_with_packages()
    package = trip.packages.get(name="Base")

    booking_import = create_booking_import(
        trip=trip,
        rows=[
            BookingImportRowInput(
                booking_contact_name="  Imported Contact  ",
                booking_contact_phone="  +919800000001  ",
                booking_contact_email="  imported@example.com  ",
                traveler_slots=[
                    BookingImportTravelerSlotInput(
                        package_id=package.id,
                        traveler_full_name="  Riya Shah  ",
                        traveler_phone="  +919800000101  ",
                        traveler_email="  riya@example.com  ",
                    )
                ],
                opening_payment_amount_inr=package.reservation_amount_inr,
                opening_payment_reference="sheet-row-1",
                opening_payment_note="Collected before TripOS onboarding.",
            )
        ],
        source_filename="pilot-import.csv",
    )

    booking = Booking.objects.get(booking_contact_name="Imported Contact")
    row = booking_import.rows.get()
    slot = booking.traveler_slots.get()
    opening_record = OpeningPaymentRecord.objects.get(booking=booking)
    ledger_entry = LedgerEntry.objects.get(opening_payment_record=opening_record)
    assert booking_import.status == BookingImport.Status.COMPLETED
    assert booking_import.created_count == 1
    assert booking_import.updated_count == 0
    assert booking_import.skipped_count == 0
    assert booking_import.conflict_count == 0
    assert row.status == BookingImportRow.Status.CREATED
    assert row.booking == booking
    assert booking.booking_contact_phone == "+919800000001"
    assert booking.booking_contact_email == "imported@example.com"
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert slot.traveler_full_name == "Riya Shah"
    assert slot.traveler_phone == "+919800000101"
    assert slot.traveler_email == "riya@example.com"
    assert opening_record.payment_reference == "sheet-row-1"
    assert ledger_entry.entry_type == LedgerEntry.EntryType.OPENING_PAYMENT_RECORD


@pytest.mark.django_db
def test_trip_bookings_booking_import_records_invalid_rows_without_side_effects():
    trip = create_trip_with_packages()

    booking_import = create_booking_import(
        trip=trip,
        rows=[
            BookingImportRowInput(
                booking_contact_name="Missing Slots",
                booking_contact_phone="+919800000002",
                traveler_slots=[],
            ),
            BookingImportRowInput(
                booking_contact_name="Wrong Package",
                booking_contact_phone="+919800000003",
                traveler_slots=[BookingImportTravelerSlotInput(package_id=999999)],
            ),
        ],
    )

    rows = list(booking_import.rows.order_by("row_number"))
    assert booking_import.status == BookingImport.Status.COMPLETED_WITH_CONFLICTS
    assert booking_import.created_count == 0
    assert booking_import.updated_count == 0
    assert booking_import.skipped_count == 1
    assert booking_import.conflict_count == 1
    assert rows[0].status == BookingImportRow.Status.SKIPPED
    assert rows[0].conflict_code == "missing_traveler_slots"
    assert rows[1].status == BookingImportRow.Status.CONFLICT
    assert rows[1].conflict_code == "validation_conflict"
    assert Booking.objects.filter(trip=trip).count() == 0
    assert OpeningPaymentRecord.objects.count() == 0


@pytest.mark.django_db
def test_legacy_booking_import_api_accepts_csv_and_returns_result_summary():
    user = get_user_model().objects.create_user(
        username="booking-import-operator@example.com",
        email="booking-import-operator@example.com",
        password="password",
    )
    trip = create_trip_with_packages()
    OrganizerMembership.objects.create(
        user=user,
        organizer=trip.organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    package = trip.packages.get(name="Base")
    csv_upload = SimpleUploadedFile(
        "bookings.csv",
        (
            "booking_contact_name,booking_contact_phone,package_id,"
            "traveler_full_name,traveler_phone,opening_payment_amount_inr\n"
            f"CSV Contact,+919800000004,{package.id},CSV Traveler,+919800000104,0\n"
        ).encode(),
        content_type="text/csv",
    )
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        f"/api/operations/organizers/{trip.organizer_id}/trips/{trip.id}/booking-imports/",
        {"file": csv_upload},
        format="multipart",
    )

    payload = response.json()
    assert response.status_code == 201, payload
    assert payload["source_filename"] == "bookings.csv"
    assert payload["created_count"] == 1
    assert payload["conflict_count"] == 0
    assert payload["rows"][0]["status"] == BookingImportRow.Status.CREATED
    assert Booking.objects.filter(
        trip=trip,
        booking_contact_name="CSV Contact",
        traveler_slots__traveler_full_name="CSV Traveler",
    ).exists()


@pytest.mark.django_db
def test_trip_bookings_owns_booking_access_link_creation_and_expiry_window():
    booking = create_reserved_booking()
    before_issue = timezone.now()

    issued = issue_booking_access_link(booking)

    assert issued.access_link.booking == booking
    assert issued.access_link.scope == BookingAccessLink.Scope.BOOKING
    assert issued.access_link.traveler_slot is None
    assert issued.access_link.token_digest != issued.token
    assert len(issued.access_link.token_digest) == 64
    assert before_issue + timedelta(days=13, hours=23, minutes=59) <= (
        issued.access_link.expires_at
    )
    assert issued.access_link.expires_at <= before_issue + timedelta(days=14, minutes=1)
    assert resolve_active_access_link(issued.token) == issued.access_link


@pytest.mark.django_db
def test_trip_bookings_rejects_invalid_expired_and_revoked_access_link_tokens():
    booking = create_reserved_booking()
    first = issue_booking_access_link(booking)
    second = issue_booking_access_link(booking)

    with pytest.raises(ValidationError, match="invalid"):
        resolve_active_access_link("not-a-real-token")
    with pytest.raises(ValidationError, match="revoked"):
        resolve_active_access_link(first.token)

    second.access_link.expires_at = timezone.now() - timedelta(minutes=1)
    second.access_link.save(update_fields=["expires_at", "updated_at"])
    with pytest.raises(ValidationError, match="expired"):
        resolve_active_access_link(second.token)


@pytest.mark.django_db
def test_trip_bookings_validates_traveler_flow_access_scope():
    booking = create_reserved_booking()
    first_slot = booking.traveler_slots.get()
    second_slot = TravelerSlot.objects.create(
        booking=booking,
        package=first_slot.package,
        position=2,
    )

    booking_link = issue_booking_access_link(booking)
    traveler_link = issue_traveler_access_link(first_slot)

    assert traveler_slot_for_access_link(booking_link.access_link, second_slot.id) == second_slot
    assert traveler_slot_for_access_link(traveler_link.access_link, first_slot.id) == first_slot
    with pytest.raises(ValidationError, match="only one Traveler"):
        traveler_slot_for_access_link(traveler_link.access_link, second_slot.id)
    with pytest.raises(Http404):
        traveler_slot_for_access_link(booking_link.access_link, second_slot.id + 1000)


def create_trip_with_packages() -> Trip:
    organizer = Organizer.objects.create(name="Safar Collective")
    trip = Trip.objects.create(
        organizer=organizer,
        title="Spiti Summer",
        start_date=date(2026, 7, 10),
        end_date=date(2026, 7, 16),
        capacity=12,
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


def create_reserved_booking() -> Booking:
    trip = create_trip_with_packages()
    package = trip.packages.get(name="Base")
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=booking, package=package, position=1)
    return booking
