from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from organizer_payments.models import ProviderPaymentSetup
from organizer_payments.online_payment_readiness import online_payment_readiness_for_organizer
from organizer_payments.provider_credentials import (
    SensitiveProviderCredentialNotFound,
    SensitiveProviderCredentialStore,
)
from organizers.models import Organizer
from trip_bookings.lifecycle import (
    required_amount_to_reserve_inr as lifecycle_required_amount_to_reserve_inr,
)
from trip_bookings.models import Booking
from trip_payments.financial_ledger import (
    booking_reconciliation,
    collected_ledger_amount_inr,
    record_financial_ledger_event,
)
from trip_payments.models import PaymentAttempt, PaymentException, ProviderPayment
from trip_payments.payment_exceptions import (
    record_late_confirmed_payment_exception,
    record_mismatched_provider_payment_exception,
)
from trip_payments.provider_adapters import (
    ProviderCheckoutAdapter,
    ProviderCheckoutAdapterError,
    ProviderCheckoutSignatureRequest,
    ProviderPaymentConfirmation,
    ProviderPaymentConfirmationAdapter,
    ProviderPaymentFetchRequest,
    checkout_adapter_for_provider,
    checkout_request_for_payment_attempt,
)
from trip_payments.reservation_rules import (
    bookable_capacity_available_for_reservation,
    reserve_booking_if_ready,
)
from trip_payments.seat_holds import (
    create_seat_hold_for_payment_attempt,
    release_active_seat_holds_for_booking,
    release_seat_hold_for_payment_attempt,
)
from trips.booking_availability import public_booking_gate_decision
from trips.models import Trip

ACTIVE_PAYMENT_ATTEMPT_STATUSES = (
    PaymentAttempt.Status.PENDING,
    PaymentAttempt.Status.CONFIRMING,
)


@dataclass(frozen=True)
class ProviderCheckoutSession:
    payment_attempt: PaymentAttempt
    checkout_payload: dict


@dataclass(frozen=True)
class BrowserCheckoutSuccessResult:
    payment_attempt: PaymentAttempt
    provider_payment: ProviderPayment | None = None
    payment_exception: PaymentException | None = None
    provider_state_verified: bool = False


@dataclass(frozen=True)
class ProviderPaymentIngestionResult:
    payment_attempt: PaymentAttempt | None = None
    provider_payment: ProviderPayment | None = None
    payment_exception: PaymentException | None = None
    ignored_reason: str = ""

    @property
    def confirmation_result(self) -> PaymentAttempt | ProviderPayment | PaymentException | None:
        return self.payment_exception or self.provider_payment or self.payment_attempt


def create_public_reservation_checkout(
    booking: Booking,
    *,
    provider_adapter: ProviderCheckoutAdapter | None = None,
) -> ProviderCheckoutSession:
    return _create_provider_checkout(
        booking,
        purpose=PaymentAttempt.Purpose.RESERVATION,
        provider_adapter=provider_adapter,
    )


def create_balance_payment_checkout(
    booking: Booking,
    *,
    provider_adapter: ProviderCheckoutAdapter | None = None,
) -> ProviderCheckoutSession:
    return _create_provider_checkout(
        booking,
        purpose=PaymentAttempt.Purpose.BALANCE,
        provider_adapter=provider_adapter,
    )


