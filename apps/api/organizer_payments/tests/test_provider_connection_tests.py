import json
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import Resolver404, resolve
from rest_framework.test import APIClient

from organizer_payments.models import (
    PayoutAccount,
    ProviderConnectionTestResult,
    ProviderPaymentSetup,
)
from organizer_payments.provider_connection_tests import ProviderConnectionTestValidation
from organizer_payments.provider_credentials import SensitiveProviderCredentialStore
from organizers.models import Organizer
from team_access.models import OrganizerMembership
from trip_bookings.models import Booking
from trip_payments.models import (
    LedgerEntry,
    PaymentAttempt,
    PlatformFeeStatement,
    ProviderPayment,
    SeatHold,
)
from trips.models import Trip, TripPackage, TripPaymentSchedule

pytestmark = pytest.mark.django_db


class FakeRazorpayOrderResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class FakeRazorpayOrderClient:
    def __init__(self):
        self.requests = []

    def __call__(self, request, timeout=None):
        if not request.full_url.rstrip("/").endswith("/orders"):
            raise AssertionError(f"Unexpected Razorpay HTTP call to {request.full_url}")
        payload = json.loads(request.data.decode("utf-8"))
        headers = dict(request.header_items())
        self.requests.append(
            {
                "url": request.full_url,
                "headers": headers,
                "payload": payload,
                "timeout": timeout,
            }
        )
        return FakeRazorpayOrderResponse(
            {
                "id": f"order_{payload['receipt']}",
                "entity": "order",
                "amount": payload["amount"],
                "amount_paid": 0,
                "amount_due": payload["amount"],
                "currency": payload["currency"],
                "receipt": payload["receipt"],
                "status": "created",
                "attempts": 0,
                "notes": payload.get("notes", {}),
            }
        )


@pytest.fixture(autouse=True)
def fake_razorpay_order_creation(monkeypatch):
    client = FakeRazorpayOrderClient()
    monkeypatch.setattr("trip_payments.provider_adapters.urlopen", client)
    return client


@pytest.fixture
def organizer():
    return Organizer.objects.create(name="Provider Test Collective")


@pytest.fixture
def user_factory():
    def create_user(email: str, *, is_staff: bool = False):
        user = get_user_model().objects.create_user(
            username=email,
            email=email,
            password="tripos-test-password",
        )
        user.is_staff = is_staff
        user.save()
        return user

    return create_user


@override_settings(
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY="provider-connection-test-key",
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY_ID="provider-connection-test-key-id",
)
def test_owner_runs_provider_connection_test_without_booking_finance_side_effects(
    user_factory,
    organizer,
):
    owner = user_factory("connection-test-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    authorize_provider_setup(organizer, mode=ProviderPaymentSetup.ProviderMode.TEST)
    before_counts = booking_finance_counts()
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        f"/api/organizers/{organizer.id}/provider-connection-tests/",
        {},
        format="json",
    )
    history_response = client.get(f"/api/organizers/{organizer.id}/provider-connection-tests/")

    organizer.provider_payment_setup.refresh_from_db()
    result = ProviderConnectionTestResult.objects.get()
    payload = response.json()
    assert response.status_code == 201
    assert history_response.status_code == 200
    assert payload["status"] == ProviderConnectionTestResult.Status.SUCCEEDED
    assert result.status == ProviderConnectionTestResult.Status.SUCCEEDED
    assert result.provider_mode == ProviderPaymentSetup.ProviderMode.TEST
    assert result.provider_account_reference == f"acct_razorpay_{organizer.id}"
    assert payload["checkout_payload"]["payment_purpose"] == "provider_connection_test"
    assert payload["checkout_payload"]["booking"] == 0
    assert payload["checkout_payload"]["payment_attempt"] == 0
    assert payload["checks"]["credentials"]["status"] == "passed"
    assert payload["checks"]["order_creation"]["status"] == "passed"
    assert payload["checks"]["browser_signature"]["status"] == "passed"
    assert payload["checks"]["webhook_signature"]["status"] == "passed"
    assert payload["checks"]["captured_confirmation"]["status"] == "passed"
    assert history_response.json()[0]["id"] == result.id
    assert organizer.provider_payment_setup.provider_connection_state == (
        ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    )
    assert booking_finance_counts() == before_counts


