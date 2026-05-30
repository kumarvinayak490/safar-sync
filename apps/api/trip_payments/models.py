from __future__ import annotations

from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from organizer_payments.models import ProviderPaymentSetup
from organizers.models import Organizer
from trip_bookings.models import Booking, BookingImport
from trips.models import Trip


def default_seat_hold_expiry():
    hold_seconds = getattr(settings, "TRIPOS_SEAT_HOLD_SECONDS", 10 * 60)
    return timezone.now() + timezone.timedelta(seconds=hold_seconds)


def first_day_of_next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def manual_payment_proof_upload_path(instance, filename: str) -> str:
    organizer_id = instance.booking.trip.organizer_id
    trip_id = instance.booking.trip_id
    booking_id = instance.booking_id
    return (
        f"manual-payment-proofs/organizer-{organizer_id}/trip-{trip_id}/"
        f"booking-{booking_id}/{filename}"
    )


class LedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        PROVIDER_PAYMENT = "provider_payment", "Provider Payment"
        APPROVED_MANUAL_PAYMENT = "approved_manual_payment", "Approved Manual Payment"
        OPENING_PAYMENT_RECORD = "opening_payment_record", "Opening Payment Record"
        BOOKING_ADJUSTMENT = "booking_adjustment", "Booking Adjustment"
        PACKAGE_CHANGE = "package_change", "Package Change"
        REFUND_RECORD = "refund_record", "Refund Record"
        PLATFORM_FEE = "platform_fee", "Platform Fee"

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="ledger_entries",
    )
    entry_type = models.CharField(max_length=40, choices=EntryType.choices)
    amount_inr = models.IntegerField()
    currency = models.CharField(max_length=3, default="INR")
    description = models.CharField(max_length=240, blank=True)
    provider_payment = models.ForeignKey(
        "ProviderPayment",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="ledger_entries",
    )
    manual_payment = models.ForeignKey(
        "ManualPayment",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="ledger_entries",
    )
    opening_payment_record = models.ForeignKey(
        "OpeningPaymentRecord",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="ledger_entries",
    )
    booking_adjustment = models.ForeignKey(
        "BookingAdjustment",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="ledger_entries",
    )
    refund_record = models.ForeignKey(
        "RefundRecord",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="ledger_entries",
    )
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(currency="INR"),
                name="ledger_entry_currency_must_be_inr",
            ),
            models.CheckConstraint(
                condition=~models.Q(amount_inr=0),
                name="ledger_entry_amount_must_be_nonzero",
            ),
            models.UniqueConstraint(
                fields=["provider_payment", "entry_type"],
                condition=models.Q(provider_payment__isnull=False),
                name="unique_provider_payment_ledger_entry_type",
            ),
            models.UniqueConstraint(
                fields=["manual_payment", "entry_type"],
                condition=models.Q(manual_payment__isnull=False),
                name="unique_manual_payment_ledger_entry_type",
            ),
            models.UniqueConstraint(
                fields=["opening_payment_record", "entry_type"],
                condition=models.Q(opening_payment_record__isnull=False),
                name="unique_opening_payment_record_ledger_entry_type",
            ),
            models.UniqueConstraint(
                fields=["booking_adjustment", "entry_type"],
                condition=models.Q(booking_adjustment__isnull=False),
                name="unique_booking_adjustment_ledger_entry_type",
            ),
            models.UniqueConstraint(
                fields=["refund_record", "entry_type"],
                condition=models.Q(refund_record__isnull=False),
                name="unique_refund_record_ledger_entry_type",
            ),
        ]
        ordering = ["occurred_at", "id"]

    def __str__(self) -> str:
        return f"{self.get_entry_type_display()} for {self.booking}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.currency != "INR":
            raise ValidationError({"currency": "INR is the only supported money currency."})
        if self.amount_inr == 0:
            raise ValidationError({"amount_inr": "Ledger Entry amount cannot be zero."})
        if (
            self.provider_payment_id
            and self.booking_id
            and self.provider_payment.booking_id != self.booking_id
        ):
            raise ValidationError(
                {"provider_payment": "Ledger Entry must match the Provider Payment Booking."}
            )
        if (
            self.manual_payment_id
            and self.booking_id
            and self.manual_payment.booking_id != self.booking_id
        ):
            raise ValidationError(
                {"manual_payment": "Ledger Entry must match the Manual Payment Booking."}
            )
        if (
            self.opening_payment_record_id
            and self.booking_id
            and self.opening_payment_record.booking_id != self.booking_id
        ):
            raise ValidationError(
                {
                    "opening_payment_record": (
                        "Ledger Entry must match the Opening Payment Record Booking."
                    )
                }
            )
        if (
            self.booking_adjustment_id
            and self.booking_id
            and self.booking_adjustment.booking_id != self.booking_id
        ):
            raise ValidationError(
                {"booking_adjustment": ("Ledger Entry must match the Booking Adjustment Booking.")}
            )
        if (
            self.refund_record_id
            and self.booking_id
            and self.refund_record.booking_id != self.booking_id
        ):
            raise ValidationError(
                {"refund_record": "Ledger Entry must match the Refund Record Booking."}
            )