def _create_provider_checkout(
    booking: Booking,
    *,
    purpose: str,
    provider_adapter: ProviderCheckoutAdapter | None,
) -> ProviderCheckoutSession:
    with transaction.atomic():
        booking = (
            Booking.objects.select_for_update()
            .select_related(
                "trip",
                "trip__organizer",
                "trip__organizer__provider_payment_setup",
                "trip__payment_schedule",
            )
            .prefetch_related("traveler_slots__package", "ledger_entries")
            .get(pk=booking.pk)
        )
        Trip.objects.select_for_update().get(pk=booking.trip_id)
        if purpose == PaymentAttempt.Purpose.RESERVATION:
            _supersede_active_payment_attempts(booking, purpose=purpose)
            amount_inr = _amount_for_checkout(booking, purpose=purpose)
        else:
            amount_inr = _amount_for_checkout(booking, purpose=purpose)
            _supersede_active_payment_attempts(booking, purpose=purpose)
        provider_setup = _connected_provider_account_for_checkout(booking.trip.organizer)
        credential = _active_provider_checkout_credential(
            booking.trip.organizer,
            provider_setup,
        )
        payment_attempt = PaymentAttempt.objects.create(
            booking=booking,
            provider=provider_setup.provider,
            purpose=purpose,
            amount_inr=amount_inr,
            status=PaymentAttempt.Status.PENDING,
        )
        if purpose == PaymentAttempt.Purpose.RESERVATION:
            create_seat_hold_for_payment_attempt(payment_attempt)
        adapter = provider_adapter or checkout_adapter_for_provider(provider_setup.provider)
        try:
            checkout = adapter.create_checkout(
                checkout_request_for_payment_attempt(payment_attempt, provider_setup, credential)
            )
        except ProviderCheckoutAdapterError as exc:
            raise ValidationError("Server-side provider order creation failed.") from exc
        payment_attempt.provider_attempt_reference = checkout.provider_order_reference
        payment_attempt.save(update_fields=["provider_attempt_reference", "updated_at"])
        payment_attempt.checkout_payload = checkout.checkout_payload
        return ProviderCheckoutSession(
            payment_attempt=payment_attempt,
            checkout_payload=checkout.checkout_payload,
        )


def record_frontend_checkout_success(payment_attempt: PaymentAttempt) -> PaymentAttempt:
    with transaction.atomic():
        payment_attempt = PaymentAttempt.objects.select_for_update().get(pk=payment_attempt.pk)
        if payment_attempt.status in {
            PaymentAttempt.Status.FAILED,
            PaymentAttempt.Status.SUPERSEDED,
        }:
            raise ValidationError("Inactive Payment Attempts cannot be marked as confirming.")
        if payment_attempt.status == PaymentAttempt.Status.CONFIRMED:
            return payment_attempt

        if payment_attempt.checkout_succeeded_at is None:
            payment_attempt.checkout_succeeded_at = timezone.now()
        payment_attempt.status = PaymentAttempt.Status.CONFIRMING
        payment_attempt.save(
            update_fields=["status", "checkout_succeeded_at", "updated_at"],
        )
        return payment_attempt


def fail_payment_attempt(
    payment_attempt: PaymentAttempt,
    *,
    failure_reason: str = "",
) -> PaymentAttempt:
    with transaction.atomic():
        payment_attempt = PaymentAttempt.objects.select_for_update().get(pk=payment_attempt.pk)
        if payment_attempt.status == PaymentAttempt.Status.CONFIRMED:
            raise ValidationError("Confirmed Payment Attempts cannot be failed.")
        if payment_attempt.status == PaymentAttempt.Status.SUPERSEDED:
            return payment_attempt
        payment_attempt.status = PaymentAttempt.Status.FAILED
        payment_attempt.failure_reason = failure_reason
        payment_attempt.save(update_fields=["status", "failure_reason", "updated_at"])
        release_seat_hold_for_payment_attempt(payment_attempt)
        return payment_attempt