@override_settings(
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY="provider-connection-test-key",
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY_ID="provider-connection-test-key-id",
)
def test_staff_provider_connection_test_records_failed_result_for_support_history(
    user_factory,
    organizer,
    monkeypatch,
):
    staff = user_factory("connection-test-staff@example.com", is_staff=True)
    authorize_provider_setup(organizer, mode=ProviderPaymentSetup.ProviderMode.LIVE)
    before_counts = booking_finance_counts()
    monkeypatch.setattr(
        "organizer_payments.provider_connection_tests.provider_connection_test_adapter_for_provider",
        lambda provider: FailingConnectionTestAdapter(),
    )
    client = APIClient()
    client.force_authenticate(staff)

    response = client.post(
        f"/api/internal-admin/organizers/{organizer.id}/provider-connection-tests/",
        {},
        format="json",
    )
    history_response = client.get(
        f"/api/internal-admin/organizers/{organizer.id}/provider-connection-tests/"
    )
    detail_response = client.get(f"/api/internal-admin/organizers/{organizer.id}/")

    organizer.provider_payment_setup.refresh_from_db()
    result = ProviderConnectionTestResult.objects.get()
    assert response.status_code == 201
    assert response.json()["status"] == ProviderConnectionTestResult.Status.FAILED
    assert response.json()["failure_reason"] == "provider_order_creation_failed"
    assert result.initiated_by == staff
    assert result.initiated_by_staff is True
    assert result.checks["order_creation"]["status"] == "failed"
    assert history_response.status_code == 200
    assert history_response.json()[0]["id"] == result.id
    assert detail_response.status_code == 200
    assert detail_response.json()["provider_connection_tests"][0]["id"] == result.id
    assert organizer.provider_payment_setup.provider_connection_state == (
        ProviderPaymentSetup.ProviderConnectionState.UNHEALTHY
    )
    assert booking_finance_counts() == before_counts


def test_provider_connection_tests_are_owner_or_staff_only(user_factory, organizer):
    owner = user_factory("connection-owner@example.com")
    operator = user_factory("connection-operator@example.com")
    staff = user_factory("connection-staff@example.com", is_staff=True)
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
    client = APIClient()

    client.force_authenticate(operator)
    operator_response = client.post(
        f"/api/organizers/{organizer.id}/provider-connection-tests/",
        {},
        format="json",
    )
    operator_history_response = client.get(
        f"/api/organizers/{organizer.id}/provider-connection-tests/"
    )
    operator_status_response = client.get(
        f"/api/organizers/{organizer.id}/payment-setup-status/"
    )
    client.force_authenticate(staff)
    staff_owner_path_response = client.post(
        f"/api/organizers/{organizer.id}/provider-connection-tests/",
        {},
        format="json",
    )
    client.force_authenticate(None)
    anonymous_response = client.post(
        f"/api/organizers/{organizer.id}/provider-connection-tests/",
        {},
        format="json",
    )

    assert operator_response.status_code == 403
    assert operator_history_response.status_code == 403
    assert operator_status_response.status_code == 200
    assert operator_status_response.json()["provider_authorization_actions"] == []
    assert staff_owner_path_response.status_code == 403
    assert anonymous_response.status_code == 403
    with pytest.raises(Resolver404):
        resolve(f"/api/public/organizers/{organizer.id}/provider-connection-tests/")
    assert ProviderConnectionTestResult.objects.count() == 0


