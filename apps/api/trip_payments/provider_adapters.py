from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError

from organizer_payments.models import ProviderPaymentSetup, SensitiveProviderCredential
from trip_payments.models import PaymentAttempt


@dataclass(frozen=True)
class ProviderCheckoutRequest:
    provider: str
    connected_provider_account_reference: str
    payment_attempt_id: int
    booking_id: int
    payment_purpose: str
    amount_inr: int
    currency: str
    booking_contact_name: str
    booking_contact_phone: str
    booking_contact_email: str
    organizer_identity_name: str
    trip_title: str
    organizer_id: int = 0
    provider_mode: str = ProviderPaymentSetup.ProviderMode.TEST
    credential_kind: str = ""
    credential_provider_account_reference: str = ""
    secret_payload: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class ProviderCheckout:
    provider: str
    provider_order_reference: str
    checkout_payload: dict


@dataclass(frozen=True)
class ProviderCheckoutSignatureRequest:
    provider: str
    provider_order_reference: str
    provider_payment_reference: str
    checkout_signature: str
    credential_kind: str
    secret_payload: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class ProviderPaymentFetchRequest:
    provider: str
    provider_payment_reference: str
    credential_kind: str
    secret_payload: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class ProviderWebhookSignatureRequest:
    provider: str
    body: bytes
    webhook_signature: str
    webhook_secret: str = field(repr=False)


@dataclass(frozen=True)
class ProviderPaymentConfirmation:
    provider: str
    provider_payment_reference: str
    provider_attempt_reference: str
    amount_inr: int
    status: str
    payment_attempt_id: int | None = None
    booking_id: int | None = None
    purpose: str | None = None
    provider_fee_amount_inr: int | None = None
    provider_net_settlement_amount_inr: int | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def is_captured(self) -> bool:
        return self.status == "captured"


class ProviderCheckoutAdapter(Protocol):
    def create_checkout(self, request: ProviderCheckoutRequest) -> ProviderCheckout: ...


class ProviderPaymentConfirmationAdapter(ProviderCheckoutAdapter, Protocol):
    def verify_checkout_signature(self, request: ProviderCheckoutSignatureRequest) -> bool: ...

    def fetch_payment(
        self, request: ProviderPaymentFetchRequest
    ) -> ProviderPaymentConfirmation: ...


class ProviderWebhookAdapter(Protocol):
    def verify_webhook_signature(self, request: ProviderWebhookSignatureRequest) -> bool: ...

    def payment_confirmation_from_webhook(
        self,
        payload: dict[str, Any],
    ) -> ProviderPaymentConfirmation: ...


class ProviderCheckoutAdapterError(Exception):
    pass


