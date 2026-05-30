import csv
import hashlib
import hmac
import json
from datetime import date, datetime, timedelta
from io import StringIO
from urllib.error import URLError

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from organizer_payments.provider_account_readiness import (
    record_provider_derived_settlement_readiness,
    record_provider_payment_capability,
)
from organizer_payments.provider_adapters import (
    ProviderOAuthAdapterError,
    ProviderOAuthTokenExchangeResult,
)
from organizer_payments.provider_authorization import record_provider_authorization_revoked
from organizer_payments.provider_credentials import (
    SensitiveProviderCredentialNotFound,
    SensitiveProviderCredentialStore,
)
from organizers.bookings.intake import (
    TravelerSlotIntakeInput,
    create_booking_from_intake,
    prepare_manual_booking_intake,
)
from organizers.bookings.operations import BookingOperationsWorkflow
from organizers.models import (
    ActivityLog,
    Booking,
    BookingAccessLink,
    BookingAdjustment,
    BookingImport,
    BookingImportRow,
    LedgerEntry,
    ManualPayment,
    ManualPaymentInstructions,
    Notification,
    OpeningPaymentRecord,
    Organizer,
    OrganizerInvitation,
    OrganizerMembership,
    PaymentAttempt,
    PaymentException,
    PayoutAccount,
    PlatformFeeStatement,
    ProviderAuthorizationSession,
    ProviderPayment,
    ProviderPaymentSetup,
    ProviderWebhookEvent,
    RefundRecord,
    SeatHold,
    SensitiveProviderCredential,
    SensitiveProviderCredentialAudit,
    TravelerDocument,
    TravelerSlot,
    Trip,
    TripItineraryDay,
    TripPackage,
    TripPaymentSchedule,
)
from organizers.operations.dashboard import build_operations_dashboard_payload
from organizers.operations.trip_overview import build_trip_overview_payload
from organizers.payments.financial_ledger import FinancialLedger
from organizers.permissions import require_membership
from organizers.services import (
    BookingImportRowInput,
    BookingImportTravelerSlotInput,
    active_reserved_traveler_count,
    active_seat_hold_count,
    add_traveler_to_booking,
    approve_manual_payment,
    available_seats,
    bookable_seats,
    booking_reconciliation,
    cancel_booking,
    cancel_traveler,
    cancel_trip,
    change_traveler_package,
    change_trip_dates,
    collected_ledger_amount_inr,
    collected_provider_payment_amount_inr,
    complete_trip,
    confirm_booking,
    confirm_provider_payment,
    confirmation_requirements_for_booking,
    core_operational_booking_count,
    create_balance_payment_checkout,
    create_booking_adjustment,
    create_booking_import,
    create_organizer_entered_manual_payment,
    create_public_payment_attempt,
    create_public_reservation_checkout,
    create_refund_record,
    derived_payment_state,
    duplicate_trip,
    effective_booking_availability,
    effective_booking_total_inr,
    fail_payment_attempt,
    is_manual_payment_capability_enabled,
    is_provider_payment_setup_complete,
    issue_balance_payment_link,
    mark_traveler_attendance,
    platform_fee_for_provider_payment_inr,
    process_automatic_reminders,
    public_availability_band,
    public_booking_readiness,
    readiness_summary_for_traveler_slot,
    record_provider_dispute_exception,
    replace_traveler,
    required_amount_to_reserve_inr,
    send_announcement,
    send_manual_payment_acknowledgement,
    send_manual_reminder,
    send_refund_acknowledgement,
)
from organizers.travelers.readiness import (
    TravelerReadiness,
    review_traveler_document,
    submit_traveler_document,
)
from team_access.invitations import (
    accept_organizer_invitation,
    create_organizer_invitation,
    resend_organizer_invitation,
    revoke_organizer_invitation,
)
from trip_bookings.access_links import (
    issue_booking_access_link,
    issue_traveler_access_link,
    resolve_active_access_link,
)
from trip_payments.provider_adapters import ProviderCheckout, ProviderPaymentConfirmation
from trip_payments.provider_payment_lifecycle import (
    ingest_provider_payment_confirmation as lifecycle_ingest_provider_payment_confirmation,
)
from trips.booking_availability import public_booking_gate_decision

pytestmark = pytest.mark.django_db

PNG_LOGO_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
WEBP_LOGO_BYTES = b"RIFF\x10\x00\x00\x00WEBPVP8 \x00\x00\x00\x00"


class FakeCheckoutAdapter:
    def __init__(self, provider_order_reference: str = "order_fake_reservation_001"):
        self.provider_order_reference = provider_order_reference
        self.requests = []

    def create_checkout(self, request):
        self.requests.append(request)
        return ProviderCheckout(
            provider=request.provider,
            provider_order_reference=self.provider_order_reference,
            checkout_payload={
                "provider": request.provider,
                "provider_order_reference": self.provider_order_reference,
                "amount_inr": request.amount_inr,
                "amount_minor": request.amount_inr * 100,
                "currency": request.currency,
                "payment_attempt": request.payment_attempt_id,
                "booking": request.booking_id,
                "payment_purpose": request.payment_purpose,
                "provider_payload": {
                    "order_id": self.provider_order_reference,
                    "amount": request.amount_inr * 100,
                    "currency": request.currency,
                },
            },
        )


class FakeOAuthAdapter:
    def __init__(
        self,
        exchange_result: ProviderOAuthTokenExchangeResult | None = None,
        exchange_error: str = "",
    ):
        self.exchange_result = exchange_result
        self.exchange_error = exchange_error
        self.authorization_requests = []
        self.exchange_requests = []

    def build_authorization_url(self, request):
        self.authorization_requests.append(request)
        return (
            "https://auth.razorpay.test/authorize"
            f"?client_id={request.client_id}&state={request.state}"
        )

    def exchange_authorization_code(self, request):
        self.exchange_requests.append(request)
        if self.exchange_error:
            raise ProviderOAuthAdapterError(self.exchange_error)
        return self.exchange_result or ProviderOAuthTokenExchangeResult(
            provider=request.provider,
            access_token="oauth_access_token_from_provider",
            refresh_token="oauth_refresh_token_from_provider",
            provider_account_reference="acct_razorpay_oauth_owner",
            provider_mode=request.provider_mode,
            scopes=list(request.scopes),
            expires_at=timezone.now() + timedelta(hours=1),
            public_token="rzp_oauth_public_token_from_provider",
        )


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


def payload_text(payload) -> str:
    return json.dumps(payload, default=str, sort_keys=True)


def test_user_can_belong_to_multiple_organizers_with_roles(user_factory):
    user = user_factory("owner@example.com")
    first = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    second = Organizer.objects.create(name="Western Ghats Weekenders")

    first_membership = OrganizerMembership.objects.create(
        user=user,
        organizer=first,
        role=OrganizerMembership.Role.OWNER,
    )
    second_membership = OrganizerMembership.objects.create(
        user=user,
        organizer=second,
        role=OrganizerMembership.Role.OPERATOR,
    )

    assert first_membership.role == OrganizerMembership.Role.OWNER
    assert second_membership.role == OrganizerMembership.Role.OPERATOR
    assert user.organizer_memberships.count() == 2


def test_organizer_allows_multiple_owners(user_factory, organizer):
    first_owner = user_factory("first-owner@example.com")
    second_owner = user_factory("second-owner@example.com")

    OrganizerMembership.objects.create(
        user=first_owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    OrganizerMembership.objects.create(
        user=second_owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )

    assert organizer.memberships.filter(role=OrganizerMembership.Role.OWNER).count() == 2


def test_last_owner_membership_cannot_be_deleted(user_factory, organizer):
    owner = user_factory("owner@example.com")
    membership = OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )

    with pytest.raises(ValidationError, match="at least one Owner"):
        membership.delete()

    assert organizer.memberships.filter(role=OrganizerMembership.Role.OWNER).count() == 1


def test_last_owner_membership_cannot_be_demoted(user_factory, organizer):
    owner = user_factory("owner@example.com")
    membership = OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )

    membership.role = OrganizerMembership.Role.OPERATOR

    with pytest.raises(ValidationError, match="at least one Owner"):
        membership.save()

    membership.refresh_from_db()
    assert membership.role == OrganizerMembership.Role.OWNER


def test_last_owner_membership_cannot_be_moved_to_another_organizer(user_factory, organizer):
    owner = user_factory("owner@example.com")
    other_organizer = Organizer.objects.create(name="Western Ghats Weekenders")
    membership = OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )

    membership.organizer = other_organizer

    with pytest.raises(ValidationError, match="at least one Owner"):
        membership.save()

    membership.refresh_from_db()
    assert membership.organizer == organizer


def test_one_owner_can_be_demoted_when_another_owner_remains(user_factory, organizer):
    first_owner = user_factory("first-owner@example.com")
    second_owner = user_factory("second-owner@example.com")
    membership = OrganizerMembership.objects.create(
        user=first_owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    OrganizerMembership.objects.create(
        user=second_owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )

    membership.role = OrganizerMembership.Role.OPERATOR
    membership.save()

    assert organizer.memberships.filter(role=OrganizerMembership.Role.OWNER).count() == 1
    assert organizer.memberships.get(user=first_owner).role == OrganizerMembership.Role.OPERATOR


def test_owner_can_create_operator_invitation_by_default(user_factory, organizer):
    owner = user_factory("owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        f"/api/organizers/{organizer.id}/team-access/",
        {"email": "Operator@Community.in"},
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    invitation = OrganizerInvitation.objects.get()
    assert payload["email"] == "operator@community.in"
    assert payload["role"] == OrganizerMembership.Role.OPERATOR
    assert invitation.role == OrganizerMembership.Role.OPERATOR
    assert invitation.invited_by == owner
    assert invitation.status == OrganizerInvitation.Status.PENDING


def test_owner_invitation_requires_explicit_owner_confirmation(user_factory, organizer):
    owner = user_factory("owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    unconfirmed_response = client.post(
        f"/api/organizers/{organizer.id}/team-access/",
        {"email": "cofounder@example.com", "role": OrganizerMembership.Role.OWNER},
        format="json",
    )
    confirmed_response = client.post(
        f"/api/organizers/{organizer.id}/team-access/",
        {
            "email": "cofounder@example.com",
            "role": OrganizerMembership.Role.OWNER,
            "confirm_owner_powers": True,
        },
        format="json",
    )

    assert unconfirmed_response.status_code == 400
    assert "confirm_owner_powers" in unconfirmed_response.json()
    assert confirmed_response.status_code == 201
    assert confirmed_response.json()["role"] == OrganizerMembership.Role.OWNER


def test_team_access_displays_memberships_and_pending_invitations(user_factory, organizer):
    owner = user_factory("owner@example.com")
    operator = user_factory("operator@example.com")
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
    create_organizer_invitation(
        organizer=organizer,
        email="pending@example.com",
        invited_by=owner,
    )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.get(f"/api/organizers/{organizer.id}/team-access/")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["memberships"]) == 2
    assert payload["owner_count"] == 1
    assert payload["pending_invitations"][0]["email"] == "pending@example.com"


def test_invited_user_can_accept_organizer_invitation(user_factory, organizer):
    owner = user_factory("owner@example.com")
    invited_user = user_factory("operator@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    invitation = create_organizer_invitation(
        organizer=organizer,
        email=invited_user.email,
        invited_by=owner,
    )
    client = APIClient()
    client.force_authenticate(invited_user)

    response = client.post(f"/api/organizer-invitations/{invitation.token}/", {}, format="json")

    assert response.status_code == 200
    membership = OrganizerMembership.objects.get(user=invited_user, organizer=organizer)
    invitation.refresh_from_db()
    assert membership.role == OrganizerMembership.Role.OPERATOR
    assert invitation.status == OrganizerInvitation.Status.ACCEPTED
    assert invitation.accepted_by == invited_user
    assert response.json()["membership"]["role"] == OrganizerMembership.Role.OPERATOR


def test_new_user_account_can_accept_owner_invitation_after_signup(user_factory, organizer):
    owner = user_factory("owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    invitation = create_organizer_invitation(
        organizer=organizer,
        email="new-owner@example.com",
        invited_by=owner,
        role=OrganizerMembership.Role.OWNER,
        confirm_owner_powers=True,
    )
    client = APIClient()

    signup_response = client.post(
        "/api/auth/signup/",
        {
            "email": "new-owner@example.com",
            "password": "tripos-test-password",
            "first_name": "New",
            "last_name": "Owner",
        },
        format="json",
    )
    accept_response = client.post(
        f"/api/organizer-invitations/{invitation.token}/",
        {},
        format="json",
    )

    assert signup_response.status_code == 201
    assert accept_response.status_code == 200
    membership = OrganizerMembership.objects.get(
        user__email="new-owner@example.com",
        organizer=organizer,
    )
    assert membership.role == OrganizerMembership.Role.OWNER


def test_invitation_acceptance_prevents_duplicate_membership(user_factory, organizer):
    owner = user_factory("owner@example.com")
    existing_operator = user_factory("operator@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    OrganizerMembership.objects.create(
        user=existing_operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )

    with pytest.raises(ValidationError, match="already has an Organizer Membership"):
        create_organizer_invitation(
            organizer=organizer,
            email=existing_operator.email,
            invited_by=owner,
        )

    invitation = OrganizerInvitation.objects.create(
        organizer=organizer,
        email=existing_operator.email,
        role=OrganizerMembership.Role.OPERATOR,
        invited_by=owner,
    )
    with pytest.raises(ValidationError, match="already has an Organizer Membership"):
        accept_organizer_invitation(token=invitation.token, user=existing_operator)


def test_pending_invitation_can_be_resent_and_revoked(user_factory, organizer):
    owner = user_factory("owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    invitation = create_organizer_invitation(
        organizer=organizer,
        email="operator@example.com",
        invited_by=owner,
    )

    resent = resend_organizer_invitation(invitation)
    revoked = revoke_organizer_invitation(resent)

    assert resent.resend_count == 1
    assert revoked.status == OrganizerInvitation.Status.REVOKED
    with pytest.raises(ValidationError, match="no longer pending"):
        accept_organizer_invitation(token=invitation.token, user=user_factory("late@example.com"))


def test_operators_cannot_manage_team_access(user_factory, organizer):
    owner = user_factory("owner@example.com")
    operator = user_factory("operator@example.com")
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
    invitation = create_organizer_invitation(
        organizer=organizer,
        email="pending@example.com",
        invited_by=owner,
    )
    client = APIClient()
    client.force_authenticate(operator)

    create_response = client.post(
        f"/api/organizers/{organizer.id}/team-access/",
        {"email": "blocked@example.com"},
        format="json",
    )
    resend_response = client.post(
        f"/api/organizers/{organizer.id}/team-access/invitations/{invitation.id}/resend/",
        {},
        format="json",
    )
    revoke_response = client.post(
        f"/api/organizers/{organizer.id}/team-access/invitations/{invitation.id}/revoke/",
        {},
        format="json",
    )

    assert create_response.status_code == 403
    assert resend_response.status_code == 403
    assert revoke_response.status_code == 403


def test_role_resolution_exposes_owner_permissions(user_factory, organizer):
    owner = user_factory("owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )

    role = require_membership(owner, organizer.id)

    assert role.role == OrganizerMembership.Role.OWNER
    assert role.can_access_operations_dashboard is True
    assert role.can_manage_organizer_identity is True
    assert role.can_manage_payment_setup is True
    assert role.can_manage_team_access is True
    assert role.can_create_trips is True
    assert role.can_view_payout_status is True
    assert role.can_use_operator_workflows is True


def test_role_resolution_exposes_operator_permissions(user_factory, organizer):
    operator = user_factory("operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )

    role = require_membership(operator, organizer.id)

    assert role.role == OrganizerMembership.Role.OPERATOR
    assert role.can_access_operations_dashboard is True
    assert role.can_manage_organizer_identity is False
    assert role.can_manage_payment_setup is False
    assert role.can_manage_team_access is False
    assert role.can_create_trips is False
    assert role.can_view_payout_status is True
    assert role.can_use_operator_workflows is True


def test_operations_dashboard_is_accessible_to_owner(user_factory, organizer):
    owner = user_factory("owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get("/api/operations/dashboard/")

    assert response.status_code == 200
    assert response.json()["active_organizer"]["name"] == organizer.name
    assert response.json()["membership"]["role"] == OrganizerMembership.Role.OWNER
    assert response.json()["payment_setup"]["provider"] == ProviderPaymentSetup.Provider.RAZORPAY
    assert response.json()["payment_setup"]["provider_payment_setup_complete"] is False
    assert response.json()["payment_setup"]["online_payment_readiness_ready"] is False


def test_operations_dashboard_is_accessible_to_operator(user_factory, organizer):
    operator = user_factory("operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.get(f"/api/operations/dashboard/?organizer={organizer.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_organizer"]["identity"]["placeholder"] is True
    assert payload["membership"]["role"] == OrganizerMembership.Role.OPERATOR


def test_operations_dashboard_read_model_builds_dashboard_payload_shape(
    user_factory,
    organizer,
):
    owner = user_factory("dashboard-read-model-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    create_bookable_trip(organizer, title="Older Trip")
    latest_trip = create_bookable_trip(organizer, title="Spiti Winter Field Week", capacity=2)
    booking = Booking.objects.create(
        trip=latest_trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(
        booking=booking,
        package=latest_trip.packages.first(),
        position=1,
    )

    payload = build_operations_dashboard_payload(owner, organizer.id)

    assert set(payload) == {
        "active_organizer",
        "membership",
        "permissions",
        "payment_setup",
        "trips",
    }
    assert payload["active_organizer"]["id"] == organizer.id
    assert payload["membership"] == {"role": OrganizerMembership.Role.OWNER, "label": "Owner"}
    assert payload["permissions"]["can_publish_trip"] is True
    assert payload["payment_setup"]["provider_payment_setup_complete"] is True
    assert payload["payment_setup"]["online_payment_readiness_ready"] is True
    assert payload["trips"]["count"] == 2
    assert len(payload["trips"]["active_summaries"]) == 2
    assert payload["trips"]["attention_items"] == []

    latest_payload = payload["trips"]["latest"]
    assert latest_payload["id"] == latest_trip.id
    assert latest_payload["available_seats"] == 1
    assert latest_payload["launch_readiness"]["ready"] is True
    assert latest_payload["operational_metrics"]["reserved_travelers"] == 1
    assert latest_payload["operational_metrics"]["core_operational_booking_count"] == 1
    assert latest_payload["bookings"][0]["booking_contact_name"] == "Asha Nair"


def test_operations_dashboard_aggregates_cross_trip_attention_items(user_factory, organizer):
    owner = user_factory("cross-trip-attention-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    payment_trip = create_bookable_trip(organizer, title="Manual Payment Queue")
    payment_booking = Booking.objects.create(
        trip=payment_trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(
        booking=payment_booking,
        package=payment_trip.packages.first(),
        position=1,
    )
    ManualPayment.objects.create(
        booking=payment_booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=8000,
    )

    overdue_trip = create_bookable_trip(
        organizer,
        title="Overdue Balance Run",
        start_date=date(2026, 5, 20),
        end_date=date(2026, 5, 25),
    )
    overdue_trip.payment_schedule.balance_due_days_before_start = 3
    overdue_trip.payment_schedule.save()
    overdue_booking = Booking.objects.create(
        trip=overdue_trip,
        booking_contact_name="Rahul Menon",
        booking_contact_phone="+919123456789",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(
        booking=overdue_booking,
        package=overdue_trip.packages.first(),
        position=1,
    )
    LedgerEntry.objects.create(
        booking=overdue_booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=8000,
        description="Historical collected amount placeholder.",
    )

    readiness_trip = create_bookable_trip(
        organizer,
        title="Traveler Readiness Run",
        requires_traveler_identity_details=True,
    )
    readiness_booking = Booking.objects.create(
        trip=readiness_trip,
        booking_contact_name="Meera Shah",
        booking_contact_phone="+919111111111",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(
        booking=readiness_booking,
        package=readiness_trip.packages.first(),
        position=1,
    )

    launch_trip = create_trip(
        organizer,
        title="Draft Launch Run",
        publication_state=Trip.PublicationState.DRAFT,
        booking_availability=Trip.BookingAvailability.CLOSED,
    )

    payload = build_operations_dashboard_payload(owner, organizer.id)

    summaries_by_id = {summary["id"]: summary for summary in payload["trips"]["active_summaries"]}
    assert summaries_by_id[payment_trip.id]["operational_metrics"]["pending_manual_payments"] == 1
    assert summaries_by_id[overdue_trip.id]["operational_metrics"]["overdue_amount_inr"] == 24000
    assert summaries_by_id[readiness_trip.id]["operational_metrics"]["missing_requirements"] == 1

    attention_by_kind = {item["kind"]: item for item in payload["trips"]["attention_items"]}
    assert attention_by_kind["payment_approvals"]["trip_id"] == payment_trip.id
    assert attention_by_kind["payment_approvals"]["count"] == 1
    assert attention_by_kind["overdue_balances"]["trip_id"] == overdue_trip.id
    assert attention_by_kind["overdue_balances"]["amount_inr"] == 24000
    assert attention_by_kind["missing_requirements"]["trip_id"] == readiness_trip.id
    assert attention_by_kind["missing_requirements"]["count"] == 1
    assert attention_by_kind["launch_blocker"]["trip_id"] == launch_trip.id
    assert "Public Trip Page" in attention_by_kind["launch_blocker"]["message"]


def test_operations_dashboard_rejects_non_member(user_factory, organizer):
    user = user_factory("outsider@example.com")
    client = APIClient()
    client.force_authenticate(user)

    response = client.get(f"/api/operations/dashboard/?organizer={organizer.id}")

    assert response.status_code == 403


def test_trip_overview_read_model_summarizes_newly_created_trip(user_factory, organizer):
    owner = user_factory("trip-overview-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer, title="Spiti Winter Field Week", capacity=24)

    payload = build_trip_overview_payload(owner, organizer.id, trip.id)

    assert payload["trip"]["id"] == trip.id
    assert payload["trip"]["title"] == "Spiti Winter Field Week"
    assert payload["capacity"] == {
        "total_seats": 24,
        "available_seats": 24,
        "reserved_travelers": 0,
        "core_operational_booking_count": 0,
    }
    assert payload["packages"][0]["name"] == "Standard shared room"
    assert payload["booking_progress"]["core_operational_booking_count"] == 0
    assert payload["payment_readiness"]["provider_payment_setup_complete"] is False
    assert payload["payment_readiness"]["online_payment_readiness_ready"] is False
    assert payload["payment_readiness"]["due_inr"] == 0
    assert payload["traveler_readiness"]["ready"] is True
    assert payload["recent_activity"] == []


def test_trip_overview_endpoint_summarizes_existing_trip_operations(
    user_factory,
    organizer,
):
    operator = user_factory("trip-overview-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(
        organizer,
        title="Kaza Autumn Run",
        capacity=3,
        requires_traveler_identity_details=True,
    )
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    traveler_slot = TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.first(),
        position=1,
    )
    ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=8000,
        payment_reference="upi-public-qr-001",
        payment_proof=SimpleUploadedFile(
            "asha-payment-proof.png",
            PNG_LOGO_BYTES,
            content_type="image/png",
        ),
        original_filename="asha-payment-proof.png",
        content_type="image/png",
        file_size=len(PNG_LOGO_BYTES),
    )
    ActivityLog.objects.create(
        organizer=organizer,
        trip=trip,
        booking=booking,
        traveler_slot=traveler_slot,
        actor=operator,
        action=ActivityLog.Action.TRAVELER_REPLACED,
    )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.get(f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/overview/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["capacity"]["total_seats"] == 3
    assert payload["capacity"]["reserved_travelers"] == 1
    assert payload["capacity"]["available_seats"] == 2
    assert payload["booking_progress"]["booking_state_counts"][Booking.BookingState.RESERVED] == 1
    assert payload["booking_progress"]["bookings"][0]["booking_contact_name"] == "Asha Nair"
    manual_payment_payload = payload["booking_progress"]["bookings"][0]["manual_payments"][0]
    assert manual_payment_payload["source"] == ManualPayment.Source.TRAVELER_SUBMITTED
    assert manual_payment_payload["status"] == ManualPayment.Status.SUBMITTED
    assert manual_payment_payload["booking_contact_name"] == "Asha Nair"
    assert manual_payment_payload["traveler_count"] == 1
    assert manual_payment_payload["package_context"] == "Standard shared room x 1"
    assert manual_payment_payload["amount_inr"] == 8000
    assert manual_payment_payload["payment_reference"] == "upi-public-qr-001"
    assert manual_payment_payload["has_payment_proof"] is True
    assert "Sensitive Payment Information" in manual_payment_payload[
        "payment_proof_status_label"
    ]
    assert manual_payment_payload["payment_proof_download_url"].endswith(
        f"/manual-payments/{manual_payment_payload['id']}/proof-download/"
    )
    assert manual_payment_payload["is_sensitive_payment_information"] is True
    assert manual_payment_payload["exclude_from_default_exports"] is True
    assert payload["payment_readiness"]["provider_payment_setup_complete"] is True
    assert payload["payment_readiness"]["online_payment_readiness_ready"] is True
    assert payload["payment_readiness"]["due_inr"] == 32000
    assert payload["payment_readiness"]["pending_manual_payments"] == 1
    assert payload["traveler_readiness"]["missing_requirements"] == 1
    assert payload["recent_activity"][0]["action"] == ActivityLog.Action.TRAVELER_REPLACED
    assert payload["recent_activity"][0]["actor_email"] == "trip-overview-operator@example.com"


def test_trip_overview_exposes_provider_reconciliation_separately(
    user_factory,
    organizer,
):
    operator = user_factory("trip-reconciliation-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer, title="Spiti Ledger Run")
    booking = create_draft_booking(trip)
    attempt = create_public_payment_attempt(booking)
    provider_payment = confirm_provider_payment(
        attempt,
        provider_payment_reference="pay_provider_trip_reconciliation_001",
        amount_inr=8000,
        provider_fee_amount_inr=240,
        provider_net_settlement_amount_inr=7760,
    )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.get(f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/overview/")

    assert response.status_code == 200
    payload = response.json()
    payment_readiness = payload["payment_readiness"]
    booking_payload = payload["booking_progress"]["bookings"][0]
    provider_payment_payload = booking_payload["provider_payments"][0]
    assert payment_readiness["collected_inr"] == 8000
    assert payment_readiness["due_inr"] == 24000
    assert payment_readiness["gross_provider_payment_amount_inr"] == 8000
    assert payment_readiness["provider_fee_amount_inr"] == 240
    assert payment_readiness["provider_net_settlement_amount_inr"] == 7760
    assert payment_readiness["platform_fee_inr"] == 160
    assert payment_readiness["provider_payment_count"] == 1
    assert payment_readiness["provider_payments_with_fee_count"] == 1
    assert payment_readiness["provider_payments_with_net_settlement_count"] == 1
    assert booking_payload["reconciliation"]["collected_inr"] == 8000
    assert booking_payload["reconciliation"]["due_inr"] == 24000
    assert booking_payload["reconciliation"]["platform_fee_inr"] == 160
    assert provider_payment_payload["id"] == provider_payment.id
    assert provider_payment_payload["gross_amount_inr"] == 8000
    assert provider_payment_payload["provider_fee_amount_inr"] == 240
    assert provider_payment_payload["provider_net_settlement_amount_inr"] == 7760
    assert provider_payment_payload["platform_fee_inr"] == 160


def test_trip_overview_payment_readiness_separates_manual_and_razorpay(
    user_factory,
    organizer,
):
    owner = user_factory("trip-overview-manual-method-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    create_ready_manual_payment_instructions(organizer)
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
        manual_payment_availability=Trip.ManualPaymentAvailability.OPEN,
    )

    payload = build_trip_overview_payload(owner, organizer.id, trip.id)

    payment_readiness = payload["payment_readiness"]
    assert payment_readiness["online_payment_readiness_ready"] is False
    assert payment_readiness["payment_method_readiness_ready"] is True
    assert payment_readiness["ready_payment_method_ids"] == ["qr_manual_payments"]
    assert payment_readiness["provider_payment_method"]["ready"] is False
    assert payment_readiness["manual_payment_method"]["ready"] is True


def test_owner_only_identity_update_is_enforced_by_backend(user_factory, organizer):
    owner = user_factory("owner@example.com")
    operator = user_factory("operator@example.com")
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
    operator_response = client.patch(
        f"/api/organizers/{organizer.id}/identity/",
        {"identity_name": "Field Team Collective"},
        format="json",
    )

    client.force_authenticate(owner)
    owner_response = client.patch(
        f"/api/organizers/{organizer.id}/identity/",
        {
            "identity_name": "Field Team Collective",
            "identity_whatsapp_number": " +91 98765 43210 ",
        },
        format="json",
    )

    assert operator_response.status_code == 403
    assert owner_response.status_code == 200
    assert owner_response.json()["identity_name"] == "Field Team Collective"
    assert owner_response.json()["identity_whatsapp_number"] == "+91 98765 43210"


def test_operator_can_view_but_not_manage_organizer_identity(user_factory, organizer):
    operator = user_factory("identity-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    client = APIClient()
    client.force_authenticate(operator)

    get_response = client.get(f"/api/organizers/{organizer.id}/identity/")
    patch_response = client.patch(
        f"/api/organizers/{organizer.id}/identity/",
        {"identity_name": "Operator Attempt"},
        format="json",
    )

    assert get_response.status_code == 200
    assert get_response.json()["name"] == organizer.name
    assert get_response.json()["logo_uploaded"] is False
    assert get_response.json()["fallback"]["initials"] == "HM"
    assert patch_response.status_code == 403


@override_settings(MEDIA_ROOT="/private/tmp/tripos-organizer-logo-test-media")
def test_owner_can_upload_replace_and_remove_organizer_logo(user_factory, organizer):
    owner = user_factory("identity-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    upload_response = client.patch(
        f"/api/organizers/{organizer.id}/identity/",
        {
            "identity_name": "Kaza Field Collective",
            "identity_logo": SimpleUploadedFile(
                "kaza.png",
                PNG_LOGO_BYTES,
                content_type="image/png",
            ),
        },
        format="multipart",
    )

    organizer.refresh_from_db()
    assert upload_response.status_code == 200
    assert upload_response.json()["name"] == "Kaza Field Collective"
    assert upload_response.json()["logo_uploaded"] is True
    assert "/media/organizer-logos/" in upload_response.json()["logo_url"]
    assert organizer.identity_logo.name.endswith(".png")

    replace_response = client.patch(
        f"/api/organizers/{organizer.id}/identity/",
        {
            "identity_logo": SimpleUploadedFile(
                "kaza.webp",
                WEBP_LOGO_BYTES,
                content_type="image/webp",
            ),
        },
        format="multipart",
    )

    organizer.refresh_from_db()
    assert replace_response.status_code == 200
    assert replace_response.json()["logo_uploaded"] is True
    assert organizer.identity_logo.name.endswith(".webp")

    remove_response = client.patch(
        f"/api/organizers/{organizer.id}/identity/",
        {"remove_identity_logo": "true"},
        format="multipart",
    )

    organizer.refresh_from_db()
    assert remove_response.status_code == 200
    assert remove_response.json()["logo_uploaded"] is False
    assert remove_response.json()["logo_url"] == ""
    assert remove_response.json()["fallback"]["initials"] == "KF"
    assert organizer.identity_logo.name == ""


@override_settings(MEDIA_ROOT="/private/tmp/tripos-organizer-logo-test-media")
def test_organizer_logo_upload_validation_rejects_non_image_files(user_factory, organizer):
    owner = user_factory("identity-validation-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/identity/",
        {
            "identity_logo": SimpleUploadedFile(
                "not-a-logo.txt",
                b"not an image",
                content_type="text/plain",
            ),
        },
        format="multipart",
    )

    organizer.refresh_from_db()
    assert response.status_code == 400
    assert "identity_logo" in response.json()
    assert organizer.identity_logo.name == ""


def test_operator_allowed_workflow_access_is_enforced_by_backend(user_factory, organizer):
    operator = user_factory("operator@example.com")
    outsider = user_factory("outsider@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )

    client = APIClient()
    client.force_authenticate(operator)
    operator_response = client.post(
        f"/api/operations/organizers/{organizer.id}/operator-workflow-access/"
    )

    client.force_authenticate(outsider)
    outsider_response = client.post(
        f"/api/operations/organizers/{organizer.id}/operator-workflow-access/"
    )

    assert operator_response.status_code == 200
    assert operator_response.json()["role"] == OrganizerMembership.Role.OPERATOR
    assert outsider_response.status_code == 403


def test_organizer_gets_one_payout_account_and_provider_payment_setup(organizer):
    assert organizer.payout_account.status == PayoutAccount.Status.NOT_STARTED
    assert organizer.provider_payment_setup.provider == ProviderPaymentSetup.Provider.RAZORPAY
    assert (
        organizer.provider_payment_setup.authorization_state
        == ProviderPaymentSetup.AuthorizationState.NOT_STARTED
    )
    assert (
        organizer.provider_payment_setup.provider_connection_state
        == ProviderPaymentSetup.ProviderConnectionState.UNHEALTHY
    )
    assert organizer.provider_payment_setup.provider_mode == ProviderPaymentSetup.ProviderMode.TEST
    assert is_manual_payment_capability_enabled(organizer) is True

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PayoutAccount.objects.create(organizer=organizer)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ProviderPaymentSetup.objects.create(organizer=organizer)


def test_provider_derived_payment_setup_facts_are_read_only_for_organizers(
    user_factory,
    organizer,
):
    owner = user_factory("owner@example.com")
    operator = user_factory("operator@example.com")
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
    operator_response = client.patch(
        f"/api/organizers/{organizer.id}/payout-account/",
        {"holder_name": "Field Team Collective"},
        format="json",
    )

    client.force_authenticate(owner)
    payout_response = client.patch(
        f"/api/organizers/{organizer.id}/payout-account/",
        {
            "holder_name": "Field Team Collective",
            "provider_account_reference": "acc_razorpay_pilot",
            "status": PayoutAccount.Status.ACTIVE,
        },
        format="json",
    )
    provider_response = client.patch(
        f"/api/organizers/{organizer.id}/provider-payment-setup/",
        {
            "status": ProviderPaymentSetup.Status.COMPLETE,
            "authorization_state": ProviderPaymentSetup.AuthorizationState.AUTHORIZED,
            "provider_verification_status": (
                ProviderPaymentSetup.ProviderVerificationStatus.VERIFIED
            ),
            "provider_payment_capability_enabled": True,
            "provider_connection_state": (ProviderPaymentSetup.ProviderConnectionState.HEALTHY),
            "provider_mode": ProviderPaymentSetup.ProviderMode.LIVE,
        },
        format="json",
    )

    organizer.payout_account.refresh_from_db()
    organizer.provider_payment_setup.refresh_from_db()
    assert operator_response.status_code == 403
    assert payout_response.status_code == 405
    assert provider_response.status_code == 405
    assert "Settlement Readiness is provider-derived" in payout_response.json()["detail"]
    assert "Provider-derived Payment Setup facts" in provider_response.json()["detail"]
    assert organizer.payout_account.status == PayoutAccount.Status.NOT_STARTED
    assert organizer.payout_account.holder_name == ""
    assert (
        organizer.provider_payment_setup.authorization_state
        == ProviderPaymentSetup.AuthorizationState.NOT_STARTED
    )


def test_provider_setup_mutation_cannot_edit_settlement_readiness(
    user_factory,
    organizer,
):
    owner = user_factory("settlement-mutation-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    organizer.payout_account.status = PayoutAccount.Status.PENDING
    organizer.payout_account.settlement_readiness_source = (
        PayoutAccount.SettlementReadinessSource.PROVIDER_DERIVED
    )
    organizer.payout_account.save()
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/provider-payment-setup/",
        {
            "status": ProviderPaymentSetup.Status.COMPLETE,
            "settlement_readiness_status": PayoutAccount.Status.ACTIVE,
            "settlement_readiness_ready": True,
            "settlement_readiness_source": (
                PayoutAccount.SettlementReadinessSource.SUPPORT_CONFIRMED
            ),
            "payout_status": PayoutAccount.Status.ACTIVE,
        },
        format="json",
    )
    status_response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")

    organizer.payout_account.refresh_from_db()
    organizer.provider_payment_setup.refresh_from_db()
    assert response.status_code == 405
    assert organizer.payout_account.status == PayoutAccount.Status.PENDING
    assert (
        organizer.payout_account.settlement_readiness_source
        == PayoutAccount.SettlementReadinessSource.PROVIDER_DERIVED
    )
    assert organizer.provider_payment_setup.status == (ProviderPaymentSetup.Status.NOT_STARTED)
    assert status_response.json()["settlement_readiness_status"] == (PayoutAccount.Status.PENDING)
    assert status_response.json()["settlement_readiness_ready"] is False


def test_owner_and_operator_can_view_payment_setup_status_and_role_actions(
    user_factory,
    organizer,
):
    owner = user_factory("owner@example.com")
    operator = user_factory("operator@example.com")
    outsider = user_factory("outsider@example.com")
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
    organizer.payout_account.status = PayoutAccount.Status.PENDING
    organizer.payout_account.settlement_readiness_source = (
        PayoutAccount.SettlementReadinessSource.SUPPORT_CONFIRMED
    )
    organizer.payout_account.support_confirmed_at = timezone.now()
    organizer.payout_account.save()
    organizer.provider_payment_setup.provider_merchant_reference = "acct_sensitive_ref"
    organizer.provider_payment_setup.authorization_state = (
        ProviderPaymentSetup.AuthorizationState.ACTION_REQUIRED
    )
    organizer.provider_payment_setup.provider_connection_state = (
        ProviderPaymentSetup.ProviderConnectionState.UNHEALTHY
    )
    organizer.provider_payment_setup.provider_mode = ProviderPaymentSetup.ProviderMode.TEST
    organizer.provider_payment_setup.save()
    client = APIClient()

    client.force_authenticate(owner)
    owner_response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")
    client.force_authenticate(operator)
    operator_response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")
    client.force_authenticate(outsider)
    outsider_response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")

    assert owner_response.status_code == 200
    assert operator_response.status_code == 200
    assert owner_response.json()["payout_status"] == PayoutAccount.Status.PENDING
    assert operator_response.json()["payout_status"] == PayoutAccount.Status.PENDING
    assert owner_response.json()["settlement_readiness_status"] == PayoutAccount.Status.PENDING
    assert (
        operator_response.json()["settlement_readiness_status_label"]
        == PayoutAccount.Status.PENDING.label
    )
    assert owner_response.json()["settlement_readiness_ready"] is False
    assert (
        owner_response.json()["settlement_readiness_source"]
        == PayoutAccount.SettlementReadinessSource.SUPPORT_CONFIRMED
    )
    assert (
        operator_response.json()["settlement_readiness_source_label"]
        == PayoutAccount.SettlementReadinessSource.SUPPORT_CONFIRMED.label
    )
    assert owner_response.json()["settlement_readiness_support_confirmed"] is True
    assert owner_response.json()["settlement_readiness_support_confirmed_at"]
    assert operator_response.json()["provider_label"] == "Razorpay"
    assert "Razorpay processes" in operator_response.json()["provider_disclosure"]
    assert (
        operator_response.json()["provider_authorization_state"]
        == ProviderPaymentSetup.AuthorizationState.ACTION_REQUIRED
    )
    assert (
        operator_response.json()["provider_connection_state"]
        == ProviderPaymentSetup.ProviderConnectionState.UNHEALTHY
    )
    assert operator_response.json()["provider_mode"] == ProviderPaymentSetup.ProviderMode.TEST
    assert owner_response.json()["can_manage_provider_authorization"] is True
    assert operator_response.json()["can_manage_provider_authorization"] is False
    owner_action_ids = [
        action["id"] for action in owner_response.json()["provider_authorization_actions"]
    ]
    assert owner_action_ids == [
        "connect",
        "retry",
        "disconnect",
        "replace",
        "test_connection",
    ]
    assert operator_response.json()["provider_authorization_actions"] == []
    assert "only Owners" in operator_response.json()["payment_setup_access_message"]
    assert "provider_merchant_reference" not in operator_response.json()
    assert "api_key_secret" not in operator_response.json()
    assert "oauth_access_token" not in operator_response.json()
    assert outsider_response.status_code == 403


def test_payment_setup_status_matches_operations_dashboard_readiness(
    user_factory,
    organizer,
):
    owner = user_factory("readiness-normalization-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    organizer.payout_account.status = PayoutAccount.Status.PENDING
    organizer.payout_account.save()
    setup = organizer.provider_payment_setup
    setup.status = ProviderPaymentSetup.Status.PENDING
    setup.authorization_state = ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    setup.provider_verification_status = ProviderPaymentSetup.ProviderVerificationStatus.VERIFIED
    setup.provider_payment_capability_enabled = True
    setup.provider_connection_state = ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    setup.provider_mode = ProviderPaymentSetup.ProviderMode.LIVE
    setup.save()
    client = APIClient()
    client.force_authenticate(owner)

    status_payload = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/").json()
    dashboard_payload = client.get(f"/api/operations/dashboard/?organizer={organizer.id}").json()[
        "payment_setup"
    ]

    normalized_keys = [
        "settlement_readiness_status",
        "settlement_readiness_ready",
        "settlement_readiness_source",
        "provider_payment_setup_status",
        "provider_payment_setup_complete",
        "provider_authorization_state",
        "provider_verification_status",
        "provider_payment_capability_enabled",
        "provider_connection_state",
        "provider_mode",
        "provider_order_creation_available",
        "online_payment_readiness_ready",
        "online_payment_readiness_blocker_code",
        "online_payment_readiness_blocker_label",
        "online_payment_readiness_message",
        "can_manage_provider_authorization",
        "payment_setup_access_message",
        "provider_authorization_actions",
    ]
    assert {key: status_payload[key] for key in normalized_keys} == {
        key: dashboard_payload[key] for key in normalized_keys
    }
    assert status_payload["online_payment_readiness_blocker_code"] == (
        "settlement_readiness_not_ready"
    )


@override_settings(
    TRIPOS_RAZORPAY_OAUTH_CLIENT_ID="rzp_oauth_client",
    TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET="rzp_oauth_secret",
    TRIPOS_RAZORPAY_OAUTH_SCOPES=["read_write"],
)
def test_only_owners_can_start_razorpay_oauth_authorization(
    user_factory,
    organizer,
    monkeypatch,
):
    owner = user_factory("oauth-owner@example.com")
    operator = user_factory("oauth-operator@example.com")
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
    adapter = FakeOAuthAdapter()
    monkeypatch.setattr(
        "organizer_payments.provider_authorization.oauth_adapter_for_provider",
        lambda provider: adapter,
    )
    client = APIClient()

    client.force_authenticate(operator)
    operator_response = client.post(
        f"/api/organizers/{organizer.id}/provider-authorization/start/",
        {"provider_mode": ProviderPaymentSetup.ProviderMode.LIVE},
        format="json",
    )
    client.force_authenticate(owner)
    owner_response = client.post(
        f"/api/organizers/{organizer.id}/provider-authorization/start/",
        {"provider_mode": ProviderPaymentSetup.ProviderMode.LIVE},
        format="json",
    )

    organizer.provider_payment_setup.refresh_from_db()
    session = ProviderAuthorizationSession.objects.get()
    assert operator_response.status_code == 403
    assert owner_response.status_code == 201
    assert owner_response.json()["provider"] == ProviderPaymentSetup.Provider.RAZORPAY
    assert owner_response.json()["provider_mode"] == ProviderPaymentSetup.ProviderMode.LIVE
    assert owner_response.json()["state"] in owner_response.json()["authorization_url"]
    assert "auth.razorpay.test" in owner_response.json()["authorization_url"]
    assert session.organizer == organizer
    assert session.initiated_by == owner
    assert session.provider_mode == ProviderPaymentSetup.ProviderMode.LIVE
    assert session.client_id == "rzp_oauth_client"
    assert session.scopes == ["read_write"]
    assert adapter.authorization_requests[0].redirect_uri.endswith(
        f"/api/organizers/{organizer.id}/provider-authorization/callback/"
    )
    assert organizer.provider_payment_setup.authorization_method == (
        ProviderPaymentSetup.AuthorizationMethod.OAUTH
    )
    assert organizer.provider_payment_setup.authorization_state == (
        ProviderPaymentSetup.AuthorizationState.PENDING
    )
    assert organizer.provider_payment_setup.status == ProviderPaymentSetup.Status.PENDING


@override_settings(
    TRIPOS_RAZORPAY_OAUTH_CLIENT_ID="rzp_oauth_client",
    TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET="rzp_oauth_secret",
)
def test_razorpay_oauth_callback_rejects_invalid_state(
    user_factory,
    organizer,
):
    owner = user_factory("oauth-invalid-state-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(
        f"/api/organizers/{organizer.id}/provider-authorization/callback/",
        {"state": "not-a-valid-state", "code": "auth_code"},
    )

    assert response.status_code == 400
    assert "state" in response.json()
    assert SensitiveProviderCredential.objects.count() == 0


@override_settings(
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY="test-provider-credential-key",
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY_ID="test-key",
    TRIPOS_RAZORPAY_OAUTH_CLIENT_ID="rzp_oauth_client",
    TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET="rzp_oauth_secret",
    TRIPOS_RAZORPAY_OAUTH_SCOPES=["read_write"],
)
def test_razorpay_oauth_callback_exchanges_code_and_stores_sensitive_credentials(
    user_factory,
    organizer,
    monkeypatch,
):
    owner = user_factory("oauth-success-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    access_token = "provider_access_token_do_not_expose"
    refresh_token = "provider_refresh_token_do_not_expose"
    public_token = "rzp_public_checkout_token"
    adapter = FakeOAuthAdapter(
        ProviderOAuthTokenExchangeResult(
            provider=ProviderPaymentSetup.Provider.RAZORPAY,
            access_token=access_token,
            refresh_token=refresh_token,
            provider_account_reference="acct_razorpay_oauth_success",
            provider_mode=ProviderPaymentSetup.ProviderMode.TEST,
            scopes=["read_write"],
            expires_at=timezone.now() + timedelta(hours=1),
            public_token=public_token,
        )
    )
    monkeypatch.setattr(
        "organizer_payments.provider_authorization.oauth_adapter_for_provider",
        lambda provider: adapter,
    )
    client = APIClient()
    client.force_authenticate(owner)
    start_response = client.post(
        f"/api/organizers/{organizer.id}/provider-authorization/start/",
        {},
        format="json",
    )

    callback_response = client.get(
        f"/api/organizers/{organizer.id}/provider-authorization/callback/",
        {"state": start_response.json()["state"], "code": "auth_code_success"},
    )

    organizer.provider_payment_setup.refresh_from_db()
    session = ProviderAuthorizationSession.objects.get()
    credential = SensitiveProviderCredential.objects.get()
    response_text = payload_text(callback_response.json())
    retrieved = SensitiveProviderCredentialStore().retrieve_active_credential(
        organizer=organizer,
        credential_kind=SensitiveProviderCredential.CredentialKind.OAUTH,
    )
    assert start_response.status_code == 201
    assert callback_response.status_code == 200
    assert access_token not in response_text
    assert refresh_token not in response_text
    assert access_token not in credential.encrypted_payload
    assert refresh_token not in credential.encrypted_payload
    assert adapter.exchange_requests[0].code == "auth_code_success"
    assert session.status == ProviderAuthorizationSession.Status.COMPLETED
    assert session.provider_account_reference == "acct_razorpay_oauth_success"
    assert credential.credential_kind == SensitiveProviderCredential.CredentialKind.OAUTH
    assert credential.provider_account_reference == "acct_razorpay_oauth_success"
    assert retrieved.secret_payload["access_token"] == access_token
    assert retrieved.secret_payload["refresh_token"] == refresh_token
    assert retrieved.secret_payload["public_token"] == public_token
    assert organizer.provider_payment_setup.provider_merchant_reference == (
        "acct_razorpay_oauth_success"
    )
    assert organizer.provider_payment_setup.authorization_state == (
        ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    )
    assert organizer.provider_payment_setup.provider_connection_state == (
        ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    )
    assert organizer.provider_payment_setup.status == ProviderPaymentSetup.Status.PENDING
    assert callback_response.json()["payment_setup"]["online_payment_readiness_ready"] is False
    assert (
        callback_response.json()["payment_setup"]["online_payment_readiness_blocker_code"]
        == "provider_verification_not_verified"
    )


@override_settings(
    TRIPOS_RAZORPAY_OAUTH_CLIENT_ID="rzp_oauth_client",
    TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET="rzp_oauth_secret",
    TRIPOS_RAZORPAY_OAUTH_SCOPES=["read_write"],
)
def test_razorpay_oauth_callback_marks_exchange_failure_without_storing_credentials(
    user_factory,
    organizer,
    monkeypatch,
):
    owner = user_factory("oauth-exchange-failure-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    adapter = FakeOAuthAdapter(exchange_error="invalid_grant")
    monkeypatch.setattr(
        "organizer_payments.provider_authorization.oauth_adapter_for_provider",
        lambda provider: adapter,
    )
    client = APIClient()
    client.force_authenticate(owner)
    start_response = client.post(
        f"/api/organizers/{organizer.id}/provider-authorization/start/",
        {},
        format="json",
    )

    callback_response = client.get(
        f"/api/organizers/{organizer.id}/provider-authorization/callback/",
        {"state": start_response.json()["state"], "code": "bad_auth_code"},
    )

    organizer.provider_payment_setup.refresh_from_db()
    session = ProviderAuthorizationSession.objects.get()
    assert callback_response.status_code == 400
    assert "code" in callback_response.json()
    assert session.status == ProviderAuthorizationSession.Status.FAILED
    assert session.failure_reason == "token_exchange_failed"
    assert organizer.provider_payment_setup.authorization_state == (
        ProviderPaymentSetup.AuthorizationState.ACTION_REQUIRED
    )
    assert organizer.provider_payment_setup.provider_connection_state == (
        ProviderPaymentSetup.ProviderConnectionState.UNHEALTHY
    )
    assert SensitiveProviderCredential.objects.count() == 0


@override_settings(
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY="test-provider-credential-key",
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY_ID="test-key",
    TRIPOS_RAZORPAY_OAUTH_CLIENT_ID="rzp_oauth_client",
    TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET="rzp_oauth_secret",
    TRIPOS_RAZORPAY_OAUTH_SCOPES=["read_write"],
)
def test_same_razorpay_account_reauthorization_rotates_oauth_credentials(
    user_factory,
    organizer,
    monkeypatch,
):
    owner = user_factory("oauth-reauth-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    adapter = FakeOAuthAdapter()
    monkeypatch.setattr(
        "organizer_payments.provider_authorization.oauth_adapter_for_provider",
        lambda provider: adapter,
    )
    client = APIClient()
    client.force_authenticate(owner)
    first_start = client.post(
        f"/api/organizers/{organizer.id}/provider-authorization/start/",
        {},
        format="json",
    )
    adapter.exchange_result = ProviderOAuthTokenExchangeResult(
        provider=ProviderPaymentSetup.Provider.RAZORPAY,
        access_token="first_oauth_access_token",
        refresh_token="first_oauth_refresh_token",
        provider_account_reference="acct_razorpay_same",
        provider_mode=ProviderPaymentSetup.ProviderMode.TEST,
        scopes=["read_write"],
        expires_at=timezone.now() + timedelta(hours=1),
    )
    first_callback = client.get(
        f"/api/organizers/{organizer.id}/provider-authorization/callback/",
        {"state": first_start.json()["state"], "code": "first_code"},
    )
    first_credential = SensitiveProviderCredential.objects.get()
    second_start = client.post(
        f"/api/organizers/{organizer.id}/provider-authorization/start/",
        {},
        format="json",
    )
    adapter.exchange_result = ProviderOAuthTokenExchangeResult(
        provider=ProviderPaymentSetup.Provider.RAZORPAY,
        access_token="second_oauth_access_token",
        refresh_token="second_oauth_refresh_token",
        provider_account_reference="acct_razorpay_same",
        provider_mode=ProviderPaymentSetup.ProviderMode.TEST,
        scopes=["read_write"],
        expires_at=timezone.now() + timedelta(hours=2),
    )

    second_callback = client.get(
        f"/api/organizers/{organizer.id}/provider-authorization/callback/",
        {"state": second_start.json()["state"], "code": "second_code"},
    )

    first_credential.refresh_from_db()
    active_credential = SensitiveProviderCredential.objects.get(
        status=SensitiveProviderCredential.Status.ACTIVE
    )
    retrieved = SensitiveProviderCredentialStore().retrieve_active_credential(
        organizer=organizer,
        credential_kind=SensitiveProviderCredential.CredentialKind.OAUTH,
    )
    organizer.provider_payment_setup.refresh_from_db()
    assert first_callback.status_code == 200
    assert second_callback.status_code == 200
    assert first_credential.status == SensitiveProviderCredential.Status.ROTATED
    assert active_credential.id != first_credential.id
    assert active_credential.provider_account_reference == "acct_razorpay_same"
    assert retrieved.secret_payload["access_token"] == "second_oauth_access_token"
    assert organizer.provider_payment_setup.provider_merchant_reference == ("acct_razorpay_same")
    assert organizer.provider_payment_setup.authorization_state == (
        ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    )
    assert (
        ProviderAuthorizationSession.objects.filter(
            status=ProviderAuthorizationSession.Status.COMPLETED
        ).count()
        == 2
    )


@override_settings(
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY="test-provider-credential-key",
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY_ID="test-key",
    TRIPOS_RAZORPAY_OAUTH_CLIENT_ID="rzp_oauth_client",
    TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET="rzp_oauth_secret",
    TRIPOS_RAZORPAY_OAUTH_SCOPES=["read_write"],
)
def test_provider_authorization_survives_after_initiating_owner_leaves_organizer(
    user_factory,
    organizer,
    monkeypatch,
):
    initiating_owner = user_factory("oauth-departing-owner@example.com")
    remaining_owner = user_factory("oauth-remaining-owner@example.com")
    initiating_membership = OrganizerMembership.objects.create(
        user=initiating_owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    OrganizerMembership.objects.create(
        user=remaining_owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    adapter = FakeOAuthAdapter()
    monkeypatch.setattr(
        "organizer_payments.provider_authorization.oauth_adapter_for_provider",
        lambda provider: adapter,
    )
    client = APIClient()
    client.force_authenticate(initiating_owner)
    start_response = client.post(
        f"/api/organizers/{organizer.id}/provider-authorization/start/",
        {},
        format="json",
    )
    callback_response = client.get(
        f"/api/organizers/{organizer.id}/provider-authorization/callback/",
        {"state": start_response.json()["state"], "code": "auth_code"},
    )

    initiating_membership.delete()
    organizer.provider_payment_setup.refresh_from_db()
    credential = SensitiveProviderCredential.objects.get()
    client.force_authenticate(remaining_owner)
    status_response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")

    assert callback_response.status_code == 200
    assert organizer.memberships.filter(user=initiating_owner).count() == 0
    assert credential.status == SensitiveProviderCredential.Status.ACTIVE
    assert organizer.provider_payment_setup.authorization_state == (
        ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    )
    assert status_response.status_code == 200
    assert status_response.json()["provider_authorization_state"] == (
        ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    )


@override_settings(
    TRIPOS_RAZORPAY_OAUTH_CLIENT_ID="rzp_oauth_client",
    TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET="rzp_oauth_secret",
    TRIPOS_RAZORPAY_OAUTH_SCOPES=["read_write"],
)
def test_different_razorpay_account_authorization_is_blocked_for_replacement_flow(
    user_factory,
    organizer,
    monkeypatch,
):
    owner = user_factory("oauth-replacement-owner@example.com")
    operator = user_factory("oauth-replacement-operator@example.com")
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
    trip = create_bookable_trip(organizer, capacity=4)
    organizer.provider_payment_setup.provider_merchant_reference = "acct_existing"
    organizer.provider_payment_setup.authorization_state = (
        ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    )
    organizer.provider_payment_setup.provider_connection_state = (
        ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    )
    organizer.provider_payment_setup.save()
    existing_credential = SensitiveProviderCredentialStore().store_oauth_credentials(
        organizer=organizer,
        access_token="existing_account_access_token",
        refresh_token="existing_account_refresh_token",
        provider_account_reference="acct_existing",
        public_token="rzp_existing_account_public",
        provider_mode=ProviderPaymentSetup.ProviderMode.LIVE,
        scopes=["read_write"],
        actor=owner,
    )
    historical_booking = create_draft_booking(trip)
    historical_attempt = create_public_payment_attempt(historical_booking)
    historical_payment = confirm_provider_payment(
        historical_attempt,
        provider_payment_reference="pay_replacement_history_001",
    )
    active_booking = create_draft_booking(trip, slot_count=2)
    active_attempt = create_public_payment_attempt(active_booking)
    active_hold = SeatHold.objects.get(payment_attempt=active_attempt)
    adapter = FakeOAuthAdapter(
        ProviderOAuthTokenExchangeResult(
            provider=ProviderPaymentSetup.Provider.RAZORPAY,
            access_token="different_account_access_token",
            refresh_token="different_account_refresh_token",
            provider_account_reference="acct_different",
            provider_mode=ProviderPaymentSetup.ProviderMode.LIVE,
            scopes=["read_write"],
            expires_at=timezone.now() + timedelta(hours=1),
        )
    )
    monkeypatch.setattr(
        "organizer_payments.provider_authorization.oauth_adapter_for_provider",
        lambda provider: adapter,
    )
    client = APIClient()
    client.force_authenticate(owner)
    start_response = client.post(
        f"/api/organizers/{organizer.id}/provider-authorization/start/",
        {},
        format="json",
    )

    callback_response = client.get(
        f"/api/organizers/{organizer.id}/provider-authorization/callback/",
        {"state": start_response.json()["state"], "code": "different_account_code"},
    )

    organizer.provider_payment_setup.refresh_from_db()
    session = ProviderAuthorizationSession.objects.get()
    assert callback_response.status_code == 409
    assert callback_response.json()["replacement_required"] is True
    assert callback_response.json()["provider_authorization_session"] == session.id
    assert callback_response.json()["lifecycle"]["revoked_credentials"] == 1
    assert callback_response.json()["lifecycle"]["closed_public_booking_trips"] == 1
    assert callback_response.json()["lifecycle"]["deactivated_payment_attempts"] == 1
    assert callback_response.json()["lifecycle"]["released_seat_holds"] == 1
    assert session.status == ProviderAuthorizationSession.Status.BLOCKED
    assert session.provider_account_reference == "acct_different"
    assert session.failure_reason == "different_provider_account"
    assert organizer.provider_payment_setup.provider_merchant_reference == "acct_existing"
    assert organizer.provider_payment_setup.authorization_state == (
        ProviderPaymentSetup.AuthorizationState.ACTION_REQUIRED
    )
    assert organizer.provider_payment_setup.provider_connection_state == (
        ProviderPaymentSetup.ProviderConnectionState.UNHEALTHY
    )
    assert organizer.provider_payment_setup.provider_payment_capability_enabled is False
    trip.refresh_from_db()
    active_attempt.refresh_from_db()
    active_hold.refresh_from_db()
    existing_credential.refresh_from_db()
    pending_credential = SensitiveProviderCredential.objects.get(
        status=SensitiveProviderCredential.Status.PENDING_REPLACEMENT
    )
    assert trip.booking_availability == Trip.BookingAvailability.CLOSED
    assert active_attempt.status == PaymentAttempt.Status.SUPERSEDED
    assert active_hold.released_at is not None
    assert existing_credential.status == SensitiveProviderCredential.Status.REVOKED
    assert pending_credential.provider_account_reference == "acct_different"
    assert ProviderPayment.objects.filter(pk=historical_payment.pk).exists()
    assert LedgerEntry.objects.filter(provider_payment=historical_payment).exists()
    assert Booking.objects.filter(pk=historical_booking.pk).exists()

    client.force_authenticate(operator)
    operator_confirm_response = client.post(
        (
            f"/api/organizers/{organizer.id}/provider-authorization/"
            f"replacements/{session.id}/confirm/"
        ),
        {"confirm_replacement": True},
        format="json",
    )
    client.force_authenticate(owner)
    unconfirmed_response = client.post(
        (
            f"/api/organizers/{organizer.id}/provider-authorization/"
            f"replacements/{session.id}/confirm/"
        ),
        {"confirm_replacement": False},
        format="json",
    )
    confirmed_response = client.post(
        (
            f"/api/organizers/{organizer.id}/provider-authorization/"
            f"replacements/{session.id}/confirm/"
        ),
        {"confirm_replacement": True},
        format="json",
    )

    session.refresh_from_db()
    organizer.provider_payment_setup.refresh_from_db()
    pending_credential.refresh_from_db()
    trip.refresh_from_db()
    assert operator_confirm_response.status_code == 403
    assert unconfirmed_response.status_code == 400
    assert confirmed_response.status_code == 200
    assert confirmed_response.json()["replacement_confirmed"] is True
    assert session.status == ProviderAuthorizationSession.Status.COMPLETED
    assert session.failure_reason == ""
    assert pending_credential.status == SensitiveProviderCredential.Status.ACTIVE
    assert organizer.provider_payment_setup.provider_merchant_reference == "acct_different"
    assert organizer.provider_payment_setup.authorization_state == (
        ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    )
    assert organizer.provider_payment_setup.provider_connection_state == (
        ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    )
    assert organizer.provider_payment_setup.provider_payment_capability_enabled is False
    assert trip.booking_availability == Trip.BookingAvailability.CLOSED


def test_owner_disconnect_revokes_credentials_and_preserves_historical_records(
    user_factory,
    organizer,
):
    owner = user_factory("disconnect-owner@example.com")
    operator = user_factory("disconnect-operator@example.com")
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
    trip = create_bookable_trip(organizer, capacity=4)
    public_url_path = trip.public_url_path
    credential = SensitiveProviderCredentialStore().store_oauth_credentials(
        organizer=organizer,
        access_token="disconnect_access_token",
        refresh_token="disconnect_refresh_token",
        provider_account_reference=organizer.provider_payment_setup.provider_merchant_reference,
        public_token="rzp_disconnect_public",
        provider_mode=ProviderPaymentSetup.ProviderMode.LIVE,
        actor=owner,
    )
    historical_booking = create_draft_booking(trip)
    historical_attempt = create_public_payment_attempt(historical_booking)
    historical_payment = confirm_provider_payment(
        historical_attempt,
        provider_payment_reference="pay_disconnect_history_001",
    )
    active_booking = create_draft_booking(trip, slot_count=2)
    active_attempt = create_public_payment_attempt(active_booking)
    active_hold = SeatHold.objects.get(payment_attempt=active_attempt)
    balance_attempt = PaymentAttempt.objects.create(
        booking=historical_booking,
        purpose=PaymentAttempt.Purpose.BALANCE,
        status=PaymentAttempt.Status.CONFIRMING,
        amount_inr=1200,
        provider_attempt_reference="order_disconnect_balance_001",
    )
    client = APIClient()

    client.force_authenticate(operator)
    operator_response = client.post(
        f"/api/organizers/{organizer.id}/provider-authorization/disconnect/"
    )
    client.force_authenticate(owner)
    owner_response = client.post(
        f"/api/organizers/{organizer.id}/provider-authorization/disconnect/"
    )

    organizer.provider_payment_setup.refresh_from_db()
    credential.refresh_from_db()
    trip.refresh_from_db()
    active_attempt.refresh_from_db()
    active_hold.refresh_from_db()
    balance_attempt.refresh_from_db()
    assert operator_response.status_code == 403
    assert owner_response.status_code == 200
    assert owner_response.json()["lifecycle"]["revoked_credentials"] == 1
    assert owner_response.json()["lifecycle"]["closed_public_booking_trips"] == 1
    assert owner_response.json()["lifecycle"]["deactivated_payment_attempts"] == 2
    assert owner_response.json()["lifecycle"]["released_seat_holds"] == 1
    assert credential.status == SensitiveProviderCredential.Status.REVOKED
    assert organizer.provider_payment_setup.authorization_state == (
        ProviderPaymentSetup.AuthorizationState.REVOKED
    )
    assert organizer.provider_payment_setup.provider_connection_state == (
        ProviderPaymentSetup.ProviderConnectionState.UNHEALTHY
    )
    assert organizer.provider_payment_setup.provider_payment_capability_enabled is False
    assert trip.booking_availability == Trip.BookingAvailability.CLOSED
    assert trip.publication_state == Trip.PublicationState.PUBLISHED
    assert trip.public_url_path == public_url_path
    assert active_attempt.status == PaymentAttempt.Status.SUPERSEDED
    assert balance_attempt.status == PaymentAttempt.Status.SUPERSEDED
    assert active_hold.released_at is not None
    assert ProviderPayment.objects.filter(pk=historical_payment.pk).exists()
    assert LedgerEntry.objects.filter(provider_payment=historical_payment).exists()
    assert Booking.objects.filter(pk=historical_booking.pk).exists()

    late_confirmation = confirm_provider_payment(
        active_attempt,
        provider_payment_reference="pay_disconnect_late_001",
        amount_inr=active_attempt.amount_inr,
    )

    assert isinstance(late_confirmation, PaymentException)
    assert late_confirmation.payment_attempt_id == active_attempt.id
    assert "inactive_payment_attempt" in late_confirmation.mismatch_reasons


def test_provider_authorization_revoked_event_closes_booking_and_releases_holds(
    organizer,
):
    trip = create_bookable_trip(organizer, capacity=2)
    credential = SensitiveProviderCredentialStore().store_oauth_credentials(
        organizer=organizer,
        access_token="revoked_event_access_token",
        refresh_token="revoked_event_refresh_token",
        provider_account_reference=organizer.provider_payment_setup.provider_merchant_reference,
        public_token="rzp_revoked_event_public",
        provider_mode=ProviderPaymentSetup.ProviderMode.LIVE,
    )
    booking = create_draft_booking(trip, slot_count=2)
    attempt = create_public_payment_attempt(booking)
    hold = SeatHold.objects.get(payment_attempt=attempt)

    result = record_provider_authorization_revoked(
        organizer=organizer,
        provider_account_reference=organizer.provider_payment_setup.provider_merchant_reference,
    )

    organizer.provider_payment_setup.refresh_from_db()
    credential.refresh_from_db()
    trip.refresh_from_db()
    attempt.refresh_from_db()
    hold.refresh_from_db()
    assert result.revoked_credentials == 1
    assert result.closed_public_booking_trips == 1
    assert result.deactivated_payment_attempts == 1
    assert result.released_seat_holds == 1
    assert credential.status == SensitiveProviderCredential.Status.REVOKED
    assert organizer.provider_payment_setup.authorization_state == (
        ProviderPaymentSetup.AuthorizationState.REVOKED
    )
    assert organizer.provider_payment_setup.provider_connection_state == (
        ProviderPaymentSetup.ProviderConnectionState.UNHEALTHY
    )
    assert trip.booking_availability == Trip.BookingAvailability.CLOSED
    assert attempt.status == PaymentAttempt.Status.SUPERSEDED
    assert hold.released_at is not None


def test_settlement_readiness_blocker_uses_organizer_facing_copy(
    user_factory,
    organizer,
):
    owner = user_factory("owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    organizer.payout_account.status = PayoutAccount.Status.PENDING
    organizer.payout_account.save()
    setup = organizer.provider_payment_setup
    setup.status = ProviderPaymentSetup.Status.COMPLETE
    setup.authorization_state = ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    setup.provider_verification_status = ProviderPaymentSetup.ProviderVerificationStatus.VERIFIED
    setup.provider_payment_capability_enabled = True
    setup.provider_connection_state = ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    setup.provider_mode = ProviderPaymentSetup.ProviderMode.LIVE
    setup.save()
    client = APIClient()
    client.force_authenticate(owner)
    response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")

    payload = response.json()
    assert response.status_code == 200
    assert payload["online_payment_readiness_ready"] is False
    assert payload["online_payment_readiness_blocker_code"] == "settlement_readiness_not_ready"
    assert payload["online_payment_readiness_blocker_label"] == "Settlement Readiness not active"
    assert "Settlement Readiness must be active" in payload["online_payment_readiness_message"]
    assert "Payout Account" not in payload["online_payment_readiness_message"]


def test_connected_provider_account_readiness_uses_mode_and_connection(
    user_factory,
    organizer,
):
    owner = user_factory("connected-account-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    organizer.payout_account.status = PayoutAccount.Status.ACTIVE
    organizer.payout_account.save()
    setup = organizer.provider_payment_setup
    setup.status = ProviderPaymentSetup.Status.COMPLETE
    setup.authorization_state = ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    setup.provider_verification_status = ProviderPaymentSetup.ProviderVerificationStatus.VERIFIED
    setup.provider_payment_capability_enabled = True
    setup.provider_connection_state = ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    setup.provider_mode = ProviderPaymentSetup.ProviderMode.TEST
    setup.save()
    client = APIClient()
    client.force_authenticate(owner)

    test_mode_response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")

    setup.provider_mode = ProviderPaymentSetup.ProviderMode.LIVE
    setup.provider_connection_state = ProviderPaymentSetup.ProviderConnectionState.UNHEALTHY
    setup.save()
    unhealthy_response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")

    assert test_mode_response.status_code == 200
    assert test_mode_response.json()["online_payment_readiness_ready"] is False
    assert (
        test_mode_response.json()["online_payment_readiness_blocker_code"]
        == "provider_mode_not_live"
    )
    assert unhealthy_response.status_code == 200
    assert unhealthy_response.json()["online_payment_readiness_ready"] is False
    assert (
        unhealthy_response.json()["online_payment_readiness_blocker_code"]
        == "provider_connection_unhealthy"
    )


def test_internal_admin_can_support_confirm_settlement_readiness_for_pilot(
    user_factory,
    organizer,
):
    owner = user_factory("pilot-owner@example.com")
    support = user_factory("pilot-support@example.com")
    support.is_staff = True
    support.save(update_fields=["is_staff"])
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    mark_online_payment_ready(organizer)
    organizer.payout_account.status = PayoutAccount.Status.PENDING
    organizer.payout_account.settlement_readiness_source = (
        PayoutAccount.SettlementReadinessSource.PROVIDER_DERIVED
    )
    organizer.payout_account.save()
    client = APIClient()

    client.force_authenticate(owner)
    owner_response = client.post(
        f"/api/internal-admin/organizers/{organizer.id}/settlement-readiness/confirm/",
        {"notes": "Provider-derived settlement data incomplete during live pilot."},
        format="json",
    )

    client.force_authenticate(support)
    support_response = client.post(
        f"/api/internal-admin/organizers/{organizer.id}/settlement-readiness/confirm/",
        {"notes": "Provider-derived settlement data incomplete during live pilot."},
        format="json",
    )

    organizer.payout_account.refresh_from_db()
    payload = support_response.json()["payment_setup"]
    assert owner_response.status_code == 403
    assert support_response.status_code == 200
    assert organizer.payout_account.status == PayoutAccount.Status.ACTIVE
    assert (
        organizer.payout_account.settlement_readiness_source
        == PayoutAccount.SettlementReadinessSource.SUPPORT_CONFIRMED
    )
    assert organizer.payout_account.support_confirmed_by == support
    assert "live pilot" in organizer.payout_account.support_confirmation_notes
    assert payload["settlement_readiness_status"] == PayoutAccount.Status.ACTIVE
    assert (
        payload["settlement_readiness_source"]
        == PayoutAccount.SettlementReadinessSource.SUPPORT_CONFIRMED
    )
    assert payload["settlement_readiness_support_confirmed"] is True
    assert payload["online_payment_readiness_ready"] is True
    assert support_response.json()["readiness_regression"]["regressed"] is False

    provider_incomplete_result = record_provider_derived_settlement_readiness(
        organizer=organizer,
        status=PayoutAccount.Status.PENDING,
        notes="Provider data still has not exposed settlement activation.",
    )

    organizer.payout_account.refresh_from_db()
    assert provider_incomplete_result.current_readiness.ready is True
    assert organizer.payout_account.status == PayoutAccount.Status.ACTIVE
    assert (
        organizer.payout_account.settlement_readiness_source
        == PayoutAccount.SettlementReadinessSource.SUPPORT_CONFIRMED
    )


def test_settlement_readiness_regression_closes_public_booking_without_unpublishing(
    organizer,
):
    trip = create_bookable_trip(organizer)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Pilot Contact",
        booking_contact_phone="+919999999999",
        booking_state=Booking.BookingState.RESERVED,
    )
    payment_attempt = PaymentAttempt.objects.create(
        booking=booking,
        status=PaymentAttempt.Status.CONFIRMED,
        amount_inr=5000,
        provider_attempt_reference="order_settlement_regression_001",
    )
    provider_payment = ProviderPayment.objects.create(
        booking=booking,
        payment_attempt=payment_attempt,
        amount_inr=5000,
        provider_payment_reference="pay_settlement_regression_001",
    )
    ledger_count = LedgerEntry.objects.count()

    result = record_provider_derived_settlement_readiness(
        organizer=organizer,
        status=PayoutAccount.Status.PENDING,
        notes="Provider reported settlement activation pending.",
    )

    trip.refresh_from_db()
    booking.refresh_from_db()
    payment_attempt.refresh_from_db()
    organizer.payout_account.refresh_from_db()
    assert result.regressed is True
    assert result.closed_public_booking_trips == 1
    assert result.current_readiness.blocker_code == "settlement_readiness_not_ready"
    assert trip.publication_state == Trip.PublicationState.PUBLISHED
    assert trip.booking_availability == Trip.BookingAvailability.CLOSED
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert payment_attempt.status == PaymentAttempt.Status.CONFIRMED
    assert ProviderPayment.objects.filter(pk=provider_payment.pk).exists()
    assert LedgerEntry.objects.count() == ledger_count
    assert (
        organizer.payout_account.settlement_readiness_source
        == PayoutAccount.SettlementReadinessSource.PROVIDER_DERIVED
    )


def test_provider_payment_capability_regression_closes_public_booking(organizer):
    trip = create_bookable_trip(organizer)

    result = record_provider_payment_capability(organizer=organizer, enabled=False)

    trip.refresh_from_db()
    organizer.provider_payment_setup.refresh_from_db()
    assert result.regressed is True
    assert result.closed_public_booking_trips == 1
    assert result.current_readiness.blocker_code == "provider_payment_capability_disabled"
    assert trip.publication_state == Trip.PublicationState.PUBLISHED
    assert trip.booking_availability == Trip.BookingAvailability.CLOSED
    assert organizer.provider_payment_setup.provider_payment_capability_enabled is False


@override_settings(
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY="test-provider-credential-key",
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY_ID="test-key",
)
def test_sensitive_provider_credential_store_encrypts_and_retrieves_oauth_material(
    organizer,
):
    store = SensitiveProviderCredentialStore()
    access_token = "oauth_access_token_do_not_expose"
    refresh_token = "oauth_refresh_token_do_not_expose"

    credential = store.store_oauth_credentials(
        organizer=organizer,
        access_token=access_token,
        refresh_token=refresh_token,
        provider_account_reference="acct_razorpay_oauth_pilot",
        public_token="rzp_oauth_pilot_public",
        provider_mode=ProviderPaymentSetup.ProviderMode.TEST,
        scopes=["read_write"],
        expires_at=timezone.now() + timedelta(hours=1),
    )

    credential.refresh_from_db()
    assert credential.credential_kind == SensitiveProviderCredential.CredentialKind.OAUTH
    assert credential.encryption_key_id == "test-key"
    assert access_token not in credential.encrypted_payload
    assert refresh_token not in credential.encrypted_payload
    assert access_token not in credential.credential_fingerprint
    assert refresh_token not in credential.credential_fingerprint

    retrieved = store.retrieve_active_credential(
        organizer=organizer,
        credential_kind=SensitiveProviderCredential.CredentialKind.OAUTH,
    )

    credential.refresh_from_db()
    assert retrieved.credential_id == credential.id
    assert retrieved.secret_payload["access_token"] == access_token
    assert retrieved.secret_payload["refresh_token"] == refresh_token
    assert retrieved.provider_account_reference == "acct_razorpay_oauth_pilot"
    assert retrieved.scopes == ["read_write"]
    assert credential.last_accessed_at is not None
    assert access_token not in repr(retrieved)
    assert refresh_token not in repr(retrieved)
    assert set(credential.audit_events.values_list("event_type", flat=True)) == {
        SensitiveProviderCredentialAudit.EventType.STORED,
        SensitiveProviderCredentialAudit.EventType.RETRIEVED,
    }
    audit_payload = payload_text(list(credential.audit_events.values("event_type", "metadata")))
    assert access_token not in audit_payload
    assert refresh_token not in audit_payload


@override_settings(
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY="test-provider-credential-key",
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY_ID="test-key",
)
def test_sensitive_provider_credential_store_rotates_and_revokes_oauth_material(
    organizer,
):
    store = SensitiveProviderCredentialStore()
    first_secret = "oauth_access_token_before_rotation"
    rotated_secret = "oauth_access_token_after_rotation"
    credential = store.store_oauth_credentials(
        organizer=organizer,
        access_token=first_secret,
        refresh_token="oauth_refresh_token_before_rotation",
        provider_account_reference="acct_razorpay_assisted",
        public_token="rzp_rotation_public_before",
        provider_mode=ProviderPaymentSetup.ProviderMode.TEST,
    )

    rotated = store.rotate_credential(
        credential,
        secret_payload={
            "access_token": rotated_secret,
            "refresh_token": "oauth_refresh_token_after_rotation",
        },
    )
    retrieved = store.retrieve_active_credential(
        organizer=organizer,
        provider_mode=ProviderPaymentSetup.ProviderMode.TEST,
    )

    credential.refresh_from_db()
    rotated.refresh_from_db()
    assert credential.status == SensitiveProviderCredential.Status.ROTATED
    assert credential.rotated_at is not None
    assert rotated.status == SensitiveProviderCredential.Status.ACTIVE
    assert retrieved.credential_id == rotated.id
    assert retrieved.secret_payload["access_token"] == rotated_secret
    assert first_secret not in rotated.encrypted_payload
    assert rotated_secret not in rotated.encrypted_payload

    store.revoke_credential(rotated, reason="Pilot credential replaced.")
    rotated.refresh_from_db()

    assert rotated.status == SensitiveProviderCredential.Status.REVOKED
    assert rotated.revoked_at is not None
    with pytest.raises(SensitiveProviderCredentialNotFound):
        store.retrieve_active_credential(
            organizer=organizer,
            provider_mode=ProviderPaymentSetup.ProviderMode.TEST,
        )
    audit_payload = payload_text(
        list(SensitiveProviderCredentialAudit.objects.values("event_type", "metadata"))
    )
    assert first_secret not in audit_payload
    assert rotated_secret not in audit_payload


def test_owner_cannot_configure_api_key_authorization_through_payment_setup_api(
    user_factory,
    organizer,
):
    owner = user_factory("api-key-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/provider-payment-setup/",
        {
            "authorization_method": ProviderPaymentSetup.AuthorizationMethod.API_KEY,
            "provider_merchant_reference": "acct_owner_attempt",
            "key_secret": "owner_should_not_store_this",
        },
        format="json",
    )

    organizer.provider_payment_setup.refresh_from_db()
    assert response.status_code == 405
    assert organizer.provider_payment_setup.authorization_method == (
        ProviderPaymentSetup.AuthorizationMethod.OAUTH
    )
    assert SensitiveProviderCredential.objects.count() == 0


@override_settings(
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY="test-provider-credential-key",
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY_ID="test-key",
)
def test_assisted_payment_setup_api_is_staff_only_and_encrypts_credentials(
    user_factory,
    organizer,
):
    operator = user_factory("assisted-operator@example.com")
    internal_staff = user_factory("assisted-staff@example.com")
    internal_staff.is_staff = True
    internal_staff.save()
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    api_key_secret = "rzp_live_api_key_secret_do_not_expose"
    webhook_secret = "rzp_live_webhook_secret_do_not_expose"
    payload = {
        "provider_mode": ProviderPaymentSetup.ProviderMode.LIVE,
        "provider_account_reference": "acct_razorpay_live_pilot",
        "key_id": "rzp_live_key_public",
        "key_secret": api_key_secret,
        "webhook_secret": webhook_secret,
        "scopes": ["orders", "payments"],
    }
    client = APIClient()

    client.force_authenticate(operator)
    operator_response = client.post(
        f"/api/internal-admin/organizers/{organizer.id}/assisted-payment-setup/",
        payload,
        format="json",
    )
    client.force_authenticate(internal_staff)
    staff_response = client.post(
        f"/api/internal-admin/organizers/{organizer.id}/assisted-payment-setup/",
        payload,
        format="json",
    )

    organizer.provider_payment_setup.refresh_from_db()
    credential = SensitiveProviderCredential.objects.get()
    response_text = payload_text(staff_response.json())
    assert operator_response.status_code == 403
    assert staff_response.status_code == 201
    assert api_key_secret not in response_text
    assert webhook_secret not in response_text
    assert api_key_secret not in credential.encrypted_payload
    assert webhook_secret not in credential.encrypted_payload
    assert credential.credential_kind == SensitiveProviderCredential.CredentialKind.API_KEY
    assert credential.provider_mode == ProviderPaymentSetup.ProviderMode.LIVE
    assert credential.status == SensitiveProviderCredential.Status.ACTIVE
    assert organizer.provider_payment_setup.authorization_method == (
        ProviderPaymentSetup.AuthorizationMethod.API_KEY
    )
    assert organizer.provider_payment_setup.authorization_state == (
        ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    )
    assert organizer.provider_payment_setup.status == ProviderPaymentSetup.Status.PENDING

    retrieved = SensitiveProviderCredentialStore().retrieve_active_credential(
        organizer=organizer,
        provider_mode=ProviderPaymentSetup.ProviderMode.LIVE,
        credential_kind=SensitiveProviderCredential.CredentialKind.API_KEY,
        actor=internal_staff,
    )

    assert retrieved.secret_payload["key_secret"] == api_key_secret
    assert retrieved.secret_payload["webhook_secret"] == webhook_secret


@override_settings(
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY="test-provider-credential-key",
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY_ID="test-key",
)
def test_normal_and_internal_admin_payloads_do_not_expose_sensitive_credentials(
    user_factory,
    organizer,
):
    owner = user_factory("credential-payload-owner@example.com")
    operator = user_factory("credential-payload-operator@example.com")
    internal_staff = user_factory("credential-payload-staff@example.com")
    internal_staff.is_staff = True
    internal_staff.save()
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
    secret = "payload_api_key_secret_do_not_expose"
    webhook_secret = "payload_webhook_secret_do_not_expose"
    SensitiveProviderCredentialStore().store_api_key_credentials(
        organizer=organizer,
        key_id="rzp_payload_key_public",
        key_secret=secret,
        webhook_secret=webhook_secret,
        provider_account_reference="acct_razorpay_payload",
    )
    client = APIClient()

    client.force_authenticate(owner)
    provider_setup_response = client.get(f"/api/organizers/{organizer.id}/provider-payment-setup/")
    owner_status_response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")
    client.force_authenticate(operator)
    operator_status_response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")
    client.force_authenticate(internal_staff)
    internal_list_response = client.get("/api/internal-admin/organizers/")
    internal_detail_response = client.get(f"/api/internal-admin/organizers/{organizer.id}/")

    for response in [
        provider_setup_response,
        owner_status_response,
        operator_status_response,
        internal_list_response,
        internal_detail_response,
    ]:
        assert response.status_code == 200
        response_text = payload_text(response.json())
        assert secret not in response_text
        assert webhook_secret not in response_text
        assert "encrypted_payload" not in response_text


def test_sensitive_provider_credential_admin_list_surfaces_are_redacted():
    from django.contrib import admin as django_admin

    credential_admin = django_admin.site._registry[SensitiveProviderCredential]
    audit_admin = django_admin.site._registry[SensitiveProviderCredentialAudit]

    assert "encrypted_payload" not in credential_admin.get_list_display(None)
    assert "encrypted_payload" not in credential_admin.get_search_fields(None)
    assert "encrypted_payload" in credential_admin.exclude
    assert "metadata" not in audit_admin.get_list_display(None)


def test_payment_setup_status_includes_creator_path_verification_url_and_manual_fallback(
    user_factory,
    organizer,
):
    owner = user_factory("creator-path-owner@example.com")
    operator = user_factory("creator-path-operator@example.com")
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
    published_trip = create_trip(
        organizer,
        title="Provider Verification Field Week",
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
    )
    create_trip(
        organizer,
        title="Draft Verification Field Week",
        publication_state=Trip.PublicationState.DRAFT,
    )
    client = APIClient()

    client.force_authenticate(owner)
    owner_response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")
    public_response = client.get(f"/api/public/trips/{organizer.slug}/{published_trip.slug}/")
    client.force_authenticate(operator)
    operator_response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")

    payload = owner_response.json()
    guidance_text = " ".join(
        [
            payload["individual_creator_payment_path"]["summary"],
            *payload["individual_creator_payment_path"]["steps"],
        ]
    )
    assert owner_response.status_code == 200
    assert operator_response.status_code == 200
    assert payload["individual_creator_payment_path"]["title"] == (
        "Individual Creator Payment Path"
    )
    assert "Public Trip URL" in guidance_text
    assert "GST" not in guidance_text
    assert "MSME" not in guidance_text
    assert "shop establishment" not in guidance_text.lower()
    assert payload["provider_verification_url"]["available"] is True
    assert payload["provider_verification_url"]["source"] == "public_trip_url"
    assert payload["provider_verification_url"]["url_path"] == published_trip.public_url_path
    assert payload["provider_verification_url"]["trip_title"] == published_trip.title
    assert payload["manual_payments_only"]["supported"] is True
    assert payload["manual_payments_only"]["active"] is True
    assert payload["manual_payments_only"]["status_label"] == "Manual Payments Only"
    assert "Bookings Opening Soon" in payload["manual_payments_only"]["public_booking_message"]
    assert (
        "Manual Bookings and Manual Payments"
        in payload["manual_payments_only"]["manual_operations_message"]
    )
    assert operator_response.json()["manual_payments_only"] == payload["manual_payments_only"]
    assert public_response.status_code == 200
    assert public_response.json()["public_booking_gate"]["reason_code"] == (
        "payment_method_readiness_missing"
    )
    assert public_response.json()["public_booking_gate"]["message"] == ("Bookings opening soon.")


def test_payment_setup_status_prompts_public_trip_page_when_verification_url_missing(
    user_factory,
    organizer,
):
    owner = user_factory("verification-url-missing-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")

    assert response.status_code == 200
    payload = response.json()["provider_verification_url"]
    assert payload["available"] is False
    assert payload["url_path"] == ""
    assert payload["status_label"] == "Publish a Public Trip Page"
    assert "Provider Verification URL" in payload["message"]


def test_manual_payment_capability_stays_separate_from_provider_payment_setup(organizer):
    setup = organizer.provider_payment_setup
    assert setup.is_complete is False
    assert is_manual_payment_capability_enabled(organizer) is True

    setup.status = ProviderPaymentSetup.Status.COMPLETE
    setup.save()

    assert is_provider_payment_setup_complete(organizer) is True
    assert is_manual_payment_capability_enabled(organizer) is True
    setup.refresh_from_db()


def test_public_booking_readiness_queries_online_payment_readiness(organizer):
    client = APIClient()

    initial_response = client.get(f"/api/public/organizers/{organizer.id}/booking-readiness/")
    mark_online_payment_ready(organizer)
    ready_response = client.get(f"/api/public/organizers/{organizer.id}/booking-readiness/")

    assert initial_response.status_code == 200
    assert initial_response.json()["online_payment_readiness_ready"] is False
    assert ready_response.status_code == 200
    assert ready_response.json()["online_payment_readiness_ready"] is True
    assert ready_response.json()["provider_payment_setup_complete"] is True


def trip_setup_payload(**overrides):
    payload = {
        "title": "Spiti Winter Field Week",
        "start_date": "2026-10-10",
        "end_date": "2026-10-15",
        "capacity": 24,
        "confirmation_requirements_note": "Identity details and emergency contact.",
        "itinerary": "Day 1: Chandigarh arrival. Day 2: Transit to Kaza.",
        "packages": [
            {
                "name": "Standard shared room",
                "description": "Shared room package.",
                "price_inr": 32000,
                "reservation_amount_inr": 8000,
                "position": 1,
            }
        ],
        "payment_schedule": {
            "balance_due_days_before_start": 14,
            "balance_reminder_lead_days": 3,
        },
    }
    payload.update(overrides)
    return payload


def create_trip(organizer, **overrides):
    trip = Trip.objects.create(
        organizer=organizer,
        title=overrides.pop("title", "Spiti Winter Field Week"),
        start_date=overrides.pop("start_date", date(2026, 10, 10)),
        end_date=overrides.pop("end_date", date(2026, 10, 15)),
        capacity=overrides.pop("capacity", 24),
        confirmation_requirements_note=overrides.pop(
            "confirmation_requirements_note",
            "Identity details and emergency contact.",
        ),
        itinerary=overrides.pop(
            "itinerary",
            "Day 1: Chandigarh arrival. Day 2: Transit to Kaza.",
        ),
        **overrides,
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


def make_trip_profile_publication_ready(trip, reviewer):
    trip.description_rich_text = rich_text_payload("Traveler-facing Spiti details.")
    trip.confirmation_requirements_reviewed_at = timezone.now()
    trip.confirmation_requirements_reviewed_by = reviewer
    trip.save(
        update_fields=[
            "description_rich_text",
            "confirmation_requirements_reviewed_at",
            "confirmation_requirements_reviewed_by",
            "updated_at",
        ]
    )
    trip.payment_schedule.reviewed_at = timezone.now()
    trip.payment_schedule.reviewed_by = reviewer
    trip.payment_schedule.save(update_fields=["reviewed_at", "reviewed_by", "updated_at"])
    TripItineraryDay.objects.get_or_create(
        trip=trip,
        sequence=1,
        defaults={
            "title": "Arrival and readiness review",
            "description_rich_text": rich_text_payload("Meet the group and review kit."),
        },
    )
    return trip


def rich_text_payload(text: str) -> dict:
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


def test_signup_creates_user_only_and_starts_local_session():
    client = APIClient()

    response = client.post(
        "/api/auth/signup/",
        {
            "email": "new-owner@example.com",
            "password": "local-auth-password-123",
            "first_name": "Nila",
            "last_name": "Shah",
        },
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["authenticated"] is True
    assert payload["user"]["email"] == "new-owner@example.com"
    assert payload["user"]["first_name"] == "Nila"
    assert payload["onboarding"]["state"] == "no_organizer"
    assert payload["onboarding"]["next_route"] == "/onboarding/organizer"

    user = get_user_model().objects.get(email="new-owner@example.com")
    assert user.organizer_memberships.count() == 0

    session_response = client.get("/api/auth/session/")
    assert session_response.status_code == 200
    assert session_response.json()["user"]["id"] == user.id


def test_login_rejects_invalid_credentials_and_does_not_start_session(user_factory):
    user_factory("owner@example.com")
    client = APIClient()

    response = client.post(
        "/api/auth/login/",
        {"email": "owner@example.com", "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == 400
    session_response = client.get("/api/auth/session/")
    assert session_response.status_code == 200
    assert session_response.json() == {
        "authenticated": False,
        "user": None,
        "onboarding": {
            "state": "unauthenticated",
            "next_route": "/login",
            "organizer": None,
            "trip_count": 0,
        },
    }


def test_login_logout_and_current_session_onboarding_states(user_factory, organizer):
    owner = user_factory("owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()

    login_response = client.post(
        "/api/auth/login/",
        {"email": "owner@example.com", "password": "tripos-test-password"},
        format="json",
    )

    assert login_response.status_code == 200
    assert login_response.json()["onboarding"]["state"] == "organizer_ready"
    assert login_response.json()["onboarding"]["next_route"] == "/home"
    assert login_response.json()["onboarding"]["trip_count"] == 0

    create_trip(organizer)
    session_response = client.get("/api/auth/session/")

    assert session_response.status_code == 200
    payload = session_response.json()
    assert payload["authenticated"] is True
    assert payload["onboarding"]["state"] == "organizer_ready"
    assert payload["onboarding"]["next_route"] == "/home"
    assert payload["onboarding"]["organizer"]["id"] == organizer.id
    assert payload["onboarding"]["trip_count"] == 1

    logout_response = client.post("/api/auth/logout/")
    assert logout_response.status_code == 204
    assert client.get("/api/auth/session/").json()["authenticated"] is False


@pytest.mark.parametrize(
    ("role", "trip_count"),
    [
        (OrganizerMembership.Role.OWNER, 0),
        (OrganizerMembership.Role.OPERATOR, 0),
        (OrganizerMembership.Role.OWNER, 2),
        (OrganizerMembership.Role.OPERATOR, 2),
    ],
)
def test_current_session_routes_members_with_organizer_to_home(
    user_factory,
    organizer,
    role,
    trip_count,
):
    user = user_factory(f"{role}-{trip_count}@example.com")
    OrganizerMembership.objects.create(
        user=user,
        organizer=organizer,
        role=role,
    )
    for index in range(trip_count):
        create_trip(organizer, title=f"Trip {index + 1}")
    client = APIClient()
    client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "tripos-test-password"},
        format="json",
    )

    response = client.get("/api/auth/session/")

    assert response.status_code == 200
    payload = response.json()["onboarding"]
    assert payload["state"] == "organizer_ready"
    assert payload["next_route"] == "/home"
    assert payload["trip_count"] == trip_count
    assert payload["organizer"]["membership_role"] == role


def test_organizer_endpoint_accepts_local_session_authentication(user_factory, organizer):
    owner = user_factory("owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.post(
        "/api/auth/login/",
        {"email": "owner@example.com", "password": "tripos-test-password"},
        format="json",
    )

    response = client.get(f"/api/operations/dashboard/?organizer={organizer.id}")

    assert response.status_code == 200
    assert response.json()["active_organizer"]["id"] == organizer.id
    assert response.json()["membership"]["role"] == OrganizerMembership.Role.OWNER


def test_signed_in_user_can_create_organizer_and_becomes_owner():
    client = APIClient(enforce_csrf_checks=True)
    signup_response = client.post(
        "/api/auth/signup/",
        {
            "email": "fresh-owner@example.com",
            "password": "local-auth-password-123",
            "first_name": "Mira",
        },
        format="json",
    )

    response = client.post(
        "/api/onboarding/organizer/",
        {"name": "Western Ghats Weekenders"},
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        format="json",
    )

    assert signup_response.status_code == 201
    assert response.status_code == 201
    payload = response.json()
    organizer = Organizer.objects.get(name="Western Ghats Weekenders")
    membership = OrganizerMembership.objects.get(
        user__email="fresh-owner@example.com",
        organizer=organizer,
    )
    assert membership.role == OrganizerMembership.Role.OWNER
    assert organizer.identity_name == "Western Ghats Weekenders"
    assert organizer.identity_logo.name == ""
    assert organizer.identity_logo_url == ""
    assert organizer.provider_payment_setup.status == ProviderPaymentSetup.Status.NOT_STARTED
    assert payload["onboarding"]["state"] == "organizer_ready"
    assert payload["onboarding"]["next_route"] == "/home"
    assert payload["onboarding"]["trip_count"] == 0
    assert payload["onboarding"]["organizer"]["membership_role"] == OrganizerMembership.Role.OWNER


def test_organizer_onboarding_requires_authenticated_session():
    client = APIClient()

    response = client.post(
        "/api/onboarding/organizer/",
        {"name": "Unauthenticated Collective"},
        format="json",
    )

    assert response.status_code == 403
    assert Organizer.objects.filter(name="Unauthenticated Collective").exists() is False


def test_organizer_onboarding_rejects_existing_members_including_operators(
    user_factory,
    organizer,
):
    operator = user_factory("operator-onboard@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        "/api/onboarding/organizer/",
        {"name": "Takeover Attempt"},
        format="json",
    )

    assert response.status_code == 403
    assert Organizer.objects.filter(name="Takeover Attempt").exists() is False
    assert operator.organizer_memberships.count() == 1


def test_operator_permissions_still_apply_with_local_session(user_factory, organizer):
    operator = user_factory("operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    client = APIClient()
    client.post(
        "/api/auth/login/",
        {"email": "operator@example.com", "password": "tripos-test-password"},
        format="json",
    )

    response = client.patch(
        f"/api/organizers/{organizer.id}/identity/",
        {"identity_name": "Field Team Collective"},
        format="json",
    )

    assert response.status_code == 403


def test_owner_can_create_paid_draft_trip_before_provider_payment_setup_is_complete(
    user_factory,
    organizer,
):
    owner = user_factory("trip-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)
    organizer.provider_payment_setup.refresh_from_db()

    response = client.post(
        f"/api/organizers/{organizer.id}/trips/",
        trip_setup_payload(),
        format="json",
    )

    assert response.status_code == 201
    assert organizer.provider_payment_setup.status == ProviderPaymentSetup.Status.NOT_STARTED
    payload = response.json()
    assert payload["title"] == "Spiti Winter Field Week"
    assert payload["publication_state"] == Trip.PublicationState.DRAFT
    assert payload["booking_availability"] == Trip.BookingAvailability.CLOSED
    assert payload["effective_booking_availability"] == Trip.BookingAvailability.CLOSED
    assert payload["capacity"] == 24
    assert payload["available_seats"] == 24
    assert payload["packages"][0]["price_inr"] == 32000
    assert payload["packages"][0]["reservation_amount_inr"] == 8000
    assert payload["payment_schedule"]["reservation_milestone"]["due"] == "immediate"
    assert payload["payment_schedule"]["has_balance_milestone"] is True
    assert payload["payment_schedule"]["balance_due_date"] == "2026-09-26"
    assert payload["public_url_path"] == f"/trips/{organizer.slug}/spiti-winter-field-week"


def test_session_owner_can_create_trip_from_trips_management_with_csrf(user_factory, organizer):
    owner = user_factory("session-trip-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient(enforce_csrf_checks=True)
    login_response = client.post(
        "/api/auth/login/",
        {"email": "session-trip-owner@example.com", "password": "tripos-test-password"},
        format="json",
    )

    response = client.post(
        f"/api/organizers/{organizer.id}/trips/",
        trip_setup_payload(
            requires_traveler_identity_details=True,
            requires_emergency_contact=True,
            requires_full_payment_before_confirmation=True,
        ),
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        format="json",
    )

    assert login_response.status_code == 200
    assert response.status_code == 201
    payload = response.json()
    assert payload["publication_state"] == Trip.PublicationState.DRAFT
    assert payload["booking_availability"] == Trip.BookingAvailability.CLOSED
    assert payload["requires_traveler_identity_details"] is True
    assert payload["requires_emergency_contact"] is True
    assert payload["requires_full_payment_before_confirmation"] is True
    assert organizer.trips.count() == 1


def test_operator_cannot_create_trip(user_factory, organizer):
    operator = user_factory("operator-create-trip@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/organizers/{organizer.id}/trips/",
        trip_setup_payload(),
        format="json",
    )

    assert response.status_code == 403
    assert "Only Owners can create Trips" in str(response.json())
    assert organizer.trips.count() == 0


def test_trip_setup_requires_at_least_one_package(user_factory, organizer):
    owner = user_factory("package-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        f"/api/organizers/{organizer.id}/trips/",
        trip_setup_payload(packages=[]),
        format="json",
    )

    assert response.status_code == 400
    assert "packages" in response.json()


def test_package_reservation_amount_cannot_exceed_price(user_factory, organizer):
    owner = user_factory("money-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    payload = trip_setup_payload(
        packages=[
            {
                "name": "Premium",
                "price_inr": 12000,
                "reservation_amount_inr": 15000,
                "position": 1,
            }
        ]
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(f"/api/organizers/{organizer.id}/trips/", payload, format="json")

    assert response.status_code == 400
    assert "reservation_amount_inr" in str(response.json())


def test_trip_setup_validates_scheduled_date_range(user_factory, organizer):
    owner = user_factory("date-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        f"/api/organizers/{organizer.id}/trips/",
        trip_setup_payload(start_date="2026-10-15", end_date="2026-10-10"),
        format="json",
    )

    assert response.status_code == 400
    assert "end_date" in response.json()


def test_operator_can_prepare_content_and_close_booking_but_cannot_launch_or_change_capacity(
    user_factory,
    organizer,
):
    owner = user_factory("launch-owner@example.com")
    operator = user_factory("launch-operator@example.com")
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
    trip = create_trip(organizer)
    make_trip_profile_publication_ready(trip, owner)
    client = APIClient()

    client.force_authenticate(operator)
    content_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"itinerary": "Day 1: revised arrival plan."},
        format="json",
    )
    capacity_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"capacity": 40},
        format="json",
    )
    publish_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"publication_state": Trip.PublicationState.PUBLISHED},
        format="json",
    )
    open_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"booking_availability": Trip.BookingAvailability.OPEN},
        format="json",
    )

    client.force_authenticate(owner)
    owner_provider_blocked_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {
            "publication_state": Trip.PublicationState.PUBLISHED,
            "publish_lock_acknowledged": True,
            "booking_availability": Trip.BookingAvailability.OPEN,
        },
        format="json",
    )
    mark_online_payment_ready(organizer)
    owner_open_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {
            "publication_state": Trip.PublicationState.PUBLISHED,
            "publish_lock_acknowledged": True,
            "booking_availability": Trip.BookingAvailability.OPEN,
        },
        format="json",
    )

    client.force_authenticate(operator)
    close_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"booking_availability": Trip.BookingAvailability.CLOSED},
        format="json",
    )

    assert content_response.status_code == 200
    assert content_response.json()["itinerary"] == "Day 1: revised arrival plan."
    assert capacity_response.status_code == 400
    assert publish_response.status_code == 400
    assert open_response.status_code == 400
    assert owner_provider_blocked_response.status_code == 400
    assert "payment_method_readiness" in owner_provider_blocked_response.json()
    assert owner_open_response.status_code == 200
    assert close_response.status_code == 200
    assert close_response.json()["booking_availability"] == Trip.BookingAvailability.CLOSED


def test_launch_manual_payment_availability_owner_controls_and_operator_readonly(
    user_factory,
    organizer,
):
    owner = user_factory("manual-launch-owner@example.com")
    operator = user_factory("manual-launch-operator@example.com")
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
    trip = create_trip(organizer)
    make_trip_profile_publication_ready(trip, owner)
    client = APIClient()
    client.force_authenticate(owner)

    publish_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {
            "publication_state": Trip.PublicationState.PUBLISHED,
            "publish_lock_acknowledged": True,
        },
        format="json",
    )
    booking_closed_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"manual_payment_availability": Trip.ManualPaymentAvailability.OPEN},
        format="json",
    )
    missing_instructions_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {
            "booking_availability": Trip.BookingAvailability.OPEN,
            "manual_payment_availability": Trip.ManualPaymentAvailability.OPEN,
        },
        format="json",
    )

    ManualPaymentInstructions.objects.create(
        organizer=organizer,
        payment_qr="manual-payment-qr/payment-qr.png",
        original_filename="payment-qr.png",
        content_type="image/png",
        file_size=128,
    )
    open_manual_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {
            "booking_availability": Trip.BookingAvailability.OPEN,
            "manual_payment_availability": Trip.ManualPaymentAvailability.OPEN,
        },
        format="json",
    )

    client.force_authenticate(operator)
    operator_view_response = client.get(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/"
    )
    operator_close_manual_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"manual_payment_availability": Trip.ManualPaymentAvailability.CLOSED},
        format="json",
    )

    client.force_authenticate(owner)
    owner_close_manual_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"manual_payment_availability": Trip.ManualPaymentAvailability.CLOSED},
        format="json",
    )

    assert publish_response.status_code == 200
    assert booking_closed_response.status_code == 400
    assert "manual_payment_availability" in booking_closed_response.json()
    assert missing_instructions_response.status_code == 400
    assert "Manual Payment Instructions" in str(missing_instructions_response.json())
    assert open_manual_response.status_code == 200
    assert open_manual_response.json()["booking_availability"] == Trip.BookingAvailability.OPEN
    assert (
        open_manual_response.json()["manual_payment_availability"]
        == Trip.ManualPaymentAvailability.OPEN
    )
    assert open_manual_response.json()["launch_readiness"]["ready"] is True
    assert (
        open_manual_response.json()["launch_readiness"]["provider_payment_method"]["ready"]
        is False
    )
    assert (
        open_manual_response.json()["launch_readiness"]["manual_payment_method"]["ready"]
        is True
    )
    assert (
        open_manual_response.json()["launch_readiness"]["ready_payment_method_ids"]
        == ["qr_manual_payments"]
    )
    assert operator_view_response.status_code == 200
    assert (
        operator_view_response.json()["manual_payment_availability"]
        == Trip.ManualPaymentAvailability.OPEN
    )
    assert (
        operator_view_response.json()["launch_readiness"]["manual_payment_method"]["ready"]
        is True
    )
    assert operator_close_manual_response.status_code == 400
    assert "manual_payment_availability" in operator_close_manual_response.json()
    assert owner_close_manual_response.status_code == 200
    assert (
        owner_close_manual_response.json()["manual_payment_availability"]
        == Trip.ManualPaymentAvailability.CLOSED
    )
    assert (
        owner_close_manual_response.json()["launch_readiness"]["manual_payment_method"][
            "blocker_code"
        ]
        == "manual_payment_availability_closed"
    )


def test_public_trip_page_publication_does_not_require_provider_payment_setup(
    user_factory,
    organizer,
):
    owner = user_factory("publish-before-setup-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    make_trip_profile_publication_ready(trip, owner)
    client = APIClient()
    client.force_authenticate(owner)

    publish_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {
            "publication_state": Trip.PublicationState.PUBLISHED,
            "publish_lock_acknowledged": True,
        },
        format="json",
    )
    trip.refresh_from_db()
    public_response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")
    open_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"booking_availability": Trip.BookingAvailability.OPEN},
        format="json",
    )

    assert organizer.provider_payment_setup.status == ProviderPaymentSetup.Status.NOT_STARTED
    assert publish_response.status_code == 200
    assert publish_response.json()["publication_state"] == Trip.PublicationState.PUBLISHED
    assert public_response.status_code == 200
    assert public_response.json()["public_booking_gate"]["reason_code"] == "booking_closed"
    assert open_response.status_code == 400
    assert "payment_method_readiness" in open_response.json()


def test_operator_cannot_change_package_commercial_terms(user_factory, organizer):
    operator = user_factory("terms-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(operator)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {
            "packages": [
                {
                    "name": "Standard shared room",
                    "price_inr": 36000,
                    "reservation_amount_inr": 9000,
                    "position": 1,
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 400
    assert "packages" in response.json()


def test_public_trip_booking_readiness_checks_publication_booking_provider_and_capacity(
    organizer,
):
    trip = create_trip(organizer, capacity=2)
    client = APIClient()

    draft_response = client.get(f"/api/public/trips/{trip.id}/booking-readiness/")
    trip.publication_state = Trip.PublicationState.PUBLISHED
    trip.booking_availability = Trip.BookingAvailability.OPEN
    trip.save()
    provider_blocked_response = client.get(f"/api/public/trips/{trip.id}/booking-readiness/")
    mark_online_payment_ready(organizer)
    ready_response = client.get(f"/api/public/trips/{trip.id}/booking-readiness/")
    capacity_blocked_response = client.get(
        f"/api/public/trips/{trip.id}/booking-readiness/?requested_seats=3"
    )
    sold_out_trip = create_bookable_trip(
        organizer,
        title="Sold Out Spiti Field Week",
        capacity=1,
    )
    sold_out_package = sold_out_trip.packages.first()
    sold_out_booking = Booking.objects.create(
        trip=sold_out_trip,
        booking_contact_name="Rahul Menon",
        booking_contact_phone="+919123456789",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(
        booking=sold_out_booking,
        package=sold_out_package,
        position=1,
    )
    sold_out_response = client.get(f"/api/public/trips/{sold_out_trip.id}/booking-readiness/")

    assert draft_response.status_code == 200
    assert draft_response.json()["ready"] is False
    assert draft_response.json()["publication_ready"] is False
    assert draft_response.json()["reason_code"] == "publication_not_published"
    assert provider_blocked_response.json()["booking_availability_open"] is True
    assert provider_blocked_response.json()["provider_payment_setup_complete"] is False
    assert provider_blocked_response.json()["online_payment_readiness_ready"] is False
    assert provider_blocked_response.json()["reason_code"] == ("payment_method_readiness_missing")
    assert ready_response.json()["ready"] is True
    assert ready_response.json()["reason_code"] == "ready"
    assert ready_response.json()["cta_state"] == "enabled"
    assert ready_response.json()["requested_seats"] == 1
    assert ready_response.json()["available_seats"] == 2
    assert ready_response.json()["active_seat_holds"] == 0
    assert ready_response.json()["bookable_seats"] == 2
    assert ready_response.json()["effective_booking_availability"] == "open"
    assert ready_response.json()["availability_band"] == "few_seats_left"
    assert capacity_blocked_response.json()["ready"] is False
    assert capacity_blocked_response.json()["capacity_available"] is False
    assert capacity_blocked_response.json()["cta_state"] == "disabled"
    assert capacity_blocked_response.json()["requested_seats"] == 3
    assert capacity_blocked_response.json()["reason_code"] == "insufficient_capacity"
    assert sold_out_response.json()["ready"] is False
    assert sold_out_response.json()["reason_code"] == "sold_out"
    assert sold_out_response.json()["available_seats"] == 0
    assert sold_out_response.json()["effective_booking_availability"] == "sold_out"
    assert sold_out_response.json()["availability_band"] == "sold_out"


def test_sold_out_booking_availability_is_derived_from_available_seats(organizer):
    trip = create_trip(organizer, capacity=1)

    assert available_seats(trip) == 1
    assert effective_booking_availability(trip) == Trip.BookingAvailability.CLOSED

    trip.booking_availability = Trip.BookingAvailability.OPEN
    trip.capacity = 0

    assert effective_booking_availability(trip) == "sold_out"


@override_settings(MEDIA_ROOT="/private/tmp/tripos-organizer-logo-test-media")
def test_public_trip_page_renders_published_trip_content_with_gate_decision(organizer):
    organizer.identity_name = "Kaza Field Collective"
    organizer.identity_whatsapp_number = "+91 98765 43210"
    organizer.identity_logo = SimpleUploadedFile(
        "kaza.png",
        PNG_LOGO_BYTES,
        content_type="image/png",
    )
    organizer.save()
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
    )
    TripPackage.objects.create(
        trip=trip,
        name="Private room",
        description="Private room for two travelers.",
        price_inr=42000,
        reservation_amount_inr=12000,
        position=2,
    )
    mark_online_payment_ready(organizer)
    client = APIClient()

    response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == trip.title
    assert payload["public_url_path"] == f"/trips/{organizer.slug}/{trip.slug}"
    assert payload["organizer_identity"]["name"] == "Kaza Field Collective"
    assert payload["organizer_identity"]["identity_whatsapp_number"] == "+91 98765 43210"
    assert payload["organizer_identity"]["logo_uploaded"] is True
    assert payload["organizer_identity"]["logo_url"].startswith(
        "http://testserver/media/organizer-logos/"
    )
    assert payload["organizer_identity"]["fallback"]["initials"] == "KF"
    assert payload["itinerary"] == "Day 1: Chandigarh arrival. Day 2: Transit to Kaza."
    assert payload["packages"][0]["price_inr"] == 32000
    assert payload["packages"][0]["reservation_amount_inr"] == 8000
    assert payload["payment_schedule"]["balance_due_date"] == "2026-09-26"
    assert payload["availability_band"] == "available"
    assert payload["availability_band_label"] == "Available"
    assert payload["public_booking_gate"]["cta_enabled"] is True
    assert payload["public_booking_gate"]["ready"] is True
    assert payload["public_booking_gate"]["reason_code"] == "ready"
    assert payload["public_booking_gate"]["requested_seats"] == 1
    assert payload["public_booking_gate"]["available_seats"] == 24
    assert payload["public_booking_gate"]["active_seat_holds"] == 0
    assert payload["public_booking_gate"]["bookable_seats"] == 24
    assert payload["public_booking_gate"]["cta_state"] == "enabled"
    assert payload["public_booking_gate"]["effective_booking_availability"] == "open"
    assert payload["public_booking_gate"]["availability_band"] == "available"
    assert "available_seats" not in payload


def test_missing_organizer_logo_does_not_block_public_booking_gate(organizer):
    organizer.identity_name = "Kaza Field Collective"
    organizer.save()
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
    )
    mark_online_payment_ready(organizer)
    client = APIClient()

    response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["organizer_identity"]["logo_uploaded"] is False
    assert payload["organizer_identity"]["logo_url"] == ""
    assert payload["organizer_identity"]["fallback"]["initials"] == "KF"
    assert payload["public_booking_gate"]["ready"] is True
    assert payload["public_booking_gate"]["reason_code"] == "ready"


@pytest.mark.parametrize(
    "publication_state",
    [Trip.PublicationState.DRAFT, Trip.PublicationState.ARCHIVED],
)
def test_draft_and_archived_publications_are_not_publicly_visible(
    organizer,
    publication_state,
):
    trip = create_trip(organizer, publication_state=publication_state)
    client = APIClient()

    response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    assert response.status_code == 404


def test_public_trip_page_keeps_published_visibility_separate_from_booking_availability(
    organizer,
):
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.CLOSED,
    )
    mark_online_payment_ready(organizer)
    client = APIClient()

    response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["publication_state"] == Trip.PublicationState.PUBLISHED
    assert payload["booking_availability"] == Trip.BookingAvailability.CLOSED
    assert payload["effective_booking_availability"] == Trip.BookingAvailability.CLOSED
    assert payload["public_booking_gate"]["cta_enabled"] is False
    assert payload["public_booking_gate"]["ready"] is False
    assert payload["public_booking_gate"]["reason_code"] == "booking_closed"
    assert payload["public_booking_gate"]["available_seats"] == 24
    assert payload["public_booking_gate"]["effective_booking_availability"] == "closed"
    assert payload["public_booking_gate"]["availability_band"] == "available"
    assert payload["public_booking_gate"]["message"] == "Bookings opening soon."


def test_public_trip_page_blocks_cta_until_provider_payment_setup_is_complete(organizer):
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
    )
    client = APIClient()

    response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["public_booking_gate"]["cta_enabled"] is False
    assert payload["public_booking_gate"]["reason_code"] == ("payment_method_readiness_missing")
    assert payload["public_booking_gate"]["booking_availability_open"] is True
    assert payload["public_booking_gate"]["online_payment_readiness_ready"] is False
    assert payload["public_booking_gate"]["provider_payment_setup_complete"] is False
    assert payload["public_booking_gate"]["effective_booking_availability"] == "open"
    assert payload["public_booking_gate"]["availability_band"] == "available"
    assert payload["public_booking_gate"]["message"] == "Bookings opening soon."


def test_public_trip_page_opens_with_ready_manual_payment_method(organizer):
    create_ready_manual_payment_instructions(organizer)
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
        manual_payment_availability=Trip.ManualPaymentAvailability.OPEN,
    )
    client = APIClient()

    response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    assert response.status_code == 200
    payload = response.json()
    gate = payload["public_booking_gate"]
    assert gate["ready"] is True
    assert gate["reason_code"] == "ready"
    assert gate["online_payment_readiness_ready"] is False
    assert gate["provider_payment_method"]["ready"] is False
    assert gate["manual_payment_method"]["ready"] is True
    assert gate["ready_payment_method_ids"] == ["qr_manual_payments"]
    assert payload["manual_payment_instructions"] == {
        "ready": True,
        "message": (
            "Scan the Payment QR and submit Payment Proof for Organizer review."
        ),
        "payment_qr_url": "http://testserver/media/manual-payment-qr/payment-qr.png",
        "upi_id": "trips@example",
        "account_name": "Himalayan Monsoon Cohort",
        "bank_transfer_details": "Bank transfer reference HMC Spiti",
    }


def test_public_trip_page_exposes_both_ready_payment_methods(organizer):
    create_ready_manual_payment_instructions(organizer)
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
        manual_payment_availability=Trip.ManualPaymentAvailability.OPEN,
    )
    mark_online_payment_ready(organizer)
    client = APIClient()

    response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    assert response.status_code == 200
    payload = response.json()
    gate = payload["public_booking_gate"]
    assert gate["ready"] is True
    assert gate["online_payment_readiness_ready"] is True
    assert gate["provider_payment_method"]["ready"] is True
    assert gate["manual_payment_method"]["ready"] is True
    assert gate["ready_payment_method_ids"] == [
        "provider_payments",
        "qr_manual_payments",
    ]
    assert payload["manual_payment_instructions"]["payment_qr_url"].startswith(
        "http://testserver/media/manual-payment-qr/"
    )


def test_public_trip_page_hides_manual_payment_instructions_when_availability_closed(
    organizer,
):
    create_ready_manual_payment_instructions(organizer)
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
        manual_payment_availability=Trip.ManualPaymentAvailability.CLOSED,
    )
    client = APIClient()

    response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["public_booking_gate"]["ready"] is False
    assert payload["public_booking_gate"]["reason_code"] == (
        "payment_method_readiness_missing"
    )
    assert payload["public_booking_gate"]["manual_payment_method"]["ready"] is False
    assert payload["manual_payment_instructions"] is None


def test_public_trip_page_hides_manual_payment_instructions_when_sold_out(organizer):
    create_ready_manual_payment_instructions(organizer)
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
        manual_payment_availability=Trip.ManualPaymentAvailability.OPEN,
        capacity=1,
    )
    package = trip.packages.first()
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Rahul Menon",
        booking_contact_phone="+919123456789",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=booking, package=package, position=1)
    client = APIClient()

    response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["public_booking_gate"]["reason_code"] == "sold_out"
    assert payload["public_booking_gate"]["manual_payment_method"]["ready"] is False
    assert payload["manual_payment_instructions"] is None


def test_public_booking_gate_requires_online_payment_readiness_not_setup_completion(
    organizer,
):
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
    )
    package = trip.packages.first()
    organizer.provider_payment_setup.status = ProviderPaymentSetup.Status.COMPLETE
    organizer.provider_payment_setup.authorization_state = (
        ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    )
    organizer.provider_payment_setup.provider_verification_status = (
        ProviderPaymentSetup.ProviderVerificationStatus.VERIFIED
    )
    organizer.provider_payment_setup.provider_payment_capability_enabled = True
    organizer.provider_payment_setup.provider_connection_state = (
        ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    )
    organizer.provider_payment_setup.provider_mode = ProviderPaymentSetup.ProviderMode.LIVE
    organizer.provider_payment_setup.save()
    client = APIClient()

    page_response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")
    draft_response = client.post(
        f"/api/public/trips/{organizer.slug}/{trip.slug}/draft-bookings/",
        {
            "booking_contact_name": "Asha Nair",
            "booking_contact_phone": "+919876543210",
            "traveler_slots": [{"package": package.id}],
        },
        format="json",
    )

    gate = page_response.json()["public_booking_gate"]
    assert page_response.status_code == 200
    assert gate["provider_payment_setup_complete"] is True
    assert gate["online_payment_readiness_ready"] is False
    assert gate["online_payment_readiness_blocker_code"] == "settlement_readiness_not_ready"
    assert gate["reason_code"] == "payment_method_readiness_missing"
    assert gate["message"] == "Bookings opening soon."
    assert draft_response.status_code == 400
    assert draft_response.json()["public_booking_gate"]["reason_code"] == (
        "payment_method_readiness_missing"
    )
    assert Booking.objects.filter(trip=trip).count() == 0


def test_public_trip_page_uses_gate_decision_for_sold_out_booking_availability(organizer):
    trip = create_bookable_trip(
        organizer,
        title="Sold Out Public Field Week",
        capacity=1,
    )
    package = trip.packages.first()
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Rahul Menon",
        booking_contact_phone="+919123456789",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=booking, package=package, position=1)
    client = APIClient()

    response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["public_booking_gate"]["ready"] is False
    assert payload["public_booking_gate"]["reason_code"] == "sold_out"
    assert payload["public_booking_gate"]["available_seats"] == 0
    assert payload["public_booking_gate"]["capacity_available"] is False
    assert payload["public_booking_gate"]["effective_booking_availability"] == "sold_out"
    assert payload["public_booking_gate"]["effective_booking_availability_label"] == "Sold out"
    assert payload["public_booking_gate"]["availability_band"] == "sold_out"
    assert payload["public_booking_gate"]["availability_band_label"] == "Sold out"
    assert payload["public_booking_gate"]["message"] == "Sold out."


def test_public_availability_bands_are_conservative_and_do_not_expose_counts(organizer):
    available_trip = create_trip(organizer, capacity=24)
    few_left_trip = create_trip(organizer, title="Few Left Field Week", capacity=3)
    sold_out_trip = create_trip(organizer, title="Sold Out Field Week", capacity=1)
    sold_out_trip.capacity = 0

    assert public_availability_band(available_trip) == "available"
    assert public_availability_band(few_left_trip) == "few_seats_left"
    assert public_availability_band(sold_out_trip) == "sold_out"
    assert effective_booking_availability(sold_out_trip) == Trip.BookingAvailability.CLOSED


def test_public_sold_out_band_is_derived_without_changing_booking_availability(organizer):
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
        capacity=1,
    )
    trip.capacity = 0

    assert public_availability_band(trip) == "sold_out"
    assert effective_booking_availability(trip) == "sold_out"
    assert trip.booking_availability == Trip.BookingAvailability.OPEN


def test_booking_contact_can_start_draft_booking_from_bookable_public_trip_page(organizer):
    trip = create_bookable_trip(organizer)
    package = trip.packages.first()
    client = APIClient()

    before_create = timezone.now()
    response = client.post(
        f"/api/public/trips/{organizer.slug}/{trip.slug}/draft-bookings/",
        {
            "booking_contact_name": "  Asha Nair  ",
            "booking_contact_phone": "  +919876543210  ",
            "booking_contact_email": "  asha@example.com  ",
            "traveler_slots": [{"package": package.id}, {"package": package.id}],
        },
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    booking = Booking.objects.get(pk=payload["id"])
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert booking.booking_contact_name == "Asha Nair"
    assert payload["booking_contact"] == {
        "name": "Asha Nair",
        "phone": "+919876543210",
        "email": "asha@example.com",
    }
    assert booking.traveler_slots.count() == 2
    assert payload["booking_reservation_amount_inr"] == 16000
    assert before_create + timedelta(hours=23, minutes=59) <= booking.draft_expires_at
    assert booking.draft_expires_at <= before_create + timedelta(hours=24, minutes=1)


def test_public_draft_booking_accepts_count_and_package_without_traveler_identity(
    organizer,
):
    trip = create_bookable_trip(organizer)
    package = trip.packages.first()
    client = APIClient()

    response = client.post(
        f"/api/public/trips/{organizer.slug}/{trip.slug}/draft-bookings/",
        {
            "booking_contact_name": "Asha Nair",
            "booking_contact_phone": "+919876543210",
            "booking_contact_email": "asha@example.com",
            "traveler_count": 3,
            "package": package.id,
        },
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    booking = Booking.objects.get(pk=payload["id"])
    slots = list(booking.traveler_slots.order_by("position"))
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert booking.traveler_slot_count == 3
    assert [slot.position for slot in slots] == [1, 2, 3]
    assert {slot.package_id for slot in slots} == {package.id}
    assert all(not slot.is_traveler for slot in slots)
    assert payload["booking_reservation_amount_inr"] == 24000
    assert payload["booking_total_inr"] == 96000
    assert BookingAccessLink.objects.filter(booking=booking).count() == 0


def test_public_draft_booking_rejects_traveler_identity_details_before_payment(
    organizer,
):
    trip = create_bookable_trip(organizer)
    package = trip.packages.first()
    client = APIClient()

    response = client.post(
        f"/api/public/trips/{organizer.slug}/{trip.slug}/draft-bookings/",
        {
            "booking_contact_name": "Asha Nair",
            "booking_contact_phone": "+919876543210",
            "traveler_slots": [
                {
                    "package": package.id,
                    "traveler_full_name": "Riya Shah",
                    "traveler_phone": "+919800000001",
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 400
    assert "Traveler Identity Details" in str(response.json())
    assert Booking.objects.filter(booking_contact_name="Asha Nair").count() == 0


@pytest.mark.parametrize(
    ("missing_field", "expected_field"),
    [
        ("booking_contact_name", "booking_contact_name"),
        ("booking_contact_phone", "booking_contact_phone"),
    ],
)
def test_draft_booking_requires_booking_contact_name_and_phone(
    organizer,
    missing_field,
    expected_field,
):
    trip = create_bookable_trip(organizer)
    package = trip.packages.first()
    payload = {
        "booking_contact_name": "Asha Nair",
        "booking_contact_phone": "+919876543210",
        "traveler_slots": [{"package": package.id}],
    }
    payload.pop(missing_field)
    client = APIClient()

    response = client.post(
        f"/api/public/trips/{organizer.slug}/{trip.slug}/draft-bookings/",
        payload,
        format="json",
    )

    assert response.status_code == 400
    assert expected_field in response.json()


def test_draft_booking_requires_traveler_slots_and_package_selection(organizer):
    trip = create_bookable_trip(organizer)
    client = APIClient()

    no_slots_response = client.post(
        f"/api/public/trips/{organizer.slug}/{trip.slug}/draft-bookings/",
        {
            "booking_contact_name": "Asha Nair",
            "booking_contact_phone": "+919876543210",
            "traveler_slots": [],
        },
        format="json",
    )
    no_package_response = client.post(
        f"/api/public/trips/{organizer.slug}/{trip.slug}/draft-bookings/",
        {
            "booking_contact_name": "Asha Nair",
            "booking_contact_phone": "+919876543210",
            "traveler_slots": [{}],
        },
        format="json",
    )

    assert no_slots_response.status_code == 400
    assert "traveler_slots" in no_slots_response.json()
    assert no_package_response.status_code == 400
    assert "package" in str(no_package_response.json())


def test_draft_booking_is_blocked_when_public_trip_page_is_not_bookable(organizer):
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.CLOSED,
    )
    package = trip.packages.first()
    mark_online_payment_ready(organizer)
    client = APIClient()

    response = client.post(
        f"/api/public/trips/{organizer.slug}/{trip.slug}/draft-bookings/",
        {
            "booking_contact_name": "Asha Nair",
            "booking_contact_phone": "+919876543210",
            "traveler_slots": [{"package": package.id}],
        },
        format="json",
    )

    assert response.status_code == 400
    assert "public_booking_gate" in response.json()
    assert response.json()["public_booking_gate"]["reason_code"] == "booking_closed"


def test_draft_booking_uses_gate_decision_when_provider_payment_setup_is_missing(
    organizer,
):
    trip = create_trip(
        organizer,
        title="Provider Blocked Public Field Week",
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
    )
    package = trip.packages.first()
    client = APIClient()

    response = client.post(
        f"/api/public/trips/{organizer.slug}/{trip.slug}/draft-bookings/",
        {
            "booking_contact_name": "Asha Nair",
            "booking_contact_phone": "+919876543210",
            "traveler_slots": [{"package": package.id}],
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["public_booking_gate"]["reason_code"] == (
        "payment_method_readiness_missing"
    )


def test_draft_booking_does_not_affect_available_seats_or_reserved_traveler_count(organizer):
    trip = create_bookable_trip(organizer, capacity=2)
    package = trip.packages.first()
    client = APIClient()

    response = client.post(
        f"/api/public/trips/{organizer.slug}/{trip.slug}/draft-bookings/",
        {
            "booking_contact_name": "Asha Nair",
            "booking_contact_phone": "+919876543210",
            "traveler_slots": [{"package": package.id}, {"package": package.id}],
        },
        format="json",
    )

    assert response.status_code == 201
    assert active_reserved_traveler_count(trip) == 0
    assert available_seats(trip) == 2
    assert public_availability_band(trip) == "few_seats_left"
    assert SeatHold.objects.filter(booking_id=response.json()["id"]).count() == 0


def test_reserved_booking_affects_available_seats_but_draft_booking_does_not(organizer):
    trip = create_bookable_trip(organizer, capacity=3)
    package = trip.packages.first()
    draft_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.DRAFT,
    )
    TravelerSlot.objects.create(booking=draft_booking, package=package, position=1)
    reserved_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Rahul Menon",
        booking_contact_phone="+919123456789",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=reserved_booking, package=package, position=1)

    assert active_reserved_traveler_count(trip) == 1
    assert available_seats(trip) == 2


@override_settings(TRIPOS_SEAT_HOLD_SECONDS=300)
def test_reservation_payment_attempt_creates_short_lived_seat_hold(organizer):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)

    assert SeatHold.objects.filter(booking=booking).count() == 0
    assert available_seats(trip) == 2
    assert bookable_seats(trip) == 2

    before_create = timezone.now()
    payment_attempt = create_public_payment_attempt(booking)
    after_create = timezone.now()

    seat_hold = SeatHold.objects.get(payment_attempt=payment_attempt)
    readiness = public_booking_readiness(trip)
    assert seat_hold.booking == booking
    assert seat_hold.trip == trip
    assert seat_hold.seat_count == 2
    assert seat_hold.released_at is None
    assert before_create + timedelta(seconds=300) <= seat_hold.expires_at
    assert seat_hold.expires_at <= after_create + timedelta(seconds=300)
    assert available_seats(trip) == 2
    assert active_seat_hold_count(trip) == 2
    assert bookable_seats(trip) == 0
    assert readiness.available_seats == 2
    assert readiness.active_seat_holds == 2
    assert readiness.bookable_seats == 0
    assert readiness.reason_code == "sold_out"
    assert readiness.cta_state == "disabled"


@override_settings(TRIPOS_SEAT_HOLD_SECONDS=300)
def test_public_booking_gate_decision_owns_seat_hold_aware_capacity(organizer):
    trip = create_bookable_trip(organizer, capacity=2)
    package = trip.packages.first()
    held_booking = create_draft_booking(trip, slot_count=1, package=package)
    held_attempt = create_public_payment_attempt(held_booking)

    competing_gate = public_booking_gate_decision(trip, requested_seats=2)
    held_booking_gate = public_booking_gate_decision(
        trip,
        requested_seats=1,
        payment_attempt=held_attempt,
    )

    assert competing_gate.requested_seats == 2
    assert competing_gate.available_seats == 2
    assert competing_gate.active_seat_holds == 1
    assert competing_gate.bookable_seats == 1
    assert competing_gate.capacity_available is False
    assert competing_gate.reason_code == "insufficient_capacity"
    assert competing_gate.cta_enabled is False
    assert competing_gate.cta_state == "disabled"
    assert competing_gate.availability_band == "few_seats_left"
    assert competing_gate.effective_booking_availability == Trip.BookingAvailability.OPEN
    assert held_booking_gate.active_seat_holds == 1
    assert held_booking_gate.bookable_seats == 2
    assert held_booking_gate.capacity_available is True
    assert held_booking_gate.ready is True
    assert held_booking_gate.cta_state == "enabled"


def test_reservation_checkout_creates_purposeful_provider_order_payload(organizer):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)
    adapter = FakeCheckoutAdapter(provider_order_reference="order_reservation_checkout_001")

    checkout_session = create_public_reservation_checkout(booking, provider_adapter=adapter)
    payment_attempt = checkout_session.payment_attempt

    assert payment_attempt.purpose == PaymentAttempt.Purpose.RESERVATION
    assert payment_attempt.status == PaymentAttempt.Status.PENDING
    assert payment_attempt.provider == ProviderPaymentSetup.Provider.RAZORPAY
    assert payment_attempt.amount_inr == booking.booking_reservation_amount_inr
    assert payment_attempt.provider_attempt_reference == "order_reservation_checkout_001"
    assert adapter.requests[0].connected_provider_account_reference == (
        organizer.provider_payment_setup.provider_merchant_reference
    )
    assert adapter.requests[0].payment_purpose == PaymentAttempt.Purpose.RESERVATION
    assert checkout_session.checkout_payload["provider"] == ProviderPaymentSetup.Provider.RAZORPAY
    assert (
        checkout_session.checkout_payload["provider_order_reference"]
        == "order_reservation_checkout_001"
    )
    assert checkout_session.checkout_payload["amount_inr"] == payment_attempt.amount_inr
    assert checkout_session.checkout_payload["amount_minor"] == payment_attempt.amount_inr * 100
    assert checkout_session.checkout_payload["payment_purpose"] == (
        PaymentAttempt.Purpose.RESERVATION
    )


def test_reservation_checkout_creates_razorpay_order_with_active_credentials(
    organizer,
    fake_razorpay_order_creation,
):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)

    checkout_session = create_public_reservation_checkout(booking)

    payment_attempt = checkout_session.payment_attempt
    order_request = fake_razorpay_order_creation.requests[-1]
    request_payload = order_request["payload"]
    checkout_payload = checkout_session.checkout_payload
    serialized_checkout = payload_text(checkout_payload)
    assert order_request["headers"]["Authorization"] == (
        f"Bearer oauth_access_token_{organizer.id}"
    )
    assert request_payload["amount"] == payment_attempt.amount_inr * 100
    assert request_payload["currency"] == "INR"
    assert request_payload["receipt"] == f"tripos_res_{payment_attempt.id}_{booking.id}"
    assert request_payload["partial_payment"] is False
    assert request_payload["notes"] == {
        "tripos_organizer_id": str(organizer.id),
        "tripos_booking_id": str(booking.id),
        "tripos_payment_attempt_id": str(payment_attempt.id),
        "tripos_payment_purpose": PaymentAttempt.Purpose.RESERVATION,
        "tripos_provider_account": organizer.provider_payment_setup.provider_merchant_reference,
    }
    assert payment_attempt.provider_attempt_reference == (
        f"order_tripos_res_{payment_attempt.id}_{booking.id}"
    )
    assert checkout_payload["public_checkout_key"] == f"rzp_public_{organizer.id}"
    assert checkout_payload["provider_payload"]["key"] == f"rzp_public_{organizer.id}"
    assert checkout_payload["provider_payload"]["order_id"] == (
        payment_attempt.provider_attempt_reference
    )
    assert checkout_payload["display"]["name"] == organizer.display_identity_name
    assert checkout_payload["prefill"]["name"] == booking.booking_contact_name
    assert "oauth_access_token" not in serialized_checkout
    assert "oauth_refresh_token" not in serialized_checkout
    assert "key_secret" not in serialized_checkout


def test_public_checkout_blocks_when_provider_order_creation_capability_is_missing(
    organizer,
):
    trip = create_trip(
        organizer,
        title="Checkout Missing Order Capability Field Week",
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
    )
    booking = create_draft_booking(trip)
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
    client = APIClient()

    readiness_response = client.get(f"/api/public/organizers/{organizer.id}/booking-readiness/")
    checkout_response = client.post(f"/api/public/bookings/{booking.id}/payment-attempts/")

    assert readiness_response.status_code == 200
    assert readiness_response.json()["online_payment_readiness_ready"] is False
    assert (
        readiness_response.json()["online_payment_readiness_blocker_code"]
        == "provider_order_creation_unavailable"
    )
    assert checkout_response.status_code == 400
    assert "payment_method_readiness_missing" in str(checkout_response.json())
    assert PaymentAttempt.objects.filter(booking=booking).count() == 0


def test_reservation_checkout_uses_active_api_key_provider_credentials(
    organizer,
    fake_razorpay_order_creation,
):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip)
    SensitiveProviderCredentialStore().store_api_key_credentials(
        organizer=organizer,
        key_id="rzp_live_public_checkout_key",
        key_secret="rzp_live_secret_do_not_expose",
        provider_account_reference=organizer.provider_payment_setup.provider_merchant_reference,
        provider_mode=ProviderPaymentSetup.ProviderMode.LIVE,
        scopes=["orders"],
    )

    checkout_session = create_public_reservation_checkout(booking)

    order_request = fake_razorpay_order_creation.requests[-1]
    checkout_payload = checkout_session.checkout_payload
    assert order_request["headers"]["Authorization"].startswith("Basic ")
    assert checkout_payload["public_checkout_key"] == "rzp_live_public_checkout_key"
    assert checkout_payload["provider_payload"]["key"] == "rzp_live_public_checkout_key"
    assert "rzp_live_secret_do_not_expose" not in payload_text(checkout_payload)


def test_reservation_checkout_rolls_back_when_razorpay_order_creation_fails(
    organizer,
    monkeypatch,
):
    def failing_order_creation(request, timeout=None):
        raise URLError("provider unavailable")

    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)
    monkeypatch.setattr("trip_payments.provider_adapters.urlopen", failing_order_creation)

    with pytest.raises(ValidationError, match="provider order creation failed"):
        create_public_reservation_checkout(booking)

    assert PaymentAttempt.objects.filter(booking=booking).count() == 0
    assert SeatHold.objects.filter(booking=booking).count() == 0


def test_retry_supersedes_active_reservation_attempt_but_keeps_balance_attempt_distinct(
    organizer,
):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)
    first_checkout = create_public_reservation_checkout(
        booking,
        provider_adapter=FakeCheckoutAdapter("order_retry_first_001"),
    )
    balance_attempt = PaymentAttempt.objects.create(
        booking=booking,
        purpose=PaymentAttempt.Purpose.BALANCE,
        amount_inr=5000,
    )

    second_checkout = create_public_reservation_checkout(
        booking,
        provider_adapter=FakeCheckoutAdapter("order_retry_second_001"),
    )

    first_attempt = PaymentAttempt.objects.get(pk=first_checkout.payment_attempt.pk)
    second_attempt = PaymentAttempt.objects.get(pk=second_checkout.payment_attempt.pk)
    first_hold = SeatHold.objects.get(payment_attempt=first_attempt)
    second_hold = SeatHold.objects.get(payment_attempt=second_attempt)
    balance_attempt.refresh_from_db()
    assert first_attempt.status == PaymentAttempt.Status.SUPERSEDED
    assert first_attempt.failure_reason == "Superseded by a newer Payment Attempt."
    assert first_hold.released_at is not None
    assert second_attempt.status == PaymentAttempt.Status.PENDING
    assert second_attempt.purpose == PaymentAttempt.Purpose.RESERVATION
    assert second_hold.released_at is None
    assert balance_attempt.status == PaymentAttempt.Status.PENDING
    assert balance_attempt.purpose == PaymentAttempt.Purpose.BALANCE
    assert (
        PaymentAttempt.objects.filter(
            booking=booking,
            purpose=PaymentAttempt.Purpose.RESERVATION,
            status__in=[PaymentAttempt.Status.PENDING, PaymentAttempt.Status.CONFIRMING],
        ).count()
        == 1
    )
    assert (
        PaymentAttempt.objects.filter(
            booking=booking,
            purpose=PaymentAttempt.Purpose.BALANCE,
            status__in=[PaymentAttempt.Status.PENDING, PaymentAttempt.Status.CONFIRMING],
        ).count()
        == 1
    )


def test_booking_can_have_only_one_active_payment_attempt_per_purpose(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    PaymentAttempt.objects.create(
        booking=booking,
        purpose=PaymentAttempt.Purpose.RESERVATION,
        amount_inr=1000,
    )

    with pytest.raises((IntegrityError, ValidationError)):
        with transaction.atomic():
            PaymentAttempt.objects.create(
                booking=booking,
                purpose=PaymentAttempt.Purpose.RESERVATION,
                amount_inr=1200,
            )

    PaymentAttempt.objects.create(
        booking=booking,
        purpose=PaymentAttempt.Purpose.BALANCE,
        amount_inr=1200,
    )


def test_public_checkout_endpoint_returns_normalized_checkout_payload(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    client = APIClient()

    response = client.post(f"/api/public/bookings/{booking.id}/payment-attempts/")

    payload = response.json()
    attempt = PaymentAttempt.objects.get(pk=payload["id"])
    assert response.status_code == 201
    assert payload["purpose"] == PaymentAttempt.Purpose.RESERVATION
    assert payload["status"] == PaymentAttempt.Status.PENDING
    assert payload["provider_attempt_reference"].startswith("order_tripos_")
    assert payload["checkout"]["provider"] == ProviderPaymentSetup.Provider.RAZORPAY
    assert (
        payload["checkout"]["provider_order_reference"] == (payload["provider_attempt_reference"])
    )
    assert (
        payload["checkout"]["provider_payload"]["order_id"]
        == (payload["provider_attempt_reference"])
    )
    assert payload["checkout"]["public_checkout_key"] == f"rzp_public_{organizer.id}"
    assert payload["checkout"]["provider_payload"]["key"] == f"rzp_public_{organizer.id}"
    assert payload["checkout"]["payment_attempt"] == attempt.id
    assert payload["checkout"]["payment_purpose"] == PaymentAttempt.Purpose.RESERVATION
    assert "oauth_access_token" not in payload_text(payload["checkout"])
    assert "oauth_refresh_token" not in payload_text(payload["checkout"])


def test_active_seat_hold_blocks_public_booking_and_checkout_start(organizer):
    trip = create_bookable_trip(organizer, capacity=2)
    package = trip.packages.first()
    held_booking = create_draft_booking(trip, slot_count=2, package=package)
    create_public_payment_attempt(held_booking)
    client = APIClient()
    readiness = public_booking_readiness(trip)

    draft_response = client.post(
        f"/api/public/trips/{organizer.slug}/{trip.slug}/draft-bookings/",
        {
            "booking_contact_name": "Competing Contact",
            "booking_contact_phone": "+919111111111",
            "traveler_count": 1,
            "package": package.id,
        },
        format="json",
    )
    competing_booking = create_draft_booking(trip, package=package)
    checkout_response = client.post(
        f"/api/public/bookings/{competing_booking.id}/payment-attempts/"
    )

    assert available_seats(trip) == 2
    assert active_seat_hold_count(trip) == 2
    assert bookable_seats(trip) == 0
    assert readiness.available_seats == 2
    assert readiness.bookable_seats == 0
    assert draft_response.status_code == 400
    assert draft_response.json()["public_booking_gate"]["reason_code"] == "sold_out"
    assert checkout_response.status_code == 400
    assert "sold_out" in str(checkout_response.json())
    assert PaymentAttempt.objects.filter(booking=competing_booking).count() == 0


def test_expired_seat_hold_releases_bookable_capacity_without_payment_abandonment_reminder(
    organizer,
):
    trip = create_bookable_trip(organizer, capacity=1)
    booking = create_draft_booking(trip)
    payment_attempt = create_public_payment_attempt(booking)
    expired_at = timezone.now() - timedelta(seconds=1)
    SeatHold.objects.filter(payment_attempt=payment_attempt).update(expires_at=expired_at)

    reminder_run = process_automatic_reminders(now=timezone.now() + timedelta(minutes=10))

    assert available_seats(trip) == 1
    assert active_seat_hold_count(trip) == 0
    assert bookable_seats(trip) == 1
    assert public_booking_readiness(trip).ready is True
    assert reminder_run.total_notifications == 0
    assert Notification.objects.filter(booking=booking).count() == 0


def test_seat_holds_release_when_payment_attempt_fails_or_confirms(organizer):
    trip = create_bookable_trip(organizer, capacity=1)
    failed_booking = create_draft_booking(trip)
    failed_attempt = create_public_payment_attempt(failed_booking)

    fail_payment_attempt(failed_attempt, failure_reason="Provider declined the payment.")

    failed_hold = SeatHold.objects.get(payment_attempt=failed_attempt)
    assert failed_hold.released_at is not None
    assert bookable_seats(trip) == 1

    reserved_booking = create_draft_booking(trip)
    confirmed_attempt = create_public_payment_attempt(reserved_booking)
    confirm_provider_payment(
        confirmed_attempt,
        provider_payment_reference="pay_provider_releases_hold_001",
    )

    confirmed_hold = SeatHold.objects.get(payment_attempt=confirmed_attempt)
    reserved_booking.refresh_from_db()
    assert confirmed_hold.released_at is not None
    assert reserved_booking.booking_state == Booking.BookingState.RESERVED
    assert active_seat_hold_count(trip) == 0
    assert available_seats(trip) == 0
    assert bookable_seats(trip) == 0


def test_direct_or_post_reservation_payment_attempts_do_not_create_seat_holds(organizer):
    trip = create_bookable_trip(organizer, capacity=1)
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save(update_fields=["booking_state", "updated_at"])

    PaymentAttempt.objects.create(booking=booking, amount_inr=1000)

    assert SeatHold.objects.filter(booking=booking).count() == 0


def test_capacity_derivation_counts_only_active_reserved_travelers(organizer):
    trip = create_bookable_trip(organizer, capacity=6)
    package = trip.packages.first()
    states = [
        Booking.BookingState.DRAFT,
        Booking.BookingState.RESERVED,
        Booking.BookingState.CONFIRMED,
        Booking.BookingState.CANCELLED,
        Booking.BookingState.COMPLETED,
    ]

    for index, state in enumerate(states, start=1):
        booking = Booking.objects.create(
            trip=trip,
            booking_contact_name=f"Booking Contact {index}",
            booking_contact_phone=f"+91987654321{index}",
            booking_state=state,
        )
        TravelerSlot.objects.create(booking=booking, package=package, position=1)

    assert active_reserved_traveler_count(trip) == 2
    assert available_seats(trip) == 4


def test_sold_out_booking_availability_derives_from_reserved_travelers(organizer):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Rahul Menon",
        booking_contact_phone="+919123456789",
        booking_state=Booking.BookingState.RESERVED,
    )
    package = trip.packages.first()
    TravelerSlot.objects.create(booking=booking, package=package, position=1)
    TravelerSlot.objects.create(booking=booking, package=package, position=2)

    assert available_seats(trip) == 0
    assert effective_booking_availability(trip) == "sold_out"


def test_draft_bookings_are_excluded_from_core_operational_counts_by_default(
    user_factory,
    organizer,
):
    owner = user_factory("counts-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_bookable_trip(organizer)
    package = trip.packages.first()
    draft_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.DRAFT,
    )
    TravelerSlot.objects.create(booking=draft_booking, package=package, position=1)
    reserved_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Rahul Menon",
        booking_contact_phone="+919123456789",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=reserved_booking, package=package, position=1)
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(f"/api/operations/dashboard/?organizer={organizer.id}")

    assert core_operational_booking_count(trip) == 1
    assert response.status_code == 200
    assert response.json()["trips"]["latest"]["core_operational_booking_count"] == 1
    assert (
        response.json()["trips"]["latest"]["operational_metrics"]["core_operational_booking_count"]
        == 1
    )
    assert response.json()["trips"]["latest"]["operational_metrics"]["reserved_travelers"] == 1


def test_operations_dashboard_lists_trip_bookings_with_state_and_derived_payment_state(
    user_factory,
    organizer,
):
    operator = user_factory("booking-list-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer, capacity=8)
    package = trip.packages.first()
    for index, state in enumerate(
        [
            Booking.BookingState.DRAFT,
            Booking.BookingState.RESERVED,
            Booking.BookingState.CONFIRMED,
            Booking.BookingState.CANCELLED,
            Booking.BookingState.COMPLETED,
        ],
        start=1,
    ):
        booking = Booking.objects.create(
            trip=trip,
            booking_contact_name=f"Booking Contact {index}",
            booking_contact_phone=f"+91987654321{index}",
            booking_state=state,
        )
        TravelerSlot.objects.create(booking=booking, package=package, position=1)
        if state in {Booking.BookingState.RESERVED, Booking.BookingState.CONFIRMED}:
            LedgerEntry.objects.create(
                booking=booking,
                entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
                amount_inr=8000,
                description="Historical collected amount placeholder.",
            )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.get(f"/api/operations/dashboard/?organizer={organizer.id}")

    assert response.status_code == 200
    bookings = response.json()["trips"]["latest"]["bookings"]
    assert {booking["booking_state"] for booking in bookings} == {
        Booking.BookingState.DRAFT,
        Booking.BookingState.RESERVED,
        Booking.BookingState.CONFIRMED,
        Booking.BookingState.CANCELLED,
        Booking.BookingState.COMPLETED,
    }
    reserved_row = next(
        booking for booking in bookings if booking["booking_state"] == Booking.BookingState.RESERVED
    )
    assert reserved_row["payment_state"] == "reservation_paid"
    assert reserved_row["reconciliation"]["collected_inr"] == 8000


def test_internal_admin_requires_staff_access_without_organizer_membership(
    user_factory,
    organizer,
):
    owner = user_factory("internal-owner@example.com")
    internal_staff = user_factory("internal-staff@example.com")
    internal_staff.is_staff = True
    internal_staff.save()
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    client = APIClient()

    client.force_authenticate(owner)
    owner_response = client.get("/api/internal-admin/organizers/")

    client.force_authenticate(internal_staff)
    staff_list_response = client.get("/api/internal-admin/organizers/")
    staff_detail_response = client.get(f"/api/internal-admin/trips/{trip.id}/")

    assert owner_response.status_code == 403
    assert staff_list_response.status_code == 200
    assert staff_list_response.json()[0]["id"] == organizer.id
    assert staff_detail_response.status_code == 200
    assert staff_detail_response.json()["id"] == trip.id


def test_internal_admin_inspects_pilot_support_records_read_only(
    user_factory,
    organizer,
):
    internal_staff = user_factory("pilot-support@example.com")
    internal_staff.is_staff = True
    internal_staff.save()
    organizer.payout_account.status = PayoutAccount.Status.ACTIVE
    organizer.payout_account.save()
    organizer.provider_payment_setup.status = ProviderPaymentSetup.Status.COMPLETE
    organizer.provider_payment_setup.provider_merchant_reference = "acct_razorpay_pilot"
    organizer.provider_payment_setup.save()
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    attempt = create_public_payment_attempt(booking)
    provider_payment = confirm_provider_payment(
        attempt,
        provider_payment_reference="pay_internal_support_001",
        amount_inr=8000,
    )
    failed_attempt = PaymentAttempt.objects.create(
        booking=booking,
        provider=PaymentAttempt.Provider.RAZORPAY,
        status=PaymentAttempt.Status.FAILED,
        amount_inr=8000,
        provider_attempt_reference="attempt_failed_support",
        failure_reason="Provider declined the payment.",
    )
    manual_payment = ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=5000,
        payment_reference="upi-pending-support",
    )
    booking_import = BookingImport.objects.create(
        trip=trip,
        submitted_by=internal_staff,
        status=BookingImport.Status.COMPLETED_WITH_CONFLICTS,
        source_filename="pilot-import.csv",
        conflict_count=1,
    )
    BookingImportRow.objects.create(
        booking_import=booking_import,
        booking=booking,
        row_number=1,
        status=BookingImportRow.Status.CONFLICT,
        conflict_code="capacity_conflict",
        message="Imported row would exceed Trip Capacity.",
        payload={"booking_contact_phone": booking.booking_contact_phone},
    )
    create_booking_adjustment(
        booking=booking,
        amount_inr=-31000,
        adjustment_reason="Pilot refund due support inspection.",
        actor=internal_staff,
    )
    ActivityLog.objects.create(
        organizer=organizer,
        trip=trip,
        booking=booking,
        actor=internal_staff,
        action=ActivityLog.Action.SENSITIVE_PAYMENT_INFORMATION_DOWNLOAD,
        metadata={"manual_payment": manual_payment.id},
    )
    client = APIClient()
    client.force_authenticate(internal_staff)

    detail_response = client.get(f"/api/internal-admin/organizers/{organizer.id}/")
    booking_response = client.get(f"/api/internal-admin/bookings/{booking.id}/")
    write_response = client.patch(
        f"/api/internal-admin/bookings/{booking.id}/",
        {"booking_contact_name": "Changed by support"},
        format="json",
    )

    organizer.provider_payment_setup.refresh_from_db()
    booking.refresh_from_db()
    detail_payload = detail_response.json()
    booking_payload = booking_response.json()
    support_booking = detail_payload["trips"][0]["bookings"][0]
    assert detail_response.status_code == 200
    assert booking_response.status_code == 200
    assert write_response.status_code == 405
    assert organizer.provider_payment_setup.provider_merchant_reference == "acct_razorpay_pilot"
    assert booking.booking_contact_name == "Asha Nair"
    assert detail_payload["payment_setup"]["payout_status"] == PayoutAccount.Status.ACTIVE
    assert detail_payload["payment_setup"]["provider_payment_setup_complete"] is True
    assert detail_payload["payment_setup"]["online_payment_readiness_ready"] is True
    assert support_booking["payment_attempts"][0]["id"] in {attempt.id, failed_attempt.id}
    assert {payment["id"] for payment in booking_payload["provider_payments"]} == {
        provider_payment.id
    }
    assert {payment["id"] for payment in booking_payload["manual_payments"]} == {manual_payment.id}
    assert booking_payload["notifications"]
    assert booking_payload["booking_import_rows"][0]["conflict_code"] == "capacity_conflict"
    assert set(booking_payload["reconciliation_flags"]) >= {
        "refund_due",
        "failed_payment_attempt",
        "submitted_manual_payment",
        "booking_import_conflict",
    }
    assert any(
        log["action"] == ActivityLog.Action.SENSITIVE_PAYMENT_INFORMATION_DOWNLOAD
        for log in booking_payload["activity_logs"]
    )


def test_internal_admin_manages_monthly_platform_fee_statements(
    user_factory,
    organizer,
):
    internal_staff = user_factory("platform-fee-staff@example.com")
    internal_staff.is_staff = True
    internal_staff.save()
    owner = user_factory("platform-fee-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    reservation_attempt = create_public_payment_attempt(booking)
    reservation_payment = confirm_provider_payment(
        reservation_attempt,
        provider_payment_reference="pay_statement_reservation_001",
        amount_inr=8000,
    )
    balance_attempt = PaymentAttempt.objects.create(
        booking=booking,
        provider=PaymentAttempt.Provider.RAZORPAY,
        purpose=PaymentAttempt.Purpose.BALANCE,
        amount_inr=4000,
        provider_attempt_reference="order_statement_balance_001",
    )
    balance_payment = confirm_provider_payment(
        balance_attempt,
        provider_payment_reference="pay_statement_balance_001",
        amount_inr=4000,
    )
    june_attempt = PaymentAttempt.objects.create(
        booking=booking,
        provider=PaymentAttempt.Provider.RAZORPAY,
        purpose=PaymentAttempt.Purpose.BALANCE,
        amount_inr=1000,
        provider_attempt_reference="order_statement_june_001",
    )
    june_payment = confirm_provider_payment(
        june_attempt,
        provider_payment_reference="pay_statement_june_001",
        amount_inr=1000,
    )
    other_organizer = Organizer.objects.create(name="Western Ghats Weekenders")
    other_trip = create_bookable_trip(other_organizer, title="Other Organizer Run")
    other_booking = create_draft_booking(other_trip)
    other_attempt = create_public_payment_attempt(other_booking)
    other_payment = confirm_provider_payment(
        other_attempt,
        provider_payment_reference="pay_statement_other_organizer_001",
        amount_inr=8000,
    )
    may_occurrence = timezone.make_aware(datetime(2026, 5, 20, 10, 0))
    june_occurrence = timezone.make_aware(datetime(2026, 6, 1, 9, 0))
    set_provider_payment_ledger_occurred_at(reservation_payment, may_occurrence)
    set_provider_payment_ledger_occurred_at(balance_payment, may_occurrence)
    set_provider_payment_ledger_occurred_at(other_payment, may_occurrence)
    set_provider_payment_ledger_occurred_at(june_payment, june_occurrence)
    client = APIClient()

    client.force_authenticate(owner)
    owner_response = client.get("/api/internal-admin/platform-fee-statements/")

    client.force_authenticate(internal_staff)
    create_response = client.post(
        "/api/internal-admin/platform-fee-statements/",
        {
            "organizer": organizer.id,
            "period_start": "2026-05-01",
            "status": PlatformFeeStatement.Status.ISSUED,
            "notes": "May pilot statement.",
        },
        format="json",
    )
    statement_id = create_response.json()["id"]
    list_response = client.get(
        f"/api/internal-admin/platform-fee-statements/?organizer={organizer.id}"
    )
    patch_response = client.patch(
        f"/api/internal-admin/platform-fee-statements/{statement_id}/",
        {
            "status": PlatformFeeStatement.Status.COLLECTED,
            "collected_at": "2026-06-07T12:00:00+05:30",
            "refresh_totals": True,
        },
        format="json",
    )
    detail_response = client.get(f"/api/internal-admin/organizers/{organizer.id}/")

    assert owner_response.status_code == 403
    assert create_response.status_code == 201
    created_payload = create_response.json()
    assert created_payload["period_start"] == "2026-05-01"
    assert created_payload["period_end"] == "2026-06-01"
    assert created_payload["period_label"] == "May 2026"
    assert created_payload["status"] == PlatformFeeStatement.Status.ISSUED
    assert created_payload["provider_payment_count"] == 2
    assert created_payload["gross_provider_payment_amount_inr"] == 12000
    assert created_payload["platform_fee_amount_inr"] == 240
    assert list_response.status_code == 200
    assert [statement["id"] for statement in list_response.json()] == [statement_id]
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == PlatformFeeStatement.Status.COLLECTED
    assert patch_response.json()["provider_payment_count"] == 2
    assert detail_response.status_code == 200
    assert detail_response.json()["platform_fee_statements"][0]["id"] == statement_id


def test_payment_setup_status_does_not_expose_platform_fee_statement_management(
    user_factory,
    organizer,
):
    owner = user_factory("statement-separation-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    PlatformFeeStatement.objects.create(
        organizer=organizer,
        period_start=date(2026, 5, 1),
        provider_payment_count=2,
        gross_provider_payment_amount_inr=12000,
        platform_fee_amount_inr=240,
    )
    client = APIClient()
    client.force_authenticate(owner)

    status_response = client.get(f"/api/organizers/{organizer.id}/payment-setup-status/")
    setup_response = client.get(f"/api/organizers/{organizer.id}/provider-payment-setup/")
    payout_response = client.get(f"/api/organizers/{organizer.id}/payout-account/")
    dashboard_response = client.get(f"/api/operations/dashboard/?organizer={organizer.id}")

    assert status_response.status_code == 200
    assert setup_response.status_code == 200
    assert payout_response.status_code == 200
    assert dashboard_response.status_code == 200
    for payload in [
        status_response.json(),
        setup_response.json(),
        payout_response.json(),
        dashboard_response.json()["payment_setup"],
    ]:
        assert "platform_fee_statements" not in payload
        assert "platform_fee_statement" not in payload
        assert "platform_fee_statement_count" not in payload


def test_trip_setup_configures_confirmation_requirements_per_trip(user_factory, organizer):
    owner = user_factory("confirmation-setup-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        f"/api/organizers/{organizer.id}/trips/",
        trip_setup_payload(
            requires_traveler_documents=True,
            requires_traveler_identity_details=True,
            requires_travel_logistics=True,
            requires_emergency_contact=True,
            requires_medical_disclosure=True,
            requires_full_payment_before_confirmation=True,
        ),
        format="json",
    )

    trip = Trip.objects.get(title="Spiti Winter Field Week")
    assert response.status_code == 201
    assert response.json()["requires_traveler_documents"] is True
    assert response.json()["requires_traveler_identity_details"] is True
    assert response.json()["requires_full_payment_before_confirmation"] is True
    assert trip.requires_emergency_contact is True
    assert not hasattr(trip.packages.first(), "requires_traveler_documents")


def test_confirmation_requirement_evaluation_reports_unmet_booking_requirements(
    user_factory,
    organizer,
):
    operator = user_factory("confirmation-dashboard-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(
        organizer,
        requires_traveler_documents=True,
        requires_traveler_identity_details=True,
        requires_travel_logistics=True,
        requires_emergency_contact=True,
        requires_medical_disclosure=True,
        requires_full_payment_before_confirmation=True,
    )
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=booking, package=trip.packages.first(), position=1)
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=8000,
        description="Historical collected amount placeholder.",
    )
    client = APIClient()
    client.force_authenticate(operator)

    requirements = confirmation_requirements_for_booking(booking)
    response = client.get(f"/api/operations/dashboard/?organizer={organizer.id}")

    assert requirements.ready is False
    assert {requirement.code for requirement in requirements.unmet_requirements} == {
        "full_payment",
        "traveler_identity_details",
        "traveler_documents",
        "travel_logistics",
        "emergency_contact",
        "medical_disclosure",
    }
    booking_row = response.json()["trips"]["latest"]["bookings"][0]
    assert response.status_code == 200
    assert booking_row["confirmation_requirements"]["ready"] is False
    assert booking_row["confirmation_requirements"]["unmet_count"] == 6
    assert response.json()["trips"]["latest"]["operational_metrics"]["missing_requirements"] == 6


def test_confirm_booking_blocks_unmet_requirements(user_factory, organizer):
    operator = user_factory("blocked-confirm-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer, requires_emergency_contact=True)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=booking, package=trip.packages.first(), position=1)
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/confirm/",
        {},
        format="json",
    )

    booking.refresh_from_db()
    assert response.status_code == 400
    assert booking.booking_state == Booking.BookingState.RESERVED


def test_operator_can_confirm_reserved_booking_without_full_payment_when_allowed(
    user_factory,
    organizer,
):
    operator = user_factory("confirm-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer, requires_traveler_identity_details=True)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.first(),
        position=1,
        traveler_full_name="Asha Nair",
        traveler_phone="+919876543210",
    )
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=8000,
        description="Reservation amount collected during import.",
    )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/confirm/",
        {},
        format="json",
    )

    booking.refresh_from_db()
    assert response.status_code == 200
    assert response.json()["booking_state"] == Booking.BookingState.CONFIRMED
    assert booking.booking_state == Booking.BookingState.CONFIRMED
    assert booking_reconciliation(booking).due_inr == 24000


def test_full_payment_expectation_blocks_confirmation_until_paid(organizer):
    trip = create_bookable_trip(
        organizer,
        requires_traveler_identity_details=True,
        requires_full_payment_before_confirmation=True,
    )
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.first(),
        position=1,
        traveler_full_name="Asha Nair",
        traveler_phone="+919876543210",
    )
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=8000,
        description="Reservation amount collected during import.",
    )

    with pytest.raises(ValidationError, match="unmet Confirmation Requirements"):
        confirm_booking(booking)

    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=24000,
        description="Balance collected before confirmation.",
    )
    confirmed_booking = confirm_booking(booking)
    confirmed_booking.refresh_from_db()

    assert confirmed_booking.booking_state == Booking.BookingState.CONFIRMED
    assert confirmation_requirements_for_booking(confirmed_booking).ready is True


@pytest.mark.parametrize(
    ("document_state", "expected_ready"),
    [
        (TravelerDocument.DocumentState.MISSING, False),
        (TravelerDocument.DocumentState.SUBMITTED, False),
        (TravelerDocument.DocumentState.APPROVED, True),
        (TravelerDocument.DocumentState.REJECTED, False),
    ],
)
def test_traveler_readiness_module_evaluates_document_states(
    organizer,
    document_state,
    expected_ready,
):
    trip = create_bookable_trip(organizer, requires_traveler_documents=True)
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    traveler_slot = booking.traveler_slots.first()
    TravelerDocument.objects.create(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        label="Passport",
        document_state=document_state,
        rejection_reason="Name is not legible."
        if document_state == TravelerDocument.DocumentState.REJECTED
        else "",
    )

    requirements = TravelerReadiness().confirmation_requirements_for_booking(booking)
    unmet_codes = {requirement.code for requirement in requirements.unmet_requirements}

    assert requirements.ready is expected_ready
    assert ("traveler_documents" in unmet_codes) is (not expected_ready)


def test_traveler_readiness_module_covers_all_confirmation_requirements(organizer):
    trip = create_bookable_trip(
        organizer,
        requires_traveler_documents=True,
        requires_traveler_identity_details=True,
        requires_travel_logistics=True,
        requires_emergency_contact=True,
        requires_medical_disclosure=True,
        requires_full_payment_before_confirmation=True,
    )
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    traveler_slot = booking.traveler_slots.first()
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=8000,
        description="Reservation amount collected during import.",
    )

    blocked_requirements = TravelerReadiness().confirmation_requirements_for_booking(booking)

    assert blocked_requirements.ready is False
    assert {requirement.code for requirement in blocked_requirements.unmet_requirements} == {
        "full_payment",
        "traveler_identity_details",
        "traveler_documents",
        "travel_logistics",
        "emergency_contact",
        "medical_disclosure",
    }

    traveler_slot.traveler_full_name = "Asha Nair"
    traveler_slot.traveler_phone = "+919876543210"
    traveler_slot.arrival_details = "Arriving at Chandigarh ISBT by 07:00."
    traveler_slot.emergency_contact_name = "Maya Rao"
    traveler_slot.emergency_contact_phone = "+919700000001"
    traveler_slot.emergency_contact_relationship = "Sibling"
    traveler_slot.medical_disclosure = "Mild asthma; carries inhaler."
    traveler_slot.medical_disclosure_submitted_at = timezone.now()
    traveler_slot.save()
    TravelerDocument.objects.create(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        label="Passport",
        document_state=TravelerDocument.DocumentState.APPROVED,
    )
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=24000,
        description="Balance collected before confirmation.",
    )

    ready_requirements = TravelerReadiness().confirmation_requirements_for_booking(booking)

    assert ready_requirements.ready is True
    assert ready_requirements.unmet_requirements == []


@override_settings(MEDIA_ROOT="/private/tmp/tripos-test-media")
def test_traveler_readiness_module_submits_and_reviews_documents(user_factory, organizer):
    reviewer = user_factory("readiness-document-reviewer@example.com")
    trip = create_bookable_trip(organizer, requires_traveler_documents=True)
    booking = create_draft_booking(trip)
    traveler_slot = booking.traveler_slots.first()
    rejected_document = TravelerDocument.objects.create(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        label="Passport",
        document_state=TravelerDocument.DocumentState.REJECTED,
        rejection_reason="Expired.",
    )

    submitted_document = submit_traveler_document(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        label="Passport",
        uploaded_file=SimpleUploadedFile(
            "passport.txt",
            b"identity document",
            content_type="text/plain",
        ),
    )
    approved_document = review_traveler_document(
        document=submitted_document,
        document_state=TravelerDocument.DocumentState.APPROVED,
        reviewer=reviewer,
    )
    rejected_again = review_traveler_document(
        document=approved_document,
        document_state=TravelerDocument.DocumentState.REJECTED,
        rejection_reason="Name is not legible.",
        reviewer=reviewer,
    )

    rejected_document.refresh_from_db()
    assert submitted_document.id == rejected_document.id
    assert submitted_document.document_state == TravelerDocument.DocumentState.SUBMITTED
    assert submitted_document.rejection_reason == ""
    assert submitted_document.reviewed_by is None
    assert submitted_document.is_sensitive_traveler_information is True
    assert submitted_document.exclude_from_default_exports is True
    assert approved_document.document_state == TravelerDocument.DocumentState.APPROVED
    assert rejected_again.document_state == TravelerDocument.DocumentState.REJECTED
    assert rejected_again.rejection_reason == "Name is not legible."
    assert ActivityLog.objects.filter(
        traveler_document=rejected_again,
        action=ActivityLog.Action.TRAVELER_DOCUMENT_APPROVED,
    ).exists()
    assert ActivityLog.objects.filter(
        traveler_document=rejected_again,
        action=ActivityLog.Action.TRAVELER_DOCUMENT_REJECTED,
    ).exists()


def test_unconfirm_booking_moves_confirmed_booking_back_to_reserved(user_factory, organizer):
    owner = user_factory("unconfirm-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_bookable_trip(organizer)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.CONFIRMED,
    )
    TravelerSlot.objects.create(booking=booking, package=trip.packages.first(), position=1)
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/unconfirm/",
        {},
        format="json",
    )

    booking.refresh_from_db()
    assert response.status_code == 200
    assert response.json()["booking_state"] == Booking.BookingState.RESERVED
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert ActivityLog.objects.filter(booking=booking).count() == 0


@pytest.mark.parametrize(
    "booking_state",
    [Booking.BookingState.RESERVED, Booking.BookingState.CONFIRMED],
)
@pytest.mark.parametrize(
    "operation",
    [
        "cancel_booking",
        "cancel_traveler",
        "replace_traveler",
        "add_traveler",
        "change_package",
        "mark_attendance",
    ],
)
def test_booking_operations_workflow_allows_active_booking_states(
    user_factory,
    organizer,
    booking_state,
    operation,
):
    actor = user_factory(f"workflow-active-{booking_state}-{operation}@example.com")
    workflow = BookingOperationsWorkflow()
    trip = create_bookable_trip(organizer, capacity=3)
    standard_package = trip.packages.first()
    premium_package = TripPackage.objects.create(
        trip=trip,
        name=f"Premium {booking_state} {operation}",
        price_inr=42000,
        reservation_amount_inr=12000,
        position=2,
    )
    booking = create_draft_booking(trip, package=standard_package)
    booking.booking_state = booking_state
    booking.save()
    traveler_slot = booking.traveler_slots.first()
    traveler_slot.traveler_full_name = "Asha Nair"
    traveler_slot.traveler_phone = "+919876543210"
    traveler_slot.save()

    if operation == "cancel_booking":
        workflow.cancel_booking(booking, cancellation_reason="Approved cancellation.", actor=actor)
        booking.refresh_from_db()
        assert booking.booking_state == Booking.BookingState.CANCELLED
    elif operation == "cancel_traveler":
        workflow.cancel_traveler(
            traveler_slot,
            cancellation_reason="Traveler dropped out.",
            actor=actor,
        )
        traveler_slot.refresh_from_db()
        assert traveler_slot.traveler_state == TravelerSlot.TravelerState.CANCELLED
    elif operation == "replace_traveler":
        replacement = workflow.replace_traveler(
            traveler_slot,
            traveler_full_name="Meera Iyer",
            traveler_phone="+919999999999",
            actor=actor,
        )
        traveler_slot.refresh_from_db()
        assert traveler_slot.traveler_state == TravelerSlot.TravelerState.REPLACED
        assert replacement.booked_package_price_inr == traveler_slot.booked_package_price_inr
    elif operation == "add_traveler":
        added = workflow.add_traveler_to_booking(
            booking,
            package=premium_package,
            traveler_full_name="Nikhil Rao",
            actor=actor,
        )
        assert added.traveler_state == TravelerSlot.TravelerState.PENDING_ADDITION
    elif operation == "change_package":
        changed = workflow.change_traveler_package(
            traveler_slot,
            package=premium_package,
            actor=actor,
        )
        assert changed.booked_package_price_inr == premium_package.price_inr
    else:
        marked = workflow.mark_traveler_attendance(
            traveler_slot,
            attendance_state=TravelerSlot.AttendanceState.CHECKED_IN,
            actor=actor,
        )
        assert marked.attendance_state == TravelerSlot.AttendanceState.CHECKED_IN


@pytest.mark.parametrize(
    "booking_state",
    [
        Booking.BookingState.DRAFT,
        Booking.BookingState.CANCELLED,
        Booking.BookingState.COMPLETED,
    ],
)
@pytest.mark.parametrize(
    "operation",
    [
        "cancel_booking",
        "cancel_traveler",
        "replace_traveler",
        "add_traveler",
        "change_package",
        "mark_attendance",
    ],
)
def test_booking_operations_workflow_rejects_inactive_booking_states(
    organizer,
    booking_state,
    operation,
):
    workflow = BookingOperationsWorkflow()
    trip = create_bookable_trip(organizer, capacity=3)
    standard_package = trip.packages.first()
    premium_package = TripPackage.objects.create(
        trip=trip,
        name=f"Premium inactive {booking_state} {operation}",
        price_inr=42000,
        reservation_amount_inr=12000,
        position=2,
    )
    booking = create_draft_booking(trip, package=standard_package)
    booking.booking_state = booking_state
    booking.save()
    traveler_slot = booking.traveler_slots.first()
    traveler_slot.traveler_full_name = "Asha Nair"
    traveler_slot.traveler_phone = "+919876543210"
    traveler_slot.save()

    with pytest.raises(ValidationError, match="Reserved or Confirmed"):
        if operation == "cancel_booking":
            workflow.cancel_booking(booking, cancellation_reason="Approved cancellation.")
        elif operation == "cancel_traveler":
            workflow.cancel_traveler(
                traveler_slot,
                cancellation_reason="Traveler dropped out.",
            )
        elif operation == "replace_traveler":
            workflow.replace_traveler(
                traveler_slot,
                traveler_full_name="Meera Iyer",
                traveler_phone="+919999999999",
            )
        elif operation == "add_traveler":
            workflow.add_traveler_to_booking(booking, package=premium_package)
        elif operation == "change_package":
            workflow.change_traveler_package(traveler_slot, package=premium_package)
        else:
            workflow.mark_traveler_attendance(
                traveler_slot,
                attendance_state=TravelerSlot.AttendanceState.CHECKED_IN,
            )


def test_booking_operations_workflow_confirm_and_unconfirm_state_guards(organizer):
    workflow = BookingOperationsWorkflow(send_confirmation_notice=lambda booking: [])
    trip = create_bookable_trip(organizer)
    reservable_booking = create_draft_booking(trip)
    reservable_booking.booking_state = Booking.BookingState.RESERVED
    reservable_booking.save()

    confirmed_booking = workflow.confirm_booking(reservable_booking)
    assert confirmed_booking.booking_state == Booking.BookingState.CONFIRMED

    unconfirmed_booking = workflow.unconfirm_booking(confirmed_booking)
    assert unconfirmed_booking.booking_state == Booking.BookingState.RESERVED

    for booking_state in [
        Booking.BookingState.DRAFT,
        Booking.BookingState.CONFIRMED,
        Booking.BookingState.CANCELLED,
        Booking.BookingState.COMPLETED,
    ]:
        booking = create_draft_booking(trip)
        booking.booking_state = booking_state
        booking.save()
        with pytest.raises(ValidationError, match="Only Reserved Bookings"):
            workflow.confirm_booking(booking)

    for booking_state in [
        Booking.BookingState.DRAFT,
        Booking.BookingState.RESERVED,
        Booking.BookingState.CANCELLED,
        Booking.BookingState.COMPLETED,
    ]:
        booking = create_draft_booking(trip)
        booking.booking_state = booking_state
        booking.save()
        with pytest.raises(ValidationError, match="Only Confirmed Bookings"):
            workflow.unconfirm_booking(booking)


@pytest.mark.parametrize(
    "role",
    [OrganizerMembership.Role.OWNER, OrganizerMembership.Role.OPERATOR],
)
def test_owner_and_operator_can_mark_traveler_check_in_and_no_show(
    user_factory,
    organizer,
    role,
):
    user = user_factory(f"attendance-{role}@example.com")
    OrganizerMembership.objects.create(user=user, organizer=organizer, role=role)
    trip = create_bookable_trip(organizer)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    traveler_slot = TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.first(),
        position=1,
        traveler_full_name="Asha Nair",
        traveler_phone="+919876543210",
    )
    client = APIClient()
    client.force_authenticate(user)

    check_in_response = client.post(
        f"/api/operations/organizers/{organizer.id}/traveler-slots/{traveler_slot.id}/check-in/",
        {},
        format="json",
    )
    no_show_response = client.post(
        f"/api/operations/organizers/{organizer.id}/traveler-slots/{traveler_slot.id}/no-show/",
        {},
        format="json",
    )

    traveler_slot.refresh_from_db()
    booking.refresh_from_db()
    assert check_in_response.status_code == 200
    assert check_in_response.json()["attendance_summary"]["checked_in"] == 1
    assert no_show_response.status_code == 200
    assert no_show_response.json()["attendance_summary"]["no_show"] == 1
    assert traveler_slot.attendance_state == TravelerSlot.AttendanceState.NO_SHOW
    assert traveler_slot.attendance_marked_by == user
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert booking.traveler_slots.filter(pk=traveler_slot.pk).exists()
    assert ActivityLog.objects.filter(
        booking=booking,
        traveler_slot=traveler_slot,
        action=ActivityLog.Action.TRAVELER_CHECKED_IN,
        actor=user,
    ).exists()
    assert ActivityLog.objects.filter(
        booking=booking,
        traveler_slot=traveler_slot,
        action=ActivityLog.Action.TRAVELER_MARKED_NO_SHOW,
        actor=user,
        metadata__attendance_state=TravelerSlot.AttendanceState.NO_SHOW,
    ).exists()


@pytest.mark.parametrize(
    "booking_state",
    [Booking.BookingState.RESERVED, Booking.BookingState.CONFIRMED],
)
def test_traveler_attendance_is_allowed_for_reserved_and_confirmed_bookings(
    organizer,
    booking_state,
):
    trip = create_bookable_trip(organizer)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=booking_state,
    )
    traveler_slot = TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.first(),
        position=1,
        traveler_full_name="Asha Nair",
        traveler_phone="+919876543210",
    )

    mark_traveler_attendance(
        traveler_slot,
        attendance_state=TravelerSlot.AttendanceState.CHECKED_IN,
    )

    traveler_slot.refresh_from_db()
    assert traveler_slot.attendance_state == TravelerSlot.AttendanceState.CHECKED_IN


@pytest.mark.parametrize(
    "booking_state",
    [
        Booking.BookingState.DRAFT,
        Booking.BookingState.CANCELLED,
        Booking.BookingState.COMPLETED,
    ],
)
def test_traveler_attendance_rejects_inactive_booking_states(organizer, booking_state):
    trip = create_bookable_trip(organizer)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=booking_state,
    )
    traveler_slot = TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.first(),
        position=1,
        traveler_full_name="Asha Nair",
        traveler_phone="+919876543210",
    )

    with pytest.raises(ValidationError, match="Reserved or Confirmed"):
        mark_traveler_attendance(
            traveler_slot,
            attendance_state=TravelerSlot.AttendanceState.CHECKED_IN,
        )

    traveler_slot.refresh_from_db()
    assert traveler_slot.attendance_state == TravelerSlot.AttendanceState.NOT_MARKED


def test_traveler_attendance_requires_traveler_identity_details(organizer):
    trip = create_bookable_trip(organizer)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    traveler_slot = TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.first(),
        position=1,
    )

    with pytest.raises(ValidationError, match="Traveler Identity Details"):
        mark_traveler_attendance(
            traveler_slot,
            attendance_state=TravelerSlot.AttendanceState.NO_SHOW,
        )


def test_non_member_cannot_mark_traveler_attendance(user_factory, organizer):
    outsider = user_factory("attendance-outsider@example.com")
    trip = create_bookable_trip(organizer)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    traveler_slot = TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.first(),
        position=1,
        traveler_full_name="Asha Nair",
        traveler_phone="+919876543210",
    )
    client = APIClient()
    client.force_authenticate(outsider)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/traveler-slots/{traveler_slot.id}/check-in/",
        {},
        format="json",
    )

    traveler_slot.refresh_from_db()
    assert response.status_code == 403
    assert traveler_slot.attendance_state == TravelerSlot.AttendanceState.NOT_MARKED


def test_no_show_has_no_financial_side_effects(user_factory, organizer):
    operator = user_factory("attendance-finance-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.CONFIRMED,
    )
    traveler_slot = TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.first(),
        position=1,
        traveler_full_name="Asha Nair",
        traveler_phone="+919876543210",
    )
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=8000,
        description="Reservation amount collected during import.",
    )
    before_total = booking.booking_total_inr
    before_payment_state = derived_payment_state(booking)
    before_reconciliation = booking_reconciliation(booking)
    before_ledger_count = booking.ledger_entries.count()
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/traveler-slots/{traveler_slot.id}/no-show/",
        {},
        format="json",
    )

    booking.refresh_from_db()
    assert response.status_code == 200
    assert booking.booking_total_inr == before_total
    assert derived_payment_state(booking) == before_payment_state
    assert booking.ledger_entries.count() == before_ledger_count
    assert booking_reconciliation(booking) == before_reconciliation


def test_operations_dashboard_and_booking_detail_show_attendance_state(
    user_factory,
    organizer,
):
    operator = user_factory("attendance-dashboard-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    checked_in_traveler = TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.first(),
        position=1,
        traveler_full_name="Asha Nair",
        traveler_phone="+919876543210",
        attendance_state=TravelerSlot.AttendanceState.CHECKED_IN,
        attendance_marked_at=timezone.now(),
        attendance_marked_by=operator,
    )
    no_show_traveler = TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.first(),
        position=2,
        traveler_full_name="Rahul Menon",
        traveler_phone="+919876543211",
        attendance_state=TravelerSlot.AttendanceState.NO_SHOW,
        attendance_marked_at=timezone.now(),
        attendance_marked_by=operator,
    )
    client = APIClient()
    client.force_authenticate(operator)

    dashboard_response = client.get(f"/api/operations/dashboard/?organizer={organizer.id}")
    detail_response = client.get(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/"
    )

    dashboard_booking = dashboard_response.json()["trips"]["latest"]["bookings"][0]
    detail_payload = detail_response.json()
    assert dashboard_response.status_code == 200
    assert detail_response.status_code == 200
    assert dashboard_booking["attendance_summary"] == {
        "not_marked": 0,
        "checked_in": 1,
        "no_show": 1,
    }
    assert {
        slot["id"]: slot["attendance_state"] for slot in dashboard_booking["traveler_slots"]
    } == {
        checked_in_traveler.id: TravelerSlot.AttendanceState.CHECKED_IN,
        no_show_traveler.id: TravelerSlot.AttendanceState.NO_SHOW,
    }
    assert detail_payload["attendance_summary"]["checked_in"] == 1
    assert detail_payload["traveler_slots"][0]["attendance_actions_available"] is True


def test_confirmation_notice_is_sent_when_booking_becomes_confirmed(organizer):
    trip = create_bookable_trip(organizer)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_contact_email="asha@example.com",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.first(),
        position=1,
        traveler_full_name="Asha Nair",
        traveler_phone="+919876543210",
    )

    confirm_booking(booking)

    notices = Notification.objects.filter(
        booking=booking,
        notification_type=Notification.NotificationType.CONFIRMATION_NOTICE,
    )
    assert notices.count() == 3
    assert notices.filter(recipient_type=Notification.RecipientType.BOOKING_CONTACT).count() == 2
    assert notices.filter(recipient_type=Notification.RecipientType.TRAVELER).count() == 1
    assert (
        ActivityLog.objects.filter(
            booking=booking,
            action=ActivityLog.Action.NOTIFICATION_SENT,
            metadata__notification_type=Notification.NotificationType.CONFIRMATION_NOTICE,
        ).count()
        == 3
    )


def test_operations_dashboard_metrics_are_action_oriented_and_exclude_drafts(
    user_factory,
    organizer,
):
    owner = user_factory("metrics-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_bookable_trip(
        organizer,
        capacity=5,
        start_date=date(2026, 5, 20),
        end_date=date(2026, 5, 25),
    )
    trip.payment_schedule.balance_due_days_before_start = 3
    trip.payment_schedule.save()
    package = trip.packages.first()

    draft_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Draft Contact",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.DRAFT,
    )
    TravelerSlot.objects.create(booking=draft_booking, package=package, position=1)

    unpaid_reserved_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Unpaid Contact",
        booking_contact_phone="+919876543211",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=unpaid_reserved_booking, package=package, position=1)

    overdue_confirmed_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Overdue Contact",
        booking_contact_phone="+919876543212",
        booking_state=Booking.BookingState.CONFIRMED,
    )
    TravelerSlot.objects.create(booking=overdue_confirmed_booking, package=package, position=1)
    LedgerEntry.objects.create(
        booking=overdue_confirmed_booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=8000,
        description="Historical collected amount placeholder.",
    )

    cancelled_unpaid_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Cancelled Contact",
        booking_contact_phone="+919876543213",
        booking_state=Booking.BookingState.CANCELLED,
    )
    TravelerSlot.objects.create(booking=cancelled_unpaid_booking, package=package, position=1)
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(f"/api/operations/dashboard/?organizer={organizer.id}")

    assert response.status_code == 200
    metrics = response.json()["trips"]["latest"]["operational_metrics"]
    assert metrics["unpaid_bookings"] == 1
    assert metrics["overdue_amount_inr"] == 56000
    assert metrics["pending_manual_payments"] == 0
    assert metrics["pending_manual_payments_supported"] is True
    assert metrics["missing_requirements"] == 0
    assert metrics["missing_requirements_supported"] is True
    assert metrics["available_seats"] == 3
    assert metrics["reserved_travelers"] == 2
    assert metrics["core_operational_booking_count"] == 3
    assert metrics["booking_state_counts"][Booking.BookingState.DRAFT] == 1
    assert metrics["booking_state_counts"][Booking.BookingState.CANCELLED] == 1


def create_bookable_trip(organizer, **overrides):
    publication_state = overrides.pop("publication_state", Trip.PublicationState.PUBLISHED)
    booking_availability = overrides.pop("booking_availability", Trip.BookingAvailability.OPEN)
    trip = create_trip(
        organizer,
        publication_state=publication_state,
        booking_availability=booking_availability,
        **overrides,
    )
    mark_online_payment_ready(organizer)
    return trip


def mark_online_payment_ready(organizer):
    organizer.payout_account.status = PayoutAccount.Status.ACTIVE
    organizer.payout_account.save()
    organizer.provider_payment_setup.status = ProviderPaymentSetup.Status.COMPLETE
    organizer.provider_payment_setup.authorization_state = (
        ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    )
    organizer.provider_payment_setup.provider_verification_status = (
        ProviderPaymentSetup.ProviderVerificationStatus.VERIFIED
    )
    organizer.provider_payment_setup.provider_payment_capability_enabled = True
    organizer.provider_payment_setup.provider_connection_state = (
        ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    )
    organizer.provider_payment_setup.provider_mode = ProviderPaymentSetup.ProviderMode.LIVE
    organizer.provider_payment_setup.provider_merchant_reference = (
        organizer.provider_payment_setup.provider_merchant_reference
        or f"acct_razorpay_{organizer.id}"
    )
    organizer.provider_payment_setup.save()
    SensitiveProviderCredentialStore().store_oauth_credentials(
        organizer=organizer,
        access_token=f"oauth_access_token_{organizer.id}",
        refresh_token=f"oauth_refresh_token_{organizer.id}",
        provider_account_reference=organizer.provider_payment_setup.provider_merchant_reference,
        public_token=f"rzp_public_{organizer.id}",
        provider_mode=ProviderPaymentSetup.ProviderMode.LIVE,
        scopes=["read_write"],
    )


def create_ready_manual_payment_instructions(organizer):
    return ManualPaymentInstructions.objects.create(
        organizer=organizer,
        payment_qr="manual-payment-qr/payment-qr.png",
        original_filename="payment-qr.png",
        content_type="image/png",
        file_size=128,
        upi_id="trips@example",
        account_name="Himalayan Monsoon Cohort",
        bank_transfer_details="Bank transfer reference HMC Spiti",
    )


def create_draft_booking(trip, *, slot_count=1, package=None):
    selected_package = package or trip.packages.first()
    intake = prepare_manual_booking_intake(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        traveler_slots=[
            TravelerSlotIntakeInput(package_id=selected_package.id)
            for _position in range(1, slot_count + 1)
        ],
    )
    return create_booking_from_intake(
        trip=trip,
        intake=intake,
        booking_state=Booking.BookingState.DRAFT,
    )


def provider_confirmation_payload(
    payment_attempt,
    *,
    provider_payment_reference="pay_provider_confirmation_001",
):
    return {
        "payment_attempt": payment_attempt.id,
        "booking": payment_attempt.booking_id,
        "provider": payment_attempt.provider,
        "purpose": payment_attempt.purpose,
        "provider_attempt_reference": payment_attempt.provider_attempt_reference,
        "provider_payment_reference": provider_payment_reference,
        "amount_inr": payment_attempt.amount_inr,
    }


RAZORPAY_WEBHOOK_SECRET = "test_razorpay_webhook_secret"


def razorpay_webhook_signature(body: bytes, secret: str = RAZORPAY_WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def post_razorpay_webhook(client, body: bytes, *, signature: str | None = None):
    return client.post(
        "/api/webhooks/razorpay/",
        data=body,
        content_type="application/json",
        HTTP_X_RAZORPAY_SIGNATURE=signature or razorpay_webhook_signature(body),
    )


def razorpay_payment_webhook_body(
    payment_attempt,
    *,
    event_reference: str,
    event_type: str = "payment.captured",
    status: str = "captured",
    provider_payment_reference: str = "pay_webhook_payment_001",
    provider_attempt_reference: str | None = None,
    amount_inr: int | None = None,
    provider_fee_amount_inr: int | None = None,
    notes: dict | None = None,
) -> bytes:
    organizer = payment_attempt.booking.trip.organizer
    payment_amount_inr = amount_inr if amount_inr is not None else payment_attempt.amount_inr
    payment_notes = (
        notes
        if notes is not None
        else {
            "tripos_organizer_id": str(organizer.id),
            "tripos_booking_id": str(payment_attempt.booking_id),
            "tripos_payment_attempt_id": str(payment_attempt.id),
            "tripos_payment_purpose": payment_attempt.purpose,
            "tripos_provider_account": organizer.provider_payment_setup.provider_merchant_reference,
        }
    )
    payload = {
        "id": event_reference,
        "entity": "event",
        "event": event_type,
        "account_id": organizer.provider_payment_setup.provider_merchant_reference,
        "payload": {
            "payment": {
                "entity": {
                    "id": provider_payment_reference,
                    "entity": "payment",
                    "amount": payment_amount_inr * 100,
                    "currency": "INR",
                    "status": status,
                    "order_id": provider_attempt_reference
                    or payment_attempt.provider_attempt_reference,
                    "notes": payment_notes,
                }
            }
        },
    }
    if provider_fee_amount_inr is not None:
        payload["payload"]["payment"]["entity"]["fee"] = provider_fee_amount_inr * 100
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def razorpay_authorization_revoked_webhook_body(
    organizer,
    *,
    event_reference: str,
    provider_account_reference: str | None = None,
) -> bytes:
    account_reference = (
        provider_account_reference or organizer.provider_payment_setup.provider_merchant_reference
    )
    payload = {
        "id": event_reference,
        "entity": "event",
        "event": "account.authorization.revoked",
        "account_id": account_reference,
        "payload": {
            "account": {
                "entity": {
                    "id": account_reference,
                }
            }
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def razorpay_checkout_signature(order_id: str, payment_id: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()


def razorpay_checkout_success_payload(
    payment_attempt,
    *,
    provider_payment_reference="pay_browser_checkout_success_001",
    provider_attempt_reference=None,
    signature_secret=None,
    signature=None,
):
    provider_order_reference = provider_attempt_reference or (
        payment_attempt.provider_attempt_reference
    )
    secret = signature_secret or f"oauth_access_token_{payment_attempt.booking.trip.organizer_id}"
    return {
        "razorpay_payment_id": provider_payment_reference,
        "razorpay_order_id": provider_order_reference,
        "razorpay_signature": signature
        or razorpay_checkout_signature(
            provider_order_reference, provider_payment_reference, secret
        ),
    }


def set_provider_payment_ledger_occurred_at(provider_payment, occurred_at):
    ProviderPayment.objects.filter(pk=provider_payment.pk).update(confirmed_at=occurred_at)
    LedgerEntry.objects.filter(provider_payment=provider_payment).update(
        occurred_at=occurred_at,
    )


def create_late_confirmed_payment_exception(organizer, *, provider_payment_reference):
    trip = create_bookable_trip(
        organizer,
        title=f"Late Exception {provider_payment_reference}",
        capacity=1,
    )
    late_booking = create_draft_booking(trip)
    late_attempt = create_public_payment_attempt(late_booking)
    SeatHold.objects.filter(payment_attempt=late_attempt).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    competing_booking = create_draft_booking(trip)
    competing_attempt = create_public_payment_attempt(competing_booking)
    confirm_provider_payment(
        competing_attempt,
        provider_payment_reference=f"{provider_payment_reference}_competing",
        amount_inr=competing_attempt.amount_inr,
    )

    payment_exception = confirm_provider_payment(
        late_attempt,
        provider_payment_reference=provider_payment_reference,
        amount_inr=late_attempt.amount_inr,
    )
    assert isinstance(payment_exception, PaymentException)
    return trip, late_booking, late_attempt, payment_exception


def create_reserved_booking_with_balance_due(organizer, *, capacity=2, slot_count=1):
    trip = create_bookable_trip(organizer, capacity=capacity)
    booking = create_draft_booking(trip, slot_count=slot_count)
    reservation_attempt = create_public_payment_attempt(booking)
    reservation_payment = confirm_provider_payment(
        reservation_attempt,
        provider_payment_reference=f"pay_balance_setup_reservation_{booking.id}",
        amount_inr=reservation_attempt.amount_inr,
    )
    booking.refresh_from_db()
    return trip, booking, reservation_attempt, reservation_payment


def test_owner_and_operator_can_create_manual_bookings_without_provider_payment_setup(
    user_factory,
    organizer,
):
    owner = user_factory("manual-owner@example.com")
    operator = user_factory("manual-operator@example.com")
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
    trip = create_trip(organizer, publication_state=Trip.PublicationState.DRAFT)
    package = trip.packages.first()
    assert organizer.provider_payment_setup.status == ProviderPaymentSetup.Status.NOT_STARTED
    client = APIClient()

    client.force_authenticate(owner)
    owner_response = client.post(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/manual-bookings/",
        {
            "booking_contact_name": "  Manual Owner Contact  ",
            "booking_contact_phone": "  +919876543210  ",
            "booking_contact_email": "  owner-contact@example.com  ",
            "traveler_slots": [{"package": package.id}, {"package": package.id}],
        },
        format="json",
    )

    client.force_authenticate(operator)
    operator_response = client.post(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/manual-bookings/",
        {
            "booking_contact_name": "Manual Operator Contact",
            "booking_contact_phone": "+919876543211",
            "traveler_slots": [{"package": package.id}],
        },
        format="json",
    )

    assert owner_response.status_code == 201
    assert owner_response.json()["booking_state"] == Booking.BookingState.DRAFT
    assert owner_response.json()["traveler_slot_count"] == 2
    assert owner_response.json()["booking_reservation_amount_inr"] == 16000
    owner_booking = Booking.objects.get(booking_contact_name="Manual Owner Contact")
    owner_slots = list(owner_booking.traveler_slots.order_by("position"))
    assert owner_booking.booking_contact_phone == "+919876543210"
    assert owner_booking.booking_contact_email == "owner-contact@example.com"
    assert [slot.position for slot in owner_slots] == [1, 2]
    assert [slot.booked_package_price_inr for slot in owner_slots] == [32000, 32000]
    assert operator_response.status_code == 201
    assert operator_response.json()["booking_state"] == Booking.BookingState.DRAFT
    assert Booking.objects.filter(trip=trip).count() == 2
    assert active_reserved_traveler_count(trip) == 0


def test_manual_booking_and_manual_payment_remain_available_when_provider_booking_is_unavailable(
    user_factory,
    organizer,
):
    operator = user_factory("manual-fallback-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
    )
    package = trip.packages.first()
    assert organizer.provider_payment_setup.status == ProviderPaymentSetup.Status.NOT_STARTED
    client = APIClient()

    public_response = client.post(
        f"/api/public/trips/{organizer.slug}/{trip.slug}/draft-bookings/",
        {
            "booking_contact_name": "Blocked Public Contact",
            "booking_contact_phone": "+919876543210",
            "traveler_count": 1,
            "package": package.id,
        },
        format="json",
    )

    client.force_authenticate(operator)
    manual_booking_response = client.post(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/manual-bookings/",
        {
            "booking_contact_name": "Manual Fallback Contact",
            "booking_contact_phone": "+919876543211",
            "traveler_slots": [{"package": package.id}],
        },
        format="json",
    )
    booking = Booking.objects.get(booking_contact_name="Manual Fallback Contact")
    manual_payment_response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/manual-payments/",
        {
            "amount_inr": 4000,
            "payment_reference": "upi-manual-fallback-001",
        },
        format="json",
    )

    assert public_response.status_code == 400
    assert public_response.json()["public_booking_gate"]["reason_code"] == (
        "payment_method_readiness_missing"
    )
    assert manual_booking_response.status_code == 201
    assert manual_booking_response.json()["booking_state"] == Booking.BookingState.DRAFT
    assert manual_payment_response.status_code == 201
    assert manual_payment_response.json()["status"] == ManualPayment.Status.APPROVED
    assert manual_payment_response.json()["reconciliation"]["collected_inr"] == 4000


def test_manual_booking_creation_requires_contact_slots_and_trip_packages(
    user_factory,
    organizer,
):
    operator = user_factory("manual-required-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer)
    other_trip = create_trip(organizer, title="Western Ghats Field Week")
    package = trip.packages.first()
    other_package = other_trip.packages.first()
    client = APIClient()
    client.force_authenticate(operator)

    missing_contact_response = client.post(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/manual-bookings/",
        {
            "booking_contact_phone": "+919876543210",
            "traveler_slots": [{"package": package.id}],
        },
        format="json",
    )
    no_slots_response = client.post(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/manual-bookings/",
        {
            "booking_contact_name": "Manual Contact",
            "booking_contact_phone": "+919876543210",
            "traveler_slots": [],
        },
        format="json",
    )
    wrong_package_response = client.post(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/manual-bookings/",
        {
            "booking_contact_name": "Manual Contact",
            "booking_contact_phone": "+919876543210",
            "traveler_slots": [{"package": other_package.id}],
        },
        format="json",
    )

    assert missing_contact_response.status_code == 400
    assert "booking_contact_name" in missing_contact_response.json()
    assert no_slots_response.status_code == 400
    assert "traveler_slots" in no_slots_response.json()
    assert wrong_package_response.status_code == 400
    assert "traveler_slots" in wrong_package_response.json()


def test_non_member_cannot_create_manual_booking(user_factory, organizer):
    outsider = user_factory("manual-outsider@example.com")
    trip = create_trip(organizer)
    package = trip.packages.first()
    client = APIClient()
    client.force_authenticate(outsider)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/manual-bookings/",
        {
            "booking_contact_name": "Manual Contact",
            "booking_contact_phone": "+919876543210",
            "traveler_slots": [{"package": package.id}],
        },
        format="json",
    )

    assert response.status_code == 403


def test_owner_and_operator_can_submit_trip_scoped_booking_import(user_factory, organizer):
    owner = user_factory("booking-import-owner@example.com")
    operator = user_factory("booking-import-operator@example.com")
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
    trip = create_trip(organizer, capacity=4)
    package = trip.packages.first()
    client = APIClient()
    payload = {
        "rows": [
            {
                "booking_contact_name": "  Imported Contact  ",
                "booking_contact_phone": "  +919800000001  ",
                "traveler_slots": [
                    {
                        "package": package.id,
                        "traveler_full_name": "  Riya Shah  ",
                        "traveler_phone": "  +919800000101  ",
                        "traveler_email": "  riya@example.com  ",
                    }
                ],
                "opening_payment_amount_inr": 8000,
            }
        ]
    }

    client.force_authenticate(owner)
    owner_response = client.post(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/booking-imports/",
        payload,
        format="json",
    )
    client.force_authenticate(operator)
    operator_response = client.post(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/booking-imports/",
        {
            "rows": [
                {
                    "booking_contact_name": "Second Imported Contact",
                    "booking_contact_phone": "+919800000002",
                    "traveler_slots": [{"package": package.id}],
                    "opening_payment_amount_inr": 0,
                }
            ]
        },
        format="json",
    )

    assert owner_response.status_code == 201
    assert operator_response.status_code == 201
    assert owner_response.json()["created_count"] == 1
    assert operator_response.json()["created_count"] == 1
    imported_booking = Booking.objects.get(booking_contact_name="Imported Contact")
    imported_slot = imported_booking.traveler_slots.get()
    assert imported_booking.booking_contact_phone == "+919800000001"
    assert imported_slot.traveler_full_name == "Riya Shah"
    assert imported_slot.traveler_phone == "+919800000101"
    assert imported_slot.traveler_email == "riya@example.com"
    assert imported_slot.booked_reservation_amount_inr == 8000
    assert BookingImport.objects.filter(trip=trip).count() == 2


def test_booking_import_creates_opening_payment_records_and_reserves_by_threshold(
    user_factory,
    organizer,
    monkeypatch,
):
    monkeypatch.setattr(
        "organizers.services.send_reservation_acknowledgement",
        lambda booking: [],
    )
    operator = user_factory("booking-import-payments@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer, capacity=4)
    package = trip.packages.first()
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/booking-imports/",
        {
            "rows": [
                {
                    "booking_contact_name": "Reserved Import",
                    "booking_contact_phone": "+919800000011",
                    "traveler_slots": [{"package": package.id}],
                    "opening_payment_amount_inr": 8000,
                    "opening_payment_reference": "sheet-row-1",
                    "opening_payment_note": "Collected before TripOS onboarding.",
                },
                {
                    "booking_contact_name": "Draft Import",
                    "booking_contact_phone": "+919800000012",
                    "traveler_slots": [{"package": package.id}],
                    "opening_payment_amount_inr": 4000,
                },
            ]
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["created_count"] == 2
    assert response.json()["conflict_count"] == 0
    reserved_booking = Booking.objects.get(booking_contact_name="Reserved Import")
    draft_booking = Booking.objects.get(booking_contact_name="Draft Import")
    opening_record = OpeningPaymentRecord.objects.get(booking=reserved_booking)
    ledger_entry = LedgerEntry.objects.get(opening_payment_record=opening_record)
    assert reserved_booking.booking_state == Booking.BookingState.RESERVED
    assert draft_booking.booking_state == Booking.BookingState.DRAFT
    assert ManualPayment.objects.filter(booking__in=[reserved_booking, draft_booking]).count() == 0
    assert opening_record.amount_inr == 8000
    assert opening_record.payment_reference == "sheet-row-1"
    assert ledger_entry.entry_type == LedgerEntry.EntryType.OPENING_PAYMENT_RECORD
    assert ledger_entry.description == "Collected before TripOS onboarding."
    assert ledger_entry.manual_payment is None
    assert derived_payment_state(reserved_booking) == "reservation_paid"


def test_booking_import_never_confirms_by_default(user_factory, organizer, monkeypatch):
    monkeypatch.setattr(
        "organizers.services.send_reservation_acknowledgement",
        lambda booking: [],
    )
    operator = user_factory("booking-import-no-confirm@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer, capacity=2)
    package = trip.packages.first()

    booking_import = create_booking_import(
        trip=trip,
        actor=operator,
        rows=[
            BookingImportRowInput(
                booking_contact_name="Ready Looking Import",
                booking_contact_phone="+919800000021",
                traveler_slots=[BookingImportTravelerSlotInput(package_id=package.id)],
                opening_payment_amount_inr=32000,
            )
        ],
    )

    booking = booking_import.rows.get().booking
    booking.refresh_from_db()
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert Booking.objects.filter(booking_state=Booking.BookingState.CONFIRMED).count() == 0


def test_booking_import_surfaces_capacity_conflicts_without_overbooking(
    user_factory,
    organizer,
    monkeypatch,
):
    monkeypatch.setattr(
        "organizers.services.send_reservation_acknowledgement",
        lambda booking: [],
    )
    operator = user_factory("booking-import-capacity@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer, capacity=1)
    package = trip.packages.first()
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/booking-imports/",
        {
            "rows": [
                {
                    "booking_contact_name": "First Import",
                    "booking_contact_phone": "+919800000031",
                    "traveler_slots": [{"package": package.id}],
                    "opening_payment_amount_inr": 8000,
                },
                {
                    "booking_contact_name": "Over Capacity Import",
                    "booking_contact_phone": "+919800000032",
                    "traveler_slots": [{"package": package.id}],
                    "opening_payment_amount_inr": 8000,
                },
            ]
        },
        format="json",
    )

    payload = response.json()
    conflict_row = next(row for row in payload["rows"] if row["status"] == "conflict")
    assert response.status_code == 201
    assert payload["created_count"] == 1
    assert payload["conflict_count"] == 1
    assert payload["status"] == BookingImport.Status.COMPLETED_WITH_CONFLICTS
    assert conflict_row["conflict_code"] == "capacity_conflict"
    assert Booking.objects.filter(trip=trip).count() == 1
    assert active_reserved_traveler_count(trip) == 1
    assert available_seats(trip) == 0


def test_booking_import_updates_existing_booking_only_within_import_trip(
    user_factory,
    organizer,
):
    operator = user_factory("booking-import-update@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer, capacity=4)
    other_trip = create_trip(organizer, title="Western Ghats Field Week", capacity=4)
    package = trip.packages.first()
    other_booking = create_draft_booking(other_trip)
    booking = create_draft_booking(trip)
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/booking-imports/",
        {
            "rows": [
                {
                    "booking_id": booking.id,
                    "booking_contact_name": "Updated Import Contact",
                    "booking_contact_phone": "+919800000041",
                    "traveler_slots": [{"package": package.id}],
                    "opening_payment_amount_inr": 0,
                },
                {
                    "booking_id": other_booking.id,
                    "booking_contact_name": "Wrong Trip Contact",
                    "booking_contact_phone": "+919800000042",
                    "traveler_slots": [{"package": package.id}],
                    "opening_payment_amount_inr": 0,
                },
            ]
        },
        format="json",
    )

    booking.refresh_from_db()
    other_booking.refresh_from_db()
    assert response.status_code == 201
    assert response.json()["updated_count"] == 1
    assert response.json()["conflict_count"] == 1
    assert booking.booking_contact_name == "Updated Import Contact"
    assert other_booking.booking_contact_name == "Asha Nair"


def test_organizer_entered_manual_payment_defaults_approved_with_optional_proof(
    user_factory,
    organizer,
):
    operator = user_factory("manual-payment-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer)
    booking = create_draft_booking(trip)
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/manual-payments/",
        {
            "amount_inr": 4000,
            "payment_reference": "upi-manual-001",
            "note": "Organizer verified direct UPI transfer.",
        },
        format="json",
    )

    booking.refresh_from_db()
    manual_payment = ManualPayment.objects.get(booking=booking)
    ledger_entry = LedgerEntry.objects.get(manual_payment=manual_payment)
    assert response.status_code == 201
    assert response.json()["source"] == ManualPayment.Source.ORGANIZER_ENTERED
    assert response.json()["status"] == ManualPayment.Status.APPROVED
    assert response.json()["has_payment_proof"] is False
    assert response.json()["reconciliation"]["collected_inr"] == 4000
    assert manual_payment.approved_by == operator
    assert manual_payment.payment_proof.name == ""
    assert ledger_entry.entry_type == LedgerEntry.EntryType.APPROVED_MANUAL_PAYMENT
    assert ledger_entry.amount_inr == 4000
    assert collected_ledger_amount_inr(booking) == 4000
    assert booking.booking_state == Booking.BookingState.DRAFT


def test_approved_manual_payment_can_reserve_when_capacity_remains(
    user_factory,
    organizer,
    monkeypatch,
):
    monkeypatch.setattr(
        "organizers.services.send_reservation_acknowledgement",
        lambda booking: [],
    )
    operator = user_factory("manual-reserve-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer, capacity=1)
    booking = create_draft_booking(trip)
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/manual-payments/",
        {"amount_inr": 8000},
        format="json",
    )

    booking.refresh_from_db()
    assert response.status_code == 201
    assert response.json()["booking_state"] == Booking.BookingState.RESERVED
    assert response.json()["payment_state"] == "reservation_paid"
    assert response.json()["reconciliation"]["collected_inr"] == 8000
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert active_reserved_traveler_count(trip) == 1
    assert available_seats(trip) == 0


def test_manual_payment_cannot_reserve_beyond_available_seats(user_factory, organizer):
    operator = user_factory("manual-overbook-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer, capacity=1)
    package = trip.packages.first()
    reserved_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Reserved Contact",
        booking_contact_phone="+919111111111",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=reserved_booking, package=package, position=1)
    draft_booking = create_draft_booking(trip)
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{draft_booking.id}/manual-payments/",
        {"amount_inr": 8000},
        format="json",
    )

    draft_booking.refresh_from_db()
    assert response.status_code == 400
    assert "manual_payment" in response.json()
    assert ManualPayment.objects.filter(booking=draft_booking).count() == 0
    assert LedgerEntry.objects.filter(booking=draft_booking).count() == 0
    assert draft_booking.booking_state == Booking.BookingState.DRAFT
    assert available_seats(trip) == 0


@override_settings(MEDIA_ROOT="/private/tmp/tripos-test-media")
def test_traveler_submitted_manual_payment_requires_proof_and_starts_submitted(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    issued = issue_booking_access_link(booking)
    client = APIClient()

    missing_proof_response = client.post(
        f"/api/portal/{issued.token}/manual-payments/",
        {
            "amount_inr": 8000,
            "payment_reference": "upi-traveler-missing-proof",
        },
        format="multipart",
    )
    response = client.post(
        f"/api/portal/{issued.token}/manual-payments/",
        {
            "amount_inr": 8000,
            "payment_reference": "upi-traveler-001",
            "note": "Paid directly to organizer UPI.",
            "payment_proof": SimpleUploadedFile(
                "upi-proof.txt",
                b"payment proof",
                content_type="text/plain",
            ),
        },
        format="multipart",
    )

    booking.refresh_from_db()
    manual_payment = ManualPayment.objects.get(booking=booking)
    assert missing_proof_response.status_code == 400
    assert response.status_code == 201
    assert response.json()["source"] == ManualPayment.Source.TRAVELER_SUBMITTED
    assert response.json()["status"] == ManualPayment.Status.SUBMITTED
    assert response.json()["has_payment_proof"] is True
    assert manual_payment.original_filename == "upi-proof.txt"
    assert manual_payment.is_sensitive_payment_information is True
    assert manual_payment.exclude_from_default_exports is True
    assert LedgerEntry.objects.filter(manual_payment=manual_payment).count() == 0
    assert collected_ledger_amount_inr(booking) == 0
    assert booking.booking_state == Booking.BookingState.DRAFT


@override_settings(MEDIA_ROOT="/private/tmp/tripos-test-media")
def test_approving_traveler_submitted_manual_payment_updates_ledger_and_reserves(
    user_factory,
    organizer,
    monkeypatch,
):
    monkeypatch.setattr(
        "organizers.services.send_reservation_acknowledgement",
        lambda booking: [],
    )
    monkeypatch.setattr(
        "organizers.services.send_manual_payment_acknowledgement",
        lambda manual_payment, *, send=True: [],
    )
    operator = user_factory("traveler-payment-approver@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer, capacity=1)
    booking = create_draft_booking(trip)
    manual_payment = ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=8000,
        payment_reference="upi-traveler-approve",
        payment_proof=SimpleUploadedFile(
            "upi-proof.txt",
            b"payment proof",
            content_type="text/plain",
        ),
        original_filename="upi-proof.txt",
        content_type="text/plain",
        file_size=13,
    )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/manual-payments/{manual_payment.id}/approve/",
        {},
        format="json",
    )

    booking.refresh_from_db()
    manual_payment.refresh_from_db()
    ledger_entry = LedgerEntry.objects.get(manual_payment=manual_payment)
    assert response.status_code == 200
    assert response.json()["status"] == ManualPayment.Status.APPROVED
    assert response.json()["payment_state"] == "reservation_paid"
    assert response.json()["reconciliation"]["collected_inr"] == 8000
    assert manual_payment.approved_by == operator
    assert ledger_entry.entry_type == LedgerEntry.EntryType.APPROVED_MANUAL_PAYMENT
    assert collected_ledger_amount_inr(booking) == 8000
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert active_reserved_traveler_count(trip) == 1


@override_settings(MEDIA_ROOT="/private/tmp/tripos-test-media")
def test_approving_partial_traveler_submitted_manual_payment_collects_without_reserving(
    user_factory,
    organizer,
    monkeypatch,
):
    monkeypatch.setattr(
        "organizers.services.send_manual_payment_acknowledgement",
        lambda manual_payment, *, send=True: [],
    )
    operator = user_factory("traveler-payment-partial-approver@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer, capacity=1)
    booking = create_draft_booking(trip)
    manual_payment = ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=4000,
        payment_reference="upi-traveler-partial",
        payment_proof=SimpleUploadedFile(
            "upi-proof.txt",
            b"payment proof",
            content_type="text/plain",
        ),
        original_filename="upi-proof.txt",
        content_type="text/plain",
        file_size=13,
    )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/manual-payments/{manual_payment.id}/approve/",
        {},
        format="json",
    )

    booking.refresh_from_db()
    manual_payment.refresh_from_db()
    assert response.status_code == 200
    assert manual_payment.status == ManualPayment.Status.APPROVED
    assert LedgerEntry.objects.get(manual_payment=manual_payment).amount_inr == 4000
    assert collected_ledger_amount_inr(booking) == 4000
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert active_reserved_traveler_count(trip) == 0
    assert available_seats(trip) == 1


@override_settings(MEDIA_ROOT="/private/tmp/tripos-test-media")
def test_approving_traveler_submitted_manual_payment_rechecks_bookable_seats(
    user_factory,
    organizer,
):
    operator = user_factory("traveler-payment-capacity-approver@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer, capacity=1)
    package = trip.packages.first()
    booking = create_draft_booking(trip)
    competing_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Competing Contact",
        booking_contact_phone="+919111111111",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=competing_booking, package=package, position=1)
    manual_payment = ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=booking.booking_reservation_amount_inr,
        payment_reference="upi-traveler-capacity-conflict",
        payment_proof=SimpleUploadedFile(
            "upi-proof.txt",
            b"payment proof",
            content_type="text/plain",
        ),
        original_filename="upi-proof.txt",
        content_type="text/plain",
        file_size=13,
    )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/manual-payments/{manual_payment.id}/approve/",
        {},
        format="json",
    )

    booking.refresh_from_db()
    manual_payment.refresh_from_db()
    assert response.status_code == 400
    assert "Bookable Seats" in str(response.json())
    assert manual_payment.status == ManualPayment.Status.SUBMITTED
    assert manual_payment.approved_at is None
    assert LedgerEntry.objects.filter(manual_payment=manual_payment).count() == 0
    assert collected_ledger_amount_inr(booking) == 0
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert active_reserved_traveler_count(trip) == 1
    assert available_seats(trip) == 0


@override_settings(MEDIA_ROOT="/private/tmp/tripos-test-media")
def test_rejecting_traveler_submitted_manual_payment_does_not_affect_ledger(
    user_factory,
    organizer,
):
    operator = user_factory("traveler-payment-rejecter@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    manual_payment = ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=8000,
        payment_reference="upi-traveler-reject",
        payment_proof=SimpleUploadedFile(
            "upi-proof.txt",
            b"payment proof",
            content_type="text/plain",
        ),
        original_filename="upi-proof.txt",
        content_type="text/plain",
        file_size=13,
    )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/manual-payments/{manual_payment.id}/reject/",
        {"rejection_reason": "Amount does not match bank reference."},
        format="json",
    )

    booking.refresh_from_db()
    manual_payment.refresh_from_db()
    assert response.status_code == 200
    assert response.json()["status"] == ManualPayment.Status.REJECTED
    assert "Amount does not match" in manual_payment.note
    assert LedgerEntry.objects.filter(manual_payment=manual_payment).count() == 0
    assert collected_ledger_amount_inr(booking) == 0
    assert booking.booking_state == Booking.BookingState.DRAFT


@override_settings(MEDIA_ROOT="/private/tmp/tripos-test-media")
def test_payment_proof_download_records_sensitive_payment_activity_log(
    user_factory,
    organizer,
):
    owner = user_factory("payment-proof-download-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    manual_payment = ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=8000,
        payment_reference="upi-proof-download",
        payment_proof=SimpleUploadedFile(
            "upi-proof.txt",
            b"payment proof",
            content_type="text/plain",
        ),
        original_filename="upi-proof.txt",
        content_type="text/plain",
        file_size=13,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(
        f"/api/operations/organizers/{organizer.id}/manual-payments/{manual_payment.id}/proof-download/"
    )

    assert response.status_code == 200
    assert response["Content-Disposition"].startswith(
        'attachment; filename="upi-proof.txt"'
    )
    log = ActivityLog.objects.get(
        booking=booking,
        action=ActivityLog.Action.SENSITIVE_PAYMENT_INFORMATION_DOWNLOAD,
    )
    assert log.actor == owner
    assert log.metadata["manual_payment"] == manual_payment.id
    assert log.metadata["is_sensitive_payment_information"] is True
    assert log.metadata["exclude_from_default_exports"] is True


def test_provider_confirmed_payment_records_money_and_reserves_public_booking(organizer):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)
    client = APIClient()

    attempt_response = client.post(f"/api/public/bookings/{booking.id}/payment-attempts/")
    attempt = PaymentAttempt.objects.get(pk=attempt_response.json()["id"])
    confirmation_response = client.post(
        f"/api/public/payment-attempts/{attempt_response.json()['id']}/provider-confirmation/",
        provider_confirmation_payload(
            attempt,
            provider_payment_reference="pay_provider_confirmed_001",
        ),
        format="json",
    )

    booking.refresh_from_db()
    assert attempt_response.status_code == 201
    assert attempt_response.json()["amount_inr"] == 16000
    assert confirmation_response.status_code == 201
    assert confirmation_response.json()["amount_inr"] == 16000
    assert confirmation_response.json()["booking_state"] == Booking.BookingState.RESERVED
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert booking.provider_payments.count() == 1
    assert collected_provider_payment_amount_inr(booking) == 16000
    assert active_reserved_traveler_count(trip) == 2
    assert available_seats(trip) == 0


def test_reservation_acknowledgement_is_sent_when_booking_becomes_reserved(organizer):
    organizer.identity_name = "Spiti Field Collective"
    organizer.save()
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip)
    traveler_slot = booking.traveler_slots.first()
    traveler_slot.traveler_full_name = "Riya Shah"
    traveler_slot.traveler_phone = "+919800000001"
    traveler_slot.traveler_email = "riya@example.com"
    traveler_slot.save()
    attempt = create_public_payment_attempt(booking)

    provider_payment = confirm_provider_payment(
        attempt,
        provider_payment_reference="pay_provider_reservation_ack_001",
        amount_inr=8000,
    )

    notifications = Notification.objects.filter(
        booking=booking,
        notification_type=Notification.NotificationType.RESERVATION_ACKNOWLEDGEMENT,
    )
    assert notifications.count() == 3
    assert (
        BookingAccessLink.objects.filter(
            booking=booking,
            scope=BookingAccessLink.Scope.BOOKING,
            revoked_at__isnull=True,
        ).count()
        == 1
    )
    assert all(notification.provider_payment == provider_payment for notification in notifications)
    assert all("Payment received: INR 8,000" in notification.body for notification in notifications)
    assert all("Balance due: INR 24,000" in notification.body for notification in notifications)
    assert all(
        "Booking-Level Access Link: /portal/" in notification.body for notification in notifications
    )
    assert notifications.filter(
        recipient_type=Notification.RecipientType.BOOKING_CONTACT,
        channel=Notification.Channel.WHATSAPP,
    ).exists()
    assert notifications.filter(
        recipient_type=Notification.RecipientType.TRAVELER,
        traveler_slot=traveler_slot,
        channel=Notification.Channel.WHATSAPP,
    ).exists()
    assert notifications.filter(
        recipient_type=Notification.RecipientType.TRAVELER,
        traveler_slot=traveler_slot,
        channel=Notification.Channel.EMAIL,
    ).exists()
    assert all("Spiti Field Collective" in notification.body for notification in notifications)
    assert (
        Notification.objects.filter(
            booking=booking,
            notification_type=Notification.NotificationType.PAYMENT_ACKNOWLEDGEMENT,
        ).count()
        == 0
    )
    assert (
        ActivityLog.objects.filter(
            booking=booking,
            action=ActivityLog.Action.NOTIFICATION_SENT,
            metadata__notification_type=Notification.NotificationType.RESERVATION_ACKNOWLEDGEMENT,
        ).count()
        == 3
    )


def test_later_provider_payment_acknowledgement_is_sent_to_booking_contact_by_default(
    organizer,
):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    booking.booking_contact_email = "asha@example.com"
    booking.save()
    reservation_attempt = create_public_payment_attempt(booking)
    confirm_provider_payment(
        reservation_attempt,
        provider_payment_reference="pay_provider_reservation_ack_base_001",
        amount_inr=8000,
    )
    balance_attempt = PaymentAttempt.objects.create(
        booking=booking,
        provider=PaymentAttempt.Provider.RAZORPAY,
        purpose=PaymentAttempt.Purpose.BALANCE,
        amount_inr=4000,
        provider_attempt_reference="order_balance_payment_ack_001",
    )

    provider_payment = confirm_provider_payment(
        balance_attempt,
        provider_payment_reference="pay_provider_payment_ack_001",
        amount_inr=4000,
    )

    payment_notifications = Notification.objects.filter(
        booking=booking,
        notification_type=Notification.NotificationType.PAYMENT_ACKNOWLEDGEMENT,
    )
    assert payment_notifications.count() == 2
    assert set(payment_notifications.values_list("channel", flat=True)) == {
        Notification.Channel.WHATSAPP,
        Notification.Channel.EMAIL,
    }
    assert all(
        notification.provider_payment == provider_payment for notification in payment_notifications
    )
    assert all("INR 4,000" in notification.body for notification in payment_notifications)
    assert (
        ActivityLog.objects.filter(
            booking=booking,
            action=ActivityLog.Action.NOTIFICATION_SENT,
            metadata__notification_type=Notification.NotificationType.PAYMENT_ACKNOWLEDGEMENT,
        ).count()
        == 2
    )


def test_balance_payment_link_creates_current_due_balance_attempt_through_portal(organizer):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip)
    reservation_attempt = create_public_payment_attempt(booking)
    confirm_provider_payment(
        reservation_attempt,
        provider_payment_reference="pay_balance_link_reservation_001",
        amount_inr=8000,
    )
    issued = issue_balance_payment_link(booking)
    client = APIClient()

    portal_response = client.get(f"/api/portal/{issued.token}/")
    custom_amount_response = client.post(
        f"/api/portal/{issued.token}/balance-payment-attempts/",
        {"amount_inr": 12000},
        format="json",
    )
    attempt_response = client.post(f"/api/portal/{issued.token}/balance-payment-attempts/")

    balance_attempt = PaymentAttempt.objects.get(pk=attempt_response.json()["id"])
    assert portal_response.status_code == 200
    assert portal_response.json()["balance_payment"]["available"] is True
    assert portal_response.json()["balance_payment"]["amount_inr"] == 24000
    assert custom_amount_response.status_code == 400
    assert attempt_response.status_code == 201
    assert balance_attempt.purpose == PaymentAttempt.Purpose.BALANCE
    assert balance_attempt.amount_inr == 24000
    assert attempt_response.json()["checkout"]["payment_purpose"] == PaymentAttempt.Purpose.BALANCE
    assert not SeatHold.objects.filter(payment_attempt=balance_attempt).exists()


def test_balance_payment_checkout_creates_razorpay_order_with_booking_access_context(
    organizer,
    fake_razorpay_order_creation,
):
    _, booking, _, _ = create_reserved_booking_with_balance_due(organizer)
    issued = issue_balance_payment_link(booking)
    client = APIClient()

    response = client.post(f"/api/portal/{issued.token}/balance-payment-attempts/")

    payload = response.json()
    balance_attempt = PaymentAttempt.objects.get(pk=payload["id"])
    order_request = fake_razorpay_order_creation.requests[-1]
    order_payload = order_request["payload"]
    checkout_payload = payload["checkout"]
    serialized_checkout = payload_text(checkout_payload)
    assert response.status_code == 201
    assert resolve_active_access_link(issued.token).booking == booking
    assert balance_attempt.booking == booking
    assert balance_attempt.purpose == PaymentAttempt.Purpose.BALANCE
    assert balance_attempt.amount_inr == 24000
    assert balance_attempt.provider_attempt_reference == (
        f"order_tripos_bal_{balance_attempt.id}_{booking.id}"
    )
    assert order_request["headers"]["Authorization"] == (
        f"Bearer oauth_access_token_{organizer.id}"
    )
    assert order_payload["amount"] == balance_attempt.amount_inr * 100
    assert order_payload["receipt"] == f"tripos_bal_{balance_attempt.id}_{booking.id}"
    assert order_payload["notes"] == {
        "tripos_organizer_id": str(organizer.id),
        "tripos_booking_id": str(booking.id),
        "tripos_payment_attempt_id": str(balance_attempt.id),
        "tripos_payment_purpose": PaymentAttempt.Purpose.BALANCE,
        "tripos_provider_account": organizer.provider_payment_setup.provider_merchant_reference,
    }
    assert checkout_payload["provider"] == ProviderPaymentSetup.Provider.RAZORPAY
    assert checkout_payload["payment_attempt"] == balance_attempt.id
    assert checkout_payload["booking"] == booking.id
    assert checkout_payload["payment_purpose"] == PaymentAttempt.Purpose.BALANCE
    assert checkout_payload["provider_payload"]["key"] == f"rzp_public_{organizer.id}"
    assert checkout_payload["provider_payload"]["order_id"] == (
        balance_attempt.provider_attempt_reference
    )
    assert "oauth_access_token" not in serialized_checkout
    assert "oauth_refresh_token" not in serialized_checkout
    assert "key_secret" not in serialized_checkout
    assert not SeatHold.objects.filter(payment_attempt=balance_attempt).exists()


def test_balance_payment_attempts_block_fully_paid_cancelled_and_traveler_level_links(
    user_factory,
    organizer,
):
    operator = user_factory("balance-blocks-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer)
    fully_paid = create_draft_booking(trip)
    fully_paid.booking_state = Booking.BookingState.RESERVED
    fully_paid.save(update_fields=["booking_state", "updated_at"])
    LedgerEntry.objects.create(
        booking=fully_paid,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=fully_paid.booking_total_inr,
        description="Fully paid opening balance.",
    )
    cancelled = create_draft_booking(trip)
    cancelled.booking_state = Booking.BookingState.CANCELLED
    cancelled.save(update_fields=["booking_state", "updated_at"])
    traveler_link = issue_traveler_access_link(cancelled.traveler_slots.first())
    client = APIClient()
    client.force_authenticate(operator)

    with pytest.raises(ValidationError, match="No balance"):
        create_balance_payment_checkout(fully_paid)
    with pytest.raises(ValidationError, match="Cancelled Bookings"):
        create_balance_payment_checkout(cancelled)
    fully_paid_response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{fully_paid.id}/balance-payment-links/",
        {},
        format="json",
    )
    cancelled_response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{cancelled.id}/balance-payment-links/",
        {},
        format="json",
    )
    traveler_link_response = client.post(
        f"/api/portal/{traveler_link.token}/balance-payment-attempts/"
    )

    assert fully_paid_response.status_code == 400
    assert cancelled_response.status_code == 400
    assert traveler_link_response.status_code == 400
    assert (
        PaymentAttempt.objects.filter(
            booking__in=[fully_paid, cancelled],
            purpose=PaymentAttempt.Purpose.BALANCE,
        ).count()
        == 0
    )


def test_blocked_balance_checkout_keeps_existing_active_balance_attempt(organizer):
    _, booking, _, _ = create_reserved_booking_with_balance_due(organizer)
    active_checkout = create_balance_payment_checkout(
        booking,
        provider_adapter=FakeCheckoutAdapter("order_balance_keep_active_001"),
    )
    active_attempt = active_checkout.payment_attempt
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=booking.booking_total_inr,
        description="Fully paid after active balance checkout.",
    )

    with pytest.raises(ValidationError, match="No balance"):
        create_balance_payment_checkout(
            booking,
            provider_adapter=FakeCheckoutAdapter("order_balance_should_not_create_001"),
        )

    active_attempt.refresh_from_db()
    assert active_attempt.status == PaymentAttempt.Status.PENDING
    assert (
        PaymentAttempt.objects.filter(
            booking=booking,
            purpose=PaymentAttempt.Purpose.BALANCE,
        ).count()
        == 1
    )


def test_owner_and_operator_can_manually_send_balance_payment_links(user_factory, organizer):
    owner = user_factory("balance-link-owner@example.com")
    operator = user_factory("balance-link-operator@example.com")
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
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.booking_contact_email = "asha@example.com"
    booking.save(update_fields=["booking_state", "booking_contact_email", "updated_at"])
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=booking.booking_reservation_amount_inr,
        description="Reservation amount collected.",
    )
    client = APIClient()

    client.force_authenticate(owner)
    owner_response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/balance-payment-links/",
        {"note": "Balance follow-up."},
        format="json",
    )
    client.force_authenticate(operator)
    operator_response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/balance-payment-links/",
        {},
        format="json",
    )

    assert owner_response.status_code == 201
    assert operator_response.status_code == 201
    assert owner_response.json()["balance_payment_link"]["amount_inr"] == 24000
    assert owner_response.json()["balance_payment_link"]["path"].startswith("/portal/")
    assert owner_response.json()["sent_count"] == 2
    assert operator_response.json()["sent_count"] == 2
    assert (
        BookingAccessLink.objects.filter(
            booking=booking,
            scope=BookingAccessLink.Scope.BOOKING,
            revoked_at__isnull=True,
        ).count()
        == 2
    )
    assert (
        Notification.objects.filter(
            booking=booking,
            notification_type=Notification.NotificationType.MANUAL_REMINDER,
            metadata__balance_payment_link=True,
        ).count()
        == 4
    )


def test_balance_due_reminders_include_balance_payment_links(organizer):
    now = timezone.make_aware(datetime(2026, 1, 7, 9, 0))
    trip = create_bookable_trip(
        organizer,
        start_date=date(2026, 1, 20),
        end_date=date(2026, 1, 24),
    )
    trip.payment_schedule.balance_due_days_before_start = 11
    trip.payment_schedule.balance_reminder_lead_days = 2
    trip.payment_schedule.save()
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Due Contact",
        booking_contact_phone="+919876543210",
        booking_contact_email="due@example.com",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=booking, package=trip.packages.first(), position=1)
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=booking.booking_reservation_amount_inr,
        description="Reservation amount collected.",
    )

    run = process_automatic_reminders(now=now)
    repeated_run = process_automatic_reminders(now=now + timedelta(hours=1))

    reminders = Notification.objects.filter(
        booking=booking,
        notification_type=Notification.NotificationType.BALANCE_DUE_REMINDER,
    )
    assert run.balance_due_reminders == 2
    assert repeated_run.balance_due_reminders == 0
    assert reminders.count() == 2
    assert all(notification.metadata["balance_payment_link"] is True for notification in reminders)
    assert all("/portal/" in notification.body for notification in reminders)
    token = reminders.first().metadata["balance_payment_link_path"].strip("/").split("/")[1]
    assert resolve_active_access_link(token).booking == booking


def test_balance_provider_payment_does_not_create_holds_or_change_capacity(organizer):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip)
    reservation_attempt = create_public_payment_attempt(booking)
    confirm_provider_payment(
        reservation_attempt,
        provider_payment_reference="pay_balance_capacity_reservation_001",
        amount_inr=8000,
    )
    premium_package = TripPackage.objects.create(
        trip=trip,
        name="Premium room",
        price_inr=42000,
        reservation_amount_inr=12000,
        position=2,
    )
    pending_addition = add_traveler_to_booking(
        booking,
        package=premium_package,
        traveler_full_name="Nikhil Rao",
        traveler_phone="+918888888888",
    )
    available_before = available_seats(trip)
    reserved_before = active_reserved_traveler_count(trip)
    checkout = create_balance_payment_checkout(
        booking,
        provider_adapter=FakeCheckoutAdapter("order_balance_capacity_001"),
    )

    provider_payment = confirm_provider_payment(
        checkout.payment_attempt,
        provider_payment_reference="pay_balance_capacity_001",
        amount_inr=checkout.payment_attempt.amount_inr,
    )

    pending_addition.refresh_from_db()
    assert provider_payment.payment_attempt.purpose == PaymentAttempt.Purpose.BALANCE
    assert not SeatHold.objects.filter(payment_attempt=checkout.payment_attempt).exists()
    assert pending_addition.traveler_state == TravelerSlot.TravelerState.PENDING_ADDITION
    assert active_reserved_traveler_count(trip) == reserved_before
    assert available_seats(trip) == available_before
    assert (
        Notification.objects.filter(
            provider_payment=provider_payment,
            notification_type=Notification.NotificationType.PAYMENT_ACKNOWLEDGEMENT,
        ).count()
        == 1
    )


def test_organizer_entered_manual_payment_acknowledgement_is_optional(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)

    silent_payment = create_organizer_entered_manual_payment(
        booking=booking,
        amount_inr=4000,
        payment_reference="manual_silent_001",
    )
    loud_payment = create_organizer_entered_manual_payment(
        booking=booking,
        amount_inr=4000,
        payment_reference="manual_loud_001",
        send_payment_acknowledgement=True,
    )

    assert Notification.objects.filter(manual_payment=silent_payment).count() == 0
    assert (
        Notification.objects.filter(
            manual_payment=loud_payment,
            notification_type=Notification.NotificationType.PAYMENT_ACKNOWLEDGEMENT,
        ).count()
        == 1
    )


def test_approved_traveler_submitted_manual_payment_acknowledgement_defaults_to_sent(
    organizer,
):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    manual_payment = ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.APPROVED,
        amount_inr=8000,
        payment_reference="traveler_manual_001",
    )

    notifications = send_manual_payment_acknowledgement(manual_payment)

    assert len(notifications) == 1
    assert (
        notifications[0].notification_type == Notification.NotificationType.PAYMENT_ACKNOWLEDGEMENT
    )
    assert notifications[0].recipient_type == Notification.RecipientType.BOOKING_CONTACT
    assert Notification.objects.filter(manual_payment=manual_payment).count() == 1


def test_refund_acknowledgement_uses_optional_safe_seam(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)

    skipped = send_refund_acknowledgement(
        booking=booking,
        amount_inr=2500,
        refund_reference="refund_optional_001",
        refund_reason="Traveler cancellation",
        send=False,
    )
    sent = send_refund_acknowledgement(
        booking=booking,
        amount_inr=2500,
        refund_reference="refund_optional_001",
        refund_reason="Traveler cancellation",
        send=True,
    )

    assert skipped == []
    assert len(sent) == 1
    assert sent[0].notification_type == Notification.NotificationType.REFUND_ACKNOWLEDGEMENT
    assert sent[0].metadata["refund_reason"] == "Traveler cancellation"
    assert (
        ActivityLog.objects.filter(
            booking=booking,
            action=ActivityLog.Action.NOTIFICATION_SENT,
            metadata__notification_type=Notification.NotificationType.REFUND_ACKNOWLEDGEMENT,
        ).count()
        == 1
    )


def test_automatic_draft_recovery_reminder_sends_once_before_expiry(organizer):
    now = timezone.make_aware(datetime(2026, 1, 10, 8, 0))
    trip = create_bookable_trip(organizer)
    eligible = create_draft_booking(trip)
    too_new = create_draft_booking(trip)
    older_than_expiry_window = create_draft_booking(trip)
    no_contact_channel = create_draft_booking(trip)
    created_at = now - timedelta(hours=20, minutes=1)
    Booking.objects.filter(pk=eligible.pk).update(
        created_at=created_at,
        draft_expires_at=created_at + timedelta(hours=24),
    )
    Booking.objects.filter(pk=too_new.pk).update(
        created_at=now - timedelta(hours=19),
        draft_expires_at=now + timedelta(hours=4),
    )
    Booking.objects.filter(pk=older_than_expiry_window.pk).update(
        created_at=now - timedelta(hours=24, minutes=1),
        draft_expires_at=now + timedelta(hours=4),
    )
    Booking.objects.filter(pk=no_contact_channel.pk).update(
        created_at=created_at,
        draft_expires_at=created_at + timedelta(hours=24),
        booking_contact_phone="",
        booking_contact_email="",
    )

    first_run = process_automatic_reminders(now=now)
    second_run = process_automatic_reminders(now=now + timedelta(minutes=5))

    reminders = Notification.objects.filter(
        notification_type=Notification.NotificationType.DRAFT_RECOVERY_REMINDER,
    )
    assert first_run.draft_recovery_reminders == 1
    assert second_run.draft_recovery_reminders == 0
    assert reminders.count() == 1
    assert reminders.get().booking == eligible
    assert reminders.get().recipient_type == Notification.RecipientType.BOOKING_CONTACT
    assert (
        ActivityLog.objects.filter(
            booking=eligible,
            action=ActivityLog.Action.NOTIFICATION_SENT,
            metadata__notification_type=Notification.NotificationType.DRAFT_RECOVERY_REMINDER,
        ).count()
        == 1
    )


def test_automatic_payment_reminders_respect_lead_time_due_balance_and_state_exclusions(
    organizer,
):
    balance_now = timezone.make_aware(datetime(2026, 1, 7, 9, 0))
    overdue_now = timezone.make_aware(datetime(2026, 1, 10, 9, 0))
    trip = create_bookable_trip(
        organizer,
        start_date=date(2026, 1, 20),
        end_date=date(2026, 1, 24),
    )
    trip.payment_schedule.balance_due_days_before_start = 11
    trip.payment_schedule.balance_reminder_lead_days = 2
    trip.payment_schedule.save()
    package = trip.packages.first()

    due_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Due Contact",
        booking_contact_phone="+919876543210",
        booking_contact_email="due@example.com",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=due_booking, package=package, position=1)
    LedgerEntry.objects.create(
        booking=due_booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=package.reservation_amount_inr,
        description="Reservation amount collected.",
    )
    completed_due_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Completed Contact",
        booking_contact_phone="+919876543211",
        booking_state=Booking.BookingState.COMPLETED,
    )
    TravelerSlot.objects.create(booking=completed_due_booking, package=package, position=1)
    cancelled_due_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Cancelled Contact",
        booking_contact_phone="+919876543212",
        booking_state=Booking.BookingState.CANCELLED,
    )
    TravelerSlot.objects.create(booking=cancelled_due_booking, package=package, position=1)

    early_run = process_automatic_reminders(now=balance_now - timedelta(days=1))
    balance_run = process_automatic_reminders(now=balance_now)
    repeated_balance_run = process_automatic_reminders(now=balance_now + timedelta(hours=1))
    overdue_run = process_automatic_reminders(now=overdue_now)
    repeated_overdue_run = process_automatic_reminders(now=overdue_now + timedelta(hours=1))

    assert early_run.balance_due_reminders == 0
    assert balance_run.balance_due_reminders == 2
    assert repeated_balance_run.balance_due_reminders == 0
    assert overdue_run.overdue_balance_reminders == 2
    assert repeated_overdue_run.overdue_balance_reminders == 0
    assert (
        Notification.objects.filter(
            notification_type=Notification.NotificationType.BALANCE_DUE_REMINDER,
        ).count()
        == 2
    )
    assert (
        Notification.objects.filter(
            notification_type=Notification.NotificationType.OVERDUE_BALANCE_REMINDER,
        ).count()
        == 2
    )
    assert not Notification.objects.filter(booking=completed_due_booking).exists()
    assert not Notification.objects.filter(booking=cancelled_due_booking).exists()
    assert (
        ActivityLog.objects.filter(
            booking=due_booking,
            action=ActivityLog.Action.NOTIFICATION_SENT,
            metadata__notification_type=Notification.NotificationType.OVERDUE_BALANCE_REMINDER,
        ).count()
        == 2
    )


def test_automatic_missing_requirements_reminder_sends_to_contact_and_relevant_traveler(
    organizer,
):
    now = timezone.make_aware(datetime(2026, 1, 17, 9, 0))
    trip = create_bookable_trip(
        organizer,
        start_date=date(2026, 1, 20),
        end_date=date(2026, 1, 24),
        requires_traveler_documents=True,
        requires_emergency_contact=True,
    )
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Readiness Contact",
        booking_contact_phone="+919876543210",
        booking_contact_email="contact@example.com",
        booking_state=Booking.BookingState.RESERVED,
    )
    traveler = TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.first(),
        position=1,
        traveler_full_name="Riya Shah",
        traveler_phone="+919800000001",
        traveler_email="riya@example.com",
    )
    Booking.objects.filter(pk=booking.pk).update(updated_at=now - timedelta(days=10))

    run = process_automatic_reminders(now=now)
    repeated_run = process_automatic_reminders(now=now + timedelta(hours=1))

    reminders = Notification.objects.filter(
        booking=booking,
        notification_type=Notification.NotificationType.MISSING_REQUIREMENTS_REMINDER,
    )
    assert run.missing_requirements_reminders == 4
    assert repeated_run.missing_requirements_reminders == 0
    assert reminders.count() == 4
    assert (
        reminders.filter(
            recipient_type=Notification.RecipientType.BOOKING_CONTACT,
            traveler_slot__isnull=True,
        ).count()
        == 2
    )
    assert (
        reminders.filter(
            recipient_type=Notification.RecipientType.TRAVELER,
            traveler_slot=traveler,
        ).count()
        == 2
    )
    assert {notification.metadata["reminder_timing"] for notification in reminders} == {"scheduled"}


def test_late_reserved_booking_gets_missing_requirements_reminder_soon_after_reservation(
    organizer,
):
    now = timezone.make_aware(datetime(2026, 1, 18, 9, 0))
    trip = create_bookable_trip(
        organizer,
        start_date=date(2026, 1, 20),
        end_date=date(2026, 1, 24),
        requires_traveler_identity_details=True,
    )
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Late Contact",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=booking, package=trip.packages.first(), position=1)
    Booking.objects.filter(pk=booking.pk).update(updated_at=now)

    run = process_automatic_reminders(now=now)

    reminder = Notification.objects.get(
        booking=booking,
        notification_type=Notification.NotificationType.MISSING_REQUIREMENTS_REMINDER,
    )
    assert run.missing_requirements_reminders == 1
    assert reminder.metadata["reminder_timing"] == "late"
    assert reminder.recipient_type == Notification.RecipientType.BOOKING_CONTACT


def test_manual_payment_reminder_allows_completed_booking_with_due_balance_and_logs_actor(
    user_factory,
    organizer,
):
    actor = user_factory("manual-reminder-operator@example.com")
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.COMPLETED
    booking.booking_contact_email = "contact@example.com"
    booking.save()

    notifications = send_manual_reminder(
        booking,
        reminder_kind="payment_balance",
        note="Please settle this before accounts close.",
        actor=actor,
    )

    assert len(notifications) == 2
    assert {notification.channel for notification in notifications} == {
        Notification.Channel.WHATSAPP,
        Notification.Channel.EMAIL,
    }
    assert {notification.notification_type for notification in notifications} == {
        Notification.NotificationType.MANUAL_REMINDER
    }
    assert {notification.metadata["reminder_kind"] for notification in notifications} == {
        "payment_balance"
    }
    assert (
        ActivityLog.objects.filter(
            booking=booking,
            actor=actor,
            action=ActivityLog.Action.NOTIFICATION_SENT,
            metadata__notification_type=Notification.NotificationType.MANUAL_REMINDER,
        ).count()
        == 2
    )


def test_manual_reminder_excludes_cancelled_payment_and_document_obligations(organizer):
    trip = create_bookable_trip(organizer, requires_traveler_documents=True)
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.CANCELLED
    booking.save()

    with pytest.raises(ValidationError, match="payment Reminders"):
        send_manual_reminder(booking, reminder_kind="payment_balance")
    with pytest.raises(ValidationError, match="document Reminders"):
        send_manual_reminder(booking, reminder_kind="missing_requirements")

    assert Notification.objects.filter(booking=booking).count() == 0


def test_manual_missing_requirements_reminder_targets_contact_and_relevant_traveler(
    organizer,
):
    trip = create_bookable_trip(
        organizer,
        requires_traveler_documents=True,
        requires_emergency_contact=True,
    )
    booking = create_draft_booking(trip, slot_count=2)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.booking_contact_email = "contact@example.com"
    booking.save()
    first_slot, second_slot = list(booking.traveler_slots.order_by("position"))
    first_slot.traveler_full_name = "Riya Shah"
    first_slot.traveler_phone = "+919800000001"
    first_slot.traveler_email = "riya@example.com"
    first_slot.save()
    second_slot.traveler_full_name = "Karan Mehta"
    second_slot.traveler_phone = "+919800000002"
    second_slot.save()
    TravelerDocument.objects.create(
        traveler_slot=second_slot,
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        document_state=TravelerDocument.DocumentState.APPROVED,
    )

    notifications = send_manual_reminder(booking, reminder_kind="missing_requirements")

    assert len(notifications) == 5
    assert (
        Notification.objects.filter(
            booking=booking,
            notification_type=Notification.NotificationType.MANUAL_REMINDER,
            recipient_type=Notification.RecipientType.BOOKING_CONTACT,
        ).count()
        == 2
    )
    assert (
        Notification.objects.filter(
            booking=booking,
            notification_type=Notification.NotificationType.MANUAL_REMINDER,
            recipient_type=Notification.RecipientType.TRAVELER,
            traveler_slot=first_slot,
        ).count()
        == 2
    )
    assert (
        Notification.objects.filter(
            booking=booking,
            notification_type=Notification.NotificationType.MANUAL_REMINDER,
            recipient_type=Notification.RecipientType.TRAVELER,
            traveler_slot=second_slot,
        ).count()
        == 1
    )


def test_announcement_targets_reserved_confirmed_contacts_and_active_travelers_only(
    user_factory,
    organizer,
):
    actor = user_factory("announcement-operator@example.com")
    trip = create_bookable_trip(organizer)
    reserved_booking = create_draft_booking(trip)
    reserved_booking.booking_state = Booking.BookingState.RESERVED
    reserved_booking.booking_contact_email = "reserved@example.com"
    reserved_booking.save()
    reserved_slot = reserved_booking.traveler_slots.first()
    reserved_slot.traveler_full_name = "Reserved Traveler"
    reserved_slot.traveler_phone = "+919800000011"
    reserved_slot.save()
    confirmed_booking = create_draft_booking(trip)
    confirmed_booking.booking_state = Booking.BookingState.CONFIRMED
    confirmed_booking.save()
    confirmed_slot = confirmed_booking.traveler_slots.first()
    confirmed_slot.traveler_full_name = "Cancelled Traveler"
    confirmed_slot.traveler_phone = "+919800000012"
    confirmed_slot.traveler_state = TravelerSlot.TravelerState.CANCELLED
    confirmed_slot.save()
    draft_booking = create_draft_booking(trip)
    cancelled_booking = create_draft_booking(trip)
    cancelled_booking.booking_state = Booking.BookingState.CANCELLED
    cancelled_booking.save()

    notifications = send_announcement(
        trip,
        subject="Pickup point changed",
        body="Boarding now starts at Gate 2.",
        actor=actor,
    )

    assert len(notifications) == 4
    assert {notification.booking_id for notification in notifications} == {
        reserved_booking.id,
        confirmed_booking.id,
    }
    assert (
        Notification.objects.filter(
            booking=draft_booking,
            notification_type=Notification.NotificationType.ANNOUNCEMENT,
        ).count()
        == 0
    )
    assert (
        Notification.objects.filter(
            booking=cancelled_booking,
            notification_type=Notification.NotificationType.ANNOUNCEMENT,
        ).count()
        == 0
    )
    assert (
        Notification.objects.filter(
            traveler_slot=confirmed_slot,
            notification_type=Notification.NotificationType.ANNOUNCEMENT,
        ).count()
        == 0
    )
    assert (
        ActivityLog.objects.filter(
            trip=trip,
            actor=actor,
            action=ActivityLog.Action.NOTIFICATION_SENT,
            metadata__notification_type=Notification.NotificationType.ANNOUNCEMENT,
        ).count()
        == 4
    )


def test_announcement_subject_is_clamped_after_organizer_identity_prefix(organizer):
    organizer.identity_name = "A" * 160
    organizer.save()
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()

    notifications = send_announcement(
        trip,
        subject="B" * 120,
        body="Gate 2 reporting.",
    )

    assert len(notifications) == 1
    assert len(notifications[0].subject) == 180
    assert notifications[0].metadata["announcement_subject"] == "B" * 120


def test_owner_and_operator_can_send_manual_reminder_and_announcement_via_operations_api(
    user_factory,
    organizer,
):
    owner = user_factory("manual-notification-owner@example.com")
    operator = user_factory("manual-notification-operator@example.com")
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
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    client = APIClient()

    client.force_authenticate(owner)
    owner_response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/manual-reminders/",
        {"reminder_kind": "payment_balance", "note": "Balance follow-up."},
        format="json",
    )
    client.force_authenticate(operator)
    operator_response = client.post(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/announcements/",
        {
            "subject": "Pickup point changed",
            "body": "Boarding now starts at Gate 2.",
        },
        format="json",
    )

    assert owner_response.status_code == 201
    assert owner_response.json()["sent_count"] == 1
    assert operator_response.status_code == 201
    assert operator_response.json()["sent_count"] == 1
    assert (
        Notification.objects.filter(
            notification_type=Notification.NotificationType.MANUAL_REMINDER,
        ).count()
        == 1
    )
    assert (
        Notification.objects.filter(
            notification_type=Notification.NotificationType.ANNOUNCEMENT,
        ).count()
        == 1
    )


def test_manual_notification_operations_api_rejects_non_members(user_factory, organizer):
    outsider = user_factory("manual-notification-outsider@example.com")
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    client = APIClient()
    client.force_authenticate(outsider)

    reminder_response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/manual-reminders/",
        {"reminder_kind": "payment_balance"},
        format="json",
    )
    announcement_response = client.post(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/announcements/",
        {"subject": "Pickup", "body": "Gate 2."},
        format="json",
    )

    assert reminder_response.status_code == 403
    assert announcement_response.status_code == 403


def test_pending_and_failed_payment_attempts_do_not_collect_money_or_reserve_capacity(organizer):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)

    pending_attempt = create_public_payment_attempt(booking)
    failed_attempt = create_public_payment_attempt(booking)
    fail_payment_attempt(failed_attempt, failure_reason="Provider declined the payment.")

    booking.refresh_from_db()
    assert PaymentAttempt.objects.get(pk=pending_attempt.pk).status == (
        PaymentAttempt.Status.SUPERSEDED
    )
    assert PaymentAttempt.objects.get(pk=failed_attempt.pk).status == PaymentAttempt.Status.FAILED
    assert ProviderPayment.objects.filter(booking=booking).count() == 0
    assert collected_provider_payment_amount_inr(booking) == 0
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert active_reserved_traveler_count(trip) == 0
    assert available_seats(trip) == 2


@override_settings(TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET="")
def test_browser_checkout_success_verifies_signature_and_marks_attempt_confirming(
    organizer,
    monkeypatch,
):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)
    attempt = create_public_payment_attempt(booking)
    client = APIClient()

    def fake_fetch_payment(self, request):
        return ProviderPaymentConfirmation(
            provider=ProviderPaymentSetup.Provider.RAZORPAY,
            provider_payment_reference=request.provider_payment_reference,
            provider_attempt_reference=attempt.provider_attempt_reference,
            amount_inr=attempt.amount_inr,
            status="authorized",
            payment_attempt_id=attempt.id,
            booking_id=booking.id,
            purpose=PaymentAttempt.Purpose.RESERVATION,
        )

    monkeypatch.setattr(
        "trip_payments.provider_adapters.RazorpayCheckoutAdapter.fetch_payment",
        fake_fetch_payment,
    )
    response = client.post(
        f"/api/public/payment-attempts/{attempt.id}/checkout-success/",
        razorpay_checkout_success_payload(attempt),
        format="json",
    )

    booking.refresh_from_db()
    attempt.refresh_from_db()
    assert response.status_code == 200
    assert response.json()["status"] == PaymentAttempt.Status.CONFIRMING
    assert response.json()["purpose"] == PaymentAttempt.Purpose.RESERVATION
    assert attempt.status == PaymentAttempt.Status.CONFIRMING
    assert attempt.checkout_succeeded_at is not None
    assert ProviderPayment.objects.filter(booking=booking).count() == 0
    assert LedgerEntry.objects.filter(booking=booking).count() == 0
    assert collected_provider_payment_amount_inr(booking) == 0
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert active_reserved_traveler_count(trip) == 0
    assert available_seats(trip) == 2


@override_settings(TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET="")
def test_browser_checkout_success_rejects_invalid_signature(organizer, monkeypatch):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)
    attempt = create_public_payment_attempt(booking)
    client = APIClient()

    def unexpected_fetch_payment(self, request):
        raise AssertionError("Invalid signatures must not fetch provider payment state.")

    monkeypatch.setattr(
        "trip_payments.provider_adapters.RazorpayCheckoutAdapter.fetch_payment",
        unexpected_fetch_payment,
    )
    response = client.post(
        f"/api/public/payment-attempts/{attempt.id}/checkout-success/",
        razorpay_checkout_success_payload(attempt, signature="not-a-valid-signature"),
        format="json",
    )

    booking.refresh_from_db()
    attempt.refresh_from_db()
    assert response.status_code == 400
    assert attempt.status == PaymentAttempt.Status.PENDING
    assert attempt.checkout_succeeded_at is None
    assert ProviderPayment.objects.filter(booking=booking).count() == 0
    assert LedgerEntry.objects.filter(booking=booking).count() == 0
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert active_reserved_traveler_count(trip) == 0
    assert available_seats(trip) == 2


@override_settings(TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET="")
def test_browser_checkout_success_rejects_mismatched_attempt_order(organizer, monkeypatch):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)
    attempt = create_public_payment_attempt(booking)
    client = APIClient()
    wrong_order_reference = "order_wrong_browser_success"

    def unexpected_fetch_payment(self, request):
        raise AssertionError("Mismatched orders must not fetch provider payment state.")

    monkeypatch.setattr(
        "trip_payments.provider_adapters.RazorpayCheckoutAdapter.fetch_payment",
        unexpected_fetch_payment,
    )
    response = client.post(
        f"/api/public/payment-attempts/{attempt.id}/checkout-success/",
        razorpay_checkout_success_payload(
            attempt,
            provider_attempt_reference=wrong_order_reference,
        ),
        format="json",
    )

    booking.refresh_from_db()
    attempt.refresh_from_db()
    assert response.status_code == 400
    assert attempt.status == PaymentAttempt.Status.PENDING
    assert attempt.checkout_succeeded_at is None
    assert ProviderPayment.objects.filter(booking=booking).count() == 0
    assert LedgerEntry.objects.filter(booking=booking).count() == 0
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert active_reserved_traveler_count(trip) == 0
    assert available_seats(trip) == 2


@override_settings(TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET="")
def test_browser_checkout_success_with_captured_fetch_reserves_through_confirmation_path(
    organizer,
    monkeypatch,
):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)
    attempt = create_public_payment_attempt(booking)
    client = APIClient()

    def fake_fetch_payment(self, request):
        return ProviderPaymentConfirmation(
            provider=ProviderPaymentSetup.Provider.RAZORPAY,
            provider_payment_reference=request.provider_payment_reference,
            provider_attempt_reference=attempt.provider_attempt_reference,
            amount_inr=attempt.amount_inr,
            status="captured",
            payment_attempt_id=attempt.id,
            booking_id=booking.id,
            purpose=PaymentAttempt.Purpose.RESERVATION,
        )

    monkeypatch.setattr(
        "trip_payments.provider_adapters.RazorpayCheckoutAdapter.fetch_payment",
        fake_fetch_payment,
    )
    response = client.post(
        f"/api/public/payment-attempts/{attempt.id}/checkout-success/",
        razorpay_checkout_success_payload(
            attempt,
            provider_payment_reference="pay_browser_checkout_captured_001",
        ),
        format="json",
    )

    booking.refresh_from_db()
    attempt.refresh_from_db()
    provider_payment = ProviderPayment.objects.get(booking=booking)
    seat_hold = SeatHold.objects.get(payment_attempt=attempt)
    assert response.status_code == 200
    assert response.json()["status"] == PaymentAttempt.Status.CONFIRMED
    assert attempt.status == PaymentAttempt.Status.CONFIRMED
    assert attempt.checkout_succeeded_at is not None
    assert provider_payment.provider_payment_reference == "pay_browser_checkout_captured_001"
    assert provider_payment.amount_inr == attempt.amount_inr
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert collected_provider_payment_amount_inr(booking) == attempt.amount_inr
    assert booking.ledger_entries.count() == 2
    assert seat_hold.released_at is not None
    assert active_reserved_traveler_count(trip) == 2
    assert available_seats(trip) == 0


@override_settings(TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET="")
def test_browser_checkout_success_authorized_only_does_not_create_provider_payment(
    organizer,
    monkeypatch,
):
    trip = create_bookable_trip(organizer, capacity=1)
    booking = create_draft_booking(trip)
    attempt = create_public_payment_attempt(booking)
    client = APIClient()

    def fake_fetch_payment(self, request):
        return ProviderPaymentConfirmation(
            provider=ProviderPaymentSetup.Provider.RAZORPAY,
            provider_payment_reference=request.provider_payment_reference,
            provider_attempt_reference=attempt.provider_attempt_reference,
            amount_inr=attempt.amount_inr,
            status="authorized",
            payment_attempt_id=attempt.id,
            booking_id=booking.id,
            purpose=PaymentAttempt.Purpose.RESERVATION,
        )

    monkeypatch.setattr(
        "trip_payments.provider_adapters.RazorpayCheckoutAdapter.fetch_payment",
        fake_fetch_payment,
    )
    response = client.post(
        f"/api/public/payment-attempts/{attempt.id}/checkout-success/",
        razorpay_checkout_success_payload(
            attempt,
            provider_payment_reference="pay_browser_checkout_authorized_001",
        ),
        format="json",
    )

    booking.refresh_from_db()
    attempt.refresh_from_db()
    assert response.status_code == 200
    assert response.json()["status"] == PaymentAttempt.Status.CONFIRMING
    assert attempt.status == PaymentAttempt.Status.CONFIRMING
    assert ProviderPayment.objects.filter(booking=booking).count() == 0
    assert LedgerEntry.objects.filter(booking=booking).count() == 0
    assert booking_reconciliation(booking).platform_fee_inr == 0
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert active_reserved_traveler_count(trip) == 0
    assert available_seats(trip) == 1


def test_provider_payment_lifecycle_ingests_authorized_only_confirmation(organizer):
    trip = create_bookable_trip(organizer, capacity=1)
    booking = create_draft_booking(trip)
    attempt = create_public_payment_attempt(booking)

    result = lifecycle_ingest_provider_payment_confirmation(
        ProviderPaymentConfirmation(
            provider=ProviderPaymentSetup.Provider.RAZORPAY,
            provider_payment_reference="pay_lifecycle_authorized_only_001",
            provider_attempt_reference=attempt.provider_attempt_reference,
            amount_inr=attempt.amount_inr,
            status="authorized",
            payment_attempt_id=attempt.id,
            booking_id=booking.id,
            purpose=PaymentAttempt.Purpose.RESERVATION,
        ),
        source="provider_lifecycle_test",
    )

    booking.refresh_from_db()
    attempt.refresh_from_db()
    assert result.ignored_reason == "payment_not_captured"
    assert result.payment_attempt == attempt
    assert result.provider_payment is None
    assert result.payment_exception is None
    assert attempt.status == PaymentAttempt.Status.CONFIRMING
    assert ProviderPayment.objects.filter(booking=booking).count() == 0
    assert LedgerEntry.objects.filter(booking=booking).count() == 0
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert active_reserved_traveler_count(trip) == 0


def test_provider_payment_lifecycle_ignores_confirmation_without_matching_attempt(organizer):
    result = lifecycle_ingest_provider_payment_confirmation(
        ProviderPaymentConfirmation(
            provider=ProviderPaymentSetup.Provider.RAZORPAY,
            provider_payment_reference="pay_lifecycle_missing_attempt_001",
            provider_attempt_reference="order_lifecycle_missing_attempt_001",
            amount_inr=8000,
            status="captured",
            payment_attempt_id=None,
            booking_id=None,
            purpose=PaymentAttempt.Purpose.RESERVATION,
        ),
        source="provider_lifecycle_test",
    )

    assert result.ignored_reason == "payment_attempt_not_found"
    assert result.payment_attempt is None
    assert result.provider_payment is None
    assert result.payment_exception is None
    assert ProviderPayment.objects.count() == 0
    assert PaymentException.objects.count() == 0


@override_settings(TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET="")
def test_balance_browser_checkout_success_uses_shared_confirmation_path_and_is_idempotent(
    organizer,
    monkeypatch,
):
    trip, booking, _, _ = create_reserved_booking_with_balance_due(organizer, capacity=2)
    balance_checkout = create_balance_payment_checkout(booking)
    balance_attempt = balance_checkout.payment_attempt
    reserved_before = active_reserved_traveler_count(trip)
    available_before = available_seats(trip)
    client = APIClient()

    def fake_fetch_payment(self, request):
        return ProviderPaymentConfirmation(
            provider=ProviderPaymentSetup.Provider.RAZORPAY,
            provider_payment_reference=request.provider_payment_reference,
            provider_attempt_reference=balance_attempt.provider_attempt_reference,
            amount_inr=balance_attempt.amount_inr,
            status="captured",
            payment_attempt_id=balance_attempt.id,
            booking_id=booking.id,
            purpose=PaymentAttempt.Purpose.BALANCE,
        )

    monkeypatch.setattr(
        "trip_payments.provider_adapters.RazorpayCheckoutAdapter.fetch_payment",
        fake_fetch_payment,
    )
    payload = razorpay_checkout_success_payload(
        balance_attempt,
        provider_payment_reference="pay_balance_browser_captured_001",
    )

    first_response = client.post(
        f"/api/public/payment-attempts/{balance_attempt.id}/checkout-success/",
        payload,
        format="json",
    )
    second_response = client.post(
        f"/api/public/payment-attempts/{balance_attempt.id}/checkout-success/",
        payload,
        format="json",
    )

    booking.refresh_from_db()
    balance_attempt.refresh_from_db()
    balance_payment = ProviderPayment.objects.get(payment_attempt=balance_attempt)
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["status"] == PaymentAttempt.Status.CONFIRMED
    assert second_response.json()["status"] == PaymentAttempt.Status.CONFIRMED
    assert balance_attempt.status == PaymentAttempt.Status.CONFIRMED
    assert balance_payment.provider_payment_reference == "pay_balance_browser_captured_001"
    assert balance_payment.amount_inr == 24000
    assert ProviderPayment.objects.filter(payment_attempt=balance_attempt).count() == 1
    assert (
        LedgerEntry.objects.filter(
            booking=booking,
            provider_payment=balance_payment,
            entry_type=LedgerEntry.EntryType.PROVIDER_PAYMENT,
        ).count()
        == 1
    )
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert active_reserved_traveler_count(trip) == reserved_before
    assert available_seats(trip) == available_before
    assert not SeatHold.objects.filter(payment_attempt=balance_attempt).exists()
    assert (
        Notification.objects.filter(
            provider_payment=balance_payment,
            notification_type=Notification.NotificationType.PAYMENT_ACKNOWLEDGEMENT,
        ).count()
        == 1
    )


@override_settings(TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET="")
def test_balance_browser_checkout_success_rejects_invalid_signature(organizer, monkeypatch):
    _, booking, _, _ = create_reserved_booking_with_balance_due(organizer)
    balance_attempt = create_balance_payment_checkout(booking).payment_attempt
    client = APIClient()

    def unexpected_fetch_payment(self, request):
        raise AssertionError("Invalid balance signatures must not fetch provider payment state.")

    monkeypatch.setattr(
        "trip_payments.provider_adapters.RazorpayCheckoutAdapter.fetch_payment",
        unexpected_fetch_payment,
    )
    response = client.post(
        f"/api/public/payment-attempts/{balance_attempt.id}/checkout-success/",
        razorpay_checkout_success_payload(balance_attempt, signature="not-a-valid-signature"),
        format="json",
    )

    booking.refresh_from_db()
    balance_attempt.refresh_from_db()
    assert response.status_code == 400
    assert balance_attempt.status == PaymentAttempt.Status.PENDING
    assert balance_attempt.checkout_succeeded_at is None
    assert ProviderPayment.objects.filter(payment_attempt=balance_attempt).count() == 0
    assert not SeatHold.objects.filter(payment_attempt=balance_attempt).exists()


@override_settings(TRIPOS_RAZORPAY_WEBHOOK_SECRET=RAZORPAY_WEBHOOK_SECRET)
def test_razorpay_webhook_rejects_invalid_signature_before_mutation(organizer):
    trip = create_bookable_trip(organizer, capacity=1)
    booking = create_draft_booking(trip)
    attempt = create_public_payment_attempt(booking)
    body = razorpay_payment_webhook_body(
        attempt,
        event_reference="evt_webhook_invalid_signature_001",
        provider_payment_reference="pay_webhook_invalid_signature_001",
    )
    client = APIClient()

    response = post_razorpay_webhook(client, body, signature="not-a-valid-signature")

    booking.refresh_from_db()
    attempt.refresh_from_db()
    assert response.status_code == 400
    assert ProviderWebhookEvent.objects.count() == 0
    assert ProviderPayment.objects.filter(booking=booking).count() == 0
    assert LedgerEntry.objects.filter(booking=booking).count() == 0
    assert attempt.status == PaymentAttempt.Status.PENDING
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert active_reserved_traveler_count(trip) == 0


@override_settings(TRIPOS_RAZORPAY_WEBHOOK_SECRET=RAZORPAY_WEBHOOK_SECRET)
def test_razorpay_webhook_captured_payment_confirms_and_dedupes(organizer):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)
    attempt = create_public_payment_attempt(booking)
    body = razorpay_payment_webhook_body(
        attempt,
        event_reference="evt_webhook_captured_duplicate_001",
        provider_payment_reference="pay_webhook_captured_duplicate_001",
        provider_fee_amount_inr=480,
    )
    client = APIClient()

    first_response = post_razorpay_webhook(client, body)
    second_response = post_razorpay_webhook(client, body)

    booking.refresh_from_db()
    attempt.refresh_from_db()
    provider_payment = ProviderPayment.objects.get(booking=booking)
    webhook_event = ProviderWebhookEvent.objects.get()
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["provider_payment"] == provider_payment.id
    assert second_response.json()["duplicate"] is True
    assert webhook_event.processing_status == ProviderWebhookEvent.ProcessingStatus.PROCESSED
    assert webhook_event.provider_payment == provider_payment
    assert ProviderWebhookEvent.objects.count() == 1
    assert ProviderPayment.objects.filter(booking=booking).count() == 1
    assert provider_payment.amount_inr == attempt.amount_inr
    assert provider_payment.provider_fee_amount_inr == 480
    assert provider_payment.provider_net_settlement_amount_inr == attempt.amount_inr - 480
    assert collected_provider_payment_amount_inr(booking) == attempt.amount_inr
    assert (
        LedgerEntry.objects.filter(
            booking=booking,
            entry_type=LedgerEntry.EntryType.PROVIDER_PAYMENT,
        ).count()
        == 1
    )
    assert (
        LedgerEntry.objects.filter(
            booking=booking,
            entry_type=LedgerEntry.EntryType.PLATFORM_FEE,
        ).count()
        == 1
    )
    assert attempt.status == PaymentAttempt.Status.CONFIRMED
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert active_reserved_traveler_count(trip) == 2


@override_settings(TRIPOS_RAZORPAY_WEBHOOK_SECRET=RAZORPAY_WEBHOOK_SECRET)
def test_razorpay_webhook_balance_captured_confirms_and_dedupes_without_capacity_change(
    organizer,
):
    trip, booking, _, _ = create_reserved_booking_with_balance_due(organizer, capacity=2)
    balance_attempt = create_balance_payment_checkout(booking).payment_attempt
    reserved_before = active_reserved_traveler_count(trip)
    available_before = available_seats(trip)
    body = razorpay_payment_webhook_body(
        balance_attempt,
        event_reference="evt_balance_webhook_captured_duplicate_001",
        provider_payment_reference="pay_balance_webhook_captured_duplicate_001",
    )
    client = APIClient()

    first_response = post_razorpay_webhook(client, body)
    second_response = post_razorpay_webhook(client, body)

    booking.refresh_from_db()
    balance_attempt.refresh_from_db()
    balance_payment = ProviderPayment.objects.get(payment_attempt=balance_attempt)
    webhook_event = ProviderWebhookEvent.objects.get(
        provider_event_reference="evt_balance_webhook_captured_duplicate_001"
    )
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["provider_payment"] == balance_payment.id
    assert second_response.json()["duplicate"] is True
    assert webhook_event.processing_status == ProviderWebhookEvent.ProcessingStatus.PROCESSED
    assert webhook_event.payment_attempt == balance_attempt
    assert webhook_event.booking == booking
    assert webhook_event.provider_payment == balance_payment
    assert ProviderPayment.objects.filter(payment_attempt=balance_attempt).count() == 1
    assert balance_attempt.status == PaymentAttempt.Status.CONFIRMED
    assert balance_payment.amount_inr == 24000
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert active_reserved_traveler_count(trip) == reserved_before
    assert available_seats(trip) == available_before
    assert not SeatHold.objects.filter(payment_attempt=balance_attempt).exists()


@override_settings(TRIPOS_RAZORPAY_WEBHOOK_SECRET=RAZORPAY_WEBHOOK_SECRET)
def test_razorpay_webhook_authorized_only_does_not_collect_money(organizer):
    trip = create_bookable_trip(organizer, capacity=1)
    booking = create_draft_booking(trip)
    attempt = create_public_payment_attempt(booking)
    body = razorpay_payment_webhook_body(
        attempt,
        event_reference="evt_webhook_authorized_only_001",
        event_type="payment.authorized",
        status="authorized",
        provider_payment_reference="pay_webhook_authorized_only_001",
    )
    client = APIClient()

    response = post_razorpay_webhook(client, body)

    booking.refresh_from_db()
    attempt.refresh_from_db()
    webhook_event = ProviderWebhookEvent.objects.get()
    assert response.status_code == 200
    assert response.json()["processing_status"] == ProviderWebhookEvent.ProcessingStatus.IGNORED
    assert webhook_event.ignored_reason == "payment_not_captured"
    assert attempt.status == PaymentAttempt.Status.CONFIRMING
    assert ProviderPayment.objects.filter(booking=booking).count() == 0
    assert LedgerEntry.objects.filter(booking=booking).count() == 0
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert active_reserved_traveler_count(trip) == 0
    assert available_seats(trip) == 1


@override_settings(TRIPOS_RAZORPAY_WEBHOOK_SECRET=RAZORPAY_WEBHOOK_SECRET)
def test_razorpay_webhook_captured_before_authorized_is_idempotent(organizer):
    trip = create_bookable_trip(organizer, capacity=1)
    booking = create_draft_booking(trip)
    attempt = create_public_payment_attempt(booking)
    provider_payment_reference = "pay_webhook_out_of_order_001"
    captured_body = razorpay_payment_webhook_body(
        attempt,
        event_reference="evt_webhook_out_of_order_captured_001",
        provider_payment_reference=provider_payment_reference,
    )
    authorized_body = razorpay_payment_webhook_body(
        attempt,
        event_reference="evt_webhook_out_of_order_authorized_001",
        event_type="payment.authorized",
        status="authorized",
        provider_payment_reference=provider_payment_reference,
    )
    client = APIClient()

    captured_response = post_razorpay_webhook(client, captured_body)
    authorized_response = post_razorpay_webhook(client, authorized_body)

    attempt.refresh_from_db()
    booking.refresh_from_db()
    assert captured_response.status_code == 200
    assert authorized_response.status_code == 200
    assert captured_response.json()["provider_payment"] is not None
    assert authorized_response.json()["processing_status"] == (
        ProviderWebhookEvent.ProcessingStatus.IGNORED
    )
    assert ProviderWebhookEvent.objects.count() == 2
    assert ProviderPayment.objects.filter(booking=booking).count() == 1
    assert (
        LedgerEntry.objects.filter(
            booking=booking,
            entry_type=LedgerEntry.EntryType.PROVIDER_PAYMENT,
        ).count()
        == 1
    )
    assert attempt.status == PaymentAttempt.Status.CONFIRMED
    assert booking.booking_state == Booking.BookingState.RESERVED


@override_settings(TRIPOS_RAZORPAY_WEBHOOK_SECRET=RAZORPAY_WEBHOOK_SECRET)
def test_razorpay_webhook_captured_mismatch_creates_payment_exception(organizer):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip)
    attempt = create_public_payment_attempt(booking)
    body = razorpay_payment_webhook_body(
        attempt,
        event_reference="evt_webhook_amount_mismatch_001",
        provider_payment_reference="pay_webhook_amount_mismatch_001",
        amount_inr=attempt.amount_inr + 1,
    )
    client = APIClient()

    response = post_razorpay_webhook(client, body)

    booking.refresh_from_db()
    attempt.refresh_from_db()
    payment_exception = PaymentException.objects.get(booking=booking)
    webhook_event = ProviderWebhookEvent.objects.get()
    assert response.status_code == 200
    assert response.json()["payment_exception"] == payment_exception.id
    assert payment_exception.exception_type == (
        PaymentException.ExceptionType.MISMATCHED_PROVIDER_PAYMENT
    )
    assert "amount" in payment_exception.mismatch_reasons
    assert webhook_event.payment_exception == payment_exception
    assert ProviderPayment.objects.filter(booking=booking).count() == 0
    assert LedgerEntry.objects.filter(booking=booking).count() == 0
    assert attempt.status == PaymentAttempt.Status.PENDING
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert active_reserved_traveler_count(trip) == 0


@override_settings(TRIPOS_RAZORPAY_WEBHOOK_SECRET=RAZORPAY_WEBHOOK_SECRET)
def test_razorpay_webhook_balance_confirmation_mismatches_reported_metadata(organizer):
    _, booking, _, _ = create_reserved_booking_with_balance_due(organizer)
    balance_attempt = create_balance_payment_checkout(booking).payment_attempt
    body = razorpay_payment_webhook_body(
        balance_attempt,
        event_reference="evt_balance_webhook_reported_metadata_mismatch_001",
        provider_payment_reference="pay_balance_webhook_reported_metadata_mismatch_001",
        amount_inr=balance_attempt.amount_inr + 1,
        notes={
            "tripos_organizer_id": str(organizer.id),
            "tripos_booking_id": str(booking.id),
            "tripos_payment_attempt_id": str(balance_attempt.id),
            "tripos_payment_purpose": PaymentAttempt.Purpose.RESERVATION,
            "tripos_provider_account": (
                organizer.provider_payment_setup.provider_merchant_reference
            ),
        },
    )
    client = APIClient()

    response = post_razorpay_webhook(client, body)

    booking.refresh_from_db()
    balance_attempt.refresh_from_db()
    payment_exception = PaymentException.objects.get(payment_attempt=balance_attempt)
    assert response.status_code == 200
    assert response.json()["payment_exception"] == payment_exception.id
    assert payment_exception.exception_type == (
        PaymentException.ExceptionType.MISMATCHED_PROVIDER_PAYMENT
    )
    assert set(payment_exception.mismatch_reasons) == {"purpose", "amount"}
    assert ProviderPayment.objects.filter(payment_attempt=balance_attempt).count() == 0
    assert (
        LedgerEntry.objects.filter(
            booking=booking,
            entry_type=LedgerEntry.EntryType.PROVIDER_PAYMENT,
        ).count()
        == 1
    )
    assert balance_attempt.status == PaymentAttempt.Status.PENDING
    assert booking.booking_state == Booking.BookingState.RESERVED


@override_settings(TRIPOS_RAZORPAY_WEBHOOK_SECRET=RAZORPAY_WEBHOOK_SECRET)
def test_razorpay_webhook_balance_confirmation_requires_reported_booking_and_purpose(
    organizer,
):
    _, booking, _, _ = create_reserved_booking_with_balance_due(organizer)
    balance_attempt = create_balance_payment_checkout(booking).payment_attempt
    body = razorpay_payment_webhook_body(
        balance_attempt,
        event_reference="evt_balance_webhook_missing_metadata_mismatch_001",
        provider_payment_reference="pay_balance_webhook_missing_metadata_mismatch_001",
        notes={},
    )
    client = APIClient()

    response = post_razorpay_webhook(client, body)

    payment_exception = PaymentException.objects.get(payment_attempt=balance_attempt)
    assert response.status_code == 200
    assert response.json()["payment_exception"] == payment_exception.id
    assert payment_exception.exception_type == (
        PaymentException.ExceptionType.MISMATCHED_PROVIDER_PAYMENT
    )
    assert set(payment_exception.mismatch_reasons) == {
        "payment_attempt",
        "booking",
        "purpose",
    }
    assert ProviderPayment.objects.filter(payment_attempt=balance_attempt).count() == 0
    assert balance_attempt.status == PaymentAttempt.Status.PENDING


@override_settings(TRIPOS_RAZORPAY_WEBHOOK_SECRET=RAZORPAY_WEBHOOK_SECRET)
def test_razorpay_webhook_late_captured_capacity_exception(organizer):
    trip = create_bookable_trip(organizer, capacity=1)
    late_booking = create_draft_booking(trip)
    late_attempt = create_public_payment_attempt(late_booking)
    SeatHold.objects.filter(payment_attempt=late_attempt).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    competing_booking = create_draft_booking(trip)
    competing_attempt = create_public_payment_attempt(competing_booking)
    confirm_provider_payment(
        competing_attempt,
        provider_payment_reference="pay_webhook_late_competing_001",
        amount_inr=competing_attempt.amount_inr,
    )
    body = razorpay_payment_webhook_body(
        late_attempt,
        event_reference="evt_webhook_late_capacity_001",
        provider_payment_reference="pay_webhook_late_capacity_001",
    )
    client = APIClient()

    response = post_razorpay_webhook(client, body)

    late_booking.refresh_from_db()
    late_attempt.refresh_from_db()
    payment_exception = PaymentException.objects.get(payment_attempt=late_attempt)
    provider_payment = ProviderPayment.objects.get(payment_attempt=late_attempt)
    assert response.status_code == 200
    assert response.json()["payment_exception"] == payment_exception.id
    assert payment_exception.exception_type == (
        PaymentException.ExceptionType.LATE_CONFIRMED_PAYMENT
    )
    assert payment_exception.provider_payment == provider_payment
    assert late_attempt.status == PaymentAttempt.Status.CONFIRMED
    assert late_booking.booking_state == Booking.BookingState.DRAFT
    assert ProviderPayment.objects.filter(booking=late_booking).count() == 1
    assert active_reserved_traveler_count(trip) == 1
    assert available_seats(trip) == 0


@override_settings(TRIPOS_RAZORPAY_WEBHOOK_SECRET=RAZORPAY_WEBHOOK_SECRET)
def test_razorpay_webhook_revocation_event_closes_public_booking(organizer):
    trip = create_bookable_trip(organizer, capacity=2)
    credential = SensitiveProviderCredential.objects.get(
        organizer=organizer,
        status=SensitiveProviderCredential.Status.ACTIVE,
    )
    booking = create_draft_booking(trip, slot_count=2)
    attempt = create_public_payment_attempt(booking)
    hold = SeatHold.objects.get(payment_attempt=attempt)
    body = razorpay_authorization_revoked_webhook_body(
        organizer,
        event_reference="evt_webhook_authorization_revoked_001",
    )
    client = APIClient()

    response = post_razorpay_webhook(client, body)

    organizer.provider_payment_setup.refresh_from_db()
    credential.refresh_from_db()
    trip.refresh_from_db()
    attempt.refresh_from_db()
    hold.refresh_from_db()
    webhook_event = ProviderWebhookEvent.objects.get()
    assert response.status_code == 200
    assert response.json()["lifecycle"]["revoked_credentials"] == 1
    assert response.json()["lifecycle"]["closed_public_booking_trips"] == 1
    assert response.json()["lifecycle"]["deactivated_payment_attempts"] == 1
    assert response.json()["lifecycle"]["released_seat_holds"] == 1
    assert webhook_event.processing_status == ProviderWebhookEvent.ProcessingStatus.PROCESSED
    assert webhook_event.organizer == organizer
    assert credential.status == SensitiveProviderCredential.Status.REVOKED
    assert organizer.provider_payment_setup.authorization_state == (
        ProviderPaymentSetup.AuthorizationState.REVOKED
    )
    assert organizer.provider_payment_setup.provider_connection_state == (
        ProviderPaymentSetup.ProviderConnectionState.UNHEALTHY
    )
    assert trip.booking_availability == Trip.BookingAvailability.CLOSED
    assert attempt.status == PaymentAttempt.Status.SUPERSEDED
    assert hold.released_at is not None


def test_backend_provider_confirmation_matches_attempt_and_reserves_booking(organizer):
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)
    attempt = create_public_payment_attempt(booking)
    client = APIClient()

    response = client.post(
        f"/api/public/payment-attempts/{attempt.id}/provider-confirmation/",
        provider_confirmation_payload(
            attempt,
            provider_payment_reference="pay_provider_confirmation_success_001",
        ),
        format="json",
    )

    booking.refresh_from_db()
    attempt.refresh_from_db()
    provider_payment = ProviderPayment.objects.get(booking=booking)
    seat_hold = SeatHold.objects.get(payment_attempt=attempt)
    assert response.status_code == 201
    assert response.json()["id"] == provider_payment.id
    assert response.json()["booking_state"] == Booking.BookingState.RESERVED
    assert attempt.status == PaymentAttempt.Status.CONFIRMED
    assert provider_payment.amount_inr == attempt.amount_inr
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert collected_provider_payment_amount_inr(booking) == attempt.amount_inr
    assert booking.ledger_entries.count() == 2
    assert seat_hold.released_at is not None
    assert active_reserved_traveler_count(trip) == 2
    assert available_seats(trip) == 0
    assert BookingAccessLink.objects.filter(booking=booking).count() == 1
    assert (
        Notification.objects.filter(
            booking=booking,
            notification_type=Notification.NotificationType.RESERVATION_ACKNOWLEDGEMENT,
        ).count()
        == 1
    )
    assert (
        Notification.objects.filter(
            booking=booking,
            notification_type=Notification.NotificationType.PAYMENT_ACKNOWLEDGEMENT,
        ).count()
        == 0
    )


def test_duplicate_provider_confirmation_is_idempotent(organizer):
    trip = create_bookable_trip(organizer, capacity=1)
    booking = create_draft_booking(trip)
    attempt = create_public_payment_attempt(booking)
    payload = provider_confirmation_payload(
        attempt,
        provider_payment_reference="pay_provider_confirmation_duplicate_001",
    )
    client = APIClient()

    first_response = client.post(
        f"/api/public/payment-attempts/{attempt.id}/provider-confirmation/",
        payload,
        format="json",
    )
    second_response = client.post(
        f"/api/public/payment-attempts/{attempt.id}/provider-confirmation/",
        payload,
        format="json",
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["id"] == second_response.json()["id"]
    assert ProviderPayment.objects.filter(booking=booking).count() == 1
    assert (
        LedgerEntry.objects.filter(
            booking=booking,
            entry_type=LedgerEntry.EntryType.PROVIDER_PAYMENT,
        ).count()
        == 1
    )
    assert (
        LedgerEntry.objects.filter(
            booking=booking,
            entry_type=LedgerEntry.EntryType.PLATFORM_FEE,
        ).count()
        == 1
    )
    assert (
        Notification.objects.filter(
            booking=booking,
            notification_type=Notification.NotificationType.RESERVATION_ACKNOWLEDGEMENT,
        ).count()
        == 1
    )
    assert BookingAccessLink.objects.filter(booking=booking).count() == 1


def test_provider_confirmation_creates_mismatched_payment_exceptions(organizer):
    trip = create_bookable_trip(organizer, capacity=4)
    booking = create_draft_booking(trip)
    other_booking = create_draft_booking(trip)
    attempt = create_public_payment_attempt(booking)
    client = APIClient()
    mismatches = {
        "booking": other_booking.id,
        "provider": "wrong_provider",
        "provider_attempt_reference": "order_wrong_confirmation",
        "amount_inr": attempt.amount_inr + 1,
    }

    for field, value in mismatches.items():
        payload = provider_confirmation_payload(
            attempt,
            provider_payment_reference=f"pay_provider_mismatch_{field}",
        )
        payload[field] = value
        response = client.post(
            f"/api/public/payment-attempts/{attempt.id}/provider-confirmation/",
            payload,
            format="json",
        )
        assert response.status_code == 202
        assert response.json()["exception_type"] == (
            PaymentException.ExceptionType.MISMATCHED_PROVIDER_PAYMENT
        )
        expected_reason = {
            "booking": "booking",
            "provider": "provider",
            "provider_attempt_reference": "provider_order",
            "amount_inr": "amount",
        }[field]
        assert expected_reason in response.json()["mismatch_reasons"]

    booking.refresh_from_db()
    attempt.refresh_from_db()
    assert attempt.status == PaymentAttempt.Status.PENDING
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert ProviderPayment.objects.filter(booking=booking).count() == 0
    assert LedgerEntry.objects.filter(booking=booking).count() == 0
    assert PaymentException.objects.filter(
        booking=booking,
        exception_type=PaymentException.ExceptionType.MISMATCHED_PROVIDER_PAYMENT,
    ).count() == len(mismatches)
    assert active_reserved_traveler_count(trip) == 0


def test_provider_confirmation_creates_mismatched_exception_for_provider_payment_reference(
    organizer,
):
    trip = create_bookable_trip(organizer, capacity=2)
    first_booking = create_draft_booking(trip)
    first_attempt = create_public_payment_attempt(first_booking)
    provider_payment = confirm_provider_payment(
        first_attempt,
        provider_payment_reference="pay_provider_reference_conflict_001",
        amount_inr=first_attempt.amount_inr,
    )
    second_booking = create_draft_booking(trip)
    second_attempt = create_public_payment_attempt(second_booking)
    client = APIClient()

    response = client.post(
        f"/api/public/payment-attempts/{second_attempt.id}/provider-confirmation/",
        provider_confirmation_payload(
            second_attempt,
            provider_payment_reference=provider_payment.provider_payment_reference,
        ),
        format="json",
    )

    second_booking.refresh_from_db()
    second_attempt.refresh_from_db()
    assert response.status_code == 202
    assert response.json()["exception_type"] == (
        PaymentException.ExceptionType.MISMATCHED_PROVIDER_PAYMENT
    )
    assert "provider_payment_reference" in response.json()["mismatch_reasons"]
    assert response.json()["provider_payment"] is None
    assert response.json()["details"]["existing_provider_payment"]["id"] == provider_payment.id
    assert second_attempt.status == PaymentAttempt.Status.PENDING
    assert second_booking.booking_state == Booking.BookingState.DRAFT
    assert ProviderPayment.objects.filter(booking=second_booking).count() == 0


def test_late_provider_confirmation_auto_reserves_when_bookable_seats_remain(organizer):
    trip = create_bookable_trip(organizer, capacity=1)
    booking = create_draft_booking(trip)
    attempt = create_public_payment_attempt(booking)
    expired_at = timezone.now() - timedelta(seconds=1)
    SeatHold.objects.filter(payment_attempt=attempt).update(expires_at=expired_at)

    confirm_provider_payment(
        attempt,
        provider_payment_reference="pay_provider_late_auto_reserve_001",
        amount_inr=8000,
    )

    booking.refresh_from_db()
    seat_hold = SeatHold.objects.get(payment_attempt=attempt)
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert seat_hold.released_at is not None
    assert active_seat_hold_count(trip) == 0
    assert active_reserved_traveler_count(trip) == 1
    assert available_seats(trip) == 0


def test_late_provider_confirmation_with_insufficient_bookable_seats_creates_exception(
    organizer,
):
    trip, booking, attempt, payment_exception = create_late_confirmed_payment_exception(
        organizer,
        provider_payment_reference="pay_provider_late_exception_001",
    )

    booking.refresh_from_db()
    attempt.refresh_from_db()
    provider_payment = ProviderPayment.objects.get(payment_attempt=attempt)
    assert payment_exception.exception_type == (
        PaymentException.ExceptionType.LATE_CONFIRMED_PAYMENT
    )
    assert payment_exception.provider_payment == provider_payment
    assert attempt.status == PaymentAttempt.Status.CONFIRMED
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert ProviderPayment.objects.filter(booking=booking).count() == 1
    assert (
        LedgerEntry.objects.filter(
            booking=booking,
            entry_type=LedgerEntry.EntryType.PROVIDER_PAYMENT,
        ).count()
        == 1
    )
    assert active_reserved_traveler_count(trip) == 1
    assert available_seats(trip) == 0
    assert (
        Notification.objects.filter(
            booking=booking,
            notification_type=Notification.NotificationType.RESERVATION_ACKNOWLEDGEMENT,
        ).count()
        == 0
    )


@pytest.mark.parametrize(
    "provider_event_type",
    [
        PaymentException.ProviderEventType.DISPUTE,
        PaymentException.ProviderEventType.CHARGEBACK,
    ],
)
def test_provider_dispute_exception_does_not_create_refund_or_change_booking_state(
    organizer,
    provider_event_type,
):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    attempt = create_public_payment_attempt(booking)
    provider_payment = confirm_provider_payment(
        attempt,
        provider_payment_reference=f"pay_provider_{provider_event_type}_001",
        amount_inr=attempt.amount_inr,
    )
    booking.refresh_from_db()
    state_before_dispute = booking.booking_state

    payment_exception = record_provider_dispute_exception(
        provider_payment,
        provider_event_type=provider_event_type,
        provider_dispute_reference=f"disp_provider_{provider_event_type}_001",
        amount_inr=provider_payment.amount_inr,
        details={"provider_reason": "provider_event"},
    )

    booking.refresh_from_db()
    assert payment_exception.exception_type == PaymentException.ExceptionType.PROVIDER_DISPUTE
    assert payment_exception.provider_payment == provider_payment
    assert payment_exception.provider_event_type == provider_event_type
    assert booking.booking_state == state_before_dispute
    assert RefundRecord.objects.filter(booking=booking).count() == 0


def test_owner_and_operator_can_resolve_late_confirmed_payment_exception(
    user_factory,
    organizer,
):
    owner = user_factory("late-exception-owner@example.com")
    operator = user_factory("late-exception-operator@example.com")
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
    _, _, _, owner_exception = create_late_confirmed_payment_exception(
        organizer,
        provider_payment_reference="pay_provider_late_owner_resolve_001",
    )
    _, _, _, operator_exception = create_late_confirmed_payment_exception(
        organizer,
        provider_payment_reference="pay_provider_late_operator_resolve_001",
    )
    client = APIClient()

    client.force_authenticate(owner)
    owner_response = client.post(
        (
            f"/api/operations/organizers/{organizer.id}/payment-exceptions/"
            f"{owner_exception.id}/resolve/"
        ),
        {"resolution_note": "Moved contact into alternate operations handling."},
        format="json",
    )
    client.force_authenticate(operator)
    operator_response = client.post(
        (
            f"/api/operations/organizers/{organizer.id}/payment-exceptions/"
            f"{operator_exception.id}/resolve/"
        ),
        {"resolution_note": "Contacted booking contact for options."},
        format="json",
    )

    owner_exception.refresh_from_db()
    operator_exception.refresh_from_db()
    assert owner_response.status_code == 200
    assert operator_response.status_code == 200
    assert owner_exception.status == PaymentException.Status.BOOKING_OPERATIONS_RESOLVED
    assert owner_exception.resolved_by == owner
    assert operator_exception.status == PaymentException.Status.BOOKING_OPERATIONS_RESOLVED
    assert operator_exception.resolved_by == operator


def test_only_late_confirmed_payment_exceptions_support_booking_resolution(
    user_factory,
    organizer,
):
    operator = user_factory("mismatch-resolution-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)
    attempt = create_public_payment_attempt(booking)
    payment_exception = confirm_provider_payment(
        attempt,
        provider_payment_reference="pay_provider_mismatch_resolution_001",
        amount_inr=attempt.amount_inr - 1,
    )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        (
            f"/api/operations/organizers/{organizer.id}/payment-exceptions/"
            f"{payment_exception.id}/resolve/"
        ),
        {"resolution_note": "Tried to resolve wrong exception type."},
        format="json",
    )

    payment_exception.refresh_from_db()
    assert response.status_code == 400
    assert payment_exception.status == PaymentException.Status.OPEN


def test_public_checkout_requires_enough_available_seats_before_payment_attempt(organizer):
    trip = create_bookable_trip(organizer, capacity=2)
    package = trip.packages.first()
    draft_booking = create_draft_booking(trip, slot_count=2, package=package)
    reserved_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Rahul Menon",
        booking_contact_phone="+919123456789",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=reserved_booking, package=package, position=1)
    client = APIClient()

    response = client.post(f"/api/public/bookings/{draft_booking.id}/payment-attempts/")

    draft_booking.refresh_from_db()
    assert response.status_code == 400
    assert "insufficient_capacity" in str(response.json())
    assert PaymentAttempt.objects.filter(booking=draft_booking).count() == 0
    assert draft_booking.booking_state == Booking.BookingState.DRAFT
    assert active_reserved_traveler_count(trip) == 1
    assert available_seats(trip) == 1


def test_public_checkout_uses_gate_decision_when_provider_payment_setup_is_missing(
    organizer,
):
    trip = create_trip(
        organizer,
        title="Checkout Provider Blocked Field Week",
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
    )
    booking = create_draft_booking(trip)
    client = APIClient()

    response = client.post(f"/api/public/bookings/{booking.id}/payment-attempts/")

    assert response.status_code == 400
    assert "payment_method_readiness_missing" in str(response.json())
    assert PaymentAttempt.objects.filter(booking=booking).count() == 0


def test_reservation_confirmation_records_amount_exception_without_booking_outcome(
    organizer,
):
    trip = create_bookable_trip(organizer, capacity=3)
    booking = create_draft_booking(trip, slot_count=2)

    first_attempt = create_public_payment_attempt(booking)
    payment_exception = confirm_provider_payment(
        first_attempt,
        provider_payment_reference="pay_provider_partial_001",
        amount_inr=8000,
    )
    booking.refresh_from_db()

    assert payment_exception.exception_type == (
        PaymentException.ExceptionType.MISMATCHED_PROVIDER_PAYMENT
    )
    assert "amount" in payment_exception.mismatch_reasons
    assert ProviderPayment.objects.filter(booking=booking).count() == 0
    assert LedgerEntry.objects.filter(booking=booking).count() == 0
    assert collected_provider_payment_amount_inr(booking) == 0
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert active_reserved_traveler_count(trip) == 0
    assert available_seats(trip) == 3

    second_attempt = create_public_payment_attempt(booking)
    confirm_provider_payment(
        second_attempt,
        provider_payment_reference="pay_provider_full_reservation_001",
        amount_inr=16000,
    )
    booking.refresh_from_db()

    assert collected_provider_payment_amount_inr(booking) == 16000
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert active_reserved_traveler_count(trip) == 2
    assert available_seats(trip) == 1


def test_late_booking_after_balance_milestone_requires_full_booking_total_to_reserve(
    organizer,
):
    trip = create_bookable_trip(
        organizer,
        start_date=date(2026, 5, 20),
        end_date=date(2026, 5, 25),
    )
    package = trip.packages.first()
    package.price_inr = 32000
    package.reservation_amount_inr = 8000
    package.save()
    trip.payment_schedule.balance_due_days_before_start = 1
    trip.payment_schedule.save()
    booking = create_draft_booking(trip, slot_count=1, package=package)

    assert booking.booking_reservation_amount_inr == 8000
    assert booking.booking_total_inr == 32000
    assert required_amount_to_reserve_inr(booking) == 32000

    attempt = create_public_payment_attempt(booking)
    confirm_provider_payment(
        attempt,
        provider_payment_reference="pay_provider_late_full_001",
        amount_inr=32000,
    )
    booking.refresh_from_db()

    assert collected_provider_payment_amount_inr(booking) == 32000
    assert booking.booking_state == Booking.BookingState.RESERVED


def test_successful_provider_payment_creates_financial_ledger_entries(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    attempt = create_public_payment_attempt(booking)
    seat_hold = SeatHold.objects.get(payment_attempt=attempt)

    provider_payment = confirm_provider_payment(
        attempt,
        provider_payment_reference="pay_provider_ledger_001",
        amount_inr=8000,
    )

    booking.refresh_from_db()
    seat_hold.refresh_from_db()
    ledger_entries = list(booking.ledger_entries.order_by("entry_type"))
    assert len(ledger_entries) == 2
    assert {entry.entry_type for entry in ledger_entries} == {
        LedgerEntry.EntryType.PROVIDER_PAYMENT,
        LedgerEntry.EntryType.PLATFORM_FEE,
    }
    assert collected_provider_payment_amount_inr(booking) == 8000
    assert platform_fee_for_provider_payment_inr(provider_payment) == 160
    assert booking_reconciliation(booking).platform_fee_inr == 160
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert seat_hold.released_at is not None
    assert active_reserved_traveler_count(trip) == 1


def test_platform_fees_are_recorded_for_reservation_and_balance_provider_payments(
    organizer,
):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    reservation_attempt = create_public_payment_attempt(booking)

    reservation_payment = confirm_provider_payment(
        reservation_attempt,
        provider_payment_reference="pay_platform_fee_reservation_001",
        amount_inr=8000,
    )
    balance_attempt = PaymentAttempt.objects.create(
        booking=booking,
        provider=PaymentAttempt.Provider.RAZORPAY,
        purpose=PaymentAttempt.Purpose.BALANCE,
        status=PaymentAttempt.Status.PENDING,
        amount_inr=4000,
        provider_attempt_reference="order_platform_fee_balance_001",
    )
    balance_payment = confirm_provider_payment(
        balance_attempt,
        provider_payment_reference="pay_platform_fee_balance_001",
        amount_inr=4000,
    )

    platform_fee_entries = LedgerEntry.objects.filter(
        booking=booking,
        entry_type=LedgerEntry.EntryType.PLATFORM_FEE,
    ).order_by("provider_payment_id")
    assert list(platform_fee_entries.values_list("amount_inr", flat=True)) == [160, 80]
    assert {entry.provider_payment_id for entry in platform_fee_entries} == {
        reservation_payment.id,
        balance_payment.id,
    }
    assert booking_reconciliation(booking).platform_fee_inr == 240
    assert collected_provider_payment_amount_inr(booking) == 12000


def test_manual_payments_do_not_create_platform_fees(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)

    create_organizer_entered_manual_payment(
        booking=booking,
        amount_inr=4000,
        payment_reference="manual_no_platform_fee_001",
    )
    traveler_submitted = ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=4000,
        payment_reference="manual_no_platform_fee_002",
        payment_proof=SimpleUploadedFile("upi-proof.txt", b"upi"),
        original_filename="upi-proof.txt",
    )
    approve_manual_payment(manual_payment=traveler_submitted)

    assert (
        LedgerEntry.objects.filter(
            booking=booking,
            entry_type=LedgerEntry.EntryType.APPROVED_MANUAL_PAYMENT,
        ).count()
        == 2
    )
    assert not LedgerEntry.objects.filter(
        booking=booking,
        entry_type=LedgerEntry.EntryType.PLATFORM_FEE,
    ).exists()
    assert booking_reconciliation(booking).platform_fee_inr == 0


def test_test_provider_mode_confirmation_does_not_create_booking_finance(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    organizer.provider_payment_setup.provider_mode = ProviderPaymentSetup.ProviderMode.TEST
    organizer.provider_payment_setup.save()
    attempt = PaymentAttempt.objects.create(
        booking=booking,
        provider=PaymentAttempt.Provider.RAZORPAY,
        purpose=PaymentAttempt.Purpose.RESERVATION,
        status=PaymentAttempt.Status.PENDING,
        amount_inr=booking.booking_reservation_amount_inr,
        provider_attempt_reference="order_test_mode_finance_001",
    )

    result = confirm_provider_payment(
        attempt,
        provider_payment_reference="pay_test_mode_finance_001",
        amount_inr=attempt.amount_inr,
    )

    booking.refresh_from_db()
    attempt.refresh_from_db()
    assert isinstance(result, PaymentException)
    assert "provider_mode" in result.mismatch_reasons
    assert ProviderPayment.objects.filter(booking=booking).count() == 0
    assert LedgerEntry.objects.filter(booking=booking).count() == 0
    assert booking_reconciliation(booking).collected_inr == 0
    assert booking_reconciliation(booking).platform_fee_inr == 0
    assert attempt.status == PaymentAttempt.Status.PENDING
    assert booking.booking_state == Booking.BookingState.DRAFT


def test_provider_fee_and_net_settlement_do_not_change_collected_balance(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    attempt = create_public_payment_attempt(booking)

    provider_payment = confirm_provider_payment(
        attempt,
        provider_payment_reference="pay_provider_gross_balance_001",
        amount_inr=8000,
        provider_fee_amount_inr=240,
        provider_net_settlement_amount_inr=7760,
    )

    reconciliation = booking_reconciliation(booking)
    assert provider_payment.amount_inr == 8000
    assert provider_payment.provider_fee_amount_inr == 240
    assert provider_payment.provider_net_settlement_amount_inr == 7760
    assert collected_provider_payment_amount_inr(booking) == 8000
    assert reconciliation.collected_inr == 8000
    assert reconciliation.due_inr == 24000
    assert reconciliation.platform_fee_inr == 160
    assert derived_payment_state(booking) == "reservation_paid"


def test_financial_ledger_interface_records_all_supported_entries(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)

    failed_attempt = PaymentAttempt.objects.create(
        booking=booking,
        amount_inr=32000,
        status=PaymentAttempt.Status.FAILED,
    )
    opening_payment_record = OpeningPaymentRecord.objects.create(
        booking=booking,
        amount_inr=8000,
        payment_reference="opening-row-1",
        note="Collected before TripOS.",
    )
    manual_payment = ManualPayment.objects.create(
        booking=booking,
        amount_inr=4000,
        payment_reference="upi-manual-1",
    )
    provider_attempt = PaymentAttempt.objects.create(
        booking=booking,
        amount_inr=10000,
        status=PaymentAttempt.Status.CONFIRMED,
        provider_attempt_reference="order_financial_ledger_interface_001",
    )
    provider_payment = ProviderPayment.objects.create(
        booking=booking,
        payment_attempt=provider_attempt,
        amount_inr=10000,
        provider_payment_reference="pay_financial_ledger_interface_001",
    )
    booking_adjustment = BookingAdjustment.objects.create(
        booking=booking,
        amount_inr=-2000,
        adjustment_reason="Goodwill correction.",
    )
    refund_record = RefundRecord.objects.create(
        booking=booking,
        amount_inr=1000,
        refund_reason="Partial refund recorded.",
    )

    FinancialLedger.record_event(opening_payment_record)
    FinancialLedger.record_event(manual_payment)
    FinancialLedger.record_event(provider_payment)
    FinancialLedger.record_event(booking_adjustment)
    FinancialLedger.record_event(refund_record)
    package_change_entry = FinancialLedger.record_package_change(
        booking=booking,
        amount_inr=1500,
        description="Package change explanation.",
    )

    ledger = FinancialLedger.for_booking(booking)
    reconciliation = ledger.reconciliation()

    assert not ProviderPayment.objects.filter(payment_attempt=failed_attempt).exists()
    assert package_change_entry is not None
    assert package_change_entry.entry_type == LedgerEntry.EntryType.PACKAGE_CHANGE
    assert reconciliation.collected_inr == 22000
    assert reconciliation.adjusted_inr == -2000
    assert reconciliation.refunded_inr == 1000
    assert reconciliation.due_inr == 9000
    assert reconciliation.platform_fee_inr == 200
    assert ledger.payment_state() == "partially_paid"


def test_financial_ledger_event_writes_are_idempotent_across_services_and_model_saves(
    user_factory,
    organizer,
):
    actor = user_factory("ledger-event-owner@example.com")
    OrganizerMembership.objects.create(
        user=actor,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    provider_attempt = create_public_payment_attempt(booking)

    provider_payment = confirm_provider_payment(
        provider_attempt,
        provider_payment_reference="pay_financial_ledger_idempotent_001",
        amount_inr=booking.booking_reservation_amount_inr,
    )
    manual_payment = create_organizer_entered_manual_payment(
        booking=booking,
        amount_inr=1000,
        payment_reference="manual-ledger-idempotent-001",
    )
    opening_payment_record = OpeningPaymentRecord.objects.create(
        booking=booking,
        amount_inr=2000,
        payment_reference="opening-ledger-idempotent-001",
        note="Imported before event writer test.",
    )
    booking_adjustment = create_booking_adjustment(
        booking=booking,
        amount_inr=-500,
        adjustment_reason="Event writer adjustment.",
        actor=actor,
    )
    refund_record = create_refund_record(
        booking=booking,
        amount_inr=300,
        refund_reason="Event writer refund.",
        refund_reference="refund-ledger-idempotent-001",
        actor=actor,
    )
    baseline_reconciliation = booking_reconciliation(booking)

    for event in (
        provider_payment,
        manual_payment,
        opening_payment_record,
        booking_adjustment,
        refund_record,
    ):
        first_entries = FinancialLedger.record_event(event)
        second_entries = FinancialLedger.record_event(event)
        event.save()
        third_entries = FinancialLedger.record_event(event)

        assert [entry.id for entry in second_entries] == [entry.id for entry in first_entries]
        assert [entry.id for entry in third_entries] == [entry.id for entry in first_entries]

    assert (
        LedgerEntry.objects.filter(
            provider_payment=provider_payment,
            entry_type=LedgerEntry.EntryType.PROVIDER_PAYMENT,
        ).count()
        == 1
    )
    assert (
        LedgerEntry.objects.filter(
            provider_payment=provider_payment,
            entry_type=LedgerEntry.EntryType.PLATFORM_FEE,
        ).count()
        == 1
    )
    assert LedgerEntry.objects.filter(manual_payment=manual_payment).count() == 1
    assert LedgerEntry.objects.filter(opening_payment_record=opening_payment_record).count() == 1
    assert LedgerEntry.objects.filter(booking_adjustment=booking_adjustment).count() == 1
    assert LedgerEntry.objects.filter(refund_record=refund_record).count() == 1

    reconciliation = booking_reconciliation(booking)
    assert reconciliation.collected_inr == baseline_reconciliation.collected_inr == 11000
    assert reconciliation.adjusted_inr == baseline_reconciliation.adjusted_inr == -500
    assert reconciliation.refunded_inr == baseline_reconciliation.refunded_inr == 300
    assert reconciliation.due_inr == baseline_reconciliation.due_inr == 20800
    assert reconciliation.platform_fee_inr == baseline_reconciliation.platform_fee_inr == 160


def test_pending_and_failed_attempts_never_enter_financial_ledger(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)

    pending_attempt = create_public_payment_attempt(booking)
    failed_attempt = create_public_payment_attempt(booking)
    fail_payment_attempt(failed_attempt, failure_reason="Provider declined the payment.")

    assert PaymentAttempt.objects.get(pk=pending_attempt.pk).status == (
        PaymentAttempt.Status.SUPERSEDED
    )
    assert PaymentAttempt.objects.get(pk=failed_attempt.pk).status == PaymentAttempt.Status.FAILED
    assert booking.ledger_entries.count() == 0
    assert collected_provider_payment_amount_inr(booking) == 0
    assert derived_payment_state(booking) == "unpaid"


def test_payment_state_is_derived_from_financial_ledger(organizer):
    trip = create_bookable_trip(organizer, capacity=4)
    booking = create_draft_booking(trip, slot_count=2)

    assert derived_payment_state(booking) == "unpaid"
    assert FinancialLedger.for_booking(booking).payment_state() == "unpaid"

    first_attempt = create_public_payment_attempt(booking)
    confirm_provider_payment(
        first_attempt,
        provider_payment_reference="pay_provider_state_001",
        amount_inr=16000,
    )
    booking.refresh_from_db()

    assert derived_payment_state(booking) == "reservation_paid"
    assert FinancialLedger.for_booking(booking).payment_state() == "reservation_paid"

    second_attempt = PaymentAttempt.objects.create(
        booking=booking,
        purpose=PaymentAttempt.Purpose.BALANCE,
        amount_inr=10000,
        provider_attempt_reference="order_provider_state_002",
    )
    confirm_provider_payment(
        second_attempt,
        provider_payment_reference="pay_provider_state_002",
        amount_inr=10000,
    )

    assert derived_payment_state(booking) == "partially_paid"
    assert FinancialLedger.for_booking(booking).payment_state() == "partially_paid"

    third_attempt = PaymentAttempt.objects.create(
        booking=booking,
        purpose=PaymentAttempt.Purpose.BALANCE,
        amount_inr=38000,
        provider_attempt_reference="order_provider_state_003",
    )
    confirm_provider_payment(
        third_attempt,
        provider_payment_reference="pay_provider_state_003",
        amount_inr=38000,
    )

    assert derived_payment_state(booking) == "fully_paid"
    assert FinancialLedger.for_booking(booking).payment_state() == "fully_paid"


def test_booking_reconciliation_reports_due_overdue_and_refund_due_amounts(organizer):
    trip = create_bookable_trip(
        organizer,
        start_date=date(2026, 5, 20),
        end_date=date(2026, 5, 25),
    )
    trip.payment_schedule.balance_due_days_before_start = 3
    trip.payment_schedule.save()
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=booking, package=trip.packages.first(), position=1)
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=8000,
        description="Historical collected amount placeholder.",
    )

    reconciliation = booking_reconciliation(booking)

    assert reconciliation.collected_inr == 8000
    assert reconciliation.due_inr == 24000
    assert reconciliation.adjusted_inr == 0
    assert reconciliation.refunded_inr == 0
    assert reconciliation.refund_due_inr == 0
    assert reconciliation.overdue_inr == 24000
    assert derived_payment_state(booking) == "overdue"
    assert FinancialLedger.for_booking(booking).payment_state() == "overdue"

    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.BOOKING_ADJUSTMENT,
        amount_inr=-26000,
        description="Goodwill discount placeholder.",
    )
    adjusted_reconciliation = booking_reconciliation(booking)

    assert effective_booking_total_inr(booking) == 6000
    assert adjusted_reconciliation.adjusted_inr == -26000
    assert adjusted_reconciliation.due_inr == 0
    assert adjusted_reconciliation.refund_due_inr == 2000
    assert derived_payment_state(booking) == "refund_due"
    assert FinancialLedger.for_booking(booking).payment_state() == "refund_due"


def test_booking_reconciliation_reports_refunded_amounts(organizer):
    trip = create_bookable_trip(organizer)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=booking, package=trip.packages.first(), position=1)
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=8000,
        description="Historical collected amount placeholder.",
    )
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.REFUND_RECORD,
        amount_inr=3000,
        description="Manual refund record placeholder.",
    )

    reconciliation = booking_reconciliation(booking)

    assert reconciliation.collected_inr == 8000
    assert reconciliation.refunded_inr == 3000
    assert reconciliation.due_inr == 27000
    assert reconciliation.refund_due_inr == 0
    assert FinancialLedger.for_booking(booking).payment_state() == "reservation_paid"

    refunded_booking = create_draft_booking(trip)
    refunded_booking.booking_state = Booking.BookingState.RESERVED
    refunded_booking.save()
    opening_payment_record = OpeningPaymentRecord.objects.create(
        booking=refunded_booking,
        amount_inr=8000,
        note="Collected before refund.",
    )
    refund_record = RefundRecord.objects.create(
        booking=refunded_booking,
        amount_inr=8000,
        refund_reason="Reservation amount refunded.",
    )
    FinancialLedger.record_opening_payment_record(opening_payment_record)
    FinancialLedger.record_refund_record(refund_record)

    refunded_ledger = FinancialLedger.for_booking(refunded_booking)

    assert refunded_ledger.reconciliation().refunded_inr == 8000
    assert refunded_ledger.payment_state() == "refunded"


def test_booking_adjustment_requires_adjustment_reason_and_records_ledger_activity(
    user_factory,
    organizer,
):
    actor = user_factory("adjustment-operator@example.com")
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()

    with pytest.raises(ValidationError, match="Adjustment Reason"):
        create_booking_adjustment(
            booking=booking,
            amount_inr=-2000,
            adjustment_reason=" ",
            actor=actor,
        )

    adjustment = create_booking_adjustment(
        booking=booking,
        amount_inr=-2000,
        adjustment_reason="Goodwill discount after room downgrade.",
        actor=actor,
    )

    ledger_entry = LedgerEntry.objects.get(booking_adjustment=adjustment)
    assert adjustment.recorded_by == actor
    assert adjustment.amount_inr == -2000
    assert ledger_entry.entry_type == LedgerEntry.EntryType.BOOKING_ADJUSTMENT
    assert ledger_entry.amount_inr == -2000
    assert ledger_entry.description == "Goodwill discount after room downgrade."
    assert ActivityLog.objects.filter(
        booking=booking,
        action=ActivityLog.Action.BOOKING_ADJUSTMENT_RECORDED,
        actor=actor,
        metadata__booking_adjustment_id=adjustment.id,
    ).exists()


def test_traveler_cancellation_releases_capacity_without_ledger_entries(user_factory, organizer):
    actor = user_factory("traveler-cancel-operator@example.com")
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    traveler_slot = booking.traveler_slots.first()

    with pytest.raises(ValidationError, match="Cancellation Reason"):
        cancel_traveler(traveler_slot, cancellation_reason=" ", actor=actor)

    cancelled_slot = cancel_traveler(
        traveler_slot,
        cancellation_reason="Medical emergency before departure.",
        actor=actor,
    )

    assert cancelled_slot.traveler_state == TravelerSlot.TravelerState.CANCELLED
    assert active_reserved_traveler_count(trip) == 1
    assert available_seats(trip) == 1
    assert LedgerEntry.objects.filter(booking=booking).count() == 0
    assert ActivityLog.objects.filter(
        booking=booking,
        traveler_slot=traveler_slot,
        action=ActivityLog.Action.TRAVELER_CANCELLED,
        metadata__cancellation_reason="Medical emergency before departure.",
    ).exists()


def test_booking_cancellation_releases_all_capacity_without_ledger_entries(user_factory, organizer):
    actor = user_factory("booking-cancel-operator@example.com")
    trip = create_bookable_trip(organizer, capacity=2)
    booking = create_draft_booking(trip, slot_count=2)
    booking.booking_state = Booking.BookingState.CONFIRMED
    booking.save()

    with pytest.raises(ValidationError, match="Cancellation Reason"):
        cancel_booking(booking, cancellation_reason="", actor=actor)

    cancelled_booking = cancel_booking(
        booking,
        cancellation_reason="Organizer approved whole-booking cancellation.",
        actor=actor,
    )

    assert cancelled_booking.booking_state == Booking.BookingState.CANCELLED
    assert active_reserved_traveler_count(trip) == 0
    assert available_seats(trip) == 2
    assert LedgerEntry.objects.filter(booking=booking).count() == 0
    assert ActivityLog.objects.filter(
        booking=booking,
        action=ActivityLog.Action.BOOKING_CANCELLED,
        metadata__cancellation_reason="Organizer approved whole-booking cancellation.",
    ).exists()


def test_trip_duplicate_copies_setup_without_operational_records(user_factory, organizer):
    actor = user_factory("duplicate-owner@example.com")
    trip = create_bookable_trip(
        organizer,
        title="Spiti Founder Run",
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
        requires_traveler_documents=True,
    )
    premium_package = TripPackage.objects.create(
        trip=trip,
        name="Premium room",
        price_inr=42000,
        reservation_amount_inr=12000,
        position=2,
    )
    booking = create_draft_booking(trip, package=premium_package)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=premium_package.reservation_amount_inr,
        description="Opening reservation amount.",
    )

    duplicate = duplicate_trip(
        trip,
        title="Spiti Second Run",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 15),
        actor=actor,
    )

    assert duplicate.id != trip.id
    assert duplicate.title == "Spiti Second Run"
    assert duplicate.start_date == date(2026, 11, 10)
    assert duplicate.publication_state == Trip.PublicationState.DRAFT
    assert duplicate.booking_availability == Trip.BookingAvailability.CLOSED
    assert duplicate.requires_traveler_documents is True
    assert duplicate.payment_schedule.balance_due_days_before_start == 14
    assert list(duplicate.packages.values_list("name", "price_inr")) == [
        ("Standard shared room", 32000),
        ("Premium room", 42000),
    ]
    assert duplicate.bookings.count() == 0
    assert LedgerEntry.objects.filter(booking__trip=duplicate).count() == 0
    assert ActivityLog.objects.filter(
        trip=trip,
        action=ActivityLog.Action.TRIP_DUPLICATED,
        metadata__duplicate_trip_id=duplicate.id,
    ).exists()


def test_trip_date_change_sends_notice_without_financial_effect(user_factory, organizer):
    actor = user_factory("date-change-owner@example.com")
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.booking_contact_email = "contact@example.com"
    booking.save()
    traveler_slot = booking.traveler_slots.first()
    traveler_slot.traveler_full_name = "Asha Rao"
    traveler_slot.traveler_phone = "+919111111111"
    traveler_slot.save()

    changed = change_trip_dates(
        trip,
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 25),
        actor=actor,
    )

    assert changed.start_date == date(2026, 10, 20)
    assert LedgerEntry.objects.filter(booking=booking).count() == 0
    assert (
        Notification.objects.filter(
            booking=booking,
            notification_type=Notification.NotificationType.DATE_CHANGE_NOTICE,
        ).count()
        == 3
    )
    assert ActivityLog.objects.filter(
        trip=trip,
        action=ActivityLog.Action.TRIP_DATE_CHANGED,
        metadata__date_change_notice_sent=True,
    ).exists()


def test_trip_cancellation_closes_booking_and_cancels_active_without_ledger_entries(
    user_factory,
    organizer,
):
    actor = user_factory("trip-cancel-owner@example.com")
    trip = create_bookable_trip(organizer, capacity=4)
    reserved_booking = create_draft_booking(trip)
    reserved_booking.booking_state = Booking.BookingState.RESERVED
    reserved_booking.save()
    confirmed_booking = create_draft_booking(trip)
    confirmed_booking.booking_state = Booking.BookingState.CONFIRMED
    confirmed_booking.save()
    draft_booking = create_draft_booking(trip)

    with pytest.raises(ValidationError, match="Cancellation Reason"):
        cancel_trip(trip, cancellation_reason="", actor=actor)

    cancelled_trip = cancel_trip(
        trip,
        cancellation_reason="Vendor permit was withdrawn.",
        actor=actor,
    )

    reserved_booking.refresh_from_db()
    confirmed_booking.refresh_from_db()
    draft_booking.refresh_from_db()
    assert cancelled_trip.booking_availability == Trip.BookingAvailability.CLOSED
    assert reserved_booking.booking_state == Booking.BookingState.CANCELLED
    assert confirmed_booking.booking_state == Booking.BookingState.CANCELLED
    assert draft_booking.booking_state == Booking.BookingState.DRAFT
    assert available_seats(trip) == 4
    assert LedgerEntry.objects.filter(booking__trip=trip).count() == 0
    assert (
        Notification.objects.filter(
            trip=trip,
            notification_type=Notification.NotificationType.CANCELLATION_NOTICE,
        ).count()
        == 2
    )
    assert ActivityLog.objects.filter(
        trip=trip,
        action=ActivityLog.Action.TRIP_CANCELLED,
        metadata__cancelled_booking_count=2,
    ).exists()


def test_completed_trip_completes_active_bookings_and_surfaces_reconciliation_flags(
    user_factory,
    organizer,
):
    actor = user_factory("trip-complete-operator@example.com")
    trip = create_bookable_trip(organizer)
    due_booking = create_draft_booking(trip)
    due_booking.booking_state = Booking.BookingState.RESERVED
    due_booking.save()
    refund_due_booking = create_draft_booking(trip)
    refund_due_booking.booking_state = Booking.BookingState.CONFIRMED
    refund_due_booking.save()
    LedgerEntry.objects.create(
        booking=refund_due_booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=40000,
        description="Over-collected balance.",
    )
    draft_booking = create_draft_booking(trip)
    cancelled_booking = create_draft_booking(trip)
    cancelled_booking.booking_state = Booking.BookingState.CANCELLED
    cancelled_booking.save()

    result = complete_trip(trip, actor=actor)

    due_booking.refresh_from_db()
    refund_due_booking.refresh_from_db()
    draft_booking.refresh_from_db()
    cancelled_booking.refresh_from_db()
    assert result.completed_booking_count == 2
    assert due_booking.booking_state == Booking.BookingState.COMPLETED
    assert refund_due_booking.booking_state == Booking.BookingState.COMPLETED
    assert draft_booking.booking_state == Booking.BookingState.DRAFT
    assert cancelled_booking.booking_state == Booking.BookingState.CANCELLED
    assert {flag for entry in result.reconciliation_flags for flag in entry["flags"]} == {
        "balance_due",
        "refund_due",
    }
    assert ActivityLog.objects.filter(
        trip=trip,
        action=ActivityLog.Action.TRIP_COMPLETED,
        metadata__completed_booking_count=2,
    ).exists()


def test_traveler_replacement_preserves_capacity_and_commercial_position(
    user_factory,
    organizer,
):
    actor = user_factory("replacement-operator@example.com")
    trip = create_bookable_trip(organizer, capacity=1)
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    original_slot = booking.traveler_slots.first()

    replacement = replace_traveler(
        original_slot,
        traveler_full_name="Meera Iyer",
        traveler_phone="+919999999999",
        traveler_email="meera@example.com",
        actor=actor,
    )
    original_slot.refresh_from_db()

    assert original_slot.traveler_state == TravelerSlot.TravelerState.REPLACED
    assert original_slot.replaced_by_slot == replacement
    assert replacement.package == original_slot.package
    assert replacement.booked_package_price_inr == original_slot.booked_package_price_inr
    assert replacement.booked_reservation_amount_inr == original_slot.booked_reservation_amount_inr
    assert active_reserved_traveler_count(trip) == 1
    assert available_seats(trip) == 0
    assert booking.booking_total_inr == original_slot.booked_package_price_inr
    assert ActivityLog.objects.filter(
        booking=booking,
        traveler_slot=original_slot,
        action=ActivityLog.Action.TRAVELER_REPLACED,
        metadata__replacement_traveler_slot_id=replacement.id,
    ).exists()


def test_traveler_addition_changes_total_but_does_not_hold_seat_until_paid(
    user_factory,
    organizer,
):
    actor = user_factory("addition-operator@example.com")
    trip = create_bookable_trip(organizer, capacity=2)
    standard_package = trip.packages.first()
    premium_package = TripPackage.objects.create(
        trip=trip,
        name="Premium room",
        price_inr=42000,
        reservation_amount_inr=12000,
        position=2,
    )
    booking = create_draft_booking(trip, package=standard_package)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=standard_package.reservation_amount_inr,
        description="Opening reservation amount.",
    )

    added_slot = add_traveler_to_booking(
        booking,
        package=premium_package,
        traveler_full_name="Nikhil Rao",
        traveler_phone="+918888888888",
        actor=actor,
    )
    booking.refresh_from_db()

    assert added_slot.traveler_state == TravelerSlot.TravelerState.PENDING_ADDITION
    assert booking.booking_total_inr == standard_package.price_inr + premium_package.price_inr
    assert booking.booking_reservation_amount_inr == (
        standard_package.reservation_amount_inr + premium_package.reservation_amount_inr
    )
    assert active_reserved_traveler_count(trip) == 1
    assert available_seats(trip) == 1

    create_organizer_entered_manual_payment(
        booking=booking,
        amount_inr=premium_package.reservation_amount_inr,
        actor=actor,
    )
    added_slot.refresh_from_db()

    assert added_slot.traveler_state == TravelerSlot.TravelerState.ACTIVE
    assert added_slot.addition_reserved_at is not None
    assert active_reserved_traveler_count(trip) == 2
    assert available_seats(trip) == 0
    assert ActivityLog.objects.filter(
        booking=booking,
        traveler_slot=added_slot,
        action=ActivityLog.Action.TRAVELER_ADDITION_RESERVED,
    ).exists()


def test_approved_traveler_submitted_payment_can_reserve_pending_addition(
    user_factory,
    organizer,
    monkeypatch,
):
    monkeypatch.setattr(
        "organizers.services.send_manual_payment_acknowledgement",
        lambda manual_payment, *, send=True: [],
    )
    operator = user_factory("addition-proof-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer, capacity=2)
    standard_package = trip.packages.first()
    premium_package = TripPackage.objects.create(
        trip=trip,
        name="Premium room",
        price_inr=42000,
        reservation_amount_inr=12000,
        position=2,
    )
    booking = create_draft_booking(trip, package=standard_package)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=standard_package.reservation_amount_inr,
        description="Opening reservation amount.",
    )
    added_slot = add_traveler_to_booking(
        booking,
        package=premium_package,
        traveler_full_name="Nikhil Rao",
        traveler_phone="+918888888888",
        actor=operator,
    )
    manual_payment = ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=premium_package.reservation_amount_inr,
        payment_proof=SimpleUploadedFile(
            "addition-payment-proof.txt",
            b"payment proof",
            content_type="text/plain",
        ),
    )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/operations/organizers/{organizer.id}/manual-payments/{manual_payment.id}/approve/",
        {},
        format="json",
    )

    added_slot.refresh_from_db()
    assert response.status_code == 200
    assert added_slot.traveler_state == TravelerSlot.TravelerState.ACTIVE
    assert added_slot.addition_reserved_at is not None
    assert active_reserved_traveler_count(trip) == 2
    assert ActivityLog.objects.filter(
        booking=booking,
        traveler_slot=added_slot,
        action=ActivityLog.Action.TRAVELER_ADDITION_RESERVED,
    ).exists()


def test_traveler_addition_requires_available_seats_at_creation_and_payment(
    user_factory,
    organizer,
):
    actor = user_factory("addition-capacity-operator@example.com")
    trip = create_bookable_trip(organizer, capacity=2)
    package = trip.packages.first()
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=package.reservation_amount_inr,
        description="Opening reservation amount.",
    )
    added_slot = add_traveler_to_booking(booking, package=package, actor=actor)
    other_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Competing Contact",
        booking_contact_phone="+917777777777",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=other_booking, package=package, position=1)

    with pytest.raises(ValidationError, match="Available Seats"):
        create_organizer_entered_manual_payment(
            booking=booking,
            amount_inr=package.reservation_amount_inr,
            actor=actor,
        )

    added_slot.refresh_from_db()
    assert added_slot.traveler_state == TravelerSlot.TravelerState.PENDING_ADDITION
    assert active_reserved_traveler_count(trip) == 2
    assert available_seats(trip) == 0


def test_post_reservation_package_change_snapshots_new_total_and_ledgers_only_delta(
    user_factory,
    organizer,
):
    actor = user_factory("package-change-operator@example.com")
    trip = create_bookable_trip(organizer)
    standard_package = trip.packages.first()
    premium_package = TripPackage.objects.create(
        trip=trip,
        name="Premium room",
        price_inr=42000,
        reservation_amount_inr=12000,
        position=2,
    )
    same_price_package = TripPackage.objects.create(
        trip=trip,
        name="Same price room",
        price_inr=premium_package.price_inr,
        reservation_amount_inr=premium_package.reservation_amount_inr,
        position=3,
    )
    booking = create_draft_booking(trip, package=standard_package)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    traveler_slot = booking.traveler_slots.first()

    changed_slot = change_traveler_package(
        traveler_slot,
        package=premium_package,
        actor=actor,
    )
    booking.refresh_from_db()

    assert changed_slot.booked_package_price_inr == premium_package.price_inr
    assert booking.booking_total_inr == premium_package.price_inr
    package_change_entry = LedgerEntry.objects.get(
        booking=booking,
        entry_type=LedgerEntry.EntryType.PACKAGE_CHANGE,
    )
    assert package_change_entry.amount_inr == premium_package.price_inr - standard_package.price_inr

    change_traveler_package(changed_slot, package=same_price_package, actor=actor)

    assert (
        LedgerEntry.objects.filter(
            booking=booking,
            entry_type=LedgerEntry.EntryType.PACKAGE_CHANGE,
        ).count()
        == 1
    )
    assert (
        ActivityLog.objects.filter(
            booking=booking,
            traveler_slot=traveler_slot,
            action=ActivityLog.Action.TRAVELER_PACKAGE_CHANGED,
        ).count()
        == 2
    )


def test_operations_api_exposes_cancellation_replacement_addition_and_package_change(
    user_factory,
    organizer,
):
    operator = user_factory("booking-change-api-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer, capacity=3)
    premium_package = TripPackage.objects.create(
        trip=trip,
        name="Premium room",
        price_inr=42000,
        reservation_amount_inr=12000,
        position=2,
    )
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    traveler_slot = booking.traveler_slots.first()
    client = APIClient()
    client.force_authenticate(operator)

    replacement_response = client.post(
        f"/api/operations/organizers/{organizer.id}/traveler-slots/{traveler_slot.id}/replace/",
        {
            "traveler_full_name": "Meera Iyer",
            "traveler_phone": "+919999999999",
            "traveler_email": "meera@example.com",
        },
        format="json",
    )
    assert replacement_response.status_code == 201
    replacement_slot = TravelerSlot.objects.get(replaces_slot=traveler_slot)

    addition_response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/traveler-additions/",
        {"package": premium_package.id, "traveler_full_name": "Nikhil Rao"},
        format="json",
    )
    assert addition_response.status_code == 201
    added_slot = TravelerSlot.objects.exclude(
        id__in=[traveler_slot.id, replacement_slot.id],
    ).get(booking=booking)
    assert added_slot.traveler_state == TravelerSlot.TravelerState.PENDING_ADDITION

    package_response = client.post(
        f"/api/operations/organizers/{organizer.id}/traveler-slots/{replacement_slot.id}/package/",
        {"package": premium_package.id},
        format="json",
    )
    assert package_response.status_code == 200
    assert package_response.json()["traveler_slots"][1]["booked_package_price_inr"] == 42000

    cancellation_error = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/cancel/",
        {"cancellation_reason": ""},
        format="json",
    )
    assert cancellation_error.status_code == 400

    cancellation_response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/cancel/",
        {"cancellation_reason": "Group moved to a different departure."},
        format="json",
    )
    assert cancellation_response.status_code == 200
    assert cancellation_response.json()["booking_state"] == Booking.BookingState.CANCELLED


def test_trip_lifecycle_api_enforces_owner_boundaries_and_booking_state_effects(
    user_factory,
    organizer,
):
    owner = user_factory("trip-lifecycle-owner@example.com")
    operator = user_factory("trip-lifecycle-operator@example.com")
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
    trip = create_trip(organizer)
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    client = APIClient()
    client.force_authenticate(operator)

    operator_date_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/date-change/",
        {"start_date": "2026-10-20", "end_date": "2026-10-25"},
        format="json",
    )
    operator_cancel_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/cancel/",
        {"cancellation_reason": "Unsafe weather window."},
        format="json",
    )

    assert operator_date_response.status_code == 403
    assert operator_cancel_response.status_code == 403

    duplicate_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/duplicate/",
        {
            "title": "Spiti Operator Copy",
            "start_date": "2026-11-10",
            "end_date": "2026-11-15",
        },
        format="json",
    )
    assert duplicate_response.status_code == 201
    duplicate = Trip.objects.get(pk=duplicate_response.json()["id"])
    assert duplicate.bookings.count() == 0
    assert duplicate.publication_state == Trip.PublicationState.DRAFT
    assert duplicate.booking_availability == Trip.BookingAvailability.CLOSED

    client.force_authenticate(owner)
    date_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/date-change/",
        {"start_date": "2026-10-20", "end_date": "2026-10-25"},
        format="json",
    )
    assert date_response.status_code == 200
    assert date_response.json()["start_date"] == "2026-10-20"
    assert Notification.objects.filter(
        booking=booking,
        notification_type=Notification.NotificationType.DATE_CHANGE_NOTICE,
    ).exists()

    client.force_authenticate(operator)
    patch_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"start_date": "2026-10-22"},
        format="json",
    )
    assert patch_response.status_code == 400

    client.force_authenticate(owner)
    cancel_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/cancel/",
        {"cancellation_reason": "Unsafe weather window."},
        format="json",
    )
    booking.refresh_from_db()
    assert cancel_response.status_code == 200
    assert cancel_response.json()["booking_availability"] == Trip.BookingAvailability.CLOSED
    assert booking.booking_state == Booking.BookingState.CANCELLED


def test_trip_completion_api_completes_active_bookings_with_reconciliation_flags(
    user_factory,
    organizer,
):
    operator = user_factory("trip-complete-api-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    client = APIClient()
    client.force_authenticate(operator)

    response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/complete/",
        {},
        format="json",
    )

    booking.refresh_from_db()
    assert response.status_code == 200
    assert booking.booking_state == Booking.BookingState.COMPLETED
    assert response.json()["completed_booking_count"] == 1
    assert response.json()["reconciliation_flags"][0]["flags"] == ["balance_due"]


def test_booking_adjustments_increase_due_and_reduce_total_to_refund_due(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=8000,
        description="Historical collected amount placeholder.",
    )

    surcharge = create_booking_adjustment(
        booking=booking,
        amount_inr=3000,
        adjustment_reason="Late equipment surcharge.",
    )
    surcharge_reconciliation = booking_reconciliation(booking)

    assert surcharge.amount_inr == 3000
    assert surcharge_reconciliation.effective_booking_total_inr == 35000
    assert surcharge_reconciliation.due_inr == 27000

    create_booking_adjustment(
        booking=booking,
        amount_inr=-30000,
        adjustment_reason="Partial cancellation commercial correction.",
    )
    refund_due_reconciliation = booking_reconciliation(booking)

    assert refund_due_reconciliation.effective_booking_total_inr == 5000
    assert refund_due_reconciliation.adjusted_inr == -27000
    assert refund_due_reconciliation.refund_due_inr == 3000
    assert derived_payment_state(booking) == "refund_due"


def test_refund_record_requires_refund_reason_and_resolves_refund_due(
    user_factory,
    organizer,
):
    actor = user_factory("refund-owner@example.com")
    OrganizerMembership.objects.create(
        user=actor,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=10000,
        description="Historical collected amount placeholder.",
    )
    create_booking_adjustment(
        booking=booking,
        amount_inr=-25000,
        adjustment_reason="Cancelled add-on removed from booking total.",
    )
    assert booking_reconciliation(booking).refund_due_inr == 3000
    assert derived_payment_state(booking) == "refund_due"

    with pytest.raises(ValidationError, match="Refund Reason"):
        create_refund_record(
            booking=booking,
            amount_inr=3000,
            refund_reason=" ",
            refund_reference="upi-refund-001",
            actor=actor,
        )

    refund_record = create_refund_record(
        booking=booking,
        amount_inr=3000,
        refund_reason="Returned over-collected amount after add-on removal.",
        refund_reference="upi-refund-001",
        actor=actor,
    )
    reconciliation = booking_reconciliation(booking)
    ledger_entry = LedgerEntry.objects.get(refund_record=refund_record)

    assert RefundRecord.objects.get(pk=refund_record.pk).recorded_by == actor
    assert ledger_entry.entry_type == LedgerEntry.EntryType.REFUND_RECORD
    assert ledger_entry.amount_inr == 3000
    assert reconciliation.refunded_inr == 3000
    assert reconciliation.refund_due_inr == 0
    assert reconciliation.due_inr == 0
    assert derived_payment_state(booking) == "fully_paid"
    assert ActivityLog.objects.filter(
        booking=booking,
        action=ActivityLog.Action.REFUND_RECORD_RECORDED,
        actor=actor,
        metadata__refund_record_id=refund_record.id,
    ).exists()


def test_operations_api_records_adjustments_and_refunds(user_factory, organizer):
    operator = user_factory("financial-records-operator@example.com")
    owner = user_factory("financial-records-owner@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    booking.booking_state = Booking.BookingState.RESERVED
    booking.save()
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=10000,
        description="Historical collected amount placeholder.",
    )
    client = APIClient()
    client.force_authenticate(operator)

    adjustment_error = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/adjustments/",
        {"amount_inr": -25000, "adjustment_reason": ""},
        format="json",
    )
    assert adjustment_error.status_code == 400

    adjustment_response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/adjustments/",
        {
            "amount_inr": -25000,
            "adjustment_reason": "Cancelled add-on removed from booking total.",
        },
        format="json",
    )
    assert adjustment_response.status_code == 201
    assert adjustment_response.json()["payment_state"] == "refund_due"
    assert adjustment_response.json()["reconciliation"]["refund_due_inr"] == 3000
    assert BookingAdjustment.objects.filter(booking=booking).count() == 1

    operator_refund_response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/refund-records/",
        {
            "amount_inr": 3000,
            "refund_reason": "Returned over-collected amount after add-on removal.",
        },
        format="json",
    )
    assert operator_refund_response.status_code == 403

    client.force_authenticate(owner)
    refund_error = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/refund-records/",
        {"amount_inr": 3000, "refund_reason": ""},
        format="json",
    )
    assert refund_error.status_code == 400

    refund_response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/refund-records/",
        {
            "amount_inr": 3000,
            "refund_reason": "Returned over-collected amount after add-on removal.",
            "refund_reference": "upi-refund-api-001",
        },
        format="json",
    )
    assert refund_response.status_code == 201
    assert refund_response.json()["payment_state"] == "fully_paid"
    assert refund_response.json()["reconciliation"]["refund_due_inr"] == 0
    assert RefundRecord.objects.filter(booking=booking).count() == 1


def test_operations_booking_detail_exposes_financial_ledger_and_reconciliation(
    user_factory,
    organizer,
):
    operator = user_factory("ledger-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    attempt = create_public_payment_attempt(booking)
    confirm_provider_payment(
        attempt,
        provider_payment_reference="pay_provider_api_001",
        amount_inr=8000,
    )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.get(f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["payment_state"] == "reservation_paid"
    assert payload["reconciliation"]["collected_inr"] == 8000
    assert payload["reconciliation"]["platform_fee_inr"] == 160
    assert payload["financial_ledger"]["currency"] == "INR"
    assert len(payload["financial_ledger"]["entries"]) == 2


def decode_csv_response(response):
    return list(csv.DictReader(StringIO(response.content.decode("utf-8"))))


@override_settings(MEDIA_ROOT="/private/tmp/tripos-test-media")
def test_operational_export_defaults_to_active_operational_rows_without_sensitive_data(
    user_factory,
    organizer,
):
    operator = user_factory("export-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer, requires_traveler_documents=True)
    booking = create_draft_booking(trip)
    traveler_slot = booking.traveler_slots.first()
    traveler_slot.traveler_full_name = "Asha Nair"
    traveler_slot.traveler_phone = "+919876543210"
    traveler_slot.traveler_email = "asha@example.com"
    traveler_slot.arrival_details = "Arriving at Chandigarh ISBT by 07:00."
    traveler_slot.departure_details = "Return bus after lunch."
    traveler_slot.pickup_location = "Sector 43 bus stand"
    traveler_slot.logistics_note = "Carries medium trekking backpack."
    traveler_slot.rooming_notes = "Prefers quiet shared room."
    traveler_slot.emergency_contact_name = "Maya Rao"
    traveler_slot.emergency_contact_phone = "+919700000001"
    traveler_slot.emergency_contact_relationship = "Sibling"
    traveler_slot.medical_disclosure = "Mild asthma; carries inhaler."
    traveler_slot.medical_disclosure_submitted_at = timezone.now()
    traveler_slot.attendance_state = TravelerSlot.AttendanceState.CHECKED_IN
    traveler_slot.attendance_marked_at = timezone.now()
    traveler_slot.attendance_marked_by = operator
    traveler_slot.save()
    TravelerDocument.objects.create(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        label="Passport",
        document_state=TravelerDocument.DocumentState.APPROVED,
        file=SimpleUploadedFile("passport.txt", b"identity", content_type="text/plain"),
        original_filename="passport.txt",
        content_type="text/plain",
        file_size=8,
        submitted_at=timezone.now(),
    )
    TravelerDocument.objects.create(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.ELIGIBILITY,
        label="Swimming Certificate",
        document_state=TravelerDocument.DocumentState.SUBMITTED,
    )
    attempt = create_public_payment_attempt(booking)
    confirm_provider_payment(
        attempt,
        provider_payment_reference="pay_export_provider_001",
        amount_inr=8000,
    )
    ManualPayment.objects.create(
        booking=booking,
        amount_inr=4000,
        payment_reference="upi-export-001",
        payment_proof=SimpleUploadedFile(
            "proof.txt",
            b"payment proof",
            content_type="text/plain",
        ),
        original_filename="proof.txt",
        content_type="text/plain",
        file_size=13,
    )
    draft_booking = create_draft_booking(trip)
    draft_slot = draft_booking.traveler_slots.first()
    draft_slot.traveler_full_name = "Draft Traveler"
    draft_slot.traveler_phone = "+919811111111"
    draft_slot.save()

    client = APIClient()
    client.force_authenticate(operator)
    response = client.get(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/operational-export.csv"
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv; charset=utf-8"
    assert response["X-TripOS-Export-Rows"] == "1"
    assert response["X-TripOS-Excluded-Draft-Bookings"] == "1"
    rows = decode_csv_response(response)
    assert len(rows) == 1
    row = rows[0]
    assert row["booking_id"] == str(booking.id)
    assert row["booking_state"] == Booking.BookingState.RESERVED
    assert row["booking_contact_name"] == "Asha Nair"
    assert row["traveler_name"] == "Asha Nair"
    assert row["package_name"] == "Standard shared room"
    assert row["payment_state"] == "partially_paid"
    assert row["document_state"] == TravelerDocument.DocumentState.SUBMITTED
    assert "Passport:identity:approved" in row["document_states"]
    assert row["travel_pickup_location"] == "Sector 43 bus stand"
    assert row["rooming_notes"] == "Prefers quiet shared room."
    assert row["emergency_contact_relationship"] == "Sibling"
    assert row["check_in_status"] == TravelerSlot.AttendanceState.CHECKED_IN
    assert row["checked_in"] == "True"
    assert row["no_show"] == "False"
    assert "balance_due" in row["reconciliation_flags"]
    assert "sensitive_medical_disclosure" not in row
    assert "sensitive_payment_proof_files" not in row
    assert "Draft Traveler" not in response.content.decode("utf-8")

    log = ActivityLog.objects.get(action=ActivityLog.Action.OPERATIONAL_EXPORT_GENERATED)
    assert log.actor == operator
    assert log.trip == trip
    assert log.booking is None
    assert log.metadata["format"] == "csv"
    assert log.metadata["row_count"] == 1
    assert log.metadata["include_sensitive_traveler_information"] is False
    assert log.metadata["include_sensitive_payment_information"] is False
    assert log.metadata["excluded_draft_booking_count"] == 1


@override_settings(MEDIA_ROOT="/private/tmp/tripos-test-media")
def test_operational_export_includes_sensitive_columns_only_when_explicitly_selected(
    user_factory,
    organizer,
):
    owner = user_factory("export-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    traveler_slot = booking.traveler_slots.first()
    traveler_slot.traveler_full_name = "Devika Rao"
    traveler_slot.traveler_phone = "+919812340000"
    traveler_slot.medical_disclosure = "Peanut allergy."
    traveler_slot.medical_disclosure_submitted_at = timezone.now()
    traveler_slot.save()
    TravelerDocument.objects.create(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        label="Passport",
        document_state=TravelerDocument.DocumentState.APPROVED,
        file=SimpleUploadedFile("passport.txt", b"identity", content_type="text/plain"),
        original_filename="passport.txt",
        content_type="text/plain",
        file_size=8,
        submitted_at=timezone.now(),
    )
    attempt = create_public_payment_attempt(booking)
    confirm_provider_payment(
        attempt,
        provider_payment_reference="pay_export_provider_002",
        amount_inr=8000,
    )
    ManualPayment.objects.create(
        booking=booking,
        amount_inr=2000,
        payment_reference="upi-export-002",
        payment_proof=SimpleUploadedFile(
            "payment-proof.txt",
            b"payment proof",
            content_type="text/plain",
        ),
        original_filename="payment-proof.txt",
        content_type="text/plain",
        file_size=13,
    )
    client = APIClient()
    client.force_authenticate(owner)

    default_response = client.get(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/operational-export.csv"
    )
    sensitive_response = client.get(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/operational-export.csv",
        {
            "include_sensitive_traveler_information": "true",
            "include_sensitive_payment_information": "true",
        },
    )

    default_rows = decode_csv_response(default_response)
    sensitive_rows = decode_csv_response(sensitive_response)
    assert "sensitive_medical_disclosure" not in default_rows[0]
    assert "sensitive_provider_payment_references" not in default_rows[0]
    assert sensitive_rows[0]["sensitive_medical_disclosure"] == "Peanut allergy."
    assert sensitive_rows[0]["sensitive_traveler_document_files"] == "passport.txt"
    assert sensitive_rows[0]["sensitive_provider_payment_references"] == ("pay_export_provider_002")
    assert sensitive_rows[0]["sensitive_manual_payment_references"] == "upi-export-002"
    assert sensitive_rows[0]["sensitive_payment_proof_files"] == "payment-proof.txt"

    sensitive_log = ActivityLog.objects.filter(
        action=ActivityLog.Action.OPERATIONAL_EXPORT_GENERATED,
        metadata__include_sensitive_traveler_information=True,
        metadata__include_sensitive_payment_information=True,
    ).get()
    assert sensitive_log.actor == owner


def test_booking_level_access_link_grants_booking_contact_scoped_portal_access(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip, slot_count=2)
    slots = list(booking.traveler_slots.all())
    issued = issue_booking_access_link(booking)
    client = APIClient()

    response = client.get(f"/api/portal/{issued.token}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_scope"] == BookingAccessLink.Scope.BOOKING
    assert payload["booking"]["id"] == booking.id
    assert [slot["id"] for slot in payload["traveler_slots"]] == [slot.id for slot in slots]


def test_traveler_level_access_link_is_scoped_to_one_traveler_slot(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip, slot_count=2)
    first_slot, second_slot = list(booking.traveler_slots.all())
    issued = issue_traveler_access_link(first_slot)
    client = APIClient()

    portal_response = client.get(f"/api/portal/{issued.token}/")
    blocked_response = client.patch(
        f"/api/portal/{issued.token}/traveler-slots/{second_slot.id}/identity/",
        {
            "traveler_full_name": "Blocked Traveler",
            "traveler_phone": "+919999999999",
        },
        format="json",
    )
    own_response = client.patch(
        f"/api/portal/{issued.token}/traveler-slots/{first_slot.id}/identity/",
        {
            "traveler_full_name": "Devika Rao",
            "traveler_phone": "+919999999999",
        },
        format="json",
    )

    first_slot.refresh_from_db()
    second_slot.refresh_from_db()
    assert portal_response.status_code == 200
    assert [slot["id"] for slot in portal_response.json()["traveler_slots"]] == [first_slot.id]
    assert blocked_response.status_code == 400
    assert own_response.status_code == 200
    assert first_slot.is_traveler is True
    assert second_slot.is_traveler is False


def test_access_links_expire_after_14_days_and_expired_links_are_rejected(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    before_issue = timezone.now()
    issued = issue_booking_access_link(booking)

    assert before_issue + timedelta(days=13, hours=23, minutes=59) <= issued.access_link.expires_at
    assert issued.access_link.expires_at <= before_issue + timedelta(days=14, minutes=1)

    issued.access_link.expires_at = timezone.now() - timedelta(minutes=1)
    issued.access_link.save()

    with pytest.raises(ValidationError, match="expired"):
        resolve_active_access_link(issued.token)


def test_regenerating_access_link_revokes_prior_link_for_same_scope(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)

    first = issue_booking_access_link(booking)
    second = issue_booking_access_link(booking)

    assert first.access_link.id != second.access_link.id
    assert BookingAccessLink.objects.get(pk=first.access_link.pk).revoked_at is not None
    assert resolve_active_access_link(second.token).id == second.access_link.id
    with pytest.raises(ValidationError, match="revoked"):
        resolve_active_access_link(first.token)


def test_booking_contact_change_revokes_prior_booking_level_links_only(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    traveler_slot = booking.traveler_slots.first()
    booking_link = issue_booking_access_link(booking)
    traveler_link = issue_traveler_access_link(traveler_slot)

    booking.booking_contact_name = "New Coordinator"
    booking.booking_contact_phone = "+918888888888"
    booking.save()

    assert BookingAccessLink.objects.get(pk=booking_link.access_link.pk).revoked_at is not None
    assert BookingAccessLink.objects.get(pk=traveler_link.access_link.pk).revoked_at is None


def test_traveler_identity_details_promote_slot_to_traveler_and_allow_shared_phone(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip, slot_count=2)
    first_slot, second_slot = list(booking.traveler_slots.all())
    issued = issue_booking_access_link(booking)
    client = APIClient()

    missing_phone_response = client.patch(
        f"/api/portal/{issued.token}/traveler-slots/{first_slot.id}/identity/",
        {"traveler_full_name": "Asha Nair"},
        format="json",
    )
    first_response = client.patch(
        f"/api/portal/{issued.token}/traveler-slots/{first_slot.id}/identity/",
        {
            "traveler_full_name": "Asha Nair",
            "traveler_phone": "+919876543210",
        },
        format="json",
    )
    second_response = client.patch(
        f"/api/portal/{issued.token}/traveler-slots/{second_slot.id}/identity/",
        {
            "traveler_full_name": "Meera Nair",
            "traveler_phone": "+919876543210",
            "traveler_email": "meera@example.com",
        },
        format="json",
    )

    first_slot.refresh_from_db()
    second_slot.refresh_from_db()
    assert missing_phone_response.status_code == 400
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_slot.is_traveler is True
    assert first_slot.traveler_email == ""
    assert second_slot.is_traveler is True
    assert first_slot.traveler_phone == second_slot.traveler_phone


def test_operator_can_regenerate_access_link_through_scoped_api(user_factory, organizer):
    operator = user_factory("access-link-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    client = APIClient()
    client.force_authenticate(operator)

    first_response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/access-links/",
        {"scope": BookingAccessLink.Scope.BOOKING},
        format="json",
    )
    second_response = client.post(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/access-links/",
        {"scope": BookingAccessLink.Scope.BOOKING},
        format="json",
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["token"] != second_response.json()["token"]
    assert BookingAccessLink.objects.get(pk=first_response.json()["id"]).revoked_at is not None


@override_settings(MEDIA_ROOT="/private/tmp/tripos-test-media")
def test_traveler_can_submit_document_through_portal_and_state_becomes_submitted(organizer):
    trip = create_bookable_trip(organizer, requires_traveler_documents=True)
    booking = create_draft_booking(trip)
    traveler_slot = booking.traveler_slots.first()
    issued = issue_traveler_access_link(traveler_slot)
    client = APIClient()

    response = client.post(
        f"/api/portal/{issued.token}/traveler-slots/{traveler_slot.id}/documents/",
        {
            "document_kind": TravelerDocument.DocumentKind.IDENTITY,
            "label": "Passport",
            "file": SimpleUploadedFile(
                "passport.txt",
                b"identity document",
                content_type="text/plain",
            ),
        },
        format="multipart",
    )

    document = TravelerDocument.objects.get(traveler_slot=traveler_slot)
    assert response.status_code == 201
    assert response.json()["document_state"] == TravelerDocument.DocumentState.SUBMITTED
    assert document.document_state == TravelerDocument.DocumentState.SUBMITTED
    assert document.original_filename == "passport.txt"
    assert document.is_sensitive_traveler_information is True
    assert document.exclude_from_default_exports is True


def test_traveler_documents_support_missing_submitted_approved_and_rejected_states(
    user_factory,
    organizer,
):
    operator = user_factory("document-reviewer@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_bookable_trip(organizer, requires_traveler_documents=True)
    booking = create_draft_booking(trip)
    traveler_slot = booking.traveler_slots.first()
    document = TravelerDocument.objects.create(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        label="Passport",
    )
    client = APIClient()
    client.force_authenticate(operator)

    assert document.document_state == TravelerDocument.DocumentState.MISSING

    document.file = SimpleUploadedFile("passport.txt", b"identity", content_type="text/plain")
    document.original_filename = "passport.txt"
    document.content_type = "text/plain"
    document.file_size = 8
    document.document_state = TravelerDocument.DocumentState.SUBMITTED
    document.submitted_at = timezone.now()
    document.save()

    approved_response = client.patch(
        f"/api/operations/organizers/{organizer.id}/traveler-documents/{document.id}/",
        {"document_state": TravelerDocument.DocumentState.APPROVED},
        format="json",
    )
    rejected_response = client.patch(
        f"/api/operations/organizers/{organizer.id}/traveler-documents/{document.id}/",
        {
            "document_state": TravelerDocument.DocumentState.REJECTED,
            "rejection_reason": "Name is not legible.",
        },
        format="json",
    )

    document.refresh_from_db()
    assert approved_response.status_code == 200
    assert approved_response.json()["document_state"] == TravelerDocument.DocumentState.APPROVED
    assert rejected_response.status_code == 200
    assert document.document_state == TravelerDocument.DocumentState.REJECTED
    assert document.rejection_reason == "Name is not legible."
    assert document.reviewed_by == operator
    assert ActivityLog.objects.filter(
        traveler_document=document,
        action=ActivityLog.Action.TRAVELER_DOCUMENT_REJECTED,
    ).exists()


def test_document_review_requires_owner_or_operator(user_factory, organizer):
    outsider = user_factory("document-outsider@example.com")
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    document = TravelerDocument.objects.create(
        traveler_slot=booking.traveler_slots.first(),
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        label="Passport",
        document_state=TravelerDocument.DocumentState.SUBMITTED,
    )
    client = APIClient()
    client.force_authenticate(outsider)

    response = client.patch(
        f"/api/operations/organizers/{organizer.id}/traveler-documents/{document.id}/",
        {"document_state": TravelerDocument.DocumentState.APPROVED},
        format="json",
    )

    assert response.status_code == 403


def test_portal_collects_travel_logistics_emergency_contact_and_medical_disclosure(
    organizer,
):
    trip = create_bookable_trip(
        organizer,
        requires_travel_logistics=True,
        requires_emergency_contact=True,
        requires_medical_disclosure=True,
    )
    booking = create_draft_booking(trip)
    traveler_slot = booking.traveler_slots.first()
    issued = issue_booking_access_link(booking)
    client = APIClient()

    logistics_response = client.patch(
        f"/api/portal/{issued.token}/traveler-slots/{traveler_slot.id}/travel-logistics/",
        {
            "arrival_details": "Arriving at Chandigarh ISBT by 07:00.",
            "departure_details": "Return bus after lunch.",
            "pickup_location": "Sector 43 bus stand",
            "logistics_note": "Carries medium trekking backpack.",
        },
        format="json",
    )
    emergency_response = client.patch(
        f"/api/portal/{issued.token}/traveler-slots/{traveler_slot.id}/emergency-contact/",
        {
            "emergency_contact_name": "Maya Rao",
            "emergency_contact_phone": "+919700000001",
            "emergency_contact_relationship": "Sibling",
        },
        format="json",
    )
    medical_response = client.patch(
        f"/api/portal/{issued.token}/traveler-slots/{traveler_slot.id}/medical-disclosure/",
        {"medical_disclosure": "Mild asthma; carries inhaler."},
        format="json",
    )

    traveler_slot.refresh_from_db()
    readiness = readiness_summary_for_traveler_slot(traveler_slot)
    assert logistics_response.status_code == 200
    assert emergency_response.status_code == 200
    assert medical_response.status_code == 200
    assert traveler_slot.has_travel_logistics is True
    assert traveler_slot.has_emergency_contact is True
    assert traveler_slot.has_medical_disclosure is True
    assert (
        medical_response.json()["medical_disclosure_status"]["is_sensitive_traveler_information"]
        is True
    )
    assert (
        medical_response.json()["medical_disclosure_status"]["exclude_from_default_exports"] is True
    )
    assert readiness["travel_logistics_ready"] is True
    assert readiness["emergency_contact_ready"] is True
    assert readiness["medical_disclosure_ready"] is True


@override_settings(MEDIA_ROOT="/private/tmp/tripos-test-media")
def test_sensitive_traveler_document_download_records_activity_log(user_factory, organizer):
    owner = user_factory("download-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    traveler_slot = booking.traveler_slots.first()
    document = TravelerDocument.objects.create(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        label="Passport",
        document_state=TravelerDocument.DocumentState.APPROVED,
        file=SimpleUploadedFile("passport.txt", b"identity", content_type="text/plain"),
        original_filename="passport.txt",
        content_type="text/plain",
        file_size=8,
        submitted_at=timezone.now(),
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(
        f"/api/operations/organizers/{organizer.id}/traveler-documents/{document.id}/download/"
    )

    assert response.status_code == 200
    log = ActivityLog.objects.get(
        traveler_document=document,
        action=ActivityLog.Action.SENSITIVE_TRAVELER_INFORMATION_DOWNLOAD,
    )
    assert log.actor == owner
    assert log.traveler_slot == traveler_slot
    assert log.metadata["exclude_from_default_exports"] is True


def test_eligibility_document_is_not_sensitive_by_default(organizer):
    trip = create_bookable_trip(organizer)
    booking = create_draft_booking(trip)
    document = TravelerDocument.objects.create(
        traveler_slot=booking.traveler_slots.first(),
        document_kind=TravelerDocument.DocumentKind.ELIGIBILITY,
        label="Swimming Certificate",
    )

    assert document.is_sensitive_traveler_information is False
    assert document.exclude_from_default_exports is False
