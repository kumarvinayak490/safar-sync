import pytest

from organizer_payments.provider_credentials import SensitiveProviderCredentialStore
from organizer_payments.setup_records import ensure_payment_setup_records
from organizers.models import (
    Booking,
    ManualPaymentInstructions,
    Organizer,
    PayoutAccount,
    ProviderPaymentSetup,
    SensitiveProviderCredential,
    TravelerSlot,
    Trip,
    TripPackage,
)
from trips.booking_availability import public_booking_gate_decision
from trips.payment_method_readiness import (
    ManualPaymentMethodReadinessFacts,
    PaymentMethod,
    PaymentMethodReadinessBlocker,
    manual_payment_method_readiness,
    payment_method_readiness_for_trip,
)

pytestmark = pytest.mark.django_db


def test_public_booking_readiness_is_ready_with_razorpay_online_payments():
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    trip = create_public_open_trip(organizer)
    mark_online_payment_ready(organizer)

    gate = public_booking_gate_decision(trip)
    provider_method = gate.payment_method_readiness.provider_method
    manual_method = gate.payment_method_readiness.manual_method

    assert gate.ready is True
    assert gate.reason_code == "ready"
    assert gate.online_payment_readiness_ready is True
    assert gate.payment_method_readiness_ready is True
    assert provider_method.id == PaymentMethod.PROVIDER_PAYMENTS
    assert provider_method.ready is True
    assert provider_method.online_payment_readiness_ready is True
    assert manual_method.id == PaymentMethod.QR_MANUAL_PAYMENTS
    assert manual_method.ready is False
    assert manual_method.blocker_code == (
        PaymentMethodReadinessBlocker.MANUAL_PAYMENT_INSTRUCTIONS_MISSING
    )


def test_public_booking_readiness_is_blocked_when_no_payment_method_is_ready():
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    trip = create_public_open_trip(organizer)

    gate = public_booking_gate_decision(trip)
    payload = gate.to_payload()

    assert gate.ready is False
    assert gate.reason_code == "payment_method_readiness_missing"
    assert gate.online_payment_readiness_ready is False
    assert gate.payment_method_readiness_ready is False
    assert payload["ready_payment_method_count"] == 0
    assert payload["ready_payment_method_ids"] == []
    assert [method["id"] for method in payload["payment_methods"]] == [
        PaymentMethod.PROVIDER_PAYMENTS,
        PaymentMethod.QR_MANUAL_PAYMENTS,
    ]
    assert payload["provider_payment_method"]["ready"] is False
    assert payload["manual_payment_method"]["ready"] is False
    assert payload["manual_payment_method"]["blocker_code"] == (
        "manual_payment_instructions_missing"
    )


def test_public_booking_readiness_is_ready_with_qr_manual_payments():
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    ManualPaymentInstructions.objects.create(
        organizer=organizer,
        payment_qr="manual-payment-qr/payment-qr.png",
        original_filename="payment-qr.png",
        content_type="image/png",
        file_size=128,
    )
    trip = create_public_open_trip(organizer)
    trip.manual_payment_availability = Trip.ManualPaymentAvailability.OPEN
    trip.save(update_fields=["manual_payment_availability", "updated_at"])

    gate = public_booking_gate_decision(trip)
    payload = gate.to_payload()

    assert gate.ready is True
    assert gate.reason_code == "ready"
    assert gate.payment_method_readiness_ready is True
    assert payload["ready_payment_method_ids"] == [PaymentMethod.QR_MANUAL_PAYMENTS]
    assert payload["provider_payment_method"]["ready"] is False
    assert payload["manual_payment_method"]["ready"] is True
    assert payload["manual_payment_method"]["manual_payment_instructions_ready"] is True
    assert payload["manual_payment_method"]["manual_payment_availability_open"] is True


def test_public_booking_gate_reports_sold_out_before_payment_method_blockers():
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    trip = create_public_open_trip(organizer, capacity=1)
    reserve_travelers(trip, count=1)

    gate = public_booking_gate_decision(trip)

    assert gate.ready is False
    assert gate.reason_code == "sold_out"
    assert gate.payment_method_readiness_ready is False
    assert gate.capacity_available is False


def test_public_booking_gate_reports_insufficient_capacity_before_payment_method_blockers():
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    trip = create_public_open_trip(organizer)
    trip.capacity = 1
    trip.save(update_fields=["capacity", "updated_at"])

    gate = public_booking_gate_decision(trip, requested_seats=2)

    assert gate.ready is False
    assert gate.reason_code == "insufficient_capacity"
    assert gate.payment_method_readiness_ready is False
    assert gate.capacity_available is False


