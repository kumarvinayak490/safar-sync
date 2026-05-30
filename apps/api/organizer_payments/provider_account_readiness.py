from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from organizer_payments.online_payment_readiness import (
    OnlinePaymentReadinessDecision,
    online_payment_readiness_for_organizer,
)
from organizers.models import Organizer, PayoutAccount, ProviderPaymentSetup, Trip


@dataclass(frozen=True)
class ReadinessRegressionResult:
    previous_readiness: OnlinePaymentReadinessDecision
    current_readiness: OnlinePaymentReadinessDecision
    closed_public_booking_trips: int

    @property
    def regressed(self) -> bool:
        return self.previous_readiness.ready and not self.current_readiness.ready

    def to_payload(self) -> dict[str, bool | int | str]:
        return {
            "regressed": self.regressed,
            "previous_online_payment_readiness_ready": self.previous_readiness.ready,
            "current_online_payment_readiness_ready": self.current_readiness.ready,
            "current_online_payment_readiness_blocker_code": (self.current_readiness.blocker_code),
            "closed_public_booking_trips": self.closed_public_booking_trips,
        }


def support_confirm_settlement_readiness(
    *,
    organizer: Organizer,
    actor,
    notes: str = "",
) -> ReadinessRegressionResult:
    if actor is None or not getattr(actor, "is_staff", False):
        raise PermissionDenied("Only TripOS staff can support-confirm Settlement Readiness.")

    with transaction.atomic():
        previous_readiness = online_payment_readiness_for_organizer(organizer)
        payout_account = _locked_payout_account(organizer)
        provider_setup = _locked_provider_payment_setup(organizer)
        payout_account.status = PayoutAccount.Status.ACTIVE
        payout_account.settlement_readiness_source = (
            PayoutAccount.SettlementReadinessSource.SUPPORT_CONFIRMED
        )
        payout_account.support_confirmed_at = timezone.now()
        payout_account.support_confirmed_by = actor
        payout_account.support_confirmation_notes = notes.strip()
        if (
            not payout_account.provider_account_reference
            and provider_setup.provider_merchant_reference
        ):
            payout_account.provider_account_reference = provider_setup.provider_merchant_reference
        payout_account.save(
            update_fields=[
                "status",
                "settlement_readiness_source",
                "support_confirmed_at",
                "support_confirmed_by",
                "support_confirmation_notes",
                "provider_account_reference",
                "updated_at",
            ]
        )
        current_readiness = online_payment_readiness_for_organizer(organizer)
        closed_trips = _close_public_booking_if_readiness_regressed(
            organizer=organizer,
            previous_readiness=previous_readiness,
            current_readiness=current_readiness,
        )
    return ReadinessRegressionResult(
        previous_readiness=previous_readiness,
        current_readiness=current_readiness,
        closed_public_booking_trips=closed_trips,
    )


def record_provider_derived_settlement_readiness(
    *,
    organizer: Organizer,
    status: str,
    provider_account_reference: str = "",
    notes: str = "",
) -> ReadinessRegressionResult:
    if status not in PayoutAccount.Status.values:
        raise ValidationError("Settlement Readiness status is not supported.")

    with transaction.atomic():
        previous_readiness = online_payment_readiness_for_organizer(organizer)
        payout_account = _locked_payout_account(organizer)
        preserves_support_confirmation = (
            payout_account.settlement_readiness_source
            == PayoutAccount.SettlementReadinessSource.SUPPORT_CONFIRMED
            and payout_account.status == PayoutAccount.Status.ACTIVE
            and status != PayoutAccount.Status.ACTIVE
        )
        if not preserves_support_confirmation:
            payout_account.status = status
            payout_account.settlement_readiness_source = (
                PayoutAccount.SettlementReadinessSource.PROVIDER_DERIVED
            )
            payout_account.support_confirmed_at = None
            payout_account.support_confirmed_by = None
            payout_account.support_confirmation_notes = ""
        payout_account.notes = notes.strip()
        if provider_account_reference.strip():
            payout_account.provider_account_reference = provider_account_reference.strip()
        update_fields = ["notes", "provider_account_reference", "updated_at"]
        if not preserves_support_confirmation:
            update_fields.extend(
                [
                    "status",
                    "settlement_readiness_source",
                    "support_confirmed_at",
                    "support_confirmed_by",
                    "support_confirmation_notes",
                ]
            )
        payout_account.save(update_fields=update_fields)
        current_readiness = online_payment_readiness_for_organizer(organizer)
        closed_trips = _close_public_booking_if_readiness_regressed(
            organizer=organizer,
            previous_readiness=previous_readiness,
            current_readiness=current_readiness,
        )
    return ReadinessRegressionResult(
        previous_readiness=previous_readiness,
        current_readiness=current_readiness,
        closed_public_booking_trips=closed_trips,
    )


def record_provider_payment_capability(
    *,
    organizer: Organizer,
    enabled: bool,
) -> ReadinessRegressionResult:
    with transaction.atomic():
        previous_readiness = online_payment_readiness_for_organizer(organizer)
        provider_setup = _locked_provider_payment_setup(organizer)
        provider_setup.provider_payment_capability_enabled = enabled
        provider_setup.save(update_fields=["provider_payment_capability_enabled", "updated_at"])
        current_readiness = online_payment_readiness_for_organizer(organizer)
        closed_trips = _close_public_booking_if_readiness_regressed(
            organizer=organizer,
            previous_readiness=previous_readiness,
            current_readiness=current_readiness,
        )
    return ReadinessRegressionResult(
        previous_readiness=previous_readiness,
        current_readiness=current_readiness,
        closed_public_booking_trips=closed_trips,
    )


def _close_public_booking_if_readiness_regressed(
    *,
    organizer: Organizer,
    previous_readiness: OnlinePaymentReadinessDecision,
    current_readiness: OnlinePaymentReadinessDecision,
) -> int:
    if not previous_readiness.ready or current_readiness.ready:
        return 0
    return (
        Trip.objects.select_for_update()
        .filter(
            organizer=organizer,
            booking_availability=Trip.BookingAvailability.OPEN,
        )
        .update(
            booking_availability=Trip.BookingAvailability.CLOSED,
            updated_at=timezone.now(),
        )
    )


def _locked_payout_account(organizer: Organizer) -> PayoutAccount:
    payout_account, _ = PayoutAccount.objects.select_for_update().get_or_create(organizer=organizer)
    return payout_account


def _locked_provider_payment_setup(organizer: Organizer) -> ProviderPaymentSetup:
    provider_setup, _ = ProviderPaymentSetup.objects.select_for_update().get_or_create(
        organizer=organizer
    )
    return provider_setup
