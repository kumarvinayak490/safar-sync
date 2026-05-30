import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from organizer_payments.models import ManualPaymentInstructions
from organizers.models import Organizer
from team_access.models import OrganizerMembership
from trips.booking_availability import public_booking_gate_decision
from trips.models import Trip, TripPackage, TripPaymentSchedule
from trips.payment_method_readiness import PaymentMethodReadinessBlocker

pytestmark = pytest.mark.django_db

PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


@pytest.fixture
def user_factory():
    def create_user(email: str):
        return get_user_model().objects.create_user(
            username=email,
            email=email,
            password="tripos-test-password",
        )

    return create_user


@pytest.fixture
def organizer():
    return Organizer.objects.create(name="Himalayan Monsoon Cohort")


def payment_qr(name: str = "payment-qr.png", content_type: str = "image/png"):
    return SimpleUploadedFile(name, PNG_BYTES, content_type=content_type)


def test_legacy_manual_payment_instructions_import_reexports_domain_owner():
    from organizer_payments.manual_payment_instructions import (
        manual_payment_instructions_payload as domain_payload,
    )
    from organizers.payments.manual_payment_instructions import (
        manual_payment_instructions_payload as legacy_payload,
    )

    assert legacy_payload is domain_payload


def test_owner_can_add_update_and_remove_manual_payment_instructions(
    settings,
    tmp_path,
    user_factory,
    organizer,
):
    settings.MEDIA_ROOT = tmp_path
    owner = user_factory("manual-instructions-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    create_response = client.patch(
        f"/api/organizers/{organizer.id}/manual-payment-instructions/",
        {
            "payment_qr": payment_qr(),
            "upi_id": " trips@example ",
            "account_name": " Field Team Collective ",
            "bank_transfer_details": " IMPS or NEFT to the shared trip account. ",
        },
        format="multipart",
    )
    update_response = client.patch(
        f"/api/organizers/{organizer.id}/manual-payment-instructions/",
        {
            "payment_qr": payment_qr("replacement.png"),
            "upi_id": "newtrips@example",
            "account_name": "Field Team Collective",
            "bank_transfer_details": "Updated bank transfer details.",
        },
        format="multipart",
    )
    status_response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")
    delete_response = client.delete(
        f"/api/organizers/{organizer.id}/manual-payment-instructions/"
    )
    deleted_status_response = client.get(
        f"/api/organizers/{organizer.id}/payment-setup-status/"
    )

    assert create_response.status_code == 200
    assert create_response.json()["ready"] is True
    assert create_response.json()["upi_id"] == "trips@example"
    assert create_response.json()["payment_qr_url"]
    assert update_response.status_code == 200
    assert update_response.json()["original_filename"] == "replacement.png"
    assert update_response.json()["content_type"] == "image/png"
    assert status_response.json()["manual_payment_instructions"]["ready"] is True
    assert (
        status_response.json()["manual_payment_method"]["manual_payment_instructions_ready"]
        is True
    )
    assert status_response.json()["manual_payment_method"]["blocker_code"] == (
        PaymentMethodReadinessBlocker.MANUAL_PAYMENT_AVAILABILITY_CLOSED
    )
    assert delete_response.status_code == 204
    assert ManualPaymentInstructions.objects.filter(organizer=organizer).exists() is False
    assert deleted_status_response.json()["manual_payment_instructions"]["ready"] is False