class BookingAdjustment(models.Model):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="booking_adjustments",
    )
    amount_inr = models.IntegerField()
    adjustment_reason = models.TextField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="recorded_booking_adjustments",
    )
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(amount_inr=0),
                name="booking_adjustment_amount_must_be_nonzero",
            ),
        ]
        ordering = ["-occurred_at", "-id"]

    def __str__(self) -> str:
        return f"Booking Adjustment {self.id} for {self.booking}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.amount_inr == 0:
            raise ValidationError({"amount_inr": "Booking Adjustment amount cannot be zero."})
        if not self.adjustment_reason.strip():
            raise ValidationError(
                {"adjustment_reason": "Booking Adjustment requires Adjustment Reason."}
            )


class RefundRecord(models.Model):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="refund_records",
    )
    amount_inr = models.PositiveIntegerField()
    refund_reason = models.TextField()
    refund_reference = models.CharField(max_length=160, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="recorded_refund_records",
    )
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_inr__gt=0),
                name="refund_record_amount_must_be_positive",
            ),
        ]
        ordering = ["-occurred_at", "-id"]

    def __str__(self) -> str:
        return f"Refund Record {self.id} for {self.booking}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.amount_inr <= 0:
            raise ValidationError({"amount_inr": "Refund Record amount must be positive."})
        if not self.refund_reason.strip():
            raise ValidationError({"refund_reason": "Refund Record requires Refund Reason."})


class PaymentAttempt(models.Model):
    class Provider(models.TextChoices):
        RAZORPAY = "razorpay", "Razorpay"

    class Purpose(models.TextChoices):
        RESERVATION = "reservation", "Reservation"
        BALANCE = "balance", "Balance"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMING = "confirming", "Confirming"
        CONFIRMED = "confirmed", "Confirmed"
        FAILED = "failed", "Failed"
        SUPERSEDED = "superseded", "Superseded"

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="payment_attempts",
    )
    provider = models.CharField(
        max_length=32,
        choices=Provider.choices,
        default=Provider.RAZORPAY,
    )
    purpose = models.CharField(
        max_length=24,
        choices=Purpose.choices,
        default=Purpose.RESERVATION,
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.PENDING,
    )
    amount_inr = models.PositiveIntegerField()
    provider_attempt_reference = models.CharField(max_length=160, blank=True)
    checkout_succeeded_at = models.DateTimeField(blank=True, null=True)
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_inr__gt=0),
                name="payment_attempt_amount_must_be_positive",
            ),
            models.UniqueConstraint(
                fields=["booking", "purpose"],
                condition=models.Q(status__in=["pending", "confirming"]),
                name="unique_active_payment_attempt_per_booking_purpose",
            ),
            models.UniqueConstraint(
                fields=["provider", "provider_attempt_reference"],
                condition=~models.Q(provider_attempt_reference=""),
                name="unique_provider_attempt_reference_per_provider",
            ),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"Payment Attempt {self.id} for {self.booking}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_active(self) -> bool:
        return self.status in {
            self.Status.PENDING,
            self.Status.CONFIRMING,
        }