def process_browser_checkout_success(
    payment_attempt: PaymentAttempt,
    *,
    provider_payment_reference: str,
    provider_attempt_reference: str,
    checkout_signature: str,
    provider_adapter: ProviderPaymentConfirmationAdapter | None = None,
) -> BrowserCheckoutSuccessResult:
    payment_attempt = (
        PaymentAttempt.objects.select_related(
            "booking",
            "booking__trip",
            "booking__trip__organizer",
            "booking__trip__organizer__provider_payment_setup",
        )
        .only(
            "id",
            "booking_id",
            "provider",
            "purpose",
            "status",
            "amount_inr",
            "provider_attempt_reference",
            "checkout_succeeded_at",
            "booking__id",
            "booking__trip_id",
            "booking__trip__organizer_id",
        )
        .get(pk=payment_attempt.pk)
    )
    provider_payment_reference = provider_payment_reference.strip()
    provider_attempt_reference = provider_attempt_reference.strip()
    checkout_signature = checkout_signature.strip()
    if not payment_attempt.provider_attempt_reference.strip():
        raise ValidationError("Payment Attempt does not have a provider order reference.")
    if provider_attempt_reference != payment_attempt.provider_attempt_reference:
        raise ValidationError("Checkout success does not match the Payment Attempt order.")
    if not provider_payment_reference or not checkout_signature:
        raise ValidationError("Checkout success requires provider payment id and signature.")

    organizer = payment_attempt.booking.trip.organizer
    provider_setup = _connected_provider_account_for_checkout(organizer)
    if provider_setup.provider != payment_attempt.provider:
        raise ValidationError("Connected Provider Account does not match the Payment Attempt.")
    credential = _active_provider_checkout_credential(organizer, provider_setup)
    adapter = provider_adapter or checkout_adapter_for_provider(provider_setup.provider)
    signature_request = ProviderCheckoutSignatureRequest(
        provider=payment_attempt.provider,
        provider_order_reference=payment_attempt.provider_attempt_reference,
        provider_payment_reference=provider_payment_reference,
        checkout_signature=checkout_signature,
        credential_kind=credential.credential_kind,
        secret_payload=dict(credential.secret_payload),
    )
    try:
        signature_valid = adapter.verify_checkout_signature(signature_request)
    except ProviderCheckoutAdapterError as exc:
        raise ValidationError("Checkout signature verification could not be completed.") from exc
    if not signature_valid:
        raise ValidationError("Checkout signature verification failed.")

    payment_attempt = record_frontend_checkout_success(payment_attempt)
    try:
        fetched_confirmation = adapter.fetch_payment(
            ProviderPaymentFetchRequest(
                provider=payment_attempt.provider,
                provider_payment_reference=provider_payment_reference,
                credential_kind=credential.credential_kind,
                secret_payload=dict(credential.secret_payload),
            )
        )
    except ProviderCheckoutAdapterError:
        return BrowserCheckoutSuccessResult(payment_attempt=payment_attempt)

    ingestion_result = ingest_provider_payment_confirmation(
        fetched_confirmation,
        payment_attempt=payment_attempt,
        source="browser_checkout_success",
    )
    payment_attempt.refresh_from_db()
    return BrowserCheckoutSuccessResult(
        payment_attempt=payment_attempt,
        provider_payment=ingestion_result.provider_payment,
        payment_exception=ingestion_result.payment_exception,
        provider_state_verified=True,
    )


def ingest_provider_payment_confirmation(
    confirmation: ProviderPaymentConfirmation,
    *,
    payment_attempt: PaymentAttempt | None = None,
    source: str = "",
) -> ProviderPaymentIngestionResult:
    del source
    payment_attempt = payment_attempt or payment_attempt_for_confirmation(confirmation)
    if payment_attempt is None:
        return ProviderPaymentIngestionResult(ignored_reason="payment_attempt_not_found")

    if not confirmation.is_captured:
        if confirmation.status == "authorized" and payment_attempt.is_active:
            payment_attempt = record_frontend_checkout_success(payment_attempt)
        return ProviderPaymentIngestionResult(
            payment_attempt=payment_attempt,
            ignored_reason="payment_not_captured",
        )

    confirmation_result = confirm_provider_payment(
        payment_attempt,
        payment_attempt_id=confirmation.payment_attempt_id,
        booking_id=confirmation.booking_id,
        provider=confirmation.provider,
        purpose=confirmation.purpose,
        provider_attempt_reference=confirmation.provider_attempt_reference,
        provider_payment_reference=confirmation.provider_payment_reference,
        amount_inr=confirmation.amount_inr,
        provider_fee_amount_inr=confirmation.provider_fee_amount_inr,
        provider_net_settlement_amount_inr=confirmation.provider_net_settlement_amount_inr,
        require_reported_metadata=True,
    )
    if isinstance(confirmation_result, ProviderPayment):
        return ProviderPaymentIngestionResult(
            payment_attempt=payment_attempt,
            provider_payment=confirmation_result,
        )
    return ProviderPaymentIngestionResult(
        payment_attempt=payment_attempt,
        payment_exception=confirmation_result,
        provider_payment=confirmation_result.provider_payment,
    )


