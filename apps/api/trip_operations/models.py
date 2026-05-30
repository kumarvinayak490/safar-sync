from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from organizers.models import Organizer
from trip_bookings.models import Booking
from trip_payments.models import ManualPayment, ProviderPayment
from trip_travelers.models import TravelerDocument, TravelerSlot
from trips.models import Trip


class ActivityLog(models.Model):
    class Action(models.TextChoices):
        NOTIFICATION_SENT = "notification_sent", "Notification Sent"
        BOOKING_CANCELLED = "booking_cancelled", "Booking Cancelled"
        TRAVELER_CANCELLED = "traveler_cancelled", "Traveler Cancelled"
        TRAVELER_REPLACED = "traveler_replaced", "Traveler Replaced"
        TRAVELER_ADDITION_CREATED = "traveler_addition_created", "Traveler Addition Created"
        TRAVELER_ADDITION_RESERVED = "traveler_addition_reserved", "Traveler Addition Reserved"
        TRAVELER_PACKAGE_CHANGED = "traveler_package_changed", "Traveler Package Changed"
        BOOKING_ADJUSTMENT_RECORDED = (
            "booking_adjustment_recorded",
            "Booking Adjustment Recorded",
        )
        REFUND_RECORD_RECORDED = "refund_record_recorded", "Refund Record Recorded"
        PAYMENT_EXCEPTION_CREATED = "payment_exception_created", "Payment Exception Created"
        PAYMENT_EXCEPTION_RESOLVED = "payment_exception_resolved", "Payment Exception Resolved"
        TRAVELER_CHECKED_IN = "traveler_checked_in", "Traveler Checked In"
        TRAVELER_MARKED_NO_SHOW = "traveler_marked_no_show", "Traveler Marked No-Show"
        SENSITIVE_TRAVELER_INFORMATION_DOWNLOAD = (
            "sensitive_traveler_information_download",
            "Sensitive Traveler Information Download",
        )
        SENSITIVE_PAYMENT_INFORMATION_DOWNLOAD = (
            "sensitive_payment_information_download",
            "Sensitive Payment Information Download",
        )
        TRAVELER_DOCUMENT_APPROVED = "traveler_document_approved", "Traveler Document Approved"
        TRAVELER_DOCUMENT_REJECTED = "traveler_document_rejected", "Traveler Document Rejected"
        OPERATIONAL_EXPORT_GENERATED = (
            "operational_export_generated",
            "Operational Export Generated",
        )
        TRIP_DUPLICATED = "trip_duplicated", "Trip Duplicated"
        TRIP_DATE_CHANGED = "trip_date_changed", "Trip Date Changed"
        TRIP_CANCELLED = "trip_cancelled", "Trip Cancelled"
        TRIP_COMPLETED = "trip_completed", "Trip Completed"
        BOOKING_COMPLETED = "booking_completed", "Booking Completed"
        TRIP_DESCRIPTION_UPDATED = "trip_description_updated", "Trip Description Updated"
        TRIP_ITINERARY_UPDATED = "trip_itinerary_updated", "Trip Itinerary Updated"
        TRIP_MEDIA_GALLERY_UPDATED = (
            "trip_media_gallery_updated",
            "Trip Media Gallery Updated",
        )
        TRIP_PACKAGES_UPDATED = "trip_packages_updated", "Trip Packages Updated"
        TRIP_PAYMENT_SCHEDULE_UPDATED = (
            "trip_payment_schedule_updated",
            "Trip Payment Schedule Updated",
        )
        TRIP_CONFIRMATION_REQUIREMENTS_UPDATED = (
            "trip_confirmation_requirements_updated",
            "Trip Confirmation Requirements Updated",
        )
        PUBLIC_TRIP_PAGE_PUBLISHED = (
            "public_trip_page_published",
            "Public Trip Page Published",
        )

    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.CASCADE,
        related_name="activity_logs",
    )
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="activity_logs",
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="activity_logs",
    )
    traveler_slot = models.ForeignKey(
        TravelerSlot,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="activity_logs",
    )
    traveler_document = models.ForeignKey(
        TravelerDocument,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="activity_logs",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="activity_logs",
    )
    action = models.CharField(max_length=80, choices=Action.choices)
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "organizers"
        ordering = ["-occurred_at", "-id"]

    def __str__(self) -> str:
        if self.booking_id is None:
            return f"{self.get_action_display()} for {self.trip}"
        return f"{self.get_action_display()} for {self.booking}"


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        DRAFT_RECOVERY_REMINDER = "draft_recovery_reminder", "Draft Recovery Reminder"
        BALANCE_DUE_REMINDER = "balance_due_reminder", "Balance Due Reminder"
        OVERDUE_BALANCE_REMINDER = "overdue_balance_reminder", "Overdue Balance Reminder"
        MISSING_REQUIREMENTS_REMINDER = (
            "missing_requirements_reminder",
            "Missing Requirements Reminder",
        )
        MANUAL_REMINDER = "manual_reminder", "Manual Reminder"
        ANNOUNCEMENT = "announcement", "Announcement"
        RESERVATION_ACKNOWLEDGEMENT = (
            "reservation_acknowledgement",
            "Reservation Acknowledgement",
        )
        CONFIRMATION_NOTICE = "confirmation_notice", "Confirmation Notice"
        PAYMENT_ACKNOWLEDGEMENT = (
            "payment_acknowledgement",
            "Payment Acknowledgement",
        )
        REFUND_ACKNOWLEDGEMENT = "refund_acknowledgement", "Refund Acknowledgement"
        DATE_CHANGE_NOTICE = "date_change_notice", "Date Change Notice"
        CANCELLATION_NOTICE = "cancellation_notice", "Cancellation Notice"

    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        EMAIL = "email", "Email"

    class RecipientType(models.TextChoices):
        BOOKING_CONTACT = "booking_contact", "Booking Contact"
        TRAVELER = "traveler", "Traveler"

    class Status(models.TextChoices):
        SENT = "sent", "Sent"

    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    traveler_slot = models.ForeignKey(
        TravelerSlot,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="notifications",
    )
    provider_payment = models.ForeignKey(
        ProviderPayment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="notifications",
    )
    manual_payment = models.ForeignKey(
        ManualPayment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=40, choices=NotificationType.choices)
    channel = models.CharField(max_length=16, choices=Channel.choices)
    recipient_type = models.CharField(max_length=24, choices=RecipientType.choices)
    recipient_name = models.CharField(max_length=160)
    recipient_phone = models.CharField(max_length=40, blank=True)
    recipient_email = models.EmailField(blank=True)
    organizer_identity_name = models.CharField(max_length=160)
    organizer_identity_logo_url = models.URLField(blank=True)
    subject = models.CharField(max_length=180)
    body = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SENT)
    idempotency_key = models.CharField(max_length=220, unique=True)
    metadata = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        ordering = ["-sent_at", "-id"]

    def __str__(self) -> str:
        return f"{self.get_notification_type_display()} to {self.recipient_name}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.channel == self.Channel.WHATSAPP and not self.recipient_phone.strip():
            raise ValidationError({"recipient_phone": "WhatsApp Notifications need a phone."})
        if self.channel == self.Channel.EMAIL and not self.recipient_email.strip():
            raise ValidationError({"recipient_email": "Email Notifications need an email."})
        if (
            self.traveler_slot_id
            and self.booking_id
            and self.traveler_slot.booking_id != self.booking_id
        ):
            raise ValidationError(
                {"traveler_slot": "Notification Traveler must belong to the Booking."}
            )
        if (
            self.provider_payment_id
            and self.booking_id
            and self.provider_payment.booking_id != self.booking_id
        ):
            raise ValidationError(
                {"provider_payment": "Notification must match the Provider Payment Booking."}
            )
        if (
            self.manual_payment_id
            and self.booking_id
            and self.manual_payment.booking_id != self.booking_id
        ):
            raise ValidationError(
                {"manual_payment": "Notification must match the Manual Payment Booking."}
            )

