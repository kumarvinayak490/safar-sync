# Generated manually for TripOS issue 16.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0011_alter_activitylog_action_notification"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BookingAdjustment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("amount_inr", models.IntegerField()),
                ("adjustment_reason", models.TextField()),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="booking_adjustments",
                        to="organizers.booking",
                    ),
                ),
                (
                    "recorded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="recorded_booking_adjustments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-occurred_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="RefundRecord",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("amount_inr", models.PositiveIntegerField()),
                ("refund_reason", models.TextField()),
                ("refund_reference", models.CharField(blank=True, max_length=160)),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="refund_records",
                        to="organizers.booking",
                    ),
                ),
                (
                    "recorded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="recorded_refund_records",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-occurred_at", "-id"],
            },
        ),
        migrations.AddField(
            model_name="ledgerentry",
            name="booking_adjustment",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ledger_entries",
                to="organizers.bookingadjustment",
            ),
        ),
        migrations.AddField(
            model_name="ledgerentry",
            name="refund_record",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ledger_entries",
                to="organizers.refundrecord",
            ),
        ),
        migrations.AlterField(
            model_name="activitylog",
            name="action",
            field=models.CharField(
                choices=[
                    ("notification_sent", "Notification Sent"),
                    ("booking_adjustment_recorded", "Booking Adjustment Recorded"),
                    ("refund_record_recorded", "Refund Record Recorded"),
                    ("traveler_checked_in", "Traveler Checked In"),
                    ("traveler_marked_no_show", "Traveler Marked No-Show"),
                    (
                        "sensitive_traveler_information_download",
                        "Sensitive Traveler Information Download",
                    ),
                    ("traveler_document_approved", "Traveler Document Approved"),
                    ("traveler_document_rejected", "Traveler Document Rejected"),
                ],
                max_length=80,
            ),
        ),
        migrations.AddConstraint(
            model_name="bookingadjustment",
            constraint=models.CheckConstraint(
                condition=~models.Q(amount_inr=0),
                name="booking_adjustment_amount_must_be_nonzero",
            ),
        ),
        migrations.AddConstraint(
            model_name="refundrecord",
            constraint=models.CheckConstraint(
                condition=models.Q(("amount_inr__gt", 0)),
                name="refund_record_amount_must_be_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="ledgerentry",
            constraint=models.UniqueConstraint(
                condition=models.Q(("booking_adjustment__isnull", False)),
                fields=("booking_adjustment", "entry_type"),
                name="unique_booking_adjustment_ledger_entry_type",
            ),
        ),
        migrations.AddConstraint(
            model_name="ledgerentry",
            constraint=models.UniqueConstraint(
                condition=models.Q(("refund_record__isnull", False)),
                fields=("refund_record", "entry_type"),
                name="unique_refund_record_ledger_entry_type",
            ),
        ),
    ]
