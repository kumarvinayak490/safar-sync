from __future__ import annotations

from dataclasses import dataclass

from organizers.models import (
    Organizer,
    PayoutAccount,
    ProviderPaymentSetup,
    SensitiveProviderCredential,
)

ProviderVerificationStatus = ProviderPaymentSetup.ProviderVerificationStatus
ProviderConnectionState = ProviderPaymentSetup.ProviderConnectionState
ProviderAuthorizationState = ProviderPaymentSetup.AuthorizationState
ProviderMode = ProviderPaymentSetup.ProviderMode


class OnlinePaymentReadinessBlocker:
    READY = "ready"
    PROVIDER_AUTHORIZATION_NOT_ACTIVE = "provider_authorization_not_active"
    PROVIDER_VERIFICATION_NOT_VERIFIED = "provider_verification_not_verified"
    SETTLEMENT_READINESS_NOT_READY = "settlement_readiness_not_ready"
    PROVIDER_PAYMENT_CAPABILITY_DISABLED = "provider_payment_capability_disabled"
    PROVIDER_CONNECTION_UNHEALTHY = "provider_connection_unhealthy"
    PROVIDER_MODE_NOT_LIVE = "provider_mode_not_live"
    PROVIDER_ORDER_CREATION_UNAVAILABLE = "provider_order_creation_unavailable"


ONLINE_PAYMENT_READINESS_BLOCKER_LABELS = {
    OnlinePaymentReadinessBlocker.READY: "Ready",
    OnlinePaymentReadinessBlocker.PROVIDER_AUTHORIZATION_NOT_ACTIVE: (
        "Provider Authorization not active"
    ),
    OnlinePaymentReadinessBlocker.PROVIDER_VERIFICATION_NOT_VERIFIED: (
        "Provider verification not verified"
    ),
    OnlinePaymentReadinessBlocker.SETTLEMENT_READINESS_NOT_READY: (
        "Settlement Readiness not active"
    ),
    OnlinePaymentReadinessBlocker.PROVIDER_PAYMENT_CAPABILITY_DISABLED: (
        "Provider payment capability disabled"
    ),
    OnlinePaymentReadinessBlocker.PROVIDER_CONNECTION_UNHEALTHY: ("Provider connection unhealthy"),
    OnlinePaymentReadinessBlocker.PROVIDER_MODE_NOT_LIVE: "Provider mode not live",
    OnlinePaymentReadinessBlocker.PROVIDER_ORDER_CREATION_UNAVAILABLE: (
        "Provider order creation unavailable"
    ),
}

ONLINE_PAYMENT_READINESS_MESSAGES = {
    OnlinePaymentReadinessBlocker.READY: ("Online Payment Readiness is ready for public booking."),
    OnlinePaymentReadinessBlocker.PROVIDER_AUTHORIZATION_NOT_ACTIVE: (
        "Active Provider Authorization is required before public booking can open."
    ),
    OnlinePaymentReadinessBlocker.PROVIDER_VERIFICATION_NOT_VERIFIED: (
        "Provider verification must be verified before public booking can open."
    ),
    OnlinePaymentReadinessBlocker.SETTLEMENT_READINESS_NOT_READY: (
        "Settlement Readiness must be active before public booking can open."
    ),
    OnlinePaymentReadinessBlocker.PROVIDER_PAYMENT_CAPABILITY_DISABLED: (
        "Provider payment capability must be enabled before public booking can open."
    ),
    OnlinePaymentReadinessBlocker.PROVIDER_CONNECTION_UNHEALTHY: (
        "Provider connection must be healthy before public booking can open."
    ),
    OnlinePaymentReadinessBlocker.PROVIDER_MODE_NOT_LIVE: (
        "Provider mode must be live before public booking can open."
    ),
    OnlinePaymentReadinessBlocker.PROVIDER_ORDER_CREATION_UNAVAILABLE: (
        "Server-side provider order creation must be available before public booking can open."
    ),
}


