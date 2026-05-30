# Generated manually for TripOS issue 07.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0004_draft_bookings"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentAttempt",
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
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("confirmed", "Confirmed"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=24,
                    ),
                ),
                ("amount_inr", models.PositiveIntegerField()),
                ("provider_attempt_reference", models.CharField(blank=True, max_length=160)),
                ("failure_reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_attempts",
                        to="organizers.booking",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="ProviderPayment",
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
                ("amount_inr", models.PositiveIntegerField()),
                (
                    "provider_payment_reference",
                    models.CharField(max_length=160, unique=True),
                ),
                ("confirmed_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="provider_payments",
                        to="organizers.booking",
                    ),
                ),
                (
                    "payment_attempt",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="provider_payment",
                        to="organizers.paymentattempt",
                    ),
                ),
            ],
            options={
                "ordering": ["-confirmed_at", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="paymentattempt",
            constraint=models.CheckConstraint(
                condition=models.Q(("amount_inr__gt", 0)),
                name="payment_attempt_amount_must_be_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="providerpayment",
            constraint=models.CheckConstraint(
                condition=models.Q(("amount_inr__gt", 0)),
                name="provider_payment_amount_must_be_positive",
            ),
        ),
    ]
