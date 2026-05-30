from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from organizer_payments.models import ProviderPaymentSetup
from organizer_payments.provider_authorization import (
    ProviderAuthorizationLifecycleResult,
    record_provider_authorization_revoked,
)
from organizers.models import Organizer
from trip_payments.models import (
    PaymentAttempt,
    PaymentException,
    ProviderPayment,
    ProviderWebhookEvent,
)
from trip_payments.provider_adapters import (
    ProviderCheckoutAdapterError,
    ProviderPaymentConfirmation,
    ProviderWebhookAdapter,
    ProviderWebhookSignatureRequest,
    webhook_adapter_for_provider,
)
from trip_payments.provider_payment_lifecycle import (
    ingest_provider_payment_confirmation,
)

RAZORPAY_PAYMENT_EVENTS = {
    "payment.authorized",
    "payment.captured",
}

RAZORPAY_AUTHORIZATION_REVOKED_EVENTS = {
    "account.authorization.revoked",
    "app.authorization.revoked",
    "application.authorization.revoked",
    "application.deauthorized",
    "merchant.authorization.revoked",
    "oauth.authorization.revoked",
}


@dataclass(frozen=True)
class ProviderWebhookProcessingResult:
    webhook_event: ProviderWebhookEvent
    duplicate: bool = False
    payment_attempt: PaymentAttempt | None = None
    provider_payment: ProviderPayment | None = None
    payment_exception: PaymentException | None = None
    lifecycle_result: ProviderAuthorizationLifecycleResult | None = None


def process_razorpay_webhook(
    *,
    body: bytes,
    signature: str,
    adapter: ProviderWebhookAdapter | None = None,
) -> ProviderWebhookProcessingResult:
    provider = ProviderPaymentSetup.Provider.RAZORPAY
    webhook_adapter = adapter or webhook_adapter_for_provider(provider)
    _verify_razorpay_webhook_signature(
        body=body,
        signature=signature,
        adapter=webhook_adapter,
    )
    payload = _decode_verified_webhook_body(body)
    event_reference = _provider_event_reference(payload, body=body)
    event_type = _event_type(payload)
    webhook_event, already_recorded = _record_verified_webhook_event(
        provider=provider,
        event_reference=event_reference,
        event_type=event_type,
        payload=payload,
    )
    if already_recorded and webhook_event.processed_at is not None:
        return ProviderWebhookProcessingResult(
            webhook_event=webhook_event,
            duplicate=True,
            payment_attempt=webhook_event.payment_attempt,
            provider_payment=webhook_event.provider_payment,
            payment_exception=webhook_event.payment_exception,
        )

    if event_type in RAZORPAY_AUTHORIZATION_REVOKED_EVENTS:
        return _process_authorization_revoked_webhook(webhook_event, payload)

    if event_type in RAZORPAY_PAYMENT_EVENTS:
        return _process_payment_webhook(webhook_event, payload, adapter=webhook_adapter)

    _mark_webhook_event_ignored(webhook_event, reason="unsupported_event_type")
    return ProviderWebhookProcessingResult(webhook_event=webhook_event)


def _verify_razorpay_webhook_signature(
    *,
    body: bytes,
    signature: str,
    adapter: ProviderWebhookAdapter,
) -> None:
    if not body:
        raise ValidationError("Razorpay webhook body is required.")
    webhook_secret = _razorpay_webhook_secret()
    try:
        signature_valid = adapter.verify_webhook_signature(
            ProviderWebhookSignatureRequest(
                provider=ProviderPaymentSetup.Provider.RAZORPAY,
                body=body,
                webhook_signature=signature,
                webhook_secret=webhook_secret,
            )
        )
    except ProviderCheckoutAdapterError as exc:
        raise ValidationError("Razorpay webhook signature verification failed.") from exc
    if not signature_valid:
        raise ValidationError("Razorpay webhook signature verification failed.")


def _razorpay_webhook_secret() -> str:
    webhook_secret = str(getattr(settings, "TRIPOS_RAZORPAY_WEBHOOK_SECRET", "")).strip()
    if not webhook_secret:
        raise ValidationError("Razorpay webhook secret is not configured.")
    return webhook_secret


