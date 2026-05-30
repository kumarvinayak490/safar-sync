from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from organizer_payments.models import (
    ProviderAuthorizationSession,
    ProviderPaymentSetup,
    SensitiveProviderCredential,
)
from organizer_payments.provider_adapters import (
    ProviderOAuthAdapter,
    ProviderOAuthAdapterError,
    ProviderOAuthAuthorizationRequest,
    ProviderOAuthTokenExchangeRequest,
    ProviderOAuthTokenExchangeResult,
    oauth_adapter_for_provider,
)
from organizer_payments.provider_credentials import SensitiveProviderCredentialStore
from organizers.models import Organizer
from team_access.models import OrganizerMembership
from trip_payments.models import PaymentAttempt, SeatHold
from trips.models import Trip


class ProviderAuthorizationError(Exception):
    pass


class ProviderAuthorizationStateError(ProviderAuthorizationError):
    pass


class ProviderAuthorizationExchangeError(ProviderAuthorizationError):
    pass


class ProviderAccountReplacementError(ProviderAuthorizationError):
    pass


@dataclass(frozen=True)
class ProviderAuthorizationStart:
    session: ProviderAuthorizationSession
    state: str
    authorization_url: str


@dataclass(frozen=True)
class ProviderAuthorizationLifecycleResult:
    provider_setup: ProviderPaymentSetup
    revoked_credentials: int = 0
    closed_public_booking_trips: int = 0
    deactivated_payment_attempts: int = 0
    released_seat_holds: int = 0


@dataclass(frozen=True)
class ProviderAuthorizationCompletion:
    session: ProviderAuthorizationSession
    provider_setup: ProviderPaymentSetup
    credential: SensitiveProviderCredential | None
    replacement_required: bool = False
    lifecycle_result: ProviderAuthorizationLifecycleResult | None = None

    @property
    def provider_account_reference(self) -> str:
        return self.session.provider_account_reference


@dataclass(frozen=True)
class ProviderAccountReplacementConfirmation:
    session: ProviderAuthorizationSession
    provider_setup: ProviderPaymentSetup
    credential: SensitiveProviderCredential
    lifecycle_result: ProviderAuthorizationLifecycleResult


def start_provider_authorization(
    *,
    organizer: Organizer,
    actor,
    request=None,
    provider_mode: str | None = None,
    adapter: ProviderOAuthAdapter | None = None,
) -> ProviderAuthorizationStart:
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Authentication is required.")
    _validate_actor_is_owner(organizer, actor=actor)

    provider_setup, _ = ProviderPaymentSetup.objects.get_or_create(organizer=organizer)
    mode = provider_mode or provider_setup.provider_mode or ProviderPaymentSetup.ProviderMode.TEST
    if mode not in ProviderPaymentSetup.ProviderMode.values:
        raise ValidationError({"provider_mode": "Unsupported Provider Mode."})
    client_id = _razorpay_oauth_client_id()
    scopes = _razorpay_oauth_scopes()
    redirect_uri = _razorpay_oauth_redirect_uri(request=request, organizer=organizer)
    state = secrets.token_urlsafe(32)
    oauth_adapter = adapter or oauth_adapter_for_provider(provider_setup.provider)
    authorization_url = oauth_adapter.build_authorization_url(
        ProviderOAuthAuthorizationRequest(
            provider=provider_setup.provider,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scopes=scopes,
            state=state,
        )
    )

    with transaction.atomic():
        provider_setup = ProviderPaymentSetup.objects.select_for_update().get(pk=provider_setup.pk)
        session = ProviderAuthorizationSession.objects.create(
            organizer=organizer,
            provider_payment_setup=provider_setup,
            provider=provider_setup.provider,
            provider_mode=mode,
            state_digest=provider_authorization_state_digest(state),
            client_id=client_id,
            redirect_uri=redirect_uri,
            scopes=scopes,
            initiated_by=actor,
        )
        provider_setup.authorization_method = ProviderPaymentSetup.AuthorizationMethod.OAUTH
        provider_setup.provider_mode = mode
        update_fields = ["authorization_method", "provider_mode", "updated_at"]
        if provider_setup.authorization_state != ProviderPaymentSetup.AuthorizationState.AUTHORIZED:
            provider_setup.authorization_state = ProviderPaymentSetup.AuthorizationState.PENDING
            update_fields.append("authorization_state")
        if provider_setup.status == ProviderPaymentSetup.Status.NOT_STARTED:
            provider_setup.status = ProviderPaymentSetup.Status.PENDING
            update_fields.append("status")
        provider_setup.save(update_fields=update_fields)

    return ProviderAuthorizationStart(
        session=session,
        state=state,
        authorization_url=authorization_url,
    )


