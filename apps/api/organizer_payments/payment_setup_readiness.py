from __future__ import annotations

from dataclasses import dataclass

from organizer_payments.manual_payment_instructions import (
    has_ready_manual_payment_instructions,
    manual_payment_instructions_payload,
)
from organizer_payments.online_payment_readiness import (
    OnlinePaymentReadinessDecision,
    online_payment_readiness_for_organizer,
)
from organizer_payments.payment_setup_guidance import (
    individual_creator_payment_path_payload,
    manual_payments_only_payload,
    provider_verification_url_payload,
)
from organizer_payments.setup_records import ensure_payment_setup_records
from organizers.models import Organizer, PayoutAccount, ProviderPaymentSetup
from organizers.serializers import PaymentSetupStatusSerializer, provider_disclosure_for
from organizers.services import is_manual_payment_capability_enabled
from team_access.permissions import OrganizerRole
from trips.payment_method_readiness import (
    ManualPaymentMethodReadinessFacts,
    PaymentMethodReadinessDecision,
    manual_payment_method_readiness,
    provider_payment_method_readiness,
)


@dataclass(frozen=True)
class PaymentSetupReadinessReadModel:
    organizer: Organizer
    payout_account: PayoutAccount
    provider_setup: ProviderPaymentSetup
    readiness: OnlinePaymentReadinessDecision
    payment_method_readiness: PaymentMethodReadinessDecision
    manual_payment_capability_enabled: bool
    can_manage_provider_authorization: bool
    can_manage_manual_payment_instructions: bool

    def to_payload(self) -> dict:
        payload = {
            "provider": self.provider_setup.provider,
            "provider_label": self.provider_setup.get_provider_display(),
            "provider_disclosure": provider_disclosure_for(self.provider_setup.provider),
            "payout_status": self.payout_account.status,
            "payout_status_label": self.payout_account.get_status_display(),
            "settlement_readiness_status": self.payout_account.status,
            "settlement_readiness_status_label": (self.payout_account.get_status_display()),
            "settlement_readiness_source": (self.payout_account.settlement_readiness_source),
            "settlement_readiness_source_label": (
                self.payout_account.get_settlement_readiness_source_display()
            ),
            "settlement_readiness_support_confirmed": (
                self.payout_account.settlement_readiness_source
                == PayoutAccount.SettlementReadinessSource.SUPPORT_CONFIRMED
            ),
            "settlement_readiness_support_confirmed_at": (self.payout_account.support_confirmed_at),
            "provider_payment_setup_status": self.provider_setup.status,
            "provider_payment_setup_status_label": (self.provider_setup.get_status_display()),
            "provider_payment_setup_complete": self.provider_setup.is_complete,
            "provider_authorization_method": self.provider_setup.authorization_method,
            "provider_authorization_method_label": (
                self.provider_setup.get_authorization_method_display()
            ),
            "provider_authorization_state": self.provider_setup.authorization_state,
            "provider_authorization_state_label": (
                self.provider_setup.get_authorization_state_display()
            ),
            **self.readiness.to_payload(),
            **self.payment_method_readiness.to_payload(),
            "manual_payment_capability_enabled": self.manual_payment_capability_enabled,
            "can_manage_manual_payment_instructions": (
                self.can_manage_manual_payment_instructions
            ),
            "manual_payment_instructions": manual_payment_instructions_payload(
                self.organizer,
                can_manage=self.can_manage_manual_payment_instructions,
            ),
            "can_manage_provider_authorization": self.can_manage_provider_authorization,
            "payment_setup_access_message": self.access_message,
            "provider_authorization_actions": self.provider_authorization_actions,
            "individual_creator_payment_path": individual_creator_payment_path_payload(),
            "provider_verification_url": provider_verification_url_payload(self.organizer),
            "manual_payments_only": manual_payments_only_payload(
                self.readiness,
                manual_payment_capability_enabled=self.manual_payment_capability_enabled,
            ),
        }
        serializer = PaymentSetupStatusSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    @property
    def access_message(self) -> str:
        if self.can_manage_provider_authorization:
            if self.readiness.ready:
                return (
                    "Owners can review the Razorpay connection and run recovery "
                    "actions when access changes."
                )
            return (
                "Owners can connect Razorpay or use recovery actions to restore "
                "Online Payment Readiness."
            )
        return (
            "Operators can view readiness blockers and recovery context, but only "
            "Owners can manage Provider Authorization."
        )

    @property
    def provider_authorization_actions(self) -> list[dict[str, bool | str]]:
        if not self.can_manage_provider_authorization:
            return []

        authorization_state = self.provider_setup.authorization_state
        has_started = authorization_state != ProviderPaymentSetup.AuthorizationState.NOT_STARTED
        has_provider_reference = bool(self.provider_setup.provider_merchant_reference)
        authorized = authorization_state == ProviderPaymentSetup.AuthorizationState.AUTHORIZED
        unhealthy = (
            self.provider_setup.provider_connection_state
            == ProviderPaymentSetup.ProviderConnectionState.UNHEALTHY
        )
        needs_recovery = authorization_state in {
            ProviderPaymentSetup.AuthorizationState.ACTION_REQUIRED,
            ProviderPaymentSetup.AuthorizationState.REVOKED,
        }

        return [
            {
                "id": "connect",
                "label": "Connect with Razorpay",
                "description": ("Start OAuth Provider Authorization on Razorpay-hosted screens."),
                "status_label": "Available" if not authorized else "Connected",
                "enabled": not authorized,
                "tone": "primary",
            },
            {
                "id": "retry",
                "label": "Retry authorization",
                "description": (
                    "Refresh Provider Authorization after revoked or unhealthy access."
                ),
                "status_label": ("Recovery" if needs_recovery or unhealthy else "No action"),
                "enabled": needs_recovery or unhealthy,
                "tone": "secondary",
            },
            {
                "id": "disconnect",
                "label": "Disconnect Razorpay",
                "description": (
                    "Remove active Provider Authorization while preserving payment records."
                ),
                "status_label": "Available" if has_started else "Not connected",
                "enabled": has_started,
                "tone": "danger",
            },
            {
                "id": "replace",
                "label": "Replace account",
                "description": (
                    "Authorize a different connected provider account for future payments."
                ),
                "status_label": (
                    "Available" if authorized or has_provider_reference else "No account"
                ),
                "enabled": authorized or has_provider_reference,
                "tone": "secondary",
            },
            {
                "id": "test_connection",
                "label": "Test connection",
                "description": (
                    "Run a Provider Connection Test without creating bookings or ledger entries."
                ),
                "status_label": "Available" if authorized else "Authorization needed",
                "enabled": authorized,
                "tone": "secondary",
            },
        ]