def test_payment_setup_status_exposes_owner_connection_test_action_when_authorized(
    user_factory,
    organizer,
):
    owner = user_factory("connection-action-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    setup = organizer.provider_payment_setup
    setup.authorization_state = ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    setup.provider_merchant_reference = f"acct_razorpay_{organizer.id}"
    setup.save()
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")

    assert response.status_code == 200
    actions = {
        action["id"]: action
        for action in response.json()["provider_authorization_actions"]
    }
    assert actions["connect"]["enabled"] is False
    assert actions["retry"]["enabled"] is True
    assert actions["disconnect"]["enabled"] is True
    assert actions["replace"]["enabled"] is True
    assert actions["test_connection"]["enabled"] is True


@override_settings(
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY="provider-connection-test-key",
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY_ID="provider-connection-test-key-id",
)
def test_test_provider_mode_connection_test_never_opens_public_booking(
    user_factory,
    organizer,
):
    owner = user_factory("test-mode-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_public_trip(organizer)
    package = trip.packages.first()
    authorize_provider_setup(
        organizer,
        mode=ProviderPaymentSetup.ProviderMode.TEST,
        complete_other_readiness_facts=True,
    )
    before_counts = booking_finance_counts()
    client = APIClient()
    client.force_authenticate(owner)

    test_response = client.post(
        f"/api/organizers/{organizer.id}/provider-connection-tests/",
        {},
        format="json",
    )
    readiness_response = client.get(f"/api/public/organizers/{organizer.id}/booking-readiness/")
    draft_response = client.post(
        f"/api/public/trips/{organizer.slug}/{trip.slug}/draft-bookings/",
        {
            "booking_contact_name": "Asha Nair",
            "booking_contact_phone": "+919876543210",
            "traveler_slots": [{"package": package.id}],
        },
        format="json",
    )

    organizer.provider_payment_setup.refresh_from_db()
    assert test_response.status_code == 201
    assert test_response.json()["status"] == ProviderConnectionTestResult.Status.SUCCEEDED
    assert organizer.provider_payment_setup.provider_mode == ProviderPaymentSetup.ProviderMode.TEST
    assert organizer.provider_payment_setup.provider_connection_state == (
        ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    )
    assert readiness_response.status_code == 200
    assert readiness_response.json()["online_payment_readiness_ready"] is False
    assert (
        readiness_response.json()["online_payment_readiness_blocker_code"]
        == "provider_mode_not_live"
    )
    assert draft_response.status_code == 400
    assert draft_response.json()["public_booking_gate"]["reason_code"] == (
        "payment_method_readiness_missing"
    )
    assert booking_finance_counts() == before_counts


class FailingConnectionTestAdapter:
    def run_connection_test(self, request):
        return ProviderConnectionTestValidation(
            checks={
                "credentials": {
                    "status": "passed",
                    "message": "Credential read succeeded.",
                },
                "order_creation": {
                    "status": "failed",
                    "message": "Provider test order creation failed.",
                },
            },
            failure_reason="provider_order_creation_failed",
        )


def authorize_provider_setup(
    organizer: Organizer,
    *,
    mode: str,
    complete_other_readiness_facts: bool = False,
) -> None:
    if complete_other_readiness_facts:
        organizer.payout_account.status = PayoutAccount.Status.ACTIVE
        organizer.payout_account.save()

    setup = organizer.provider_payment_setup
    setup.status = (
        ProviderPaymentSetup.Status.COMPLETE
        if complete_other_readiness_facts
        else ProviderPaymentSetup.Status.PENDING
    )
    setup.authorization_state = ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    setup.provider_verification_status = (
        ProviderPaymentSetup.ProviderVerificationStatus.VERIFIED
        if complete_other_readiness_facts
        else ProviderPaymentSetup.ProviderVerificationStatus.NOT_STARTED
    )
    setup.provider_payment_capability_enabled = complete_other_readiness_facts
    setup.provider_connection_state = ProviderPaymentSetup.ProviderConnectionState.UNHEALTHY
    setup.provider_mode = mode
    setup.provider_merchant_reference = f"acct_razorpay_{organizer.id}"
    setup.save()

    SensitiveProviderCredentialStore().store_oauth_credentials(
        organizer=organizer,
        access_token=f"oauth_access_token_{organizer.id}",
        refresh_token=f"oauth_refresh_token_{organizer.id}",
        provider_account_reference=setup.provider_merchant_reference,
        public_token=f"rzp_connection_public_{organizer.id}",
        provider_mode=mode,
        scopes=["read_write"],
    )


def booking_finance_counts() -> dict[str, int]:
    return {
        "bookings": Booking.objects.count(),
        "payment_attempts": PaymentAttempt.objects.count(),
        "seat_holds": SeatHold.objects.count(),
        "provider_payments": ProviderPayment.objects.count(),
        "ledger_entries": LedgerEntry.objects.count(),
        "platform_fee_statements": PlatformFeeStatement.objects.count(),
    }


def create_public_trip(organizer: Organizer) -> Trip:
    trip = Trip.objects.create(
        organizer=organizer,
        title="Provider Connection Public Trip",
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 15),
        capacity=24,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
    )
    TripPackage.objects.create(
        trip=trip,
        name="Standard shared room",
        price_inr=32000,
        reservation_amount_inr=8000,
    )
    TripPaymentSchedule.objects.create(
        trip=trip,
        balance_due_days_before_start=14,
    )
    return trip