@dataclass(frozen=True)
class OnlinePaymentReadinessRequirement:
    fact_name: str
    expected_value: bool | str
    blocker_code: str

    def is_met(self, facts: OnlinePaymentReadinessFacts) -> bool:
        return getattr(facts, self.fact_name) == self.expected_value


@dataclass(frozen=True)
class OnlinePaymentReadinessFacts:
    provider_authorization_state: str = ProviderAuthorizationState.NOT_STARTED
    provider_verification_status: str = ProviderVerificationStatus.NOT_STARTED
    payout_status: str = PayoutAccount.Status.NOT_STARTED
    provider_payment_capability_enabled: bool = False
    provider_connection_state: str = ProviderConnectionState.UNHEALTHY
    provider_mode: str = ProviderMode.TEST
    provider_order_creation_available: bool = False


ONLINE_PAYMENT_READINESS_REQUIREMENTS = (
    OnlinePaymentReadinessRequirement(
        fact_name="provider_authorization_state",
        expected_value=ProviderAuthorizationState.AUTHORIZED,
        blocker_code=OnlinePaymentReadinessBlocker.PROVIDER_AUTHORIZATION_NOT_ACTIVE,
    ),
    OnlinePaymentReadinessRequirement(
        fact_name="provider_verification_status",
        expected_value=ProviderVerificationStatus.VERIFIED,
        blocker_code=OnlinePaymentReadinessBlocker.PROVIDER_VERIFICATION_NOT_VERIFIED,
    ),
    OnlinePaymentReadinessRequirement(
        fact_name="payout_status",
        expected_value=PayoutAccount.Status.ACTIVE,
        blocker_code=OnlinePaymentReadinessBlocker.SETTLEMENT_READINESS_NOT_READY,
    ),
    OnlinePaymentReadinessRequirement(
        fact_name="provider_payment_capability_enabled",
        expected_value=True,
        blocker_code=OnlinePaymentReadinessBlocker.PROVIDER_PAYMENT_CAPABILITY_DISABLED,
    ),
    OnlinePaymentReadinessRequirement(
        fact_name="provider_connection_state",
        expected_value=ProviderConnectionState.HEALTHY,
        blocker_code=OnlinePaymentReadinessBlocker.PROVIDER_CONNECTION_UNHEALTHY,
    ),
    OnlinePaymentReadinessRequirement(
        fact_name="provider_mode",
        expected_value=ProviderMode.LIVE,
        blocker_code=OnlinePaymentReadinessBlocker.PROVIDER_MODE_NOT_LIVE,
    ),
    OnlinePaymentReadinessRequirement(
        fact_name="provider_order_creation_available",
        expected_value=True,
        blocker_code=OnlinePaymentReadinessBlocker.PROVIDER_ORDER_CREATION_UNAVAILABLE,
    ),
)


@dataclass(frozen=True)
class OnlinePaymentReadinessDecision:
    facts: OnlinePaymentReadinessFacts
    ready: bool
    blocker_code: str

    @property
    def status_label(self) -> str:
        return "Ready" if self.ready else "Blocked"

    @property
    def blocker_label(self) -> str:
        return ONLINE_PAYMENT_READINESS_BLOCKER_LABELS[self.blocker_code]

    @property
    def message(self) -> str:
        return ONLINE_PAYMENT_READINESS_MESSAGES[self.blocker_code]

    @property
    def payout_account_ready(self) -> bool:
        return self.facts.payout_status == PayoutAccount.Status.ACTIVE

    @property
    def settlement_readiness_ready(self) -> bool:
        return self.payout_account_ready

    def to_payload(self) -> dict[str, bool | str]:
        return {
            "online_payment_readiness_ready": self.ready,
            "online_payment_readiness_status_label": self.status_label,
            "online_payment_readiness_blocker_code": self.blocker_code,
            "online_payment_readiness_blocker_label": self.blocker_label,
            "online_payment_readiness_message": self.message,
            "provider_authorization_state": self.facts.provider_authorization_state,
            "provider_authorization_state_label": _choice_label(
                ProviderAuthorizationState,
                self.facts.provider_authorization_state,
            ),
            "provider_verification_status": self.facts.provider_verification_status,
            "provider_verification_status_label": _choice_label(
                ProviderVerificationStatus,
                self.facts.provider_verification_status,
            ),
            "payout_account_ready": self.payout_account_ready,
            "settlement_readiness_ready": self.settlement_readiness_ready,
            "provider_payment_capability_enabled": (self.facts.provider_payment_capability_enabled),
            "provider_connection_state": self.facts.provider_connection_state,
            "provider_connection_state_label": _choice_label(
                ProviderConnectionState,
                self.facts.provider_connection_state,
            ),
            "provider_mode": self.facts.provider_mode,
            "provider_mode_label": _choice_label(
                ProviderMode,
                self.facts.provider_mode,
            ),
            "provider_order_creation_available": (self.facts.provider_order_creation_available),
        }