def test_method_level_status_normalization_keeps_manual_path_blocked_until_prerequisites():
    manual_missing_instructions = manual_payment_method_readiness(
        ManualPaymentMethodReadinessFacts(
            manual_payment_instructions_present=False,
            manual_payment_availability_open=True,
            booking_availability_open=True,
            capacity_available=True,
        )
    )
    manual_closed_for_trip = manual_payment_method_readiness(
        ManualPaymentMethodReadinessFacts(
            manual_payment_instructions_present=True,
            manual_payment_availability_open=False,
            booking_availability_open=True,
            capacity_available=True,
        )
    )
    manual_ready = manual_payment_method_readiness(
        ManualPaymentMethodReadinessFacts(
            manual_payment_instructions_present=True,
            manual_payment_availability_open=True,
            booking_availability_open=True,
            capacity_available=True,
        )
    )

    assert manual_missing_instructions.to_payload() == {
        "id": "qr_manual_payments",
        "label": "Manual Payments",
        "method_type": "qr_manual_payment",
        "ready": False,
        "status_label": "Blocked",
        "blocker_code": "manual_payment_instructions_missing",
        "blocker_label": "Manual Payment Instructions missing",
        "message": (
            "Manual Payments require Manual Payment Instructions before travelers can scan "
            "a Payment QR."
        ),
        "action_label": "Scan QR code to pay",
        "provider": "",
        "provider_label": "",
        "online_payment_readiness_ready": None,
        "manual_payment_instructions_ready": False,
        "manual_payment_availability_open": True,
        "requires_review": True,
    }
    assert manual_closed_for_trip.blocker_code == "manual_payment_availability_closed"
    assert manual_ready.ready is True
    assert manual_ready.status_label == "Ready"
    assert manual_ready.to_payload()["action_label"] == "Scan QR code to pay"


def test_qr_manual_payments_require_open_booking_availability():
    manual_booking_closed = manual_payment_method_readiness(
        ManualPaymentMethodReadinessFacts(
            manual_payment_instructions_present=True,
            manual_payment_availability_open=True,
            booking_availability_open=False,
            capacity_available=True,
        )
    )

    assert manual_booking_closed.ready is False
    assert manual_booking_closed.blocker_code == (
        PaymentMethodReadinessBlocker.BOOKING_AVAILABILITY_CLOSED
    )


def test_payment_method_readiness_payload_exposes_method_summary():
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    trip = create_public_open_trip(organizer)
    mark_online_payment_ready(organizer)

    payload = payment_method_readiness_for_trip(
        trip,
        capacity_available=True,
    ).to_payload()

    assert payload["payment_method_readiness_ready"] is True
    assert payload["payment_method_readiness_status_label"] == "Ready"
    assert payload["ready_payment_method_count"] == 1
    assert payload["ready_payment_method_ids"] == [PaymentMethod.PROVIDER_PAYMENTS]
    assert payload["provider_payment_method"]["online_payment_readiness_ready"] is True
    assert payload["manual_payment_method"]["manual_payment_instructions_ready"] is False


def create_public_open_trip(organizer: Organizer, *, capacity: int = 24) -> Trip:
    return Trip.objects.create(
        organizer=organizer,
        title="Spiti Winter Field Week",
        start_date="2026-10-10",
        end_date="2026-10-15",
        capacity=capacity,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
    )


def reserve_travelers(trip: Trip, *, count: int) -> None:
    package = TripPackage.objects.create(
        trip=trip,
        name="Standard shared room",
        price_inr=32000,
        reservation_amount_inr=8000,
    )
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Rahul Menon",
        booking_contact_phone="+919123456789",
        booking_state=Booking.BookingState.RESERVED,
    )
    for position in range(1, count + 1):
        TravelerSlot.objects.create(booking=booking, package=package, position=position)


def mark_online_payment_ready(organizer: Organizer) -> None:
    ensure_payment_setup_records(organizer)
    organizer.payout_account.status = PayoutAccount.Status.ACTIVE
    organizer.payout_account.save()
    setup = organizer.provider_payment_setup
    setup.status = ProviderPaymentSetup.Status.COMPLETE
    setup.authorization_state = ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    setup.provider_verification_status = ProviderPaymentSetup.ProviderVerificationStatus.VERIFIED
    setup.provider_payment_capability_enabled = True
    setup.provider_connection_state = ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    setup.provider_mode = ProviderPaymentSetup.ProviderMode.LIVE
    setup.provider_merchant_reference = f"acct_razorpay_{organizer.id}"
    setup.save()
    SensitiveProviderCredentialStore().store_oauth_credentials(
        organizer=organizer,
        access_token=f"oauth_access_token_{organizer.id}",
        refresh_token=f"oauth_refresh_token_{organizer.id}",
        provider_account_reference=setup.provider_merchant_reference,
        public_token=f"rzp_public_{organizer.id}",
        provider_mode=ProviderPaymentSetup.ProviderMode.LIVE,
        scopes=["read_write"],
    )
    assert SensitiveProviderCredential.objects.filter(organizer=organizer).exists()
