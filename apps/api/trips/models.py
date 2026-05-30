from __future__ import annotations

import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from organizers.models import Organizer
from trips.rich_text import default_trip_rich_text, sanitize_trip_rich_text


def trip_media_storage_key() -> str:
    return secrets.token_urlsafe(18)


def trip_media_asset_upload_path(instance, filename: str) -> str:
    extension = filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else "image"
    return (
        f"trip-media/organizer-{instance.organizer_id}/"
        f"{instance.storage_key}.{extension}"
    )


class Trip(models.Model):
    class PublicationState(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    class BookingAvailability(models.TextChoices):
        CLOSED = "closed", "Closed"
        OPEN = "open", "Open"

    class ManualPaymentAvailability(models.TextChoices):
        CLOSED = "closed", "Closed"
        OPEN = "open", "Open"

    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.CASCADE,
        related_name="trips",
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    capacity = models.PositiveIntegerField()
    confirmation_requirements_note = models.TextField(blank=True)
    requires_traveler_documents = models.BooleanField(default=False)
    requires_traveler_identity_details = models.BooleanField(default=False)
    requires_travel_logistics = models.BooleanField(default=False)
    requires_emergency_contact = models.BooleanField(default=False)
    requires_medical_disclosure = models.BooleanField(default=False)
    requires_full_payment_before_confirmation = models.BooleanField(default=False)
    confirmation_requirements_reviewed_at = models.DateTimeField(blank=True, null=True)
    confirmation_requirements_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reviewed_trip_confirmation_requirements",
    )
    description_rich_text = models.JSONField(default=default_trip_rich_text, blank=True)
    itinerary = models.TextField(blank=True)
    publication_state = models.CharField(
        max_length=24,
        choices=PublicationState.choices,
        default=PublicationState.DRAFT,
    )
    booking_availability = models.CharField(
        max_length=24,
        choices=BookingAvailability.choices,
        default=BookingAvailability.CLOSED,
    )
    manual_payment_availability = models.CharField(
        max_length=24,
        choices=ManualPaymentAvailability.choices,
        default=ManualPaymentAvailability.CLOSED,
    )
    public_url_path = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.UniqueConstraint(
                fields=["organizer", "slug"],
                name="unique_trip_slug_per_organizer",
            ),
            models.CheckConstraint(
                condition=models.Q(capacity__gt=0),
                name="trip_capacity_must_be_positive",
            ),
        ]
        ordering = ["start_date", "title", "id"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:200]
        if not self.public_url_path and self.organizer_id and self.slug:
            self.public_url_path = f"/trips/{self.organizer.slug}/{self.slug}"
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "Trip end date cannot be before Trip Start Date."})
        self.description_rich_text = sanitize_trip_rich_text(self.description_rich_text)

    @property
    def confirmation_requirements_reviewed(self) -> bool:
        return self.confirmation_requirements_reviewed_at is not None


class TripItineraryDay(models.Model):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="itinerary_days",
    )
    sequence = models.PositiveIntegerField()
    title = models.CharField(max_length=140)
    date_label = models.CharField(max_length=80, blank=True)
    description_rich_text = models.JSONField(default=default_trip_rich_text, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.UniqueConstraint(
                fields=["trip", "sequence"],
                name="unique_itinerary_day_sequence_per_trip",
            ),
            models.CheckConstraint(
                condition=models.Q(sequence__gt=0),
                name="itinerary_day_sequence_must_be_positive",
            ),
        ]
        ordering = ["sequence", "id"]

    def __str__(self) -> str:
        return f"Day {self.sequence}: {self.title}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        self.title = self.title.strip()
        self.date_label = self.date_label.strip()
        if not self.title:
            raise ValidationError({"title": "Itinerary Day title is required."})
        self.description_rich_text = sanitize_trip_rich_text(self.description_rich_text)


