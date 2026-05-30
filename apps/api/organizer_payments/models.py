from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from organizers.models import Organizer


def default_provider_authorization_state_expiry():
    state_seconds = getattr(settings, "TRIPOS_PROVIDER_AUTHORIZATION_STATE_SECONDS", 15 * 60)
    return timezone.now() + timezone.timedelta(seconds=state_seconds)


def payment_qr_upload_path(instance, filename: str) -> str:
    extension = filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else "qr"
    return f"payment-qr/organizer-{instance.organizer_id}/payment-qr.{extension}"


class PayoutAccount(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        ACTION_REQUIRED = "action_required", "Action required"

    class SettlementReadinessSource(models.TextChoices):
        PROVIDER_DERIVED = "provider_derived", "Provider derived"
        SUPPORT_CONFIRMED = "support_confirmed", "Support confirmed"

    organizer = models.OneToOneField(
        Organizer,
        on_delete=models.CASCADE,
        related_name="payout_account",
    )
    holder_name = models.CharField(max_length=160, blank=True)
    provider_account_reference = models.CharField(max_length=160, blank=True)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    settlement_readiness_source = models.CharField(
        max_length=24,
        choices=SettlementReadinessSource.choices,
        default=SettlementReadinessSource.PROVIDER_DERIVED,
    )
    support_confirmed_at = models.DateTimeField(blank=True, null=True)
    support_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="support_confirmed_settlement_readiness",
    )
    support_confirmation_notes = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        ordering = ["organizer__name", "id"]

    def __str__(self) -> str:
        return f"Payout Account for {self.organizer}"