class SeatHold(models.Model):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="seat_holds",
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="seat_holds",
    )
    payment_attempt = models.OneToOneField(
        PaymentAttempt,
        on_delete=models.CASCADE,
        related_name="seat_hold",
    )
    seat_count = models.PositiveIntegerField()
    expires_at = models.DateTimeField(default=default_seat_hold_expiry)
    released_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(seat_count__gt=0),
                name="seat_hold_count_must_be_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["trip", "released_at", "expires_at"],
                name="seat_hold_active_lookup",
            ),
        ]
        ordering = ["expires_at", "id"]

    def __str__(self) -> str:
        return f"Seat Hold {self.id} for {self.booking}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_active(self) -> bool:
        return self.released_at is None and self.expires_at > timezone.now()

    def clean(self):
        super().clean()
        if self.booking_id and self.trip_id and self.booking.trip_id != self.trip_id:
            raise ValidationError({"trip": "Seat Hold Trip must match the Booking Trip."})
        if (
            self.payment_attempt_id
            and self.booking_id
            and self.payment_attempt.booking_id != self.booking_id
        ):
            raise ValidationError(
                {"payment_attempt": "Seat Hold must match the Payment Attempt Booking."}
            )


class ProviderPayment(models.Model):
    class Provider(models.TextChoices):
        RAZORPAY = "razorpay", "Razorpay"

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="provider_payments",
    )
    payment_attempt = models.OneToOneField(
        PaymentAttempt,
        on_delete=models.PROTECT,
        related_name="provider_payment",
    )
    provider = models.CharField(
        max_length=32,
        choices=Provider.choices,
        default=Provider.RAZORPAY,
    )
    amount_inr = models.PositiveIntegerField()
    provider_fee_amount_inr = models.PositiveIntegerField(blank=True, null=True)
    provider_net_settlement_amount_inr = models.PositiveIntegerField(blank=True, null=True)
    provider_payment_reference = models.CharField(max_length=160, unique=True)
    confirmed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_inr__gt=0),
                name="provider_payment_amount_must_be_positive",
            ),
        ]
        ordering = ["-confirmed_at", "-id"]

    def __str__(self) -> str:
        return f"Provider Payment {self.provider_payment_reference} for {self.booking}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.payment_attempt_id and self.booking_id:
            attempt = self.payment_attempt
            if attempt.booking_id != self.booking_id:
                raise ValidationError(
                    {"payment_attempt": "Provider Payment must match the Payment Attempt Booking."}
                )
        if (
            self.provider_fee_amount_inr is not None
            and self.amount_inr is not None
            and self.provider_fee_amount_inr > self.amount_inr
        ):
            raise ValidationError(
                {
                    "provider_fee_amount_inr": (
                        "Provider Fee Amount cannot exceed Gross Provider Payment Amount."
                    )
                }
            )
        if (
            self.provider_net_settlement_amount_inr is not None
            and self.amount_inr is not None
            and self.provider_net_settlement_amount_inr > self.amount_inr
        ):
            raise ValidationError(
                {
                    "provider_net_settlement_amount_inr": (
                        "Provider Net Settlement Amount cannot exceed "
                        "Gross Provider Payment Amount."
                    )
                }
            )


class PlatformFeeStatement(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        COLLECTED = "collected", "Collected"
        VOID = "void", "Void"

    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.CASCADE,
        related_name="platform_fee_statements",
    )
    period_start = models.DateField()
    currency = models.CharField(max_length=3, default="INR")
    provider_payment_count = models.PositiveIntegerField(default=0)
    gross_provider_payment_amount_inr = models.PositiveIntegerField(default=0)
    platform_fee_amount_inr = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    notes = models.TextField(blank=True)
    generated_at = models.DateTimeField(blank=True, null=True)
    issued_at = models.DateTimeField(blank=True, null=True)
    collected_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(currency="INR"),
                name="platform_fee_statement_currency_must_be_inr",
            ),
            models.UniqueConstraint(
                fields=["organizer", "period_start"],
                name="unique_platform_fee_statement_organizer_period",
            ),
        ]
        ordering = ["-period_start", "organizer__name", "id"]

    def __str__(self) -> str:
        return f"Platform Fee Statement for {self.organizer} ({self.period_label})"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def period_end(self) -> date:
        return first_day_of_next_month(self.period_start)

    @property
    def period_label(self) -> str:
        return self.period_start.strftime("%B %Y")

    def clean(self):
        super().clean()
        if self.currency != "INR":
            raise ValidationError({"currency": "INR is the only supported money currency."})
        if self.period_start and self.period_start.day != 1:
            raise ValidationError(
                {"period_start": "Platform Fee Statement periods start on the first day."}
            )