def test_operator_can_view_manual_payment_instruction_readiness_but_not_edit(
    settings,
    tmp_path,
    user_factory,
    organizer,
):
    settings.MEDIA_ROOT = tmp_path
    owner = user_factory("manual-instructions-owner-view@example.com")
    operator = user_factory("manual-instructions-operator@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    ManualPaymentInstructions.objects.create(
        organizer=organizer,
        payment_qr=payment_qr(),
        original_filename="payment-qr.png",
        content_type="image/png",
        file_size=len(PNG_BYTES),
        upi_id="trips@example",
    )
    client = APIClient()
    client.force_authenticate(operator)

    get_response = client.get(
        f"/api/organizers/{organizer.id}/manual-payment-instructions/"
    )
    status_response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")
    patch_response = client.patch(
        f"/api/organizers/{organizer.id}/manual-payment-instructions/",
        {"upi_id": "operator@example"},
        format="multipart",
    )
    delete_response = client.delete(
        f"/api/organizers/{organizer.id}/manual-payment-instructions/"
    )

    assert get_response.status_code == 200
    assert get_response.json()["ready"] is True
    assert get_response.json()["can_manage"] is False
    assert status_response.status_code == 200
    assert status_response.json()["can_manage_manual_payment_instructions"] is False
    assert status_response.json()["manual_payment_instructions"]["ready"] is True
    assert patch_response.status_code == 403
    assert delete_response.status_code == 403


def test_payment_qr_upload_validates_image_content(settings, tmp_path, user_factory, organizer):
    settings.MEDIA_ROOT = tmp_path
    owner = user_factory("manual-instructions-validation-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/manual-payment-instructions/",
        {
            "payment_qr": SimpleUploadedFile(
                "payment-qr.png",
                b"not an image",
                content_type="image/png",
            ),
        },
        format="multipart",
    )

    assert response.status_code == 400
    assert "payment_qr" in response.json()
    assert ManualPaymentInstructions.objects.filter(organizer=organizer).exists() is False


def test_manual_payment_instructions_feed_method_readiness_without_opening_later_slices(
    settings,
    tmp_path,
    organizer,
):
    settings.MEDIA_ROOT = tmp_path
    ManualPaymentInstructions.objects.create(
        organizer=organizer,
        payment_qr=payment_qr(),
        original_filename="payment-qr.png",
        content_type="image/png",
        file_size=len(PNG_BYTES),
    )
    trip = Trip.objects.create(
        organizer=organizer,
        title="Spiti Winter Field Week",
        start_date="2026-10-10",
        end_date="2026-10-15",
        capacity=24,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
    )

    gate = public_booking_gate_decision(trip)

    assert gate.ready is False
    assert gate.payment_method_readiness.manual_method.manual_payment_instructions_ready is True
    assert gate.payment_method_readiness.manual_method.blocker_code == (
        PaymentMethodReadinessBlocker.MANUAL_PAYMENT_AVAILABILITY_CLOSED
    )


def test_public_trip_page_reads_domain_owned_manual_payment_instructions(
    settings,
    tmp_path,
    organizer,
):
    settings.MEDIA_ROOT = tmp_path
    ManualPaymentInstructions.objects.create(
        organizer=organizer,
        payment_qr=SimpleUploadedFile(
            "payment-qr.png",
            PNG_BYTES,
            content_type="image/png",
        ),
        original_filename="payment-qr.png",
        content_type="image/png",
        file_size=len(PNG_BYTES),
        upi_id="trips@example",
        account_name="Himalayan Monsoon Cohort",
        bank_transfer_details="Bank transfer reference HMC Spiti",
    )
    trip = Trip.objects.create(
        organizer=organizer,
        title="Spiti Winter Field Week",
        slug="spiti-winter-field-week",
        start_date="2026-10-10",
        end_date="2026-10-15",
        capacity=24,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
        manual_payment_availability=Trip.ManualPaymentAvailability.OPEN,
    )
    TripPaymentSchedule.objects.create(trip=trip)
    TripPackage.objects.create(
        trip=trip,
        name="Base camp",
        price_inr=12000,
        reservation_amount_inr=2500,
    )

    response = APIClient().get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    assert response.status_code == 200
    assert response.json()["public_booking_gate"]["manual_payment_method"]["ready"] is True
    assert response.json()["manual_payment_instructions"] == {
        "ready": True,
        "message": "Scan the Payment QR and submit Payment Proof for Organizer review.",
        "payment_qr_url": (
            f"http://testserver/media/payment-qr/organizer-{organizer.id}/payment-qr.png"
        ),
        "upi_id": "trips@example",
        "account_name": "Himalayan Monsoon Cohort",
        "bank_transfer_details": "Bank transfer reference HMC Spiti",
    }