def _decode_verified_webhook_body(body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("Razorpay webhook body is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValidationError("Razorpay webhook body must be a JSON object.")
    return payload


def _record_verified_webhook_event(
    *,
    provider: str,
    event_reference: str,
    event_type: str,
    payload: dict[str, Any],
) -> tuple[ProviderWebhookEvent, bool]:
    try:
        with transaction.atomic():
            webhook_event = (
                ProviderWebhookEvent.objects.select_for_update()
                .filter(provider=provider, provider_event_reference=event_reference)
                .first()
            )
            if webhook_event is not None:
                return webhook_event, True
            return (
                ProviderWebhookEvent.objects.create(
                    provider=provider,
                    provider_event_reference=event_reference,
                    event_type=event_type,
                    provider_account_reference=_provider_account_reference(payload),
                    raw_payload=payload,
                ),
                False,
            )
    except IntegrityError:
        return (
            ProviderWebhookEvent.objects.get(
                provider=provider,
                provider_event_reference=event_reference,
            ),
            True,
        )


def _process_payment_webhook(
    webhook_event: ProviderWebhookEvent,
    payload: dict[str, Any],
    *,
    adapter: ProviderWebhookAdapter,
) -> ProviderWebhookProcessingResult:
    try:
        confirmation = adapter.payment_confirmation_from_webhook(payload)
    except ProviderCheckoutAdapterError:
        _mark_webhook_event_failed(webhook_event, reason="malformed_payment_payload")
        return ProviderWebhookProcessingResult(webhook_event=webhook_event)

    ingestion_result = ingest_provider_payment_confirmation(
        confirmation,
        source="razorpay_webhook",
    )
    payment_attempt = ingestion_result.payment_attempt
    if payment_attempt is not None:
        payment_attempt.refresh_from_db()
    if ingestion_result.ignored_reason:
        _mark_webhook_event_ignored(
            webhook_event,
            reason=ingestion_result.ignored_reason,
            confirmation=confirmation,
            payment_attempt=payment_attempt,
        )
        return ProviderWebhookProcessingResult(
            webhook_event=webhook_event,
            payment_attempt=payment_attempt,
        )

    provider_payment = ingestion_result.provider_payment
    payment_exception = ingestion_result.payment_exception

    _mark_webhook_event_processed(
        webhook_event,
        processing_status=ProviderWebhookEvent.ProcessingStatus.PROCESSED,
        confirmation=confirmation,
        payment_attempt=payment_attempt,
        provider_payment=provider_payment,
        payment_exception=payment_exception,
    )
    return ProviderWebhookProcessingResult(
        webhook_event=webhook_event,
        payment_attempt=payment_attempt,
        provider_payment=provider_payment,
        payment_exception=payment_exception,
    )


def _process_authorization_revoked_webhook(
    webhook_event: ProviderWebhookEvent,
    payload: dict[str, Any],
) -> ProviderWebhookProcessingResult:
    provider_account_reference = _provider_account_reference(payload)
    organizer = _organizer_for_provider_account_reference(provider_account_reference)
    if organizer is None:
        _mark_webhook_event_ignored(
            webhook_event,
            reason="provider_account_not_found",
            provider_account_reference=provider_account_reference,
        )
        return ProviderWebhookProcessingResult(webhook_event=webhook_event)

    lifecycle_result = record_provider_authorization_revoked(
        organizer=organizer,
        provider=ProviderPaymentSetup.Provider.RAZORPAY,
        provider_account_reference=provider_account_reference,
    )
    _mark_webhook_event_processed(
        webhook_event,
        processing_status=ProviderWebhookEvent.ProcessingStatus.PROCESSED,
        organizer=organizer,
        provider_account_reference=provider_account_reference,
    )
    return ProviderWebhookProcessingResult(
        webhook_event=webhook_event,
        lifecycle_result=lifecycle_result,
    )


def _mark_webhook_event_processed(
    webhook_event: ProviderWebhookEvent,
    *,
    processing_status: str,
    confirmation: ProviderPaymentConfirmation | None = None,
    organizer: Organizer | None = None,
    provider_account_reference: str = "",
    payment_attempt: PaymentAttempt | None = None,
    provider_payment: ProviderPayment | None = None,
    payment_exception: PaymentException | None = None,
) -> None:
    webhook_event.processing_status = processing_status
    webhook_event.ignored_reason = ""
    webhook_event.processed_at = timezone.now()
    if provider_account_reference:
        webhook_event.provider_account_reference = provider_account_reference
    if confirmation is not None:
        webhook_event.provider_attempt_reference = confirmation.provider_attempt_reference
        webhook_event.provider_payment_reference = confirmation.provider_payment_reference
    if payment_attempt is not None:
        webhook_event.payment_attempt = payment_attempt
        webhook_event.booking = payment_attempt.booking
        webhook_event.organizer = payment_attempt.booking.trip.organizer
    if organizer is not None:
        webhook_event.organizer = organizer
    webhook_event.provider_payment = provider_payment
    webhook_event.payment_exception = payment_exception
    webhook_event.save(
        update_fields=[
            "provider_account_reference",
            "provider_attempt_reference",
            "provider_payment_reference",
            "organizer",
            "booking",
            "payment_attempt",
            "provider_payment",
            "payment_exception",
            "processing_status",
            "ignored_reason",
            "processed_at",
            "updated_at",
        ]
    )


def _mark_webhook_event_ignored(
    webhook_event: ProviderWebhookEvent,
    *,
    reason: str,
    confirmation: ProviderPaymentConfirmation | None = None,
    provider_account_reference: str = "",
    payment_attempt: PaymentAttempt | None = None,
) -> None:
    _mark_webhook_event_processed(
        webhook_event,
        processing_status=ProviderWebhookEvent.ProcessingStatus.IGNORED,
        confirmation=confirmation,
        provider_account_reference=provider_account_reference,
        payment_attempt=payment_attempt,
    )
    webhook_event.ignored_reason = reason
    webhook_event.save(update_fields=["ignored_reason", "updated_at"])


def _mark_webhook_event_failed(webhook_event: ProviderWebhookEvent, *, reason: str) -> None:
    webhook_event.processing_status = ProviderWebhookEvent.ProcessingStatus.FAILED
    webhook_event.ignored_reason = reason
    webhook_event.processed_at = timezone.now()
    webhook_event.save(
        update_fields=["processing_status", "ignored_reason", "processed_at", "updated_at"]
    )


def _provider_event_reference(payload: dict[str, Any], *, body: bytes) -> str:
    event_reference = str(payload.get("id") or payload.get("event_id") or "").strip()
    if event_reference:
        return event_reference
    return f"sha256:{hashlib.sha256(body).hexdigest()}"


def _event_type(payload: dict[str, Any]) -> str:
    return str(payload.get("event") or "").strip().lower() or "unknown"


def _provider_account_reference(payload: dict[str, Any]) -> str:
    candidates = [
        payload.get("account_id"),
        payload.get("merchant_id"),
    ]
    payload_wrapper = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    for key in ("account", "merchant"):
        wrapper = payload_wrapper.get(key)
        if isinstance(wrapper, dict):
            entity = wrapper.get("entity")
            if isinstance(entity, dict):
                candidates.extend([entity.get("id"), entity.get("account_id")])
    payment_wrapper = payload_wrapper.get("payment")
    if isinstance(payment_wrapper, dict):
        payment_entity = payment_wrapper.get("entity")
        if isinstance(payment_entity, dict):
            notes = (
                payment_entity.get("notes") if isinstance(payment_entity.get("notes"), dict) else {}
            )
            candidates.extend(
                [
                    payment_entity.get("account_id"),
                    notes.get("tripos_provider_account"),
                ]
            )

    for candidate in candidates:
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    return ""


def _organizer_for_provider_account_reference(provider_account_reference: str) -> Organizer | None:
    normalized_reference = provider_account_reference.strip()
    if not normalized_reference:
        return None
    provider_setup = (
        ProviderPaymentSetup.objects.select_related("organizer")
        .filter(
            provider=ProviderPaymentSetup.Provider.RAZORPAY,
            provider_merchant_reference=normalized_reference,
        )
        .first()
    )
    return provider_setup.organizer if provider_setup is not None else None
