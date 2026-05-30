from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import override_settings
from django.utils import timezone

from organizer_payments.models import (
    ProviderAuthorizationSession,
    ProviderPaymentSetup,
    SensitiveProviderCredential,
    SensitiveProviderCredentialAudit,
)
from organizer_payments.provider_adapters import ProviderOAuthTokenExchangeResult
from organizer_payments.provider_authorization import (
    complete_provider_authorization,
    start_provider_authorization,
)
from organizer_payments.provider_credentials import (
    SensitiveProviderCredentialStore,
    configure_assisted_api_key_credentials,
)
from organizers.models import Organizer
from team_access.models import OrganizerMembership

pytestmark = pytest.mark.django_db


class FakeOAuthAdapter:
    def __init__(self, exchange_result: ProviderOAuthTokenExchangeResult):
        self.exchange_result = exchange_result
        self.authorization_requests = []
        self.exchange_requests = []

    def build_authorization_url(self, request):
        self.authorization_requests.append(request)
        return f"https://auth.razorpay.test/authorize?state={request.state}"

    def exchange_authorization_code(self, request):
        self.exchange_requests.append(request)
        return self.exchange_result


def create_user(email: str, *, is_staff: bool = False):
    user = get_user_model().objects.create_user(
        username=email,
        email=email,
        password="tripos-test-password",
    )
    user.is_staff = is_staff
    user.save()
    return user


@override_settings(
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY="provider-auth-test-key",
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY_ID="provider-auth-test-key-id",
    TRIPOS_RAZORPAY_OAUTH_CLIENT_ID="rzp_oauth_client",
    TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET="rzp_oauth_secret",
    TRIPOS_RAZORPAY_OAUTH_SCOPES=["read_write"],
)
def test_provider_authorization_lifecycle_stores_sensitive_oauth_credentials():
    organizer = Organizer.objects.create(name="Provider Authorization Collective")
    owner = create_user("provider-auth-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    access_token = "oauth-access-token-never-exposed"
    refresh_token = "oauth-refresh-token-never-exposed"
    adapter = FakeOAuthAdapter(
        ProviderOAuthTokenExchangeResult(
            provider=ProviderPaymentSetup.Provider.RAZORPAY,
            access_token=access_token,
            refresh_token=refresh_token,
            provider_account_reference="acct_razorpay_domain_owner",
            provider_mode=ProviderPaymentSetup.ProviderMode.LIVE,
            scopes=["read_write"],
            expires_at=timezone.now() + timedelta(hours=1),
            public_token="rzp_public_domain_owner",
        )
    )

    started = start_provider_authorization(
        organizer=organizer,
        actor=owner,
        provider_mode=ProviderPaymentSetup.ProviderMode.LIVE,
        adapter=adapter,
    )
    completed = complete_provider_authorization(
        organizer=organizer,
        actor=owner,
        state=started.state,
        code="oauth-code",
        adapter=adapter,
    )

    organizer.provider_payment_setup.refresh_from_db()
    credential = SensitiveProviderCredential.objects.get()
    retrieved = SensitiveProviderCredentialStore().retrieve_active_credential(
        organizer=organizer,
        credential_kind=SensitiveProviderCredential.CredentialKind.OAUTH,
    )
    credential.refresh_from_db()
    assert completed.session.status == ProviderAuthorizationSession.Status.COMPLETED
    assert completed.provider_account_reference == "acct_razorpay_domain_owner"
    assert completed.credential == credential
    assert organizer.provider_payment_setup.authorization_state == (
        ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    )
    assert organizer.provider_payment_setup.provider_connection_state == (
        ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    )
    assert credential.provider_account_reference == "acct_razorpay_domain_owner"
    assert access_token not in credential.encrypted_payload
    assert refresh_token not in credential.encrypted_payload
    assert retrieved.secret_payload["access_token"] == access_token
    assert retrieved.secret_payload["refresh_token"] == refresh_token
    assert set(credential.audit_events.values_list("event_type", flat=True)) == {
        SensitiveProviderCredentialAudit.EventType.STORED,
        SensitiveProviderCredentialAudit.EventType.RETRIEVED,
    }


@override_settings(
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY="provider-api-key-test-key",
    TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY_ID="provider-api-key-test-key-id",
)
def test_assisted_api_key_provider_credentials_are_staff_only_and_audited():
    organizer = Organizer.objects.create(name="Assisted Provider Setup Collective")
    owner = create_user("assisted-provider-owner@example.com")
    staff = create_user("assisted-provider-staff@example.com", is_staff=True)

    with pytest.raises(PermissionDenied):
        configure_assisted_api_key_credentials(
            organizer=organizer,
            actor=owner,
            key_id="rzp_key_public",
            key_secret="rzp_key_secret_never_exposed",
            webhook_secret="webhook_secret_never_exposed",
            provider_account_reference="acct_assisted_api_key",
            provider_mode=ProviderPaymentSetup.ProviderMode.TEST,
        )

    credential = configure_assisted_api_key_credentials(
        organizer=organizer,
        actor=staff,
        key_id="rzp_key_public",
        key_secret="rzp_key_secret_never_exposed",
        webhook_secret="webhook_secret_never_exposed",
        provider_account_reference="acct_assisted_api_key",
        provider_mode=ProviderPaymentSetup.ProviderMode.TEST,
    )
    organizer.provider_payment_setup.refresh_from_db()
    retrieved = SensitiveProviderCredentialStore().retrieve_active_credential(
        organizer=organizer,
        credential_kind=SensitiveProviderCredential.CredentialKind.API_KEY,
    )
    credential.refresh_from_db()

    assert credential.credential_kind == SensitiveProviderCredential.CredentialKind.API_KEY
    assert credential.status == SensitiveProviderCredential.Status.ACTIVE
    assert credential.created_by == staff
    assert "rzp_key_secret_never_exposed" not in credential.encrypted_payload
    assert "webhook_secret_never_exposed" not in credential.encrypted_payload
    assert organizer.provider_payment_setup.authorization_method == (
        ProviderPaymentSetup.AuthorizationMethod.API_KEY
    )
    assert organizer.provider_payment_setup.authorization_state == (
        ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    )
    assert retrieved.secret_payload["key_id"] == "rzp_key_public"
    assert retrieved.secret_payload["key_secret"] == "rzp_key_secret_never_exposed"
    assert retrieved.secret_payload["webhook_secret"] == "webhook_secret_never_exposed"
    assert set(credential.audit_events.values_list("event_type", flat=True)) == {
        SensitiveProviderCredentialAudit.EventType.STORED,
        SensitiveProviderCredentialAudit.EventType.RETRIEVED,
    }
