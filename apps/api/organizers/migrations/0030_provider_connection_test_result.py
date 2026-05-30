# Generated for TripOS Provider Connection Test results.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0029_provider_authorization_session"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProviderConnectionTestResult",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "provider",
                    models.CharField(
                        choices=[("razorpay", "Razorpay")], default="razorpay", max_length=32
                    ),
                ),
                (
                    "provider_mode",
                    models.CharField(
                        choices=[("test", "Test"), ("live", "Live")],
                        default="test",
                        max_length=12,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("running", "Running"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                        ],
                        default="running",
                        max_length=24,
                    ),
                ),
                ("provider_account_reference", models.CharField(blank=True, max_length=160)),
                ("provider_order_reference", models.CharField(blank=True, max_length=160)),
                ("provider_payment_reference", models.CharField(blank=True, max_length=160)),
                ("checks", models.JSONField(blank=True, default=dict)),
                ("checkout_payload", models.JSONField(blank=True, default=dict)),
                ("failure_reason", models.TextField(blank=True)),
                ("initiated_by_staff", models.BooleanField(default=False)),
                ("started_at", models.DateTimeField(default=timezone.now)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "initiated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="initiated_provider_connection_tests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organizer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="provider_connection_test_results",
                        to="organizers.organizer",
                    ),
                ),
                (
                    "provider_payment_setup",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="connection_test_results",
                        to="organizers.providerpaymentsetup",
                    ),
                ),
            ],
            options={
                "ordering": ["-started_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="providerconnectiontestresult",
            index=models.Index(
                fields=["organizer", "provider", "provider_mode", "status", "started_at"],
                name="provider_conn_test_lookup",
            ),
        ),
    ]