class PaymentException(models.Model):
    class ExceptionType(models.TextChoices):
        LATE_CONFIRMED_PAYMENT = (
            "late_confirmed_payment",
            "Late Confirmed Payment Exception",
        )
        MISMATCHED_PROVIDER_PAYMENT = (
            "mismatched_provider_payment",
            "Mismatched Provider Payment Exception",
        )
        PROVIDER_DISPUTE = "provider_dispute", "Provider Dispute Exception"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        BOOKING_OPERATIONS_RESOLVED = (
            "booking_operations_resolved",
            "Booking Operations Resolved",
        )

    class ProviderEventType(models.TextChoices):
        DISPUTE = "dispute", "Dispute"
        CHARGEBACK = "chargeback", "Chargeback"

    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.CASCADE,
        related_name="payment_exceptions",
    )
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="payment_exceptions",
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="payment_exceptions",
    )
    payment_attempt = models.ForeignKey(
        PaymentAttempt,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="payment_exceptions",
    )
    provider_payment = models.ForeignKey(
        ProviderPayment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="payment_exceptions",
    )
    exception_type = models.CharField(max_length=40, choices=ExceptionType.choices)
    status = models.CharField(
        max_length=40,
        choices=Status.choices,
        default=Status.OPEN,
    )
    provider = models.CharField(max_length=32, blank=True)
    amount_inr = models.PositiveIntegerField()
    provider_attempt_reference = models.CharField(max_length=160, blank=True)
    provider_payment_reference = models.CharField(max_length=160, blank=True)
    provider_event_type = models.CharField(
        max_length=32,
        choices=ProviderEventType.choices,
        blank=True,
    )
    provider_dispute_reference = models.CharField(max_length=160, blank=True)
    mismatch_reasons = models.JSONField(default=list, blank=True)
    details = models.JSONField(default=dict, blank=True)
    resolution_note = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="resolved_payment_exceptions",
    )
    resolved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_inr__gt=0),
                name="payment_exception_amount_must_be_positive",
            ),
            models.UniqueConstraint(
                fields=["exception_type", "provider", "provider_payment_reference"],
                condition=~models.Q(provider_payment_reference=""),
                name="unique_payment_exception_provider_reference",
            ),
            models.UniqueConstraint(
                fields=["exception_type", "provider_dispute_reference"],
                condition=~models.Q(provider_dispute_reference=""),
                name="unique_payment_exception_dispute_reference",
            ),
            models.UniqueConstraint(
                fields=["exception_type", "provider_payment"],
                condition=models.Q(provider_payment__isnull=False),
                name="unique_payment_exception_provider_payment",
            ),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.get_exception_type_display()} {self.id} for {self.booking}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.amount_inr <= 0:
            raise ValidationError({"amount_inr": "Payment Exception amount must be positive."})
        if self.booking_id and self.trip_id and self.booking.trip_id != self.trip_id:
            raise ValidationError({"trip": "Payment Exception Trip must match Booking Trip."})
        if (
            self.booking_id
            and self.organizer_id
            and self.booking.trip.organizer_id != self.organizer_id
        ):
            raise ValidationError(
                {"organizer": "Payment Exception Organizer must match Booking Organizer."}
            )
        if (
            self.payment_attempt_id
            and self.booking_id
            and self.payment_attempt.booking_id != self.booking_id
        ):
            raise ValidationError(
                {"payment_attempt": ("Payment Exception must match the Payment Attempt Booking.")}
            )
        if (
            self.provider_payment_id
            and self.booking_id
            and self.provider_payment.booking_id != self.booking_id
        ):
            raise ValidationError(
                {"provider_payment": ("Payment Exception must match the Provider Payment Booking.")}
            )
        if (
            self.status == self.Status.BOOKING_OPERATIONS_RESOLVED
            and self.exception_type != self.ExceptionType.LATE_CONFIRMED_PAYMENT
        ):
            raise ValidationError(
                {
                    "status": (
                        "Only Late Confirmed Payment Exceptions support booking "
                        "operations resolution."
                    )
                }
            )
        if self.exception_type == self.ExceptionType.LATE_CONFIRMED_PAYMENT:
            if self.provider_payment_id is None:
                raise ValidationError(
                    {
                        "provider_payment": (
                            "Late Confirmed Payment Exception requires Provider Payment."
                        )
                    }
                )
        if self.exception_type == self.ExceptionType.MISMATCHED_PROVIDER_PAYMENT:
            if not self.mismatch_reasons:
                raise ValidationError(
                    {
                        "mismatch_reasons": (
                            "Mismatched Provider Payment Exception requires mismatch reasons."
                        )
                    }
                )
        if self.exception_type == self.ExceptionType.PROVIDER_DISPUTE:
            if self.provider_payment_id is None:
                raise ValidationError(
                    {"provider_payment": "Provider Dispute Exception requires Provider Payment."}
                )
            if not self.provider_event_type:
                raise ValidationError(
                    {"provider_event_type": "Provider Dispute Exception requires event type."}
                )
            if not self.provider_dispute_reference.strip():
                raise ValidationError(
                    {
                        "provider_dispute_reference": (
                            "Provider Dispute Exception requires dispute reference."
                        )
                    }
                )