class ProviderPaymentSetup(models.Model):
    class Provider(models.TextChoices):
        RAZORPAY = "razorpay", "Razorpay"

    class AuthorizationMethod(models.TextChoices):
        OAUTH = "oauth", "OAuth Provider Authorization"
        API_KEY = "api_key", "API Key Provider Authorization"
        ASSISTED = "assisted", "Assisted Payment Setup"

    class AuthorizationState(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        PENDING = "pending", "Pending"
        AUTHORIZED = "authorized", "Authorized"
        ACTION_REQUIRED = "action_required", "Action required"
        REVOKED = "revoked", "Revoked"

    class ProviderVerificationStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        DETAILS_NEEDED = "details_needed", "Details needed"
        SUBMITTED = "submitted", "Submitted"
        IN_REVIEW = "in_review", "In review"
        ACTION_REQUIRED = "action_required", "Action required"
        VERIFIED = "verified", "Verified"

    class ProviderConnectionState(models.TextChoices):
        HEALTHY = "healthy", "Healthy"
        UNHEALTHY = "unhealthy", "Unhealthy"

    class ProviderMode(models.TextChoices):
        TEST = "test", "Test"
        LIVE = "live", "Live"

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        PENDING = "pending", "Pending"
        COMPLETE = "complete", "Complete"
        ACTION_REQUIRED = "action_required", "Action required"

    organizer = models.OneToOneField(
        Organizer,
        on_delete=models.CASCADE,
        related_name="provider_payment_setup",
    )
    provider = models.CharField(
        max_length=32,
        choices=Provider.choices,
        default=Provider.RAZORPAY,
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    provider_merchant_reference = models.CharField(max_length=160, blank=True)
    authorization_method = models.CharField(
        max_length=24,
        choices=AuthorizationMethod.choices,
        default=AuthorizationMethod.OAUTH,
    )
    authorization_state = models.CharField(
        max_length=24,
        choices=AuthorizationState.choices,
        default=AuthorizationState.NOT_STARTED,
    )
    provider_verification_status = models.CharField(
        max_length=24,
        choices=ProviderVerificationStatus.choices,
        default=ProviderVerificationStatus.NOT_STARTED,
    )
    provider_payment_capability_enabled = models.BooleanField(default=False)
    provider_connection_state = models.CharField(
        max_length=24,
        choices=ProviderConnectionState.choices,
        default=ProviderConnectionState.UNHEALTHY,
    )
    provider_mode = models.CharField(
        max_length=12,
        choices=ProviderMode.choices,
        default=ProviderMode.TEST,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        ordering = ["organizer__name", "id"]

    def __str__(self) -> str:
        return f"Provider Payment Setup for {self.organizer}"

    @property
    def is_complete(self) -> bool:
        return self.status == self.Status.COMPLETE


class ManualPaymentInstructions(models.Model):
    organizer = models.OneToOneField(
        Organizer,
        on_delete=models.CASCADE,
        related_name="manual_payment_instructions",
    )
    payment_qr = models.FileField(upload_to=payment_qr_upload_path, max_length=255, blank=True)
    original_filename = models.CharField(max_length=240, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    upi_id = models.CharField(max_length=80, blank=True)
    account_name = models.CharField(max_length=160, blank=True)
    bank_transfer_details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        ordering = ["organizer__name", "id"]

    def __str__(self) -> str:
        return f"Manual Payment Instructions for {self.organizer}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        self.upi_id = self.upi_id.strip()
        self.account_name = self.account_name.strip()
        self.bank_transfer_details = self.bank_transfer_details.strip()

    @property
    def payment_qr_url(self) -> str:
        if not self.payment_qr:
            return ""
        try:
            return self.payment_qr.url
        except ValueError:
            return ""

    @property
    def is_ready(self) -> bool:
        return bool(self.payment_qr)


class SensitiveProviderCredential(models.Model):
    class CredentialKind(models.TextChoices):
        OAUTH = "oauth", "OAuth Provider Authorization"
        API_KEY = "api_key", "API Key Provider Authorization"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING_REPLACEMENT = "pending_replacement", "Pending replacement"
        ROTATED = "rotated", "Rotated"
        REVOKED = "revoked", "Revoked"

    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.CASCADE,
        related_name="sensitive_provider_credentials",
    )
    provider_payment_setup = models.ForeignKey(
        ProviderPaymentSetup,
        on_delete=models.CASCADE,
        related_name="sensitive_credentials",
    )
    provider = models.CharField(
        max_length=32,
        choices=ProviderPaymentSetup.Provider.choices,
        default=ProviderPaymentSetup.Provider.RAZORPAY,
    )
    provider_mode = models.CharField(
        max_length=12,
        choices=ProviderPaymentSetup.ProviderMode.choices,
        default=ProviderPaymentSetup.ProviderMode.TEST,
    )
    credential_kind = models.CharField(max_length=24, choices=CredentialKind.choices)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    provider_account_reference = models.CharField(max_length=160, blank=True)
    scopes = models.JSONField(default=list, blank=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    encrypted_payload = models.TextField()
    encryption_key_id = models.CharField(max_length=80)
    credential_fingerprint = models.CharField(max_length=96)
    last_accessed_at = models.DateTimeField(blank=True, null=True)
    rotated_at = models.DateTimeField(blank=True, null=True)
    revoked_at = models.DateTimeField(blank=True, null=True)
    revoked_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_sensitive_provider_credentials",
    )
    rotated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="rotated_sensitive_provider_credentials",
    )
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="revoked_sensitive_provider_credentials",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.UniqueConstraint(
                fields=["organizer", "provider", "provider_mode"],
                condition=models.Q(status="active"),
                name="unique_active_sensitive_provider_credential",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organizer", "provider", "provider_mode", "status"],
                name="cred_active_lookup",
            ),
            models.Index(
                fields=["provider", "provider_account_reference"],
                name="cred_provider_acct_lookup",
            ),
        ]
        ordering = ["organizer__name", "-created_at", "-id"]

    def __str__(self) -> str:
        return (
            f"{self.get_credential_kind_display()} credential "
            f"for {self.organizer} in {self.get_provider_mode_display()} mode"
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if (
            self.organizer_id
            and self.provider_payment_setup_id
            and self.provider_payment_setup.organizer_id != self.organizer_id
        ):
            raise ValidationError(
                {
                    "provider_payment_setup": (
                        "Sensitive Provider Credential must match the Organizer's "
                        "Provider Payment Setup."
                    )
                }
            )
        if not self.encrypted_payload.strip():
            raise ValidationError({"encrypted_payload": "Encrypted payload is required."})
        if not self.encryption_key_id.strip():
            raise ValidationError({"encryption_key_id": "Encryption key id is required."})
        if not self.credential_fingerprint.strip():
            raise ValidationError({"credential_fingerprint": "Credential fingerprint is required."})
        if not isinstance(self.scopes, list):
            raise ValidationError({"scopes": "Scopes must be a list."})
        if self.status == self.Status.ACTIVE:
            if self.revoked_at is not None:
                raise ValidationError(
                    {"revoked_at": "Active credentials cannot have a revoked timestamp."}
                )
            if self.rotated_at is not None:
                raise ValidationError(
                    {"rotated_at": "Active credentials cannot have a rotated timestamp."}
                )
        if self.status == self.Status.REVOKED and self.revoked_at is None:
            raise ValidationError({"revoked_at": "Revoked credentials need a timestamp."})
        if self.status == self.Status.ROTATED and self.rotated_at is None:
            raise ValidationError({"rotated_at": "Rotated credentials need a timestamp."})


class SensitiveProviderCredentialAudit(models.Model):
    class EventType(models.TextChoices):
        STORED = "stored", "Stored"
        RETRIEVED = "retrieved", "Retrieved"
        ROTATED = "rotated", "Rotated"
        REVOKED = "revoked", "Revoked"

    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.CASCADE,
        related_name="sensitive_provider_credential_audits",
    )
    credential = models.ForeignKey(
        SensitiveProviderCredential,
        on_delete=models.CASCADE,
        related_name="audit_events",
    )
    event_type = models.CharField(max_length=24, choices=EventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="sensitive_provider_credential_audits",
    )
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "organizers"
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(
                fields=["organizer", "event_type", "occurred_at"],
                name="cred_audit_event_lookup",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_event_type_display()} credential event for {self.organizer}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if (
            self.organizer_id
            and self.credential_id
            and self.credential.organizer_id != self.organizer_id
        ):
            raise ValidationError(
                {"credential": "Credential audit must match the credential Organizer."}
            )


class ProviderAuthorizationSession(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        BLOCKED = "blocked", "Blocked"

    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.CASCADE,
        related_name="provider_authorization_sessions",
    )
    provider_payment_setup = models.ForeignKey(
        ProviderPaymentSetup,
        on_delete=models.CASCADE,
        related_name="authorization_sessions",
    )
    provider = models.CharField(
        max_length=32,
        choices=ProviderPaymentSetup.Provider.choices,
        default=ProviderPaymentSetup.Provider.RAZORPAY,
    )
    provider_mode = models.CharField(
        max_length=12,
        choices=ProviderPaymentSetup.ProviderMode.choices,
        default=ProviderPaymentSetup.ProviderMode.TEST,
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.PENDING,
    )
    state_digest = models.CharField(max_length=96, unique=True)
    client_id = models.CharField(max_length=160)
    redirect_uri = models.CharField(max_length=600)
    scopes = models.JSONField(default=list, blank=True)
    provider_account_reference = models.CharField(max_length=160, blank=True)
    failure_reason = models.TextField(blank=True)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="initiated_provider_authorization_sessions",
    )
    expires_at = models.DateTimeField(default=default_provider_authorization_state_expiry)
    completed_at = models.DateTimeField(blank=True, null=True)
    failed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["organizer", "provider", "status", "expires_at"],
                name="provider_auth_state_lookup",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_provider_display()} Provider Authorization "
            f"for {self.organizer} ({self.get_status_display()})"
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if (
            self.organizer_id
            and self.provider_payment_setup_id
            and self.provider_payment_setup.organizer_id != self.organizer_id
        ):
            raise ValidationError(
                {
                    "provider_payment_setup": (
                        "Provider Authorization Session must match the Organizer's "
                        "Provider Payment Setup."
                    )
                }
            )
        if not self.state_digest.strip():
            raise ValidationError({"state_digest": "State digest is required."})
        if not self.client_id.strip():
            raise ValidationError({"client_id": "OAuth client id is required."})
        if not self.redirect_uri.strip():
            raise ValidationError({"redirect_uri": "Redirect URI is required."})
        if not isinstance(self.scopes, list):
            raise ValidationError({"scopes": "Scopes must be a list."})
        if self.status == self.Status.COMPLETED and self.completed_at is None:
            raise ValidationError({"completed_at": "Completed sessions need a timestamp."})
        if self.status in {self.Status.FAILED, self.Status.BLOCKED} and self.failed_at is None:
            raise ValidationError({"failed_at": "Failed sessions need a timestamp."})


