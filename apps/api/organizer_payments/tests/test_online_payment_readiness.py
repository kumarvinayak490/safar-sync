import pytest

from organizer_payments.online_payment_readiness import (
    OnlinePaymentReadinessBlocker,
    OnlinePaymentReadinessFacts,
    ProviderAuthorizationState,
    ProviderConnectionState,
    ProviderMode,
    ProviderVerificationStatus,
    derive_online_payment_readiness,
    online_payment_readiness_for_organizer,
)
from organizers.models import (
    Organizer,
    PayoutAccount,
    ProviderPaymentSetup,
    SensitiveProviderCredential,
)


def ready_facts(**overrides):
    facts = {
        "provider_authorization_state": ProviderAuthorizationState.AUTHORIZED,
        "provider_verification_status": ProviderVerificationStatus.VERIFIED,
        "payout_status": PayoutAccount.Status.ACTIVE,
        "provider_payment_capability_enabled": True,
        "provider_connection_state": ProviderConnectionState.HEALTHY,
        "provider_mode": ProviderMode.LIVE,
        "provider_order_creation_available": True,
    }
    facts.update(overrides)
    return OnlinePaymentReadinessFacts(**facts)


def test_online_payment_readiness_is_ready_when_all_facts_are_ready():
    readiness = derive_online_payment_readiness(ready_facts())

    assert readiness.ready is True
    assert readiness.blocker_code == OnlinePaymentReadinessBlocker.READY
    assert readiness.to_payload()["online_payment_readiness_ready"] is True


def test_online_payment_readiness_blocks_missing_provider_authorization():
    readiness = derive_online_payment_readiness(
        ready_facts(provider_authorization_state=ProviderAuthorizationState.REVOKED)
    )

    assert readiness.ready is False
    assert readiness.blocker_code == OnlinePaymentReadinessBlocker.PROVIDER_AUTHORIZATION_NOT_ACTIVE


def test_online_payment_readiness_blocks_missing_provider_verification():
    readiness = derive_online_payment_readiness(
        ready_facts(provider_verification_status=ProviderVerificationStatus.IN_REVIEW)
    )

    assert readiness.ready is False
    assert (
        readiness.blocker_code == OnlinePaymentReadinessBlocker.PROVIDER_VERIFICATION_NOT_VERIFIED
    )


def test_online_payment_readiness_blocks_missing_settlement_readiness():
    readiness = derive_online_payment_readiness(
        ready_facts(payout_status=PayoutAccount.Status.PENDING)
    )

    assert readiness.ready is False
    assert readiness.blocker_code == OnlinePaymentReadinessBlocker.SETTLEMENT_READINESS_NOT_READY


def test_online_payment_readiness_blocks_disabled_provider_capability():
    readiness = derive_online_payment_readiness(
        ready_facts(provider_payment_capability_enabled=False)
    )

    assert readiness.ready is False
    assert (
        readiness.blocker_code == OnlinePaymentReadinessBlocker.PROVIDER_PAYMENT_CAPABILITY_DISABLED
    )


def test_online_payment_readiness_blocks_unhealthy_provider_connection():
    readiness = derive_online_payment_readiness(
        ready_facts(provider_connection_state=ProviderConnectionState.UNHEALTHY)
    )

    assert readiness.ready is False
    assert readiness.blocker_code == OnlinePaymentReadinessBlocker.PROVIDER_CONNECTION_UNHEALTHY


def test_online_payment_readiness_blocks_test_provider_mode():
    readiness = derive_online_payment_readiness(ready_facts(provider_mode=ProviderMode.TEST))

    assert readiness.ready is False
    assert readiness.blocker_code == OnlinePaymentReadinessBlocker.PROVIDER_MODE_NOT_LIVE


def test_online_payment_readiness_blocks_missing_provider_order_creation():
    readiness = derive_online_payment_readiness(
        ready_facts(provider_order_creation_available=False)
    )

    assert readiness.ready is False
    assert (
        readiness.blocker_code == OnlinePaymentReadinessBlocker.PROVIDER_ORDER_CREATION_UNAVAILABLE
    )


@pytest.mark.django_db
def test_organizer_online_payment_readiness_blocks_unstarted_payment_setup():
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")

    readiness = online_payment_readiness_for_organizer(organizer)

    assert readiness.ready is False
    assert readiness.blocker_code == OnlinePaymentReadinessBlocker.PROVIDER_AUTHORIZATION_NOT_ACTIVE


@pytest.mark.django_db
def test_organizer_online_payment_readiness_blocks_partially_configured_settlement_readiness():
    organizer = Organizer.objects.create(name="Partially Configured Payments")
    provider_setup = organizer.provider_payment_setup
    provider_setup.status = ProviderPaymentSetup.Status.COMPLETE
    provider_setup.authorization_state = ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    provider_setup.provider_verification_status = (
        ProviderPaymentSetup.ProviderVerificationStatus.VERIFIED
    )
    provider_setup.provider_payment_capability_enabled = True
    provider_setup.provider_connection_state = ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    provider_setup.provider_mode = ProviderPaymentSetup.ProviderMode.LIVE
    provider_setup.provider_merchant_reference = f"acct_razorpay_{organizer.id}"
    provider_setup.save()

    readiness = online_payment_readiness_for_organizer(organizer)

    assert readiness.ready is False
    assert readiness.blocker_code == OnlinePaymentReadinessBlocker.SETTLEMENT_READINESS_NOT_READY
    assert readiness.settlement_readiness_ready is False


@pytest.mark.django_db
def test_organizer_online_payment_readiness_is_ready_when_setup_and_settlement_are_ready():
    organizer = Organizer.objects.create(name="Ready Provider Payments")
    provider_setup = organizer.provider_payment_setup
    provider_setup.status = ProviderPaymentSetup.Status.COMPLETE
    provider_setup.authorization_state = ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    provider_setup.provider_verification_status = (
        ProviderPaymentSetup.ProviderVerificationStatus.VERIFIED
    )
    provider_setup.provider_payment_capability_enabled = True
    provider_setup.provider_connection_state = ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    provider_setup.provider_mode = ProviderPaymentSetup.ProviderMode.LIVE
    provider_setup.provider_merchant_reference = f"acct_razorpay_{organizer.id}"
    provider_setup.save()
    organizer.payout_account.status = PayoutAccount.Status.ACTIVE
    organizer.payout_account.save()
    SensitiveProviderCredential.objects.create(
        organizer=organizer,
        provider_payment_setup=provider_setup,
        provider=provider_setup.provider,
        provider_mode=provider_setup.provider_mode,
        credential_kind=SensitiveProviderCredential.CredentialKind.OAUTH,
        status=SensitiveProviderCredential.Status.ACTIVE,
        provider_account_reference=provider_setup.provider_merchant_reference,
        scopes=["read_write"],
        encrypted_payload="encrypted-oauth-token",
        encryption_key_id="test-key",
        credential_fingerprint=f"fingerprint-{organizer.id}",
    )

    readiness = online_payment_readiness_for_organizer(organizer)

    assert readiness.ready is True
    assert readiness.blocker_code == OnlinePaymentReadinessBlocker.READY
    assert readiness.settlement_readiness_ready is True