def complete_provider_authorization(
    *,
    organizer: Organizer,
    actor,
    state: str,
    code: str,
    adapter: ProviderOAuthAdapter | None = None,
    store: SensitiveProviderCredentialStore | None = None,
) -> ProviderAuthorizationCompletion:
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Authentication is required.")

    session = _pending_session_for_state(organizer=organizer, state=state)
    _validate_session_actor(session, actor=actor)
    oauth_adapter = adapter or oauth_adapter_for_provider(session.provider)
    exchange_request = ProviderOAuthTokenExchangeRequest(
        provider=session.provider,
        client_id=session.client_id,
        client_secret=_razorpay_oauth_client_secret(),
        redirect_uri=session.redirect_uri,
        code=code.strip(),
        provider_mode=session.provider_mode,
        scopes=list(session.scopes),
    )
    try:
        exchange = oauth_adapter.exchange_authorization_code(exchange_request)
    except ProviderOAuthAdapterError as exc:
        _mark_session_failed(session.pk, reason="token_exchange_failed")
        raise ProviderAuthorizationExchangeError(
            "Provider Authorization could not be completed."
        ) from exc

    return _complete_valid_exchange(
        organizer=organizer,
        actor=actor,
        state=state,
        exchange=exchange,
        store=store or SensitiveProviderCredentialStore(),
    )


def disconnect_provider_authorization(
    *,
    organizer: Organizer,
    actor,
    store: SensitiveProviderCredentialStore | None = None,
) -> ProviderAuthorizationLifecycleResult:
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Authentication is required.")
    _validate_actor_is_owner(organizer, actor=actor)
    return _revoke_connected_provider_account_access(
        organizer=organizer,
        actor=actor,
        store=store or SensitiveProviderCredentialStore(),
        reason="Connected Provider Account disconnected.",
        authorization_state=ProviderPaymentSetup.AuthorizationState.REVOKED,
    )


def record_provider_authorization_revoked(
    *,
    organizer: Organizer,
    provider: str = ProviderPaymentSetup.Provider.RAZORPAY,
    provider_account_reference: str = "",
    reason: str = "Provider Authorization was revoked by the provider.",
    store: SensitiveProviderCredentialStore | None = None,
) -> ProviderAuthorizationLifecycleResult:
    with transaction.atomic():
        provider_setup, _ = ProviderPaymentSetup.objects.select_for_update().get_or_create(
            organizer=organizer
        )
        if provider_setup.provider != provider:
            return ProviderAuthorizationLifecycleResult(provider_setup=provider_setup)
        normalized_reference = provider_account_reference.strip()
        current_reference = provider_setup.provider_merchant_reference.strip()
        if normalized_reference and current_reference and normalized_reference != current_reference:
            return ProviderAuthorizationLifecycleResult(provider_setup=provider_setup)

    return _revoke_connected_provider_account_access(
        organizer=organizer,
        actor=None,
        store=store or SensitiveProviderCredentialStore(),
        reason=reason,
        authorization_state=ProviderPaymentSetup.AuthorizationState.REVOKED,
    )