class ProviderConnectionTestResult(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.CASCADE,
        related_name="provider_connection_test_results",
    )
    provider_payment_setup = models.ForeignKey(
        ProviderPaymentSetup,
        on_delete=models.CASCADE,
        related_name="connection_test_results",
    )
    provider = models.CharField(
        max_length=32,
        choices=ProviderPaymentSetup.Provider.choices,
        default=ProviderPaymentSetup.Provider.RAZORPAY,
    )
    provider_mode = models.CharField(
        max_length=12,
        choices=ProviderPaymentSetup.ProviderMode.choices,
        default=ProviderPaymentSetup.ProviderMode.TEST,
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.RUNNING,
    )
    provider_account_reference = models.CharField(max_length=160, blank=True)
    provider_order_reference = models.CharField(max_length=160, blank=True)
    provider_payment_reference = models.CharField(max_length=160, blank=True)
    checks = models.JSONField(default=dict, blank=True)
    checkout_payload = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="initiated_provider_connection_tests",
    )
    initiated_by_staff = models.BooleanField(default=False)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        ordering = ["-started_at", "-id"]
        indexes = [
            models.Index(
                fields=["organizer", "provider", "provider_mode", "status", "started_at"],
                name="provider_conn_test_lookup",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_provider_display()} Provider Connection Test "
            f"for {self.organizer} ({self.get_status_display()})"
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if (
            self.organizer_id
            and self.provider_payment_setup_id
            and self.provider_payment_setup.organizer_id != self.organizer_id
        ):
            raise ValidationError(
                {
                    "provider_payment_setup": (
                        "Provider Connection Test Result must match the Organizer's "
                        "Provider Payment Setup."
                    )
                }
            )
        if not isinstance(self.checks, dict):
            raise ValidationError({"checks": "Provider Connection Test checks must be an object."})
        if not isinstance(self.checkout_payload, dict):
            raise ValidationError(
                {"checkout_payload": "Provider Connection Test checkout payload must be an object."}
            )
        if self.status in {self.Status.SUCCEEDED, self.Status.FAILED}:
            if self.completed_at is None:
                raise ValidationError({"completed_at": "Completed test results need a timestamp."})
        if self.status == self.Status.FAILED and not self.failure_reason.strip():
            raise ValidationError({"failure_reason": "Failed test results need a reason."})