def confirm_provider_payment(
    payment_attempt: PaymentAttempt,
    *,
    provider_payment_reference: str,
    amount_inr: int | None = None,
    provider_fee_amount_inr: int | None = None,
    provider_net_settlement_amount_inr: int | None = None,
    payment_attempt_id: int | None = None,
    booking_id: int | None = None,
    provider: str | None = None,
    provider_attempt_reference: str | None = None,
    purpose: str | None = None,
    require_reported_metadata: bool = False,
) -> ProviderPayment | PaymentException:
    with transaction.atomic():
        payment_attempt = (
            PaymentAttempt.objects.select_for_update()
            .select_related("booking", "booking__trip", "booking__trip__payment_schedule")
            .get(pk=payment_attempt.pk)
        )
        booking = (
            Booking.objects.select_for_update()
            .select_related("trip", "trip__organizer", "trip__payment_schedule")
            .prefetch_related("traveler_slots__package")
            .get(pk=payment_attempt.booking_id)
        )
        provider_payment_reference = provider_payment_reference.strip()
        confirmation = {
            "payment_attempt_id": _reported_or_expected_confirmation_value(
                payment_attempt_id,
                payment_attempt.id,
                require_reported_metadata=require_reported_metadata,
            ),
            "booking_id": _reported_or_expected_confirmation_value(
                booking_id,
                booking.id,
                require_reported_metadata=require_reported_metadata,
            ),
            "provider": _reported_or_expected_confirmation_value(
                provider,
                payment_attempt.provider,
                require_reported_metadata=require_reported_metadata,
            ),
            "provider_attempt_reference": _reported_or_expected_confirmation_value(
                provider_attempt_reference,
                payment_attempt.provider_attempt_reference,
                require_reported_metadata=require_reported_metadata,
            ),
            "purpose": _reported_or_expected_confirmation_value(
                purpose,
                payment_attempt.purpose,
                require_reported_metadata=require_reported_metadata,
            ),
            "amount_inr": _reported_or_expected_confirmation_value(
                amount_inr,
                payment_attempt.amount_inr,
                require_reported_metadata=require_reported_metadata,
            ),
        }
        _validate_provider_payment_confirmation_basics(
            provider_payment_reference=provider_payment_reference,
            provider_attempt_reference=confirmation["provider_attempt_reference"],
            amount_inr=confirmation["amount_inr"],
            allow_missing_provider_attempt_reference=require_reported_metadata,
        )

        existing_by_reference = (
            ProviderPayment.objects.select_for_update()
            .select_related("payment_attempt", "booking")
            .filter(provider_payment_reference=provider_payment_reference)
            .first()
        )
        if existing_by_reference is not None:
            duplicate_mismatch_reasons = _existing_provider_payment_mismatch_reasons(
                existing_by_reference,
                payment_attempt,
                confirmation,
            )
            if duplicate_mismatch_reasons:
                return record_mismatched_provider_payment_exception(
                    payment_attempt,
                    provider_payment_reference=provider_payment_reference,
                    confirmation=confirmation,
                    mismatch_reasons=duplicate_mismatch_reasons,
                    provider_payment=existing_by_reference,
                )
            release_seat_hold_for_payment_attempt(payment_attempt)
            return existing_by_reference

        existing_for_attempt = getattr(payment_attempt, "provider_payment", None)
        if existing_for_attempt is not None:
            existing_attempt_mismatch_reasons = _existing_provider_payment_mismatch_reasons(
                existing_for_attempt,
                payment_attempt,
                confirmation,
            )
            if existing_for_attempt.provider_payment_reference != provider_payment_reference:
                existing_attempt_mismatch_reasons.append("provider_payment_reference")
            if existing_attempt_mismatch_reasons:
                return record_mismatched_provider_payment_exception(
                    payment_attempt,
                    provider_payment_reference=provider_payment_reference,
                    confirmation=confirmation,
                    mismatch_reasons=existing_attempt_mismatch_reasons,
                    provider_payment=existing_for_attempt,
                )
            release_seat_hold_for_payment_attempt(payment_attempt)
            return existing_for_attempt

        mismatch_reasons = _provider_confirmation_mismatch_reasons(
            payment_attempt,
            confirmation,
        )
        if not _payment_attempt_uses_live_provider_mode(payment_attempt):
            mismatch_reasons.append("provider_mode")
        if payment_attempt.status in {
            PaymentAttempt.Status.FAILED,
            PaymentAttempt.Status.SUPERSEDED,
        }:
            mismatch_reasons.append("inactive_payment_attempt")
        if mismatch_reasons:
            return record_mismatched_provider_payment_exception(
                payment_attempt,
                provider_payment_reference=provider_payment_reference,
                confirmation=confirmation,
                mismatch_reasons=mismatch_reasons,
            )

        provider_payment = ProviderPayment.objects.create(
            booking=booking,
            payment_attempt=payment_attempt,
            provider=payment_attempt.provider,
            amount_inr=confirmation["amount_inr"],
            provider_fee_amount_inr=provider_fee_amount_inr,
            provider_net_settlement_amount_inr=provider_net_settlement_amount_inr,
            provider_payment_reference=provider_payment_reference,
        )
        record_financial_ledger_event(provider_payment)
        payment_attempt.status = PaymentAttempt.Status.CONFIRMED
        payment_attempt.save()
        booking_was_post_reservation = booking.booking_state in {
            Booking.BookingState.RESERVED,
            Booking.BookingState.CONFIRMED,
            Booking.BookingState.COMPLETED,
        }
        if (
            payment_attempt.purpose == PaymentAttempt.Purpose.RESERVATION
            and booking.booking_state == Booking.BookingState.DRAFT
            and collected_ledger_amount_inr(booking) >= required_amount_to_reserve_inr(booking)
            and not bookable_capacity_available_for_reservation(
                booking,
                payment_attempt=payment_attempt,
            )
        ):
            payment_exception = record_late_confirmed_payment_exception(
                provider_payment,
                payment_attempt=payment_attempt,
            )
            release_seat_hold_for_payment_attempt(payment_attempt)
            return payment_exception

        booking_became_reserved = False
        if payment_attempt.purpose == PaymentAttempt.Purpose.RESERVATION:
            booking_became_reserved = reserve_booking_if_ready(
                booking,
                payment_attempt=payment_attempt,
                provider_payment=provider_payment,
            )
            _reserve_pending_traveler_additions_if_ready(booking)
            release_active_seat_holds_for_booking(booking)
            release_seat_hold_for_payment_attempt(payment_attempt)
        if not booking_became_reserved and booking_was_post_reservation:
            _send_provider_payment_acknowledgement(provider_payment)
        return provider_payment


