"""Organizer aggregate root model and historical migration anchor.

This module deliberately defines only the Organizer root model. The imports at
the bottom keep old ``organizers.models`` callers working while persisted model
ownership moves into domain apps through staged migrations.
"""

from __future__ import annotations

from django.db import models
from django.utils.text import slugify


def organizer_logo_upload_path(instance, filename: str) -> str:
    extension = filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else "logo"
    return f"organizer-logos/organizer-{instance.id}/logo.{extension}"


class Organizer(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    identity_name = models.CharField(max_length=160, blank=True)
    identity_whatsapp_number = models.CharField(max_length=40, blank=True)
    identity_logo = models.FileField(
        upload_to=organizer_logo_upload_path,
        max_length=255,
        blank=True,
    )
    identity_logo_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:180]
        super().save(*args, **kwargs)

    @property
    def display_identity_name(self) -> str:
        from organizer_profile.identity import public_organizer_name

        return public_organizer_name(self)

    @property
    def display_identity_logo_url(self) -> str:
        from organizer_profile.identity import public_organizer_logo_url

        return public_organizer_logo_url(self)


# Compatibility import surface while call sites move to domain apps. Do not add
# new business models to this module for organizer-adjacent domains.
from organizer_payments.models import (  # noqa: E402,F401
    ManualPaymentInstructions,
    PayoutAccount,
    ProviderAuthorizationSession,
    ProviderConnectionTestResult,
    ProviderPaymentSetup,
    SensitiveProviderCredential,
    SensitiveProviderCredentialAudit,
    default_provider_authorization_state_expiry,
    payment_qr_upload_path,
)
from team_access.models import (  # noqa: E402,F401
    OrganizerInvitation,
    OrganizerMembership,
    default_invitation_token,
)
from trip_bookings.models import (  # noqa: E402,F401
    Booking,
    BookingAccessLink,
    BookingImport,
    BookingImportRow,
    default_access_link_expiry,
    default_draft_expiry,
)
from trip_operations.models import ActivityLog, Notification  # noqa: E402,F401
from trip_payments.models import (  # noqa: E402,F401
    BookingAdjustment,
    LedgerEntry,
    ManualPayment,
    OpeningPaymentRecord,
    PaymentAttempt,
    PaymentException,
    PlatformFeeStatement,
    ProviderPayment,
    ProviderWebhookEvent,
    RefundRecord,
    SeatHold,
    default_seat_hold_expiry,
    first_day_of_next_month,
    manual_payment_proof_upload_path,
)
from trip_travelers.models import (  # noqa: E402,F401
    TravelerDocument,
    TravelerSlot,
    traveler_document_upload_path,
)
from trips.models import (  # noqa: E402,F401
    Trip,
    TripItineraryDay,
    TripMediaAsset,
    TripMediaItem,
    TripPackage,
    TripPackageQuerySet,
    TripPaymentSchedule,
    trip_media_asset_upload_path,
    trip_media_storage_key,
)
