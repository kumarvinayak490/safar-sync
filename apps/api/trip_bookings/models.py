from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from trips.models import Trip


def default_draft_expiry():
    return timezone.now() + timezone.timedelta(hours=24)


def default_access_link_expiry():
    return timezone.now() + timezone.timedelta(days=14)


class Booking(models.Model):
    class BookingState(models.TextChoices):
        DRAFT = "draft", "Draft"
        RESERVED = "reserved", "Reserved"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    booking_contact_name = models.CharField(max_length=160)
    booking_contact_phone = models.CharField(max_length=40)
    booking_contact_email = models.EmailField(blank=True)
    booking_state = models.CharField(
        max_length=24,
        choices=BookingState.choices,
        default=BookingState.DRAFT,
    )
    draft_expires_at = models.DateTimeField(default=default_draft_expiry)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"Booking {self.id} for {self.trip}"

    def save(self, *args, **kwargs):
        revoke_booking_level_links = False
        if self.pk:
            prior = (
                type(self)
                .objects.filter(pk=self.pk)
                .only(
                    "booking_contact_name",
                    "booking_contact_phone",
                    "booking_contact_email",
                )
                .first()
            )
            revoke_booking_level_links = prior is not None and (
                prior.booking_contact_name != self.booking_contact_name
                or prior.booking_contact_phone != self.booking_contact_phone
                or prior.booking_contact_email != self.booking_contact_email
            )
        self.full_clean()
        super().save(*args, **kwargs)
        if revoke_booking_level_links:
            from trip_bookings.access_links import revoke_booking_level_access_links

            revoke_booking_level_access_links(self)

    @property
    def is_draft(self) -> bool:
        return self.booking_state == self.BookingState.DRAFT

    @property
    def booking_reservation_amount_inr(self) -> int:
        from trip_travelers.slots import booking_reservation_amount_inr

        return booking_reservation_amount_inr(self)

    @property
    def booking_total_inr(self) -> int:
        from trip_travelers.slots import booking_total_inr

        return booking_total_inr(self)

    @property
    def collected_provider_payment_amount_inr(self) -> int:
        from trip_payments.financial_ledger import collected_provider_payment_amount_inr

        return collected_provider_payment_amount_inr(self)

    @property
    def traveler_slot_count(self) -> int:
        from trip_travelers.slots import traveler_slot_count_for_booking

        return traveler_slot_count_for_booking(self)


class BookingImport(models.Model):
    class Status(models.TextChoices):
        COMPLETED = "completed", "Completed"
        COMPLETED_WITH_CONFLICTS = "completed_with_conflicts", "Completed with conflicts"

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="booking_imports",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="submitted_booking_imports",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.COMPLETED,
    )
    source_filename = models.CharField(max_length=240, blank=True)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    conflict_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "organizers"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"Booking Import {self.id} for {self.trip}"


class BookingImportRow(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        SKIPPED = "skipped", "Skipped"
        CONFLICT = "conflict", "Conflict"

    booking_import = models.ForeignKey(
        BookingImport,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="import_rows",
    )
    row_number = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices)
    conflict_code = models.CharField(max_length=80, blank=True)
    message = models.CharField(max_length=240, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.UniqueConstraint(
                fields=["booking_import", "row_number"],
                name="unique_booking_import_row_number",
            )
        ]
        ordering = ["row_number", "id"]

    def __str__(self) -> str:
        return f"Booking Import Row {self.row_number} for {self.booking_import}"


class BookingAccessLink(models.Model):
    class Scope(models.TextChoices):
        BOOKING = "booking", "Booking-Level"
        TRAVELER = "traveler", "Traveler-Level"

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="access_links",
    )
    traveler_slot = models.ForeignKey(
        "organizers.TravelerSlot",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="access_links",
    )
    scope = models.CharField(max_length=16, choices=Scope.choices)
    token_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(default=default_access_link_expiry)
    revoked_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(scope="booking", traveler_slot__isnull=True)
                    | models.Q(scope="traveler", traveler_slot__isnull=False)
                ),
                name="access_link_scope_matches_traveler_slot",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_scope_display()} Access Link for {self.booking}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and not self.is_expired

    def clean(self):
        super().clean()
        if self.scope == self.Scope.BOOKING and self.traveler_slot_id is not None:
            raise ValidationError(
                {"traveler_slot": "Booking-Level Access Links cannot target one Traveler Slot."}
            )
        if self.scope == self.Scope.TRAVELER and self.traveler_slot_id is None:
            raise ValidationError(
                {"traveler_slot": "Traveler-Level Access Links require a Traveler Slot."}
            )
        if (
            self.booking_id
            and self.traveler_slot_id
            and self.traveler_slot.booking_id != self.booking_id
        ):
            raise ValidationError(
                {"traveler_slot": "Traveler-Level Access Link must match the Booking."}
            )
