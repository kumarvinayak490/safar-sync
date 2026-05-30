from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from organizer_payments.models import ProviderPaymentSetup


@dataclass(frozen=True)
class ProviderOAuthAuthorizationRequest:
    provider: str
    client_id: str
    redirect_uri: str
    scopes: list[str]
    state: str


@dataclass(frozen=True)
class ProviderOAuthTokenExchangeRequest:
    provider: str
    client_id: str
    client_secret: str
    redirect_uri: str
    code: str
    provider_mode: str
    scopes: list[str]


@dataclass(frozen=True)
class ProviderOAuthTokenExchangeResult:
    provider: str
    access_token: str
    refresh_token: str
    provider_account_reference: str
    provider_mode: str
    scopes: list[str]
    expires_at: object | None = None
    public_token: str = ""


class ProviderOAuthAdapterError(Exception):
    pass


class ProviderOAuthAdapter(Protocol):
    def build_authorization_url(self, request: ProviderOAuthAuthorizationRequest) -> str: ...

    def exchange_authorization_code(
        self,
        request: ProviderOAuthTokenExchangeRequest,
    ) -> ProviderOAuthTokenExchangeResult: ...


class RazorpayOAuthAdapter:
    def __init__(
        self,
        *,
        authorize_url: str | None = None,
        token_url: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.authorize_url = authorize_url or settings.TRIPOS_RAZORPAY_OAUTH_AUTHORIZE_URL
        self.token_url = token_url or settings.TRIPOS_RAZORPAY_OAUTH_TOKEN_URL
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.TRIPOS_RAZORPAY_OAUTH_TIMEOUT_SECONDS
        )

    def build_authorization_url(self, request: ProviderOAuthAuthorizationRequest) -> str:
        if request.provider != ProviderPaymentSetup.Provider.RAZORPAY:
            raise ValidationError("Razorpay OAuth adapter received an unsupported provider.")
        self._require_value(request.client_id, "Razorpay OAuth client id is not configured.")
        self._require_value(request.redirect_uri, "Razorpay OAuth redirect URI is required.")
        if not request.scopes:
            raise ValidationError("At least one Razorpay OAuth scope is required.")
        query_params: list[tuple[str, str]] = [
            ("client_id", request.client_id),
            ("response_type", "code"),
            ("redirect_uri", request.redirect_uri),
            ("state", request.state),
        ]
        if len(request.scopes) == 1:
            query_params.append(("scope", request.scopes[0]))
        else:
            query_params.extend(("scope[]", scope) for scope in request.scopes)
        return f"{self.authorize_url}?{urlencode(query_params)}"

    def exchange_authorization_code(
        self,
        request: ProviderOAuthTokenExchangeRequest,
    ) -> ProviderOAuthTokenExchangeResult:
        if request.provider != ProviderPaymentSetup.Provider.RAZORPAY:
            raise ValidationError("Razorpay OAuth adapter received an unsupported provider.")
        self._require_value(request.client_id, "Razorpay OAuth client id is not configured.")
        self._require_value(
            request.client_secret,
            "Razorpay OAuth client secret is not configured.",
        )
        if request.provider_mode not in {
            ProviderPaymentSetup.ProviderMode.TEST,
            ProviderPaymentSetup.ProviderMode.LIVE,
        }:
            raise ValidationError("Unsupported Razorpay OAuth provider mode.")
        payload = {
            "client_id": request.client_id,
            "client_secret": request.client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": request.redirect_uri,
            "code": request.code,
            "mode": request.provider_mode,
        }
        response_payload = self._post_json(payload)
        return self._token_exchange_result(response_payload, request=request)

    def _post_json(self, payload: dict[str, str]) -> dict:
        request = Request(
            self.token_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise ProviderOAuthAdapterError("Razorpay OAuth token exchange failed.") from exc
        except URLError as exc:
            raise ProviderOAuthAdapterError(
                "Razorpay OAuth token exchange could not reach the provider."
            ) from exc
        try:
            decoded = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise ProviderOAuthAdapterError(
                "Razorpay OAuth token exchange returned malformed data."
            ) from exc
        if not isinstance(decoded, dict):
            raise ProviderOAuthAdapterError(
                "Razorpay OAuth token exchange returned malformed data."
            )
        return decoded

    def _token_exchange_result(
        self,
        payload: dict,
        *,
        request: ProviderOAuthTokenExchangeRequest,
    ) -> ProviderOAuthTokenExchangeResult:
        access_token = str(payload.get("access_token", "")).strip()
        refresh_token = str(payload.get("refresh_token", "")).strip()
        public_token = str(payload.get("public_token", "")).strip()
        provider_account_reference = self._provider_account_reference(payload)
        if not access_token or not refresh_token or not provider_account_reference:
            raise ProviderOAuthAdapterError(
                "Razorpay OAuth token exchange did not return complete credential data."
            )
        provider_mode = str(payload.get("mode") or request.provider_mode).strip()
        if provider_mode not in {
            ProviderPaymentSetup.ProviderMode.TEST,
            ProviderPaymentSetup.ProviderMode.LIVE,
        }:
            provider_mode = request.provider_mode
        scopes = self._scopes(payload.get("scope"), fallback=request.scopes)
        expires_at = self._expires_at(payload)
        return ProviderOAuthTokenExchangeResult(
            provider=ProviderPaymentSetup.Provider.RAZORPAY,
            access_token=access_token,
            refresh_token=refresh_token,
            provider_account_reference=provider_account_reference,
            provider_mode=provider_mode,
            scopes=scopes,
            expires_at=expires_at,
            public_token=public_token,
        )

    def _provider_account_reference(self, payload: dict) -> str:
        return str(
            payload.get("razorpay_account_id")
            or payload.get("account_id")
            or payload.get("merchant_id")
            or ""
        ).strip()

    def _scopes(self, value, *, fallback: list[str]) -> list[str]:
        if isinstance(value, list):
            return [str(scope).strip() for scope in value if str(scope).strip()]
        if isinstance(value, str):
            return [scope for scope in value.replace(",", " ").split() if scope]
        return list(fallback)

    def _expires_at(self, payload: dict):
        expires_at = payload.get("expires_at")
        if expires_at:
            try:
                return datetime.fromtimestamp(float(expires_at), tz=UTC)
            except (TypeError, ValueError, OSError):
                return None
        expires_in = payload.get("expires_in")
        if expires_in:
            try:
                return timezone.now() + timedelta(seconds=int(expires_in))
            except (TypeError, ValueError):
                return None
        return None

    def _require_value(self, value: str, message: str) -> None:
        if not value.strip():
            raise ValidationError(message)


def oauth_adapter_for_provider(provider: str) -> ProviderOAuthAdapter:
    if provider == ProviderPaymentSetup.Provider.RAZORPAY:
        return RazorpayOAuthAdapter()
    raise ValidationError("Payment provider is not supported for OAuth Provider Authorization.")