class ProviderWebhookEvent(models.Model):
    class ProcessingStatus(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSED = "processed", "Processed"
        IGNORED = "ignored", "Ignored"
        FAILED = "failed", "Failed"

    provider = models.CharField(
        max_length=32,
        choices=ProviderPaymentSetup.Provider.choices,
        default=ProviderPaymentSetup.Provider.RAZORPAY,
    )
    provider_event_reference = models.CharField(max_length=200)
    event_type = models.CharField(max_length=120)
    provider_account_reference = models.CharField(max_length=160, blank=True)
    provider_attempt_reference = models.CharField(max_length=160, blank=True)
    provider_payment_reference = models.CharField(max_length=160, blank=True)
    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="provider_webhook_events",
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="provider_webhook_events",
    )
    payment_attempt = models.ForeignKey(
        PaymentAttempt,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="provider_webhook_events",
    )
    provider_payment = models.ForeignKey(
        ProviderPayment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="provider_webhook_events",
    )
    payment_exception = models.ForeignKey(
        PaymentException,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="provider_webhook_events",
    )
    processing_status = models.CharField(
        max_length=24,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.RECEIVED,
    )
    ignored_reason = models.TextField(blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_event_reference"],
                name="unique_provider_webhook_event_reference",
            ),
        ]
        indexes = [
            models.Index(fields=["provider", "event_type"], name="provider_webhook_event_type"),
            models.Index(
                fields=["provider", "provider_payment_reference"],
                name="provider_webhook_payment_ref",
            ),
            models.Index(
                fields=["provider", "provider_attempt_reference"],
                name="provider_webhook_attempt_ref",
            ),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.provider} webhook {self.provider_event_reference}"


class ManualPayment(models.Model):
    class Source(models.TextChoices):
        ORGANIZER_ENTERED = "organizer_entered", "Organizer-entered"
        TRAVELER_SUBMITTED = "traveler_submitted", "Traveler-submitted"

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="manual_payments",
    )
    source = models.CharField(
        max_length=32,
        choices=Source.choices,
        default=Source.ORGANIZER_ENTERED,
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.APPROVED,
    )
    amount_inr = models.PositiveIntegerField()
    payment_reference = models.CharField(max_length=160, blank=True)
    payment_proof = models.FileField(upload_to=manual_payment_proof_upload_path, blank=True)
    original_filename = models.CharField(max_length=240, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    note = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="approved_manual_payments",
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_inr__gt=0),
                name="manual_payment_amount_must_be_positive",
            ),
        ]
        ordering = ["-submitted_at", "-id"]

    def __str__(self) -> str:
        return f"{self.get_status_display()} Manual Payment {self.id} for {self.booking}"

    def save(self, *args, **kwargs):
        if self.status == self.Status.APPROVED and self.approved_at is None:
            self.approved_at = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_sensitive_payment_information(self) -> bool:
        return bool(self.payment_proof)

    @property
    def exclude_from_default_exports(self) -> bool:
        return self.is_sensitive_payment_information


class OpeningPaymentRecord(models.Model):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="opening_payment_records",
    )
    booking_import = models.ForeignKey(
        BookingImport,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="opening_payment_records",
    )
    amount_inr = models.PositiveIntegerField()
    payment_reference = models.CharField(max_length=160, blank=True)
    note = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="recorded_opening_payment_records",
    )
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_inr__gt=0),
                name="opening_payment_record_amount_must_be_positive",
            ),
        ]
        ordering = ["-occurred_at", "-id"]

    def __str__(self) -> str:
        return f"Opening Payment Record {self.id} for {self.booking}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