def payment_attempt_for_confirmation(
    confirmation: ProviderPaymentConfirmation,
) -> PaymentAttempt | None:
    attempts = PaymentAttempt.objects.select_related(
        "booking",
        "booking__trip",
        "booking__trip__organizer",
    ).filter(provider=confirmation.provider)
    provider_attempt_reference = confirmation.provider_attempt_reference.strip()
    if provider_attempt_reference:
        payment_attempt = attempts.filter(
            provider_attempt_reference=provider_attempt_reference,
        ).first()
        if payment_attempt is not None:
            return payment_attempt
    if confirmation.payment_attempt_id is not None:
        return attempts.filter(pk=confirmation.payment_attempt_id).first()
    return None


def required_amount_to_reserve_inr(booking: Booking) -> int:
    return lifecycle_required_amount_to_reserve_inr(booking)


def current_balance_due_inr(booking: Booking) -> int:
    return booking_reconciliation(booking).due_inr


def _amount_for_checkout(booking: Booking, *, purpose: str) -> int:
    if purpose == PaymentAttempt.Purpose.RESERVATION:
        _validate_booking_can_attempt_provider_payment(booking)
        return required_amount_to_reserve_inr(booking)
    if purpose == PaymentAttempt.Purpose.BALANCE:
        amount_inr = current_balance_due_inr(booking)
        _validate_balance_payment_link_available(booking, amount_inr=amount_inr)
        return amount_inr
    raise ValidationError("Payment Attempt purpose is not supported.")


