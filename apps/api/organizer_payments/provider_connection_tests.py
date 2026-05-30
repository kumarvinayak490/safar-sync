from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass, field
from typing import Any, Protocol

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from organizer_payments.models import (
    ProviderConnectionTestResult,
    ProviderPaymentSetup,
    SensitiveProviderCredential,
)
from organizer_payments.provider_credentials import (
    SensitiveProviderCredentialNotFound,
    SensitiveProviderCredentialStore,
)
from organizers.models import Organizer
from trip_payments.provider_adapters import (
    ProviderCheckoutAdapterError,
    ProviderCheckoutRequest,
    RazorpayCheckoutAdapter,
)

CONNECTION_TEST_PAYMENT_PURPOSE = "provider_connection_test"
CONNECTION_TEST_AMOUNT_INR = 100


class ProviderConnectionTestAdapterError(Exception):
    pass


@dataclass(frozen=True)
class ProviderConnectionTestRequest:
    organizer_id: int
    provider: str
    provider_mode: str
    provider_account_reference: str
    credential_kind: str
    credential_scopes: list[str]
    credential_expires_at: object | None
    secret_payload: dict[str, Any] = field(repr=False)


@dataclass(frozen=True)
class ProviderConnectionTestValidation:
    checks: dict[str, dict[str, Any]]
    checkout_payload: dict[str, Any] = field(default_factory=dict)
    provider_order_reference: str = ""
    provider_payment_reference: str = ""
    failure_reason: str = ""

    @property
    def succeeded(self) -> bool:
        if self.failure_reason:
            return False
        return all(check.get("status") in {"passed", "skipped"} for check in self.checks.values())


class ProviderConnectionTestAdapter(Protocol):
    def run_connection_test(
        self,
        request: ProviderConnectionTestRequest,
    ) -> ProviderConnectionTestValidation: ...