def payment_setup_readiness_read_model(
    organizer: Organizer,
    *,
    role: OrganizerRole | None = None,
    can_manage_provider_authorization: bool | None = None,
) -> PaymentSetupReadinessReadModel:
    ensure_payment_setup_records(organizer)
    if can_manage_provider_authorization is None:
        can_manage_provider_authorization = (
            role.can_manage_payment_setup if role is not None else False
        )
    return PaymentSetupReadinessReadModel(
        organizer=organizer,
        payout_account=organizer.payout_account,
        provider_setup=organizer.provider_payment_setup,
        readiness=online_payment_readiness_for_organizer(organizer),
        payment_method_readiness=PaymentMethodReadinessDecision(
            provider_method=provider_payment_method_readiness(organizer),
            manual_method=manual_payment_method_readiness(
                ManualPaymentMethodReadinessFacts(
                    manual_payment_instructions_present=has_ready_manual_payment_instructions(
                        organizer
                    ),
                    booking_availability_open=True,
                    capacity_available=True,
                )
            ),
        ),
        manual_payment_capability_enabled=is_manual_payment_capability_enabled(organizer),
        can_manage_provider_authorization=can_manage_provider_authorization,
        can_manage_manual_payment_instructions=can_manage_provider_authorization,
    )


def payment_setup_status_payload(
    organizer: Organizer,
    *,
    role: OrganizerRole | None = None,
    can_manage_provider_authorization: bool | None = None,
) -> dict:
    return payment_setup_readiness_read_model(
        organizer,
        role=role,
        can_manage_provider_authorization=can_manage_provider_authorization,
    ).to_payload()
