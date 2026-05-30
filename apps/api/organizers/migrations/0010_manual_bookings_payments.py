# Generated manually for TripOS issue 14.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import organizers.models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0009_confirmation_requirements"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ManualPayment",
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
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("organizer_entered", "Organizer-entered"),
                            ("traveler_submitted", "Traveler-submitted"),
                        ],
                        default="organizer_entered",
                        max_length=32,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("submitted", "Submitted"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ],
                        default="approved",
                        max_length=24,
                    ),
                ),
                ("amount_inr", models.PositiveIntegerField()),
                ("payment_reference", models.CharField(blank=True, max_length=160)),
                (
                    "payment_proof",
                    models.FileField(
                        blank=True,
                        upload_to=organizers.models.manual_payment_proof_upload_path,
                    ),
                ),
                ("original_filename", models.CharField(blank=True, max_length=240)),
                ("content_type", models.CharField(blank=True, max_length=120)),
                ("file_size", models.PositiveIntegerField(default=0)),
                ("note", models.TextField(blank=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("submitted_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="approved_manual_payments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="manual_payments",
                        to="organizers.booking",
                    ),
                ),
            ],
            options={
                "ordering": ["-submitted_at", "-id"],
            },
        ),
        migrations.AddField(
            model_name="ledgerentry",
            name="manual_payment",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ledger_entries",
                to="organizers.manualpayment",
            ),
        ),
        migrations.AddConstraint(
            model_name="manualpayment",
            constraint=models.CheckConstraint(
                condition=models.Q(("amount_inr__gt", 0)),
                name="manual_payment_amount_must_be_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="ledgerentry",
            constraint=models.UniqueConstraint(
                condition=models.Q(("manual_payment__isnull", False)),
                fields=("manual_payment", "entry_type"),
                name="unique_manual_payment_ledger_entry_type",
            ),
        ),
    ]