@transaction.atomic
def confirm_provider_account_replacement(
    *,
    organizer: Organizer,
    actor,
    session_id: int,
    store: SensitiveProviderCredentialStore | None = None,
) -> ProviderAccountReplacementConfirmation:
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Authentication is required.")
    _validate_actor_is_owner(organizer, actor=actor)

    credential_store = store or SensitiveProviderCredentialStore()
    session = (
        ProviderAuthorizationSession.objects.select_for_update()
        .select_related("provider_payment_setup")
        .filter(
            pk=session_id,
            organizer=organizer,
            status=ProviderAuthorizationSession.Status.BLOCKED,
            failure_reason="different_provider_account",
        )
        .first()
    )
    if session is None:
        raise ProviderAccountReplacementError(
            "Provider account replacement confirmation is not available."
        )

    pending_credential = (
        SensitiveProviderCredential.objects.select_for_update()
        .filter(
            organizer=organizer,
            provider=session.provider,
            provider_mode=session.provider_mode,
            provider_account_reference=session.provider_account_reference,
            credential_kind=SensitiveProviderCredential.CredentialKind.OAUTH,
            status=SensitiveProviderCredential.Status.PENDING_REPLACEMENT,
        )
        .order_by("-created_at", "-id")
        .first()
    )
    if pending_credential is None:
        raise ProviderAccountReplacementError(
            "Replacement credentials are no longer available. Retry Provider Authorization."
        )

    provider_setup = ProviderPaymentSetup.objects.select_for_update().get(
        pk=session.provider_payment_setup_id
    )
    activated_credential = credential_store.activate_pending_replacement_credential(
        pending_credential,
        actor=actor,
    )
    session.status = ProviderAuthorizationSession.Status.COMPLETED
    session.failure_reason = ""
    session.failed_at = None
    session.completed_at = timezone.now()
    session.save(
        update_fields=[
            "status",
            "failure_reason",
            "failed_at",
            "completed_at",
            "updated_at",
        ]
    )
    provider_setup.provider_merchant_reference = pending_credential.provider_account_reference
    provider_setup.provider_mode = pending_credential.provider_mode
    provider_setup.authorization_method = ProviderPaymentSetup.AuthorizationMethod.OAUTH
    provider_setup.authorization_state = ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    provider_setup.provider_connection_state = ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    provider_setup.provider_payment_capability_enabled = False
    provider_setup.status = ProviderPaymentSetup.Status.PENDING
    provider_setup.save(
        update_fields=[
            "provider_merchant_reference",
            "provider_mode",
            "authorization_method",
            "authorization_state",
            "provider_connection_state",
            "provider_payment_capability_enabled",
            "status",
            "updated_at",
        ]
    )
    return ProviderAccountReplacementConfirmation(
        session=session,
        provider_setup=provider_setup,
        credential=activated_credential,
        lifecycle_result=ProviderAuthorizationLifecycleResult(provider_setup=provider_setup),
    )


