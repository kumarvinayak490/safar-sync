from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from trip_bookings.models import Booking
from trips.models import TripPackage


def traveler_document_upload_path(instance, filename: str) -> str:
    organizer_id = instance.traveler_slot.booking.trip.organizer_id
    trip_id = instance.traveler_slot.booking.trip_id
    traveler_slot_id = instance.traveler_slot_id
    return (
        f"traveler-documents/organizer-{organizer_id}/trip-{trip_id}/"
        f"traveler-slot-{traveler_slot_id}/{filename}"
    )


class TravelerSlot(models.Model):
    class TravelerState(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "cancelled", "Cancelled"
        REPLACED = "replaced", "Replaced"
        PENDING_ADDITION = "pending_addition", "Pending Addition"

    class AttendanceState(models.TextChoices):
        NOT_MARKED = "not_marked", "Not marked"
        CHECKED_IN = "checked_in", "Checked in"
        NO_SHOW = "no_show", "No-show"

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="traveler_slots",
    )
    package = models.ForeignKey(
        TripPackage,
        on_delete=models.PROTECT,
        related_name="traveler_slots",
    )
    position = models.PositiveIntegerField(default=1)
    traveler_state = models.CharField(
        max_length=32,
        choices=TravelerState.choices,
        default=TravelerState.ACTIVE,
    )
    booked_package_price_inr = models.PositiveIntegerField(default=0)
    booked_reservation_amount_inr = models.PositiveIntegerField(default=0)
    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="cancelled_traveler_slots",
    )
    replaced_by_slot = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="replaces_slot",
    )
    addition_reserved_at = models.DateTimeField(blank=True, null=True)
    traveler_full_name = models.CharField(max_length=160, blank=True)
    traveler_phone = models.CharField(max_length=40, blank=True)
    traveler_email = models.EmailField(blank=True)
    arrival_details = models.CharField(max_length=240, blank=True)
    departure_details = models.CharField(max_length=240, blank=True)
    pickup_location = models.CharField(max_length=160, blank=True)
    logistics_note = models.TextField(blank=True)
    rooming_notes = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=160, blank=True)
    emergency_contact_phone = models.CharField(max_length=40, blank=True)
    emergency_contact_relationship = models.CharField(max_length=80, blank=True)
    medical_disclosure = models.TextField(blank=True)
    medical_disclosure_submitted_at = models.DateTimeField(blank=True, null=True)
    attendance_state = models.CharField(
        max_length=24,
        choices=AttendanceState.choices,
        default=AttendanceState.NOT_MARKED,
    )
    attendance_marked_at = models.DateTimeField(blank=True, null=True)
    attendance_marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="marked_traveler_attendance",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "position"],
                name="unique_traveler_slot_position_per_booking",
            )
        ]
        ordering = ["position", "id"]

    def __str__(self) -> str:
        if self.is_traveler:
            return f"Traveler {self.traveler_full_name} for {self.booking}"
        return f"Traveler Slot {self.position} for {self.booking}"

    def save(self, *args, **kwargs):
        if self.package_id:
            if self.booked_package_price_inr == 0:
                self.booked_package_price_inr = self.package.price_inr
            if self.booked_reservation_amount_inr == 0:
                self.booked_reservation_amount_inr = self.package.reservation_amount_inr
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.booking_id and self.package_id and self.package.trip_id != self.booking.trip_id:
            raise ValidationError({"package": "Traveler Slot Package must belong to the Trip."})

    @property
    def is_traveler(self) -> bool:
        return bool(self.traveler_full_name.strip() and self.traveler_phone.strip())

    @property
    def is_active_for_capacity(self) -> bool:
        return self.traveler_state == self.TravelerState.ACTIVE

    @property
    def has_travel_logistics(self) -> bool:
        return any(
            [
                self.arrival_details.strip(),
                self.departure_details.strip(),
                self.pickup_location.strip(),
                self.logistics_note.strip(),
            ]
        )

    @property
    def has_emergency_contact(self) -> bool:
        return bool(
            self.emergency_contact_name.strip()
            and self.emergency_contact_phone.strip()
            and self.emergency_contact_relationship.strip()
        )

    @property
    def has_medical_disclosure(self) -> bool:
        return bool(self.medical_disclosure.strip())


class TravelerDocument(models.Model):
    class DocumentKind(models.TextChoices):
        IDENTITY = "identity", "Identity Traveler Document"
        ELIGIBILITY = "eligibility", "Eligibility Traveler Document"

    class DocumentState(models.TextChoices):
        MISSING = "missing", "Missing"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    traveler_slot = models.ForeignKey(
        TravelerSlot,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_kind = models.CharField(
        max_length=24,
        choices=DocumentKind.choices,
        default=DocumentKind.IDENTITY,
    )
    label = models.CharField(max_length=120, default="Identity Document")
    document_state = models.CharField(
        max_length=24,
        choices=DocumentState.choices,
        default=DocumentState.MISSING,
    )
    file = models.FileField(upload_to=traveler_document_upload_path, blank=True)
    original_filename = models.CharField(max_length=240, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    rejection_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reviewed_traveler_documents",
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.UniqueConstraint(
                fields=["traveler_slot", "document_kind", "label"],
                name="unique_traveler_document_label_per_slot",
            )
        ]
        ordering = ["traveler_slot__position", "document_kind", "label", "id"]

    def __str__(self) -> str:
        return f"{self.label} for {self.traveler_slot}"

    def save(self, *args, **kwargs):
        if self.document_kind == self.DocumentKind.IDENTITY and not self.label:
            self.label = "Identity Document"
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_sensitive_traveler_information(self) -> bool:
        return self.document_kind == self.DocumentKind.IDENTITY

    @property
    def exclude_from_default_exports(self) -> bool:
        return self.is_sensitive_traveler_information

