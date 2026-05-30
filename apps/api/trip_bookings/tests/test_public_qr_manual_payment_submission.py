from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from organizers.models import (
    Booking,
    LedgerEntry,
    ManualPayment,
    ManualPaymentInstructions,
    Organizer,
    SeatHold,
    Trip,
    TripPackage,
    TripPaymentSchedule,
)
from trip_bookings.lifecycle import active_reserved_traveler_count, available_seats

pytestmark = pytest.mark.django_db

PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


def test_public_qr_submission_creates_draft_booking_and_submitted_manual_payment():
    trip, package = create_manual_ready_trip(reservation_amount_inr=3500)

    response = post_public_qr_submission(trip, package, traveler_count=2)

    assert response.status_code == 201, response.json()
    booking = Booking.objects.get()
    manual_payment = ManualPayment.objects.get()
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert booking.traveler_slot_count == 2
    assert booking.booking_reservation_amount_inr == 7000
    assert manual_payment.booking == booking
    assert manual_payment.source == ManualPayment.Source.TRAVELER_SUBMITTED
    assert manual_payment.status == ManualPayment.Status.SUBMITTED
    assert manual_payment.amount_inr == 7000
    assert manual_payment.payment_reference == "upi-ref-101"
    assert manual_payment.payment_proof
    assert response.json()["booking"] == booking.id
    assert response.json()["amount_inr"] == 7000


def test_public_qr_submission_creates_no_seat_hold_ledger_entry_or_reserved_seats():
    trip, package = create_manual_ready_trip(capacity=4, reservation_amount_inr=3000)

    response = post_public_qr_submission(trip, package, traveler_count=3)

    assert response.status_code == 201, response.json()
    booking = Booking.objects.get()
    assert SeatHold.objects.count() == 0
    assert LedgerEntry.objects.count() == 0
    assert active_reserved_traveler_count(trip) == 0
    assert available_seats(trip) == 4
    assert booking.booking_state == Booking.BookingState.DRAFT


def test_public_qr_submission_requires_payment_proof():
    trip, package = create_manual_ready_trip()

    response = post_public_qr_submission(trip, package, payment_proof=None)

    assert response.status_code == 400
    assert Booking.objects.count() == 0
    assert ManualPayment.objects.count() == 0


def test_public_qr_submission_rejects_invalid_package():
    trip, _package = create_manual_ready_trip()

    response = post_public_qr_submission(trip, package_id=999999)

    assert response.status_code == 400
    assert Booking.objects.count() == 0
    assert ManualPayment.objects.count() == 0


def test_public_qr_submission_rejects_withdrawn_package():
    trip, package = create_manual_ready_trip()
    package.lifecycle_state = TripPackage.LifecycleState.WITHDRAWN
    package.save()

    response = post_public_qr_submission(trip, package)

    assert response.status_code == 400
    assert Booking.objects.count() == 0
    assert ManualPayment.objects.count() == 0


def test_public_qr_submission_rejects_insufficient_capacity():
    trip, package = create_manual_ready_trip(capacity=1)

    response = post_public_qr_submission(trip, package, traveler_count=2)

    assert response.status_code == 400
    assert response.json()["public_booking_gate"]["reason_code"] == "insufficient_capacity"
    assert Booking.objects.count() == 0
    assert ManualPayment.objects.count() == 0


def test_public_qr_submission_rejects_closed_booking_availability():
    trip, package = create_manual_ready_trip(
        booking_availability=Trip.BookingAvailability.CLOSED
    )

    response = post_public_qr_submission(trip, package)

    assert response.status_code == 400
    assert response.json()["public_booking_gate"]["reason_code"] == "booking_closed"
    assert Booking.objects.count() == 0
    assert ManualPayment.objects.count() == 0


def test_public_qr_submission_rejects_missing_manual_payment_instructions():
    trip, package = create_manual_ready_trip()
    trip.organizer.manual_payment_instructions.delete()

    response = post_public_qr_submission(trip, package)

    assert response.status_code == 400
    assert (
        response.json()["manual_payment_method"]["blocker_code"]
        == "manual_payment_instructions_missing"
    )
    assert Booking.objects.count() == 0
    assert ManualPayment.objects.count() == 0


def test_public_qr_submission_rejects_closed_manual_payment_availability():
    trip, package = create_manual_ready_trip(
        manual_payment_availability=Trip.ManualPaymentAvailability.CLOSED
    )

    response = post_public_qr_submission(trip, package)

    assert response.status_code == 400
    assert (
        response.json()["manual_payment_method"]["blocker_code"]
        == "manual_payment_availability_closed"
    )
    assert Booking.objects.count() == 0
    assert ManualPayment.objects.count() == 0


def create_manual_ready_trip(
    *,
    capacity=8,
    reservation_amount_inr=2500,
    booking_availability=Trip.BookingAvailability.OPEN,
    manual_payment_availability=Trip.ManualPaymentAvailability.OPEN,
):
    organizer = Organizer.objects.create(name="Public QR Organizer")
    ManualPaymentInstructions.objects.create(
        organizer=organizer,
        payment_qr=SimpleUploadedFile("payment-qr.png", PNG_BYTES, content_type="image/png"),
        original_filename="payment-qr.png",
        content_type="image/png",
        file_size=len(PNG_BYTES),
        upi_id="tripos@upi",
    )
    trip = Trip.objects.create(
        organizer=organizer,
        title="Western Ghats Public QR",
        start_date=date(2026, 8, 20),
        end_date=date(2026, 8, 24),
        capacity=capacity,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=booking_availability,
        manual_payment_availability=manual_payment_availability,
    )
    TripPaymentSchedule.objects.create(trip=trip)
    package = TripPackage.objects.create(
        trip=trip,
        name="Base camp",
        price_inr=12000,
        reservation_amount_inr=reservation_amount_inr,
    )
    return trip, package


def post_public_qr_submission(
    trip,
    package=None,
    *,
    package_id=None,
    traveler_count=1,
    payment_proof=True,
):
    proof_file = (
        SimpleUploadedFile("payment-proof.png", PNG_BYTES, content_type="image/png")
        if payment_proof
        else None
    )
    data = {
        "booking_contact_name": "Asha Rao",
        "booking_contact_phone": "+919999000111",
        "booking_contact_email": "asha@example.com",
        "traveler_count": traveler_count,
        "package": package_id if package_id is not None else package.id,
        "payment_reference": "upi-ref-101",
    }
    if proof_file is not None:
        data["payment_proof"] = proof_file

    return APIClient().post(
        f"/api/public/trips/{trip.organizer.slug}/{trip.slug}/manual-payments/",
        data,
        format="multipart",
    )
