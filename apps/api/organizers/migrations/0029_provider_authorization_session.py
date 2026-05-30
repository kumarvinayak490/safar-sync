# Generated for TripOS Razorpay OAuth Provider Authorization state.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import organizers.models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0028_sensitive_provider_credentials"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProviderAuthorizationSession",
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
                            ("pending", "Pending"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("blocked", "Blocked"),
                        ],
                        default="pending",
                        max_length=24,
                    ),
                ),
                ("state_digest", models.CharField(max_length=96, unique=True)),
                ("client_id", models.CharField(max_length=160)),
                ("redirect_uri", models.CharField(max_length=600)),
                ("scopes", models.JSONField(blank=True, default=list)),
                ("provider_account_reference", models.CharField(blank=True, max_length=160)),
                ("failure_reason", models.TextField(blank=True)),
                (
                    "expires_at",
                    models.DateTimeField(
                        default=organizers.models.default_provider_authorization_state_expiry
                    ),
                ),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "initiated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="initiated_provider_authorization_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organizer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="provider_authorization_sessions",
                        to="organizers.organizer",
                    ),
                ),
                (
                    "provider_payment_setup",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="authorization_sessions",
                        to="organizers.providerpaymentsetup",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="providerauthorizationsession",
            index=models.Index(
                fields=["organizer", "provider", "status", "expires_at"],
                name="provider_auth_state_lookup",
            ),
        ),
    ]