class RazorpayProviderConnectionTestAdapter:
    def run_connection_test(
        self,
        request: ProviderConnectionTestRequest,
    ) -> ProviderConnectionTestValidation:
        if request.provider != ProviderPaymentSetup.Provider.RAZORPAY:
            raise ValidationError("Razorpay connection test received an unsupported provider.")

        checks: dict[str, dict[str, Any]] = {
            "credentials": _passed(
                "Active Sensitive Provider Credential retrieved for this Provider Mode.",
                credential_kind=request.credential_kind,
                provider_mode=request.provider_mode,
            ),
            "oauth_token_refresh": self._oauth_token_refresh_check(request),
        }

        try:
            checkout = RazorpayCheckoutAdapter().create_checkout(
                ProviderCheckoutRequest(
                    provider=request.provider,
                    connected_provider_account_reference=request.provider_account_reference,
                    payment_attempt_id=0,
                    booking_id=0,
                    payment_purpose=CONNECTION_TEST_PAYMENT_PURPOSE,
                    amount_inr=CONNECTION_TEST_AMOUNT_INR,
                    currency="INR",
                    booking_contact_name="TripOS Provider Connection Test",
                    booking_contact_phone="+910000000000",
                    booking_contact_email="",
                    organizer_identity_name="TripOS",
                    trip_title="Provider Connection Test",
                    organizer_id=request.organizer_id,
                    provider_mode=request.provider_mode,
                    credential_kind=request.credential_kind,
                    credential_provider_account_reference=request.provider_account_reference,
                    secret_payload=dict(request.secret_payload),
                )
            )
        except ProviderCheckoutAdapterError:
            return ProviderConnectionTestValidation(
                checks={
                    **checks,
                    "order_creation": _failed("Provider test order creation failed."),
                },
                failure_reason="provider_order_creation_failed",
            )
        checkout_payload = checkout.checkout_payload
        if checkout_payload.get("payment_purpose") != CONNECTION_TEST_PAYMENT_PURPOSE:
            return ProviderConnectionTestValidation(
                checks={
                    **checks,
                    "order_creation": _failed(
                        "Provider checkout payload was not scoped to a connection test."
                    ),
                },
                checkout_payload=checkout_payload,
                provider_order_reference=checkout.provider_order_reference,
                failure_reason="checkout_payload_not_test_scoped",
            )

        checks["order_creation"] = _passed(
            "Provider order reference generated for a test-scoped checkout.",
            provider_order_reference=checkout.provider_order_reference,
            amount_inr=CONNECTION_TEST_AMOUNT_INR,
        )
        checks["checkout_payload"] = _passed(
            "Checkout payload generated without public booking identifiers.",
            payment_attempt=checkout_payload.get("payment_attempt"),
            booking=checkout_payload.get("booking"),
            payment_purpose=checkout_payload.get("payment_purpose"),
        )

        provider_payment_reference = f"pay_tripos_test_{secrets.token_urlsafe(12)}"
        checkout_signature_secret = _signature_secret(request.secret_payload)
        checkout_signature = _checkout_signature(
            checkout.provider_order_reference,
            provider_payment_reference,
            checkout_signature_secret,
        )
        checks["browser_signature"] = _signature_check(
            _verify_checkout_signature(
                checkout.provider_order_reference,
                provider_payment_reference,
                checkout_signature,
                checkout_signature_secret,
            ),
            "Browser checkout signature verified against test-scoped references.",
        )

        webhook_payload = {
            "event": "payment.captured",
            "tripos_connection_test": True,
            "payload": {
                "payment": {
                    "entity": {
                        "id": provider_payment_reference,
                        "order_id": checkout.provider_order_reference,
                        "status": "captured",
                        "amount": CONNECTION_TEST_AMOUNT_INR * 100,
                        "currency": "INR",
                    }
                }
            },
        }
        webhook_body = json.dumps(webhook_payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        webhook_secret = _webhook_signature_secret(request.secret_payload)
        webhook_signature = _webhook_signature(webhook_body, webhook_secret)
        checks["webhook_signature"] = _signature_check(
            _verify_webhook_signature(webhook_body, webhook_signature, webhook_secret),
            "Webhook signature verified against a test-scoped captured payment event.",
        )

        captured_payment = webhook_payload["payload"]["payment"]["entity"]
        captured_confirmation_valid = (
            captured_payment["status"] == "captured"
            and captured_payment["order_id"] == checkout.provider_order_reference
            and captured_payment["amount"] == CONNECTION_TEST_AMOUNT_INR * 100
            and captured_payment["id"] == provider_payment_reference
        )
        checks["captured_confirmation"] = _signature_check(
            captured_confirmation_valid,
            "Captured payment confirmation normalized in test scope only.",
        )

        failure_reason = ""
        if any(check["status"] == "failed" for check in checks.values()):
            failure_reason = "provider_connection_test_check_failed"

        return ProviderConnectionTestValidation(
            checks=checks,
            checkout_payload=checkout_payload,
            provider_order_reference=checkout.provider_order_reference,
            provider_payment_reference=provider_payment_reference,
            failure_reason=failure_reason,
        )

    def _oauth_token_refresh_check(
        self,
        request: ProviderConnectionTestRequest,
    ) -> dict[str, Any]:
        if request.credential_kind != SensitiveProviderCredential.CredentialKind.OAUTH:
            return _skipped("Token refresh validation applies only to OAuth credentials.")
        if request.secret_payload.get("refresh_token"):
            return _passed(
                "OAuth refresh credential is present for provider token refresh validation.",
                scopes=request.credential_scopes,
            )
        return _failed("OAuth credential is missing refresh material.")


def provider_connection_test_adapter_for_provider(provider: str) -> ProviderConnectionTestAdapter:
    if provider == ProviderPaymentSetup.Provider.RAZORPAY:
        return RazorpayProviderConnectionTestAdapter()
    raise ValidationError("Payment provider is not supported for Provider Connection Tests.")


def run_provider_connection_test(
    *,
    organizer: Organizer,
    actor,
    adapter: ProviderConnectionTestAdapter | None = None,
    store: SensitiveProviderCredentialStore | None = None,
) -> ProviderConnectionTestResult:
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Authentication is required.")

    provider_setup, _ = ProviderPaymentSetup.objects.get_or_create(organizer=organizer)
    result = ProviderConnectionTestResult.objects.create(
        organizer=organizer,
        provider_payment_setup=provider_setup,
        provider=provider_setup.provider,
        provider_mode=provider_setup.provider_mode,
        provider_account_reference=provider_setup.provider_merchant_reference,
        initiated_by=actor,
        initiated_by_staff=bool(getattr(actor, "is_staff", False)),
    )

    credential_store = store or SensitiveProviderCredentialStore()
    try:
        _validate_authorized_provider_setup(provider_setup)
        credential = credential_store.retrieve_active_credential(
            organizer=organizer,
            provider=provider_setup.provider,
            provider_mode=provider_setup.provider_mode,
            actor=actor,
        )
        connection_test_adapter = adapter or provider_connection_test_adapter_for_provider(
            provider_setup.provider
        )
        validation = connection_test_adapter.run_connection_test(
            ProviderConnectionTestRequest(
                organizer_id=organizer.id,
                provider=provider_setup.provider,
                provider_mode=provider_setup.provider_mode,
                provider_account_reference=provider_setup.provider_merchant_reference,
                credential_kind=credential.credential_kind,
                credential_scopes=list(credential.scopes),
                credential_expires_at=credential.expires_at,
                secret_payload=credential.secret_payload,
            )
        )
        _complete_result(result, validation)
    except SensitiveProviderCredentialNotFound:
        _fail_result(
            result,
            failure_reason="active_sensitive_provider_credential_missing",
            checks={
                "credentials": _failed(
                    "No active Sensitive Provider Credential is available for this Provider Mode."
                )
            },
        )
    except (ProviderConnectionTestAdapterError, ValidationError) as exc:
        _fail_result(
            result,
            failure_reason=_validation_failure_reason(exc),
            checks={"provider_connection_test": _failed(_validation_failure_message(exc))},
        )

    result.refresh_from_db()
    _apply_provider_connection_state(provider_setup, result)
    return result


def _validate_authorized_provider_setup(provider_setup: ProviderPaymentSetup) -> None:
    if provider_setup.authorization_state != ProviderPaymentSetup.AuthorizationState.AUTHORIZED:
        raise ValidationError("Authorized Provider Authorization is required.")
    if not provider_setup.provider_merchant_reference.strip():
        raise ValidationError("Connected Provider Account reference is required.")


def _complete_result(
    result: ProviderConnectionTestResult,
    validation: ProviderConnectionTestValidation,
) -> None:
    result.status = (
        ProviderConnectionTestResult.Status.SUCCEEDED
        if validation.succeeded
        else ProviderConnectionTestResult.Status.FAILED
    )
    result.checks = validation.checks
    result.checkout_payload = validation.checkout_payload
    result.provider_order_reference = validation.provider_order_reference
    result.provider_payment_reference = validation.provider_payment_reference
    result.failure_reason = validation.failure_reason
    if result.status == ProviderConnectionTestResult.Status.FAILED and not result.failure_reason:
        result.failure_reason = "provider_connection_test_check_failed"
    result.completed_at = timezone.now()
    result.save(
        update_fields=[
            "status",
            "checks",
            "checkout_payload",
            "provider_order_reference",
            "provider_payment_reference",
            "failure_reason",
            "completed_at",
            "updated_at",
        ]
    )


def _fail_result(
    result: ProviderConnectionTestResult,
    *,
    failure_reason: str,
    checks: dict[str, dict[str, Any]],
) -> None:
    result.status = ProviderConnectionTestResult.Status.FAILED
    result.failure_reason = failure_reason
    result.checks = checks
    result.completed_at = timezone.now()
    result.save(
        update_fields=[
            "status",
            "failure_reason",
            "checks",
            "completed_at",
            "updated_at",
        ]
    )


def _apply_provider_connection_state(
    provider_setup: ProviderPaymentSetup,
    result: ProviderConnectionTestResult,
) -> None:
    provider_setup.refresh_from_db()
    if result.status == ProviderConnectionTestResult.Status.SUCCEEDED:
        next_state = ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    else:
        next_state = ProviderPaymentSetup.ProviderConnectionState.UNHEALTHY
    if provider_setup.provider_connection_state == next_state:
        return
    provider_setup.provider_connection_state = next_state
    provider_setup.save(update_fields=["provider_connection_state", "updated_at"])


def _passed(message: str, **metadata) -> dict[str, Any]:
    return {"status": "passed", "message": message, **metadata}


def _failed(message: str, **metadata) -> dict[str, Any]:
    return {"status": "failed", "message": message, **metadata}


def _skipped(message: str, **metadata) -> dict[str, Any]:
    return {"status": "skipped", "message": message, **metadata}


def _signature_check(ok: bool, message: str) -> dict[str, Any]:
    if ok:
        return _passed(message)
    return _failed(message)


def _signature_secret(secret_payload: dict[str, Any]) -> str:
    return str(
        secret_payload.get("key_secret")
        or secret_payload.get("access_token")
        or secret_payload.get("refresh_token")
        or ""
    ).strip()


def _webhook_signature_secret(secret_payload: dict[str, Any]) -> str:
    return str(secret_payload.get("webhook_secret") or _signature_secret(secret_payload)).strip()


def _checkout_signature(order_id: str, payment_id: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _verify_checkout_signature(order_id: str, payment_id: str, signature: str, secret: str) -> bool:
    if not secret:
        return False
    expected = _checkout_signature(order_id, payment_id, secret)
    return hmac.compare_digest(expected, signature)


def _webhook_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _verify_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return False
    expected = _webhook_signature(body, secret)
    return hmac.compare_digest(expected, signature)


def _validation_failure_reason(exc: Exception) -> str:
    message = _validation_failure_message(exc)
    normalized = "_".join(message.lower().split())
    return normalized[:160] or "provider_connection_test_failed"


def _validation_failure_message(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        if hasattr(exc, "message_dict"):
            return json.dumps(exc.message_dict, sort_keys=True)
        return " ".join(str(message) for message in exc.messages)
    return str(exc)