def _validate_provider_payment_confirmation_basics(
    *,
    provider_payment_reference: str,
    provider_attempt_reference: str | None,
    amount_inr: int | None,
    allow_missing_provider_attempt_reference: bool = False,
) -> None:
    if not provider_payment_reference:
        raise ValidationError("Provider Payment Confirmation requires provider payment reference.")
    if (
        not allow_missing_provider_attempt_reference
        and not str(provider_attempt_reference or "").strip()
    ):
        raise ValidationError("Provider Payment Confirmation requires provider order reference.")
    if amount_inr is None or amount_inr <= 0:
        raise ValidationError("Provider Payment amount must be positive.")


def _reported_or_expected_confirmation_value(
    reported_value,
    expected_value,
    *,
    require_reported_metadata: bool,
):
    if require_reported_metadata:
        return reported_value
    return expected_value if reported_value is None else reported_value


def _provider_confirmation_mismatch_reasons(
    payment_attempt: PaymentAttempt,
    confirmation: dict,
) -> list[str]:
    mismatch_reasons = []
    if confirmation["payment_attempt_id"] != payment_attempt.id:
        mismatch_reasons.append("payment_attempt")
    if confirmation["booking_id"] != payment_attempt.booking_id:
        mismatch_reasons.append("booking")
    if confirmation["provider"] != payment_attempt.provider:
        mismatch_reasons.append("provider")
    if confirmation["purpose"] != payment_attempt.purpose:
        mismatch_reasons.append("purpose")
    if confirmation["provider_attempt_reference"] != payment_attempt.provider_attempt_reference:
        mismatch_reasons.append("provider_order")
    if confirmation["amount_inr"] != payment_attempt.amount_inr:
        mismatch_reasons.append("amount")
    return mismatch_reasons


def _payment_attempt_uses_live_provider_mode(payment_attempt: PaymentAttempt) -> bool:
    provider_setup = getattr(
        payment_attempt.booking.trip.organizer,
        "provider_payment_setup",
        None,
    )
    return (
        provider_setup is not None
        and provider_setup.provider == payment_attempt.provider
        and provider_setup.provider_mode == ProviderPaymentSetup.ProviderMode.LIVE
    )


def _existing_provider_payment_mismatch_reasons(
    provider_payment: ProviderPayment,
    payment_attempt: PaymentAttempt,
    confirmation: dict,
) -> list[str]:
    mismatch_reasons = []
    if provider_payment.payment_attempt_id != payment_attempt.id:
        mismatch_reasons.append("provider_payment_reference")
    if provider_payment.booking_id != confirmation["booking_id"]:
        mismatch_reasons.append("booking")
    if provider_payment.provider != confirmation["provider"]:
        mismatch_reasons.append("provider")
    if provider_payment.payment_attempt.purpose != confirmation["purpose"]:
        mismatch_reasons.append("purpose")
    if provider_payment.amount_inr != confirmation["amount_inr"]:
        mismatch_reasons.append("amount")
    return mismatch_reasons