def derive_online_payment_readiness(
    facts: OnlinePaymentReadinessFacts,
) -> OnlinePaymentReadinessDecision:
    for requirement in ONLINE_PAYMENT_READINESS_REQUIREMENTS:
        if not requirement.is_met(facts):
            return _blocked(facts, requirement.blocker_code)

    return OnlinePaymentReadinessDecision(
        facts=facts,
        ready=True,
        blocker_code=OnlinePaymentReadinessBlocker.READY,
    )


def online_payment_readiness_for_organizer(
    organizer: Organizer,
) -> OnlinePaymentReadinessDecision:
    return derive_online_payment_readiness(online_payment_readiness_facts(organizer))


def online_payment_readiness_facts(organizer: Organizer) -> OnlinePaymentReadinessFacts:
    payout_account = _payout_account_for(organizer)
    provider_setup = _provider_payment_setup_for(organizer)

    return OnlinePaymentReadinessFacts(
        provider_authorization_state=(
            provider_setup.authorization_state
            if provider_setup is not None
            else ProviderAuthorizationState.NOT_STARTED
        ),
        provider_verification_status=(
            provider_setup.provider_verification_status
            if provider_setup is not None
            else ProviderVerificationStatus.NOT_STARTED
        ),
        payout_status=(
            payout_account.status
            if payout_account is not None
            else PayoutAccount.Status.NOT_STARTED
        ),
        provider_payment_capability_enabled=(
            provider_setup.provider_payment_capability_enabled
            if provider_setup is not None
            else False
        ),
        provider_connection_state=(
            provider_setup.provider_connection_state
            if provider_setup is not None
            else ProviderConnectionState.UNHEALTHY
        ),
        provider_mode=(
            provider_setup.provider_mode if provider_setup is not None else ProviderMode.TEST
        ),
        provider_order_creation_available=_provider_order_creation_available(
            organizer,
            provider_setup,
        ),
    )


def _blocked(
    facts: OnlinePaymentReadinessFacts,
    blocker_code: str,
) -> OnlinePaymentReadinessDecision:
    return OnlinePaymentReadinessDecision(
        facts=facts,
        ready=False,
        blocker_code=blocker_code,
    )


def _choice_label(choice_class, value: str) -> str:
    try:
        return choice_class(value).label
    except (TypeError, ValueError):
        return value


def _payout_account_for(organizer: Organizer) -> PayoutAccount | None:
    return PayoutAccount.objects.filter(organizer=organizer).first()


def _provider_payment_setup_for(organizer: Organizer) -> ProviderPaymentSetup | None:
    return ProviderPaymentSetup.objects.filter(organizer=organizer).first()


def _provider_order_creation_available(
    organizer: Organizer,
    provider_setup: ProviderPaymentSetup | None,
) -> bool:
    if provider_setup is None:
        return False
    if provider_setup.provider != ProviderPaymentSetup.Provider.RAZORPAY:
        return False
    if not provider_setup.provider_merchant_reference.strip():
        return False
    return SensitiveProviderCredential.objects.filter(
        organizer=organizer,
        provider=provider_setup.provider,
        provider_mode=provider_setup.provider_mode,
        provider_account_reference=provider_setup.provider_merchant_reference,
        status=SensitiveProviderCredential.Status.ACTIVE,
    ).exists()