class TripMediaAsset(models.Model):
    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.CASCADE,
        related_name="trip_media_assets",
    )
    uploaded_for_trip = models.ForeignKey(
        Trip,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="uploaded_media_assets",
    )
    image = models.FileField(upload_to=trip_media_asset_upload_path, max_length=255)
    storage_key = models.CharField(max_length=48, unique=True, default=trip_media_storage_key)
    original_filename = models.CharField(max_length=240, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="uploaded_trip_media_assets",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "organizers"
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return self.original_filename or f"Trip Media Asset {self.id}"

    @property
    def image_url(self) -> str:
        if not self.image:
            return ""
        try:
            return self.image.url
        except ValueError:
            return ""


class TripMediaItem(models.Model):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="media_items",
    )
    asset = models.ForeignKey(
        TripMediaAsset,
        on_delete=models.PROTECT,
        related_name="media_items",
    )
    position = models.PositiveIntegerField(default=1)
    caption = models.CharField(max_length=220, blank=True)
    alt_text = models.CharField(max_length=220, blank=True)
    is_public = models.BooleanField(default=False)
    is_cover = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        ordering = ["position", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(position__gt=0),
                name="trip_media_item_position_must_be_positive",
            ),
            models.UniqueConstraint(
                fields=["trip"],
                condition=models.Q(is_cover=True),
                name="unique_cover_trip_media_item_per_trip",
            ),
        ]

    def __str__(self) -> str:
        return f"Trip Media Item {self.position} for {self.trip}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        self.caption = self.caption.strip()
        self.alt_text = self.alt_text.strip()
        if self.trip_id and self.asset_id and self.asset.organizer_id != self.trip.organizer_id:
            raise ValidationError({"asset": "Trip Media Asset must belong to the Trip Organizer."})
        if self.is_cover and self.trip_id:
            existing_cover = type(self).objects.filter(trip_id=self.trip_id, is_cover=True)
            if self.pk:
                existing_cover = existing_cover.exclude(pk=self.pk)
            if existing_cover.exists():
                raise ValidationError({"is_cover": "A Trip can have only one cover image."})


class TripPackageQuerySet(models.QuerySet):
    def active(self):
        return self.filter(lifecycle_state=TripPackage.LifecycleState.ACTIVE)

    def withdrawn(self):
        return self.filter(lifecycle_state=TripPackage.LifecycleState.WITHDRAWN)


class TripPackage(models.Model):
    class LifecycleState(models.TextChoices):
        ACTIVE = "active", "Active"
        WITHDRAWN = "withdrawn", "Withdrawn"

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="packages",
    )
    name = models.CharField(max_length=140)
    price_inr = models.PositiveIntegerField()
    reservation_amount_inr = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=1)
    lifecycle_state = models.CharField(
        max_length=16,
        choices=LifecycleState.choices,
        default=LifecycleState.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TripPackageQuerySet.as_manager()

    class Meta:
        app_label = "organizers"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price_inr__gt=0),
                name="trip_package_price_must_be_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(reservation_amount_inr__gt=0),
                name="trip_package_reservation_amount_must_be_positive",
            ),
        ]
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return f"{self.name} for {self.trip}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if (
            self.price_inr
            and self.reservation_amount_inr
            and self.reservation_amount_inr > self.price_inr
        ):
            raise ValidationError(
                {"reservation_amount_inr": ("Reservation Amount cannot exceed Package price.")}
            )

    @property
    def is_withdrawn(self) -> bool:
        return self.lifecycle_state == self.LifecycleState.WITHDRAWN


class TripPaymentSchedule(models.Model):
    trip = models.OneToOneField(
        Trip,
        on_delete=models.CASCADE,
        related_name="payment_schedule",
    )
    balance_due_days_before_start = models.PositiveIntegerField(blank=True, null=True)
    balance_reminder_lead_days = models.PositiveIntegerField(default=3)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reviewed_trip_payment_schedules",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        ordering = ["trip__start_date", "trip__title", "id"]

    def __str__(self) -> str:
        return f"Payment Schedule for {self.trip}"

    @property
    def has_balance_milestone(self) -> bool:
        return self.balance_due_days_before_start is not None

    @property
    def is_reviewed(self) -> bool:
        return self.reviewed_at is not None

    @property
    def balance_due_date(self):
        if self.balance_due_days_before_start is None:
            return None
        from datetime import timedelta

        return self.trip.start_date - timedelta(days=self.balance_due_days_before_start)