def _validate_booking_can_attempt_provider_payment(booking: Booking) -> None:
    if booking.booking_state != Booking.BookingState.DRAFT:
        raise ValidationError("Only Draft Bookings can start public checkout.")

    requested_seats = booking.traveler_slot_count
    if requested_seats <= 0:
        raise ValidationError("Booking must have Traveler Slots before public checkout.")

    readiness = public_booking_gate_decision(booking.trip, requested_seats=requested_seats)
    if not readiness.ready:
        raise ValidationError(
            f"Public checkout blocked by Public Booking Gate: {readiness.reason_code}."
        )


def _validate_balance_payment_link_available(
    booking: Booking,
    *,
    amount_inr: int,
) -> None:
    if booking.booking_state == Booking.BookingState.DRAFT:
        raise ValidationError("Balance Payment Links are available after reservation.")
    if booking.booking_state == Booking.BookingState.CANCELLED:
        raise ValidationError("Cancelled Bookings cannot start Balance Payment Attempts.")
    if amount_inr <= 0:
        raise ValidationError("No balance is currently due.")
    readiness = online_payment_readiness_for_organizer(booking.trip.organizer)
    if not readiness.ready:
        raise ValidationError(f"Online Payment Readiness is blocked: {readiness.message}")


def _connected_provider_account_for_checkout(
    organizer: Organizer,
) -> ProviderPaymentSetup:
    try:
        provider_setup = organizer.provider_payment_setup
    except ProviderPaymentSetup.DoesNotExist as exc:
        raise ValidationError(
            "Connected Provider Account is required before provider checkout."
        ) from exc

    if not provider_setup.provider_merchant_reference.strip():
        raise ValidationError(
            "Connected Provider Account reference is required before provider checkout."
        )
    return provider_setup


def _active_provider_checkout_credential(
    organizer: Organizer,
    provider_setup: ProviderPaymentSetup,
):
    try:
        credential = SensitiveProviderCredentialStore().retrieve_active_credential(
            organizer=organizer,
            provider=provider_setup.provider,
            provider_mode=provider_setup.provider_mode,
        )
    except SensitiveProviderCredentialNotFound as exc:
        raise ValidationError(
            "Active Sensitive Provider Credentials are required for provider order creation."
        ) from exc

    if credential.provider_account_reference != provider_setup.provider_merchant_reference:
        raise ValidationError(
            "Active Sensitive Provider Credentials do not match the Connected Provider Account."
        )
    return credential


def _supersede_active_payment_attempts(
    booking: Booking,
    *,
    purpose: str,
) -> int:
    active_attempts = list(
        PaymentAttempt.objects.select_for_update().filter(
            booking=booking,
            purpose=purpose,
            status__in=ACTIVE_PAYMENT_ATTEMPT_STATUSES,
        )
    )
    for active_attempt in active_attempts:
        active_attempt.status = PaymentAttempt.Status.SUPERSEDED
        active_attempt.failure_reason = "Superseded by a newer Payment Attempt."
        active_attempt.save(update_fields=["status", "failure_reason", "updated_at"])
        release_seat_hold_for_payment_attempt(active_attempt)
    return len(active_attempts)


def _send_provider_payment_acknowledgement(provider_payment: ProviderPayment) -> None:
    from organizers.services import send_provider_payment_acknowledgement

    send_provider_payment_acknowledgement(provider_payment)


def _reserve_pending_traveler_additions_if_ready(booking: Booking) -> None:
    from organizers.services import reserve_pending_traveler_additions_if_ready

    reserve_pending_traveler_additions_if_ready(booking)