class RazorpayCheckoutAdapter:
    def __init__(
        self,
        *,
        orders_url: str | None = None,
        payments_url: str | None = None,
        timeout_seconds: float | None = None,
        http_client=None,
    ):
        api_base_url = settings.TRIPOS_RAZORPAY_API_BASE_URL.rstrip("/")
        self.orders_url = orders_url or f"{api_base_url}/orders"
        self.payments_url = payments_url or f"{api_base_url}/payments"
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.TRIPOS_RAZORPAY_API_TIMEOUT_SECONDS
        )
        self.http_client = http_client or urlopen

    def create_checkout(self, request: ProviderCheckoutRequest) -> ProviderCheckout:
        if request.provider != ProviderPaymentSetup.Provider.RAZORPAY:
            raise ValidationError("Razorpay checkout adapter received an unsupported provider.")
        if not request.connected_provider_account_reference.strip():
            raise ValidationError(
                "Connected Provider Account reference is required before provider checkout."
            )
        if request.currency != "INR":
            raise ValidationError("INR is the only supported checkout currency.")
        if request.amount_inr <= 0:
            raise ValidationError("Checkout amount must be positive.")

        amount_minor = request.amount_inr * 100
        receipt = self._receipt(request)
        notes = self._notes(request)
        provider_order = self._create_order(
            request,
            amount_minor=amount_minor,
            receipt=receipt,
            notes=notes,
        )
        provider_order_reference = self._provider_order_reference(provider_order)
        self._validate_order_response(
            provider_order,
            amount_minor=amount_minor,
            currency=request.currency,
        )
        public_checkout_key = self._public_checkout_key(request)
        description_prefix = (
            "Balance payment"
            if request.payment_purpose == PaymentAttempt.Purpose.BALANCE
            else "Reservation payment"
        )
        display = {
            "name": request.organizer_identity_name,
            "description": f"{description_prefix} for {request.trip_title}",
        }
        prefill = {
            "name": request.booking_contact_name,
            "contact": request.booking_contact_phone,
            "email": request.booking_contact_email,
        }
        return ProviderCheckout(
            provider=ProviderPaymentSetup.Provider.RAZORPAY,
            provider_order_reference=provider_order_reference,
            checkout_payload={
                "provider": ProviderPaymentSetup.Provider.RAZORPAY,
                "provider_order_reference": provider_order_reference,
                "amount_inr": request.amount_inr,
                "amount_minor": amount_minor,
                "currency": request.currency,
                "public_checkout_key": public_checkout_key,
                "payment_attempt": request.payment_attempt_id,
                "booking": request.booking_id,
                "payment_purpose": request.payment_purpose,
                "display": display,
                "prefill": prefill,
                "provider_payload": {
                    "key": public_checkout_key,
                    "order_id": provider_order_reference,
                    "amount": amount_minor,
                    "currency": request.currency,
                    "name": display["name"],
                    "description": display["description"],
                    "prefill": prefill,
                    "notes": notes,
                },
            },
        )

    def _create_order(
        self,
        request: ProviderCheckoutRequest,
        *,
        amount_minor: int,
        receipt: str,
        notes: dict[str, str],
    ) -> dict[str, Any]:
        payload = {
            "amount": amount_minor,
            "currency": request.currency,
            "receipt": receipt,
            "notes": notes,
            "partial_payment": False,
        }
        http_request = Request(
            self.orders_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(request),
            method="POST",
        )
        try:
            with self.http_client(http_request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise ProviderCheckoutAdapterError("Razorpay order creation failed.") from exc
        except URLError as exc:
            raise ProviderCheckoutAdapterError(
                "Razorpay order creation could not reach the provider."
            ) from exc
        try:
            decoded = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise ProviderCheckoutAdapterError(
                "Razorpay order creation returned malformed data."
            ) from exc
        if not isinstance(decoded, dict):
            raise ProviderCheckoutAdapterError("Razorpay order creation returned malformed data.")
        return decoded

    def _headers(self, request: ProviderCheckoutRequest) -> dict[str, str]:
        return self._headers_for_credential(
            credential_kind=request.credential_kind,
            secret_payload=request.secret_payload,
        )

    def _headers_for_credential(
        self,
        *,
        credential_kind: str,
        secret_payload: dict[str, Any],
    ) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if credential_kind == SensitiveProviderCredential.CredentialKind.API_KEY:
            key_id = self._required_secret_from_payload(secret_payload, "key_id")
            key_secret = self._required_secret_from_payload(secret_payload, "key_secret")
            basic_token = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode("ascii")
            headers["Authorization"] = f"Basic {basic_token}"
            return headers

        access_token = self._required_secret_from_payload(secret_payload, "access_token")
        headers["Authorization"] = f"Bearer {access_token}"
        return headers

    def _public_checkout_key(self, request: ProviderCheckoutRequest) -> str:
        if request.credential_kind == SensitiveProviderCredential.CredentialKind.API_KEY:
            return self._required_secret(request, "key_id")
        public_token = str(request.secret_payload.get("public_token") or "").strip()
        if not public_token:
            raise ProviderCheckoutAdapterError(
                "Razorpay public checkout key is unavailable for this credential."
            )
        return public_token

    def _required_secret(self, request: ProviderCheckoutRequest, field_name: str) -> str:
        value = str(request.secret_payload.get(field_name) or "").strip()
        if not value:
            raise ProviderCheckoutAdapterError(
                "Active Sensitive Provider Credential is incomplete for order creation."
            )
        return value

    def _required_secret_from_payload(
        self,
        secret_payload: dict[str, Any],
        field_name: str,
    ) -> str:
        value = str(secret_payload.get(field_name) or "").strip()
        if not value:
            raise ProviderCheckoutAdapterError(
                "Active Sensitive Provider Credential is incomplete for provider checkout."
            )
        return value

    def verify_checkout_signature(self, request: ProviderCheckoutSignatureRequest) -> bool:
        if request.provider != ProviderPaymentSetup.Provider.RAZORPAY:
            raise ValidationError("Razorpay checkout adapter received an unsupported provider.")
        provider_order_reference = request.provider_order_reference.strip()
        provider_payment_reference = request.provider_payment_reference.strip()
        checkout_signature = request.checkout_signature.strip()
        if not provider_order_reference or not provider_payment_reference or not checkout_signature:
            return False
        signature_secret = self._checkout_signature_secret(request)
        expected_signature = hmac.new(
            signature_secret.encode("utf-8"),
            f"{provider_order_reference}|{provider_payment_reference}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_signature, checkout_signature)

    def verify_webhook_signature(self, request: ProviderWebhookSignatureRequest) -> bool:
        if request.provider != ProviderPaymentSetup.Provider.RAZORPAY:
            raise ValidationError("Razorpay webhook adapter received an unsupported provider.")
        webhook_signature = request.webhook_signature.strip()
        webhook_secret = request.webhook_secret.strip()
        if not request.body or not webhook_signature or not webhook_secret:
            return False
        expected_signature = hmac.new(
            webhook_secret.encode("utf-8"),
            request.body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_signature, webhook_signature)

    def fetch_payment(self, request: ProviderPaymentFetchRequest) -> ProviderPaymentConfirmation:
        if request.provider != ProviderPaymentSetup.Provider.RAZORPAY:
            raise ValidationError("Razorpay checkout adapter received an unsupported provider.")
        provider_payment_reference = request.provider_payment_reference.strip()
        if not provider_payment_reference:
            raise ProviderCheckoutAdapterError("Razorpay payment id is required.")
        http_request = Request(
            f"{self.payments_url.rstrip('/')}/{provider_payment_reference}",
            headers=self._headers_for_credential(
                credential_kind=request.credential_kind,
                secret_payload=request.secret_payload,
            ),
            method="GET",
        )
        try:
            with self.http_client(http_request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise ProviderCheckoutAdapterError("Razorpay payment fetch failed.") from exc
        except URLError as exc:
            raise ProviderCheckoutAdapterError(
                "Razorpay payment fetch could not reach the provider."
            ) from exc
        try:
            decoded = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise ProviderCheckoutAdapterError(
                "Razorpay payment fetch returned malformed data."
            ) from exc
        if not isinstance(decoded, dict):
            raise ProviderCheckoutAdapterError("Razorpay payment fetch returned malformed data.")
        return self._payment_confirmation(decoded)

    def payment_confirmation_from_webhook(
        self,
        payload: dict[str, Any],
    ) -> ProviderPaymentConfirmation:
        payment_payload = payload.get("payload")
        if not isinstance(payment_payload, dict):
            raise ProviderCheckoutAdapterError("Razorpay webhook did not include payment details.")
        payment_wrapper = payment_payload.get("payment")
        if not isinstance(payment_wrapper, dict):
            raise ProviderCheckoutAdapterError("Razorpay webhook did not include payment details.")
        payment_entity = payment_wrapper.get("entity")
        if not isinstance(payment_entity, dict):
            raise ProviderCheckoutAdapterError("Razorpay webhook did not include payment details.")
        return self._payment_confirmation(payment_entity)

    def _checkout_signature_secret(self, request: ProviderCheckoutSignatureRequest) -> str:
        if request.credential_kind == SensitiveProviderCredential.CredentialKind.API_KEY:
            return self._required_secret_from_payload(request.secret_payload, "key_secret")
        signature_secret = str(
            request.secret_payload.get("checkout_signature_secret") or ""
        ).strip()
        if signature_secret:
            return signature_secret
        return self._required_secret_from_payload(request.secret_payload, "access_token")

    def _payment_confirmation(self, payload: dict[str, Any]) -> ProviderPaymentConfirmation:
        provider_payment_reference = str(payload.get("id") or "").strip()
        provider_attempt_reference = str(payload.get("order_id") or "").strip()
        status = str(payload.get("status") or "").strip().lower()
        currency = str(payload.get("currency") or "").strip().upper()
        if currency and currency != "INR":
            raise ProviderCheckoutAdapterError("Razorpay payment fetch returned non-INR payment.")
        amount_inr = self._minor_units_to_inr(payload.get("amount"), "amount")
        notes = payload.get("notes") if isinstance(payload.get("notes"), dict) else {}
        if not provider_payment_reference or not provider_attempt_reference or not status:
            raise ProviderCheckoutAdapterError(
                "Razorpay payment fetch returned incomplete payment details."
            )
        provider_fee_amount_inr = self._optional_minor_units_to_inr(payload.get("fee"), "fee")
        provider_net_settlement_amount_inr = None
        if provider_fee_amount_inr is not None:
            if provider_fee_amount_inr > amount_inr:
                raise ProviderCheckoutAdapterError(
                    "Razorpay payment fetch returned an invalid fee."
                )
            provider_net_settlement_amount_inr = amount_inr - provider_fee_amount_inr
        return ProviderPaymentConfirmation(
            provider=ProviderPaymentSetup.Provider.RAZORPAY,
            provider_payment_reference=provider_payment_reference,
            provider_attempt_reference=provider_attempt_reference,
            amount_inr=amount_inr,
            status=status,
            payment_attempt_id=self._optional_int_note(notes, "tripos_payment_attempt_id"),
            booking_id=self._optional_int_note(notes, "tripos_booking_id"),
            purpose=self._optional_note(notes, "tripos_payment_purpose"),
            provider_fee_amount_inr=provider_fee_amount_inr,
            provider_net_settlement_amount_inr=provider_net_settlement_amount_inr,
            raw_payload=payload,
        )

    def _minor_units_to_inr(self, value, field_name: str) -> int:
        try:
            amount_minor = int(value)
        except (TypeError, ValueError) as exc:
            raise ProviderCheckoutAdapterError(
                f"Razorpay payment fetch returned an invalid {field_name}."
            ) from exc
        if amount_minor <= 0 or amount_minor % 100 != 0:
            raise ProviderCheckoutAdapterError(
                f"Razorpay payment fetch returned an invalid {field_name}."
            )
        return amount_minor // 100

    def _optional_minor_units_to_inr(self, value, field_name: str) -> int | None:
        if value in (None, ""):
            return None
        try:
            amount_minor = int(value)
        except (TypeError, ValueError) as exc:
            raise ProviderCheckoutAdapterError(
                f"Razorpay payment fetch returned an invalid {field_name}."
            ) from exc
        if amount_minor < 0 or amount_minor % 100 != 0:
            raise ProviderCheckoutAdapterError(
                f"Razorpay payment fetch returned an invalid {field_name}."
            )
        return amount_minor // 100

    def _optional_note(self, notes: dict[str, Any], key: str) -> str | None:
        value = str(notes.get(key) or "").strip()
        return value or None

    def _optional_int_note(self, notes: dict[str, Any], key: str) -> int | None:
        value = self._optional_note(notes, key)
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _receipt(self, request: ProviderCheckoutRequest) -> str:
        if request.payment_purpose == PaymentAttempt.Purpose.RESERVATION:
            purpose = "res"
        elif request.payment_purpose == PaymentAttempt.Purpose.BALANCE:
            purpose = "bal"
        else:
            purpose = "test"
        if request.payment_attempt_id > 0:
            return f"tripos_{purpose}_{request.payment_attempt_id}_{request.booking_id}"[:40]
        return f"tripos_{purpose}_{secrets.token_urlsafe(8)}"[:40]

    def _notes(self, request: ProviderCheckoutRequest) -> dict[str, str]:
        return {
            "tripos_organizer_id": str(request.organizer_id),
            "tripos_booking_id": str(request.booking_id),
            "tripos_payment_attempt_id": str(request.payment_attempt_id),
            "tripos_payment_purpose": request.payment_purpose,
            "tripos_provider_account": request.connected_provider_account_reference[:256],
        }

    def _provider_order_reference(self, payload: dict[str, Any]) -> str:
        provider_order_reference = str(payload.get("id") or "").strip()
        if not provider_order_reference:
            raise ProviderCheckoutAdapterError(
                "Razorpay order creation did not return an order id."
            )
        return provider_order_reference

    def _validate_order_response(
        self,
        payload: dict[str, Any],
        *,
        amount_minor: int,
        currency: str,
    ) -> None:
        try:
            response_amount = int(payload.get("amount"))
        except (TypeError, ValueError) as exc:
            raise ProviderCheckoutAdapterError(
                "Razorpay order creation returned an invalid amount."
            ) from exc
        response_currency = str(payload.get("currency") or "").upper()
        if response_amount != amount_minor or response_currency != currency:
            raise ProviderCheckoutAdapterError(
                "Razorpay order creation returned mismatched order details."
            )


def checkout_adapter_for_provider(provider: str) -> ProviderCheckoutAdapter:
    if provider == ProviderPaymentSetup.Provider.RAZORPAY:
        return RazorpayCheckoutAdapter()
    raise ValidationError("Payment provider is not supported for checkout.")


def webhook_adapter_for_provider(provider: str) -> ProviderWebhookAdapter:
    if provider == ProviderPaymentSetup.Provider.RAZORPAY:
        return RazorpayCheckoutAdapter()
    raise ValidationError("Payment provider is not supported for webhooks.")


def checkout_request_for_payment_attempt(
    payment_attempt: PaymentAttempt,
    provider_setup: ProviderPaymentSetup,
    credential,
) -> ProviderCheckoutRequest:
    booking = payment_attempt.booking
    trip = booking.trip
    return ProviderCheckoutRequest(
        provider=provider_setup.provider,
        connected_provider_account_reference=provider_setup.provider_merchant_reference,
        payment_attempt_id=payment_attempt.id,
        booking_id=booking.id,
        payment_purpose=payment_attempt.purpose,
        amount_inr=payment_attempt.amount_inr,
        currency="INR",
        booking_contact_name=booking.booking_contact_name,
        booking_contact_phone=booking.booking_contact_phone,
        booking_contact_email=booking.booking_contact_email,
        organizer_identity_name=trip.organizer.display_identity_name,
        trip_title=trip.title,
        organizer_id=trip.organizer_id,
        provider_mode=provider_setup.provider_mode,
        credential_kind=credential.credential_kind,
        credential_provider_account_reference=credential.provider_account_reference,
        secret_payload=dict(credential.secret_payload),
    )
