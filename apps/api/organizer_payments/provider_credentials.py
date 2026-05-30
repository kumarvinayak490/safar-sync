from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from organizer_payments.models import (
    ProviderPaymentSetup,
    SensitiveProviderCredential,
    SensitiveProviderCredentialAudit,
)
from organizers.models import Organizer

TOKEN_VERSION = "v1"
TOKEN_PREFIX = f"{TOKEN_VERSION}:"
SALT_BYTES = 16
NONCE_BYTES = 16
TAG_BYTES = 32


class SensitiveProviderCredentialError(Exception):
    pass


class SensitiveProviderCredentialNotFound(SensitiveProviderCredentialError):
    pass


class SensitiveProviderCredentialIntegrityError(SensitiveProviderCredentialError):
    pass


@dataclass(frozen=True)
class RetrievedSensitiveProviderCredential:
    credential_id: int
    organizer_id: int
    provider: str
    provider_mode: str
    credential_kind: str
    provider_account_reference: str
    scopes: list[str]
    expires_at: object | None
    secret_payload: dict[str, Any] = field(repr=False)


class ProviderCredentialCipher:
    """Small authenticated encryption wrapper kept behind the credential store."""

    def encrypt(self, payload: dict[str, Any]) -> tuple[str, str]:
        plaintext = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        salt = os.urandom(SALT_BYTES)
        nonce = os.urandom(NONCE_BYTES)
        encryption_key, authentication_key = self._keys(salt)
        ciphertext = self._xor(plaintext, self._keystream(encryption_key, nonce, len(plaintext)))
        tag = hmac.new(
            authentication_key,
            self._authenticated_data(salt, nonce, ciphertext),
            hashlib.sha256,
        ).digest()
        token = TOKEN_PREFIX + base64.urlsafe_b64encode(salt + nonce + tag + ciphertext).decode(
            "ascii"
        )
        return token, self.key_id

    def decrypt(self, token: str, *, key_id: str | None = None) -> dict[str, Any]:
        if not token.startswith(TOKEN_PREFIX):
            raise SensitiveProviderCredentialIntegrityError("Unsupported credential token version.")
        try:
            decoded = base64.urlsafe_b64decode(token.removeprefix(TOKEN_PREFIX).encode("ascii"))
        except (ValueError, TypeError) as exc:
            raise SensitiveProviderCredentialIntegrityError(
                "Credential token is malformed."
            ) from exc
        minimum_size = SALT_BYTES + NONCE_BYTES + TAG_BYTES
        if len(decoded) <= minimum_size:
            raise SensitiveProviderCredentialIntegrityError("Credential token is incomplete.")
        salt = decoded[:SALT_BYTES]
        nonce = decoded[SALT_BYTES : SALT_BYTES + NONCE_BYTES]
        tag = decoded[SALT_BYTES + NONCE_BYTES : minimum_size]
        ciphertext = decoded[minimum_size:]
        encryption_key, authentication_key = self._keys(salt)
        expected_tag = hmac.new(
            authentication_key,
            self._authenticated_data(salt, nonce, ciphertext, key_id=key_id),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(tag, expected_tag):
            raise SensitiveProviderCredentialIntegrityError("Credential token failed verification.")
        plaintext = self._xor(
            ciphertext,
            self._keystream(encryption_key, nonce, len(ciphertext)),
        )
        try:
            return json.loads(plaintext.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SensitiveProviderCredentialIntegrityError(
                "Credential payload is malformed."
            ) from exc

    @property
    def key_id(self) -> str:
        return str(getattr(settings, "TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY_ID", "local"))

    def _keys(self, salt: bytes) -> tuple[bytes, bytes]:
        configured_key = str(
            getattr(settings, "TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY", settings.SECRET_KEY)
        ).encode("utf-8")
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            configured_key,
            b"tripos-sensitive-provider-credential" + salt,
            120_000,
            dklen=64,
        )
        return derived[:32], derived[32:]

    def _authenticated_data(
        self,
        salt: bytes,
        nonce: bytes,
        ciphertext: bytes,
        *,
        key_id: str | None = None,
    ) -> bytes:
        return b"|".join(
            [
                TOKEN_VERSION.encode("ascii"),
                (key_id or self.key_id).encode("utf-8"),
                salt,
                nonce,
                ciphertext,
            ]
        )

    def _keystream(self, key: bytes, nonce: bytes, length: int) -> bytes:
        blocks = []
        counter = 0
        while sum(len(block) for block in blocks) < length:
            blocks.append(
                hmac.new(
                    key,
                    nonce + counter.to_bytes(8, "big"),
                    hashlib.sha256,
                ).digest()
            )
            counter += 1
        return b"".join(blocks)[:length]

    def _xor(self, left: bytes, right: bytes) -> bytes:
        return bytes(
            left_byte ^ right_byte for left_byte, right_byte in zip(left, right, strict=True)
        )


class SensitiveProviderCredentialStore:
    def __init__(self, *, cipher: ProviderCredentialCipher | None = None):
        self.cipher = cipher or ProviderCredentialCipher()

    @transaction.atomic
    def store_oauth_credentials(
        self,
        *,
        organizer: Organizer,
        access_token: str,
        refresh_token: str,
        provider_account_reference: str,
        public_token: str = "",
        provider_mode: str = ProviderPaymentSetup.ProviderMode.TEST,
        scopes: list[str] | None = None,
        expires_at=None,
        actor=None,
    ) -> SensitiveProviderCredential:
        return self._store(
            organizer=organizer,
            credential_kind=SensitiveProviderCredential.CredentialKind.OAUTH,
            provider_mode=provider_mode,
            provider_account_reference=provider_account_reference,
            scopes=scopes or [],
            expires_at=expires_at,
            secret_payload=self._oauth_secret_payload(
                access_token=access_token,
                refresh_token=refresh_token,
                public_token=public_token,
            ),
            actor=actor,
        )

    @transaction.atomic
    def store_pending_replacement_oauth_credentials(
        self,
        *,
        organizer: Organizer,
        access_token: str,
        refresh_token: str,
        provider_account_reference: str,
        public_token: str = "",
        provider_mode: str = ProviderPaymentSetup.ProviderMode.TEST,
        scopes: list[str] | None = None,
        expires_at=None,
        actor=None,
    ) -> SensitiveProviderCredential:
        return self._store(
            organizer=organizer,
            credential_kind=SensitiveProviderCredential.CredentialKind.OAUTH,
            provider_mode=provider_mode,
            provider_account_reference=provider_account_reference,
            scopes=scopes or [],
            expires_at=expires_at,
            secret_payload=self._oauth_secret_payload(
                access_token=access_token,
                refresh_token=refresh_token,
                public_token=public_token,
            ),
            actor=actor,
            status=SensitiveProviderCredential.Status.PENDING_REPLACEMENT,
            rotate_existing_active=False,
        )

    @transaction.atomic
    def store_api_key_credentials(
        self,
        *,
        organizer: Organizer,
        key_id: str,
        key_secret: str,
        provider_account_reference: str,
        provider_mode: str = ProviderPaymentSetup.ProviderMode.TEST,
        webhook_secret: str = "",
        scopes: list[str] | None = None,
        expires_at=None,
        actor=None,
    ) -> SensitiveProviderCredential:
        secret_payload = {
            "key_id": self._require_secret(key_id, "key_id"),
            "key_secret": self._require_secret(key_secret, "key_secret"),
        }
        if webhook_secret.strip():
            secret_payload["webhook_secret"] = webhook_secret.strip()
        return self._store(
            organizer=organizer,
            credential_kind=SensitiveProviderCredential.CredentialKind.API_KEY,
            provider_mode=provider_mode,
            provider_account_reference=provider_account_reference,
            scopes=scopes or [],
            expires_at=expires_at,
            secret_payload=secret_payload,
            actor=actor,
        )

    @transaction.atomic
    def rotate_credential(
        self,
        credential: SensitiveProviderCredential,
        *,
        secret_payload: dict[str, Any],
        actor=None,
        scopes: list[str] | None = None,
        expires_at=None,
    ) -> SensitiveProviderCredential:
        credential.status = SensitiveProviderCredential.Status.ROTATED
        credential.rotated_at = timezone.now()
        credential.rotated_by = actor
        credential.save(update_fields=["status", "rotated_at", "rotated_by", "updated_at"])
        self._audit(
            credential,
            SensitiveProviderCredentialAudit.EventType.ROTATED,
            actor=actor,
            metadata={"replacement_pending": True},
        )
        return self._store(
            organizer=credential.organizer,
            credential_kind=credential.credential_kind,
            provider_mode=credential.provider_mode,
            provider_account_reference=credential.provider_account_reference,
            scopes=scopes if scopes is not None else list(credential.scopes),
            expires_at=expires_at if expires_at is not None else credential.expires_at,
            secret_payload=secret_payload,
            actor=actor,
            rotated_from=credential,
        )

    @transaction.atomic
    def revoke_credential(
        self,
        credential: SensitiveProviderCredential,
        *,
        actor=None,
        reason: str = "",
    ) -> SensitiveProviderCredential:
        credential.status = SensitiveProviderCredential.Status.REVOKED
        credential.revoked_at = timezone.now()
        credential.revoked_by = actor
        credential.revoked_reason = reason.strip()
        credential.save(
            update_fields=[
                "status",
                "revoked_at",
                "revoked_by",
                "revoked_reason",
                "updated_at",
            ]
        )
        self._audit(
            credential,
            SensitiveProviderCredentialAudit.EventType.REVOKED,
            actor=actor,
            metadata={"reason_present": bool(credential.revoked_reason)},
        )
        return credential

    @transaction.atomic
    def revoke_credentials_for_organizer(
        self,
        *,
        organizer: Organizer,
        provider: str = ProviderPaymentSetup.Provider.RAZORPAY,
        provider_mode: str | None = None,
        statuses: tuple[str, ...] | None = None,
        actor=None,
        reason: str = "",
    ) -> int:
        credential_statuses = statuses or (
            SensitiveProviderCredential.Status.ACTIVE,
            SensitiveProviderCredential.Status.PENDING_REPLACEMENT,
        )
        credentials = SensitiveProviderCredential.objects.select_for_update().filter(
            organizer=organizer,
            provider=provider,
            status__in=credential_statuses,
        )
        if provider_mode is not None:
            credentials = credentials.filter(provider_mode=provider_mode)
        revoked_count = 0
        for credential in credentials:
            self.revoke_credential(credential, actor=actor, reason=reason)
            revoked_count += 1
        return revoked_count

    @transaction.atomic
    def activate_pending_replacement_credential(
        self,
        credential: SensitiveProviderCredential,
        *,
        actor=None,
    ) -> SensitiveProviderCredential:
        credential = SensitiveProviderCredential.objects.select_for_update().get(pk=credential.pk)
        if credential.status != SensitiveProviderCredential.Status.PENDING_REPLACEMENT:
            raise ValidationError(
                "Only pending replacement Sensitive Provider Credentials can be activated."
            )

        active_credentials = (
            SensitiveProviderCredential.objects.select_for_update()
            .filter(
                organizer=credential.organizer,
                provider=credential.provider,
                provider_mode=credential.provider_mode,
                status=SensitiveProviderCredential.Status.ACTIVE,
            )
            .exclude(pk=credential.pk)
        )
        for active_credential in active_credentials:
            self.revoke_credential(
                active_credential,
                actor=actor,
                reason="Connected Provider Account replaced.",
            )

        credential.status = SensitiveProviderCredential.Status.ACTIVE
        credential.save(update_fields=["status", "updated_at"])
        return credential

    @transaction.atomic
    def retrieve_active_credential(
        self,
        *,
        organizer: Organizer,
        provider: str = ProviderPaymentSetup.Provider.RAZORPAY,
        provider_mode: str | None = None,
        credential_kind: str | None = None,
        actor=None,
    ) -> RetrievedSensitiveProviderCredential:
        credentials = SensitiveProviderCredential.objects.select_for_update().filter(
            organizer=organizer,
            provider=provider,
            status=SensitiveProviderCredential.Status.ACTIVE,
        )
        if provider_mode is not None:
            credentials = credentials.filter(provider_mode=provider_mode)
        if credential_kind is not None:
            credentials = credentials.filter(credential_kind=credential_kind)
        credential = credentials.order_by("-created_at", "-id").first()
        if credential is None:
            raise SensitiveProviderCredentialNotFound(
                "No active Sensitive Provider Credential is available."
            )
        secret_payload = self.cipher.decrypt(
            credential.encrypted_payload,
            key_id=credential.encryption_key_id,
        )
        credential.last_accessed_at = timezone.now()
        credential.save(update_fields=["last_accessed_at", "updated_at"])
        self._audit(
            credential,
            SensitiveProviderCredentialAudit.EventType.RETRIEVED,
            actor=actor,
        )
        return RetrievedSensitiveProviderCredential(
            credential_id=credential.id,
            organizer_id=credential.organizer_id,
            provider=credential.provider,
            provider_mode=credential.provider_mode,
            credential_kind=credential.credential_kind,
            provider_account_reference=credential.provider_account_reference,
            scopes=list(credential.scopes),
            expires_at=credential.expires_at,
            secret_payload=secret_payload,
        )

    def safe_summary(self, credential: SensitiveProviderCredential) -> dict[str, Any]:
        return {
            "id": credential.id,
            "provider": credential.provider,
            "provider_mode": credential.provider_mode,
            "credential_kind": credential.credential_kind,
            "status": credential.status,
            "provider_account_reference": credential.provider_account_reference,
            "scopes": list(credential.scopes),
            "expires_at": credential.expires_at,
            "encryption_key_id": credential.encryption_key_id,
            "credential_fingerprint": credential.credential_fingerprint,
            "last_accessed_at": credential.last_accessed_at,
            "created_at": credential.created_at,
            "updated_at": credential.updated_at,
        }

    def _store(
        self,
        *,
        organizer: Organizer,
        credential_kind: str,
        provider_mode: str,
        provider_account_reference: str,
        scopes: list[str],
        expires_at,
        secret_payload: dict[str, Any],
        actor,
        rotated_from: SensitiveProviderCredential | None = None,
        status: str = SensitiveProviderCredential.Status.ACTIVE,
        rotate_existing_active: bool = True,
    ) -> SensitiveProviderCredential:
        provider_setup, _ = ProviderPaymentSetup.objects.get_or_create(organizer=organizer)
        now = timezone.now()
        if status == SensitiveProviderCredential.Status.ACTIVE and rotate_existing_active:
            existing_active = SensitiveProviderCredential.objects.select_for_update().filter(
                organizer=organizer,
                provider=provider_setup.provider,
                provider_mode=provider_mode,
                status=SensitiveProviderCredential.Status.ACTIVE,
            )
            if rotated_from is not None:
                existing_active = existing_active.exclude(pk=rotated_from.pk)
            for existing in existing_active:
                existing.status = SensitiveProviderCredential.Status.ROTATED
                existing.rotated_at = now
                existing.rotated_by = actor
                existing.save(update_fields=["status", "rotated_at", "rotated_by", "updated_at"])
                self._audit(
                    existing,
                    SensitiveProviderCredentialAudit.EventType.ROTATED,
                    actor=actor,
                    metadata={"replacement_credential_kind": credential_kind},
                )
        encrypted_payload, key_id = self.cipher.encrypt(secret_payload)
        credential = SensitiveProviderCredential.objects.create(
            organizer=organizer,
            provider_payment_setup=provider_setup,
            provider=provider_setup.provider,
            provider_mode=provider_mode,
            credential_kind=credential_kind,
            status=status,
            provider_account_reference=provider_account_reference.strip(),
            scopes=list(scopes),
            expires_at=expires_at,
            encrypted_payload=encrypted_payload,
            encryption_key_id=key_id,
            credential_fingerprint=self._fingerprint(secret_payload),
            created_by=actor,
        )
        self._audit(
            credential,
            SensitiveProviderCredentialAudit.EventType.STORED,
            actor=actor,
            metadata={
                "credential_kind": credential_kind,
                "provider_mode": provider_mode,
                "rotated_from": rotated_from.id if rotated_from is not None else None,
                "status": status,
            },
        )
        return credential

    def _audit(
        self,
        credential: SensitiveProviderCredential,
        event_type: str,
        *,
        actor=None,
        metadata: dict[str, Any] | None = None,
    ) -> SensitiveProviderCredentialAudit:
        return SensitiveProviderCredentialAudit.objects.create(
            organizer=credential.organizer,
            credential=credential,
            event_type=event_type,
            actor=actor,
            metadata=metadata or {},
        )

    def _fingerprint(self, secret_payload: dict[str, Any]) -> str:
        configured_key = str(
            getattr(settings, "TRIPOS_PROVIDER_CREDENTIAL_ENCRYPTION_KEY", settings.SECRET_KEY)
        ).encode("utf-8")
        digest = hmac.new(
            configured_key,
            json.dumps(secret_payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"sha256:{digest}"

    def _oauth_secret_payload(
        self,
        *,
        access_token: str,
        refresh_token: str,
        public_token: str = "",
    ) -> dict[str, str]:
        payload = {
            "access_token": self._require_secret(access_token, "access_token"),
            "refresh_token": self._require_secret(refresh_token, "refresh_token"),
        }
        if public_token.strip():
            payload["public_token"] = public_token.strip()
        return payload

    def _require_secret(self, value: str, field_name: str) -> str:
        if not value.strip():
            raise ValidationError(
                {field_name: "Sensitive Provider Credential material is required."}
            )
        return value.strip()


@transaction.atomic
def configure_assisted_api_key_credentials(
    *,
    organizer: Organizer,
    actor,
    key_id: str,
    key_secret: str,
    provider_account_reference: str,
    provider_mode: str = ProviderPaymentSetup.ProviderMode.TEST,
    webhook_secret: str = "",
    scopes: list[str] | None = None,
    expires_at=None,
    store: SensitiveProviderCredentialStore | None = None,
) -> SensitiveProviderCredential:
    if actor is None or not actor.is_authenticated or not actor.is_staff:
        raise PermissionDenied("Internal TripOS staff access is required.")
    credential_store = store or SensitiveProviderCredentialStore()
    credential = credential_store.store_api_key_credentials(
        organizer=organizer,
        key_id=key_id,
        key_secret=key_secret,
        webhook_secret=webhook_secret,
        provider_account_reference=provider_account_reference,
        provider_mode=provider_mode,
        scopes=scopes or [],
        expires_at=expires_at,
        actor=actor,
    )
    provider_setup = credential.provider_payment_setup
    provider_setup.provider_merchant_reference = provider_account_reference.strip()
    provider_setup.provider_mode = provider_mode
    provider_setup.authorization_method = ProviderPaymentSetup.AuthorizationMethod.API_KEY
    provider_setup.authorization_state = ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    provider_setup.provider_connection_state = ProviderPaymentSetup.ProviderConnectionState.HEALTHY
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
    return credential