def provider_authorization_state_digest(state: str) -> str:
    configured_key = str(
        getattr(settings, "TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY", settings.SECRET_KEY)
    ).encode("utf-8")
    digest = hmac.new(
        configured_key,
        f"tripos-provider-authorization-state:{state}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256:{digest}"


def _pending_session_for_state(*, organizer: Organizer, state: str) -> ProviderAuthorizationSession:
    state_value = state.strip()
    if not state_value:
        raise ProviderAuthorizationStateError("Provider Authorization state is required.")
    session = (
        ProviderAuthorizationSession.objects.select_related(
            "organizer",
            "provider_payment_setup",
            "initiated_by",
        )
        .filter(
            organizer=organizer,
            state_digest=provider_authorization_state_digest(state_value),
            status=ProviderAuthorizationSession.Status.PENDING,
        )
        .first()
    )
    if session is None:
        raise ProviderAuthorizationStateError("Provider Authorization state is invalid.")
    if session.expires_at <= timezone.now():
        _mark_session_failed(session.pk, reason="state_expired")
        raise ProviderAuthorizationStateError("Provider Authorization state has expired.")
    if session.client_id != _razorpay_oauth_client_id():
        _mark_session_failed(session.pk, reason="client_id_mismatch")
        raise ProviderAuthorizationStateError("Provider Authorization state is invalid.")
    return session


def _validate_session_actor(session: ProviderAuthorizationSession, *, actor) -> None:
    if session.initiated_by_id != actor.id:
        raise PermissionDenied(
            "Provider Authorization must be completed by the User who started it."
        )


def _validate_actor_is_owner(organizer: Organizer, *, actor) -> None:
    if not OrganizerMembership.objects.filter(
        organizer=organizer,
        user=actor,
        role=OrganizerMembership.Role.OWNER,
    ).exists():
        raise PermissionDenied("Only Owners can manage Provider Authorization.")


@transaction.atomic
def _complete_valid_exchange(
    *,
    organizer: Organizer,
    actor,
    state: str,
    exchange: ProviderOAuthTokenExchangeResult,
    store: SensitiveProviderCredentialStore,
) -> ProviderAuthorizationCompletion:
    session = (
        ProviderAuthorizationSession.objects.select_for_update()
        .select_related("provider_payment_setup")
        .get(
            organizer=organizer,
            state_digest=provider_authorization_state_digest(state),
            status=ProviderAuthorizationSession.Status.PENDING,
        )
    )
    provider_setup = ProviderPaymentSetup.objects.select_for_update().get(
        pk=session.provider_payment_setup_id
    )
    if exchange.provider != session.provider:
        _mark_session_failed(session.pk, reason="provider_mismatch")
        raise ProviderAuthorizationExchangeError(
            "Provider Authorization returned an unexpected provider."
        )
    if exchange.provider_mode not in ProviderPaymentSetup.ProviderMode.values:
        _mark_session_failed(session.pk, reason="provider_mode_mismatch")
        raise ProviderAuthorizationExchangeError(
            "Provider Authorization returned an unsupported Provider Mode."
        )
    normalized_account_reference = exchange.provider_account_reference.strip()
    if not normalized_account_reference:
        _mark_session_failed(session.pk, reason="provider_account_reference_missing")
        raise ProviderAuthorizationExchangeError(
            "Provider Authorization did not return a connected provider account."
        )
    existing_account_reference = provider_setup.provider_merchant_reference.strip()
    if existing_account_reference and existing_account_reference != normalized_account_reference:
        lifecycle_result = _revoke_connected_provider_account_access(
            organizer=organizer,
            actor=actor,
            store=store,
            reason="Connected Provider Account replacement pending.",
            authorization_state=ProviderPaymentSetup.AuthorizationState.ACTION_REQUIRED,
            credential_statuses=(SensitiveProviderCredential.Status.ACTIVE,),
        )
        provider_setup = lifecycle_result.provider_setup
        pending_credential = store.store_pending_replacement_oauth_credentials(
            organizer=organizer,
            access_token=exchange.access_token,
            refresh_token=exchange.refresh_token,
            provider_account_reference=normalized_account_reference,
            public_token=exchange.public_token,
            provider_mode=exchange.provider_mode,
            scopes=list(exchange.scopes),
            expires_at=exchange.expires_at,
            actor=actor,
        )
        session.status = ProviderAuthorizationSession.Status.BLOCKED
        session.provider_account_reference = normalized_account_reference
        session.failure_reason = "different_provider_account"
        session.failed_at = timezone.now()
        session.save(
            update_fields=[
                "status",
                "provider_account_reference",
                "failure_reason",
                "failed_at",
                "updated_at",
            ]
        )
        return ProviderAuthorizationCompletion(
            session=session,
            provider_setup=provider_setup,
            credential=pending_credential,
            replacement_required=True,
            lifecycle_result=lifecycle_result,
        )

    credential = store.store_oauth_credentials(
        organizer=organizer,
        access_token=exchange.access_token,
        refresh_token=exchange.refresh_token,
        provider_account_reference=normalized_account_reference,
        public_token=exchange.public_token,
        provider_mode=exchange.provider_mode,
        scopes=list(exchange.scopes),
        expires_at=exchange.expires_at,
        actor=actor,
    )
    session.status = ProviderAuthorizationSession.Status.COMPLETED
    session.provider_account_reference = normalized_account_reference
    session.completed_at = timezone.now()
    session.save(
        update_fields=[
            "status",
            "provider_account_reference",
            "completed_at",
            "updated_at",
        ]
    )
    provider_setup.provider_merchant_reference = normalized_account_reference
    provider_setup.provider_mode = exchange.provider_mode
    provider_setup.authorization_method = ProviderPaymentSetup.AuthorizationMethod.OAUTH
    provider_setup.authorization_state = ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    provider_setup.provider_connection_state = ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    if provider_setup.status in {
        ProviderPaymentSetup.Status.NOT_STARTED,
        ProviderPaymentSetup.Status.ACTION_REQUIRED,
    }:
        provider_setup.status = ProviderPaymentSetup.Status.PENDING
    provider_setup.save(
        update_fields=[
            "provider_merchant_reference",
            "provider_mode",
            "authorization_method",
            "authorization_state",
            "provider_connection_state",
            "status",
            "updated_at",
        ]
    )
    return ProviderAuthorizationCompletion(
        session=session,
        provider_setup=provider_setup,
        credential=credential,
    )


@transaction.atomic
def _revoke_connected_provider_account_access(
    *,
    organizer: Organizer,
    actor,
    store: SensitiveProviderCredentialStore,
    reason: str,
    authorization_state: str,
    credential_statuses: tuple[str, ...] | None = None,
) -> ProviderAuthorizationLifecycleResult:
    provider_setup, _ = ProviderPaymentSetup.objects.select_for_update().get_or_create(
        organizer=organizer
    )
    revoked_credentials = store.revoke_credentials_for_organizer(
        organizer=organizer,
        provider=provider_setup.provider,
        statuses=credential_statuses,
        actor=actor,
        reason=reason,
    )
    provider_setup.authorization_method = ProviderPaymentSetup.AuthorizationMethod.OAUTH
    provider_setup.authorization_state = authorization_state
    provider_setup.provider_connection_state = (
        ProviderPaymentSetup.ProviderConnectionState.UNHEALTHY
    )
    provider_setup.provider_payment_capability_enabled = False
    provider_setup.status = ProviderPaymentSetup.Status.ACTION_REQUIRED
    provider_setup.save(
        update_fields=[
            "authorization_method",
            "authorization_state",
            "provider_connection_state",
            "provider_payment_capability_enabled",
            "status",
            "updated_at",
        ]
    )
    closed_trips, deactivated_attempts, released_holds = (
        _close_new_public_booking_and_deactivate_unpaid_attempts(
            organizer=organizer,
            failure_reason=reason,
        )
    )
    return ProviderAuthorizationLifecycleResult(
        provider_setup=provider_setup,
        revoked_credentials=revoked_credentials,
        closed_public_booking_trips=closed_trips,
        deactivated_payment_attempts=deactivated_attempts,
        released_seat_holds=released_holds,
    )


def _close_new_public_booking_and_deactivate_unpaid_attempts(
    *,
    organizer: Organizer,
    failure_reason: str,
) -> tuple[int, int, int]:
    now = timezone.now()
    closed_trips = (
        Trip.objects.select_for_update()
        .filter(
            organizer=organizer,
            booking_availability=Trip.BookingAvailability.OPEN,
        )
        .update(
            booking_availability=Trip.BookingAvailability.CLOSED,
            updated_at=now,
        )
    )
    active_attempt_ids = list(
        PaymentAttempt.objects.select_for_update()
        .filter(
            booking__trip__organizer=organizer,
            status__in=[
                PaymentAttempt.Status.PENDING,
                PaymentAttempt.Status.CONFIRMING,
            ],
        )
        .values_list("id", flat=True)
    )
    deactivated_attempts = 0
    released_holds = 0
    if active_attempt_ids:
        deactivated_attempts = PaymentAttempt.objects.filter(id__in=active_attempt_ids).update(
            status=PaymentAttempt.Status.SUPERSEDED,
            failure_reason=failure_reason,
            updated_at=now,
        )
        released_holds = SeatHold.objects.filter(
            payment_attempt_id__in=active_attempt_ids,
            released_at__isnull=True,
        ).update(released_at=now)
    return closed_trips, deactivated_attempts, released_holds


@transaction.atomic
def _mark_session_failed(session_id: int, *, reason: str) -> None:
    session = ProviderAuthorizationSession.objects.select_for_update().filter(pk=session_id).first()
    if session is None or session.status != ProviderAuthorizationSession.Status.PENDING:
        return
    session.status = ProviderAuthorizationSession.Status.FAILED
    session.failure_reason = reason
    session.failed_at = timezone.now()
    session.save(update_fields=["status", "failure_reason", "failed_at", "updated_at"])
    provider_setup = ProviderPaymentSetup.objects.select_for_update().get(
        pk=session.provider_payment_setup_id
    )
    if provider_setup.authorization_state == ProviderPaymentSetup.AuthorizationState.PENDING:
        provider_setup.authorization_state = ProviderPaymentSetup.AuthorizationState.ACTION_REQUIRED
        provider_setup.provider_connection_state = (
            ProviderPaymentSetup.ProviderConnectionState.UNHEALTHY
        )
        provider_setup.status = ProviderPaymentSetup.Status.ACTION_REQUIRED
        provider_setup.save(
            update_fields=[
                "authorization_state",
                "provider_connection_state",
                "status",
                "updated_at",
            ]
        )


def _razorpay_oauth_client_id() -> str:
    client_id = str(getattr(settings, "TRIPOS_RAZORPAY_OAUTH_CLIENT_ID", "")).strip()
    if not client_id:
        raise ValidationError("Razorpay OAuth client id is not configured.")
    return client_id


def _razorpay_oauth_client_secret() -> str:
    client_secret = str(getattr(settings, "TRIPOS_RAZORPAY_OAUTH_CLIENT_SECRET", "")).strip()
    if not client_secret:
        raise ValidationError("Razorpay OAuth client secret is not configured.")
    return client_secret


def _razorpay_oauth_scopes() -> list[str]:
    scopes: Any = getattr(settings, "TRIPOS_RAZORPAY_OAUTH_SCOPES", ["read_write"])
    if isinstance(scopes, str):
        normalized = [scope.strip() for scope in scopes.split(",") if scope.strip()]
    else:
        normalized = [str(scope).strip() for scope in scopes if str(scope).strip()]
    if not normalized:
        raise ValidationError("At least one Razorpay OAuth scope is required.")
    return normalized


def _razorpay_oauth_redirect_uri(*, request, organizer: Organizer) -> str:
    configured = str(getattr(settings, "TRIPOS_RAZORPAY_OAUTH_REDIRECT_URI", "")).strip()
    if configured:
        return configured
    callback_path = reverse(
        "organizer-provider-authorization-callback",
        kwargs={"organizer_id": organizer.id},
    )
    if request is not None:
        return request.build_absolute_uri(callback_path)
    return callback_path
