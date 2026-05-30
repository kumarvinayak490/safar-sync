# Generated for TripOS Razorpay webhook ingestion.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0032_settlement_readiness_source"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProviderWebhookEvent",
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
                    "provider",
                    models.CharField(
                        choices=[("razorpay", "Razorpay")],
                        default="razorpay",
                        max_length=32,
                    ),
                ),
                ("provider_event_reference", models.CharField(max_length=200)),
                ("event_type", models.CharField(max_length=120)),
                ("provider_account_reference", models.CharField(blank=True, max_length=160)),
                ("provider_attempt_reference", models.CharField(blank=True, max_length=160)),
                ("provider_payment_reference", models.CharField(blank=True, max_length=160)),
                (
                    "processing_status",
                    models.CharField(
                        choices=[
                            ("received", "Received"),
                            ("processed", "Processed"),
                            ("ignored", "Ignored"),
                            ("failed", "Failed"),
                        ],
                        default="received",
                        max_length=24,
                    ),
                ),
                ("ignored_reason", models.TextField(blank=True)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "booking",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="provider_webhook_events",
                        to="organizers.booking",
                    ),
                ),
                (
                    "organizer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="provider_webhook_events",
                        to="organizers.organizer",
                    ),
                ),
                (
                    "payment_attempt",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="provider_webhook_events",
                        to="organizers.paymentattempt",
                    ),
                ),
                (
                    "payment_exception",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="provider_webhook_events",
                        to="organizers.paymentexception",
                    ),
                ),
                (
                    "provider_payment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="provider_webhook_events",
                        to="organizers.providerpayment",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="providerwebhookevent",
            constraint=models.UniqueConstraint(
                fields=("provider", "provider_event_reference"),
                name="unique_provider_webhook_event_reference",
            ),
        ),
        migrations.AddIndex(
            model_name="providerwebhookevent",
            index=models.Index(
                fields=["provider", "event_type"],
                name="provider_webhook_event_type",
            ),
        ),
        migrations.AddIndex(
            model_name="providerwebhookevent",
            index=models.Index(
                fields=["provider", "provider_payment_reference"],
                name="provider_webhook_payment_ref",
            ),
        ),
        migrations.AddIndex(
            model_name="providerwebhookevent",
            index=models.Index(
                fields=["provider", "provider_attempt_reference"],
                name="provider_webhook_attempt_ref",
            ),
        ),
    ]
