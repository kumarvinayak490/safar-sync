# Generated manually for TripOS issue 08.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0005_provider_payments"),
    ]

    operations = [
        migrations.CreateModel(
            name="LedgerEntry",
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
                    "entry_type",
                    models.CharField(
                        choices=[
                            ("provider_payment", "Provider Payment"),
                            ("approved_manual_payment", "Approved Manual Payment"),
                            ("opening_payment_record", "Opening Payment Record"),
                            ("booking_adjustment", "Booking Adjustment"),
                            ("refund_record", "Refund Record"),
                            ("platform_fee", "Platform Fee"),
                        ],
                        max_length=40,
                    ),
                ),
                ("amount_inr", models.IntegerField()),
                ("currency", models.CharField(default="INR", max_length=3)),
                ("description", models.CharField(blank=True, max_length=240)),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ledger_entries",
                        to="organizers.booking",
                    ),
                ),
                (
                    "provider_payment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ledger_entries",
                        to="organizers.providerpayment",
                    ),
                ),
            ],
            options={
                "ordering": ["occurred_at", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="ledgerentry",
            constraint=models.CheckConstraint(
                condition=models.Q(currency="INR"),
                name="ledger_entry_currency_must_be_inr",
            ),
        ),
        migrations.AddConstraint(
            model_name="ledgerentry",
            constraint=models.CheckConstraint(
                condition=~models.Q(amount_inr=0),
                name="ledger_entry_amount_must_be_nonzero",
            ),
        ),
        migrations.AddConstraint(
            model_name="ledgerentry",
            constraint=models.UniqueConstraint(
                condition=models.Q(provider_payment__isnull=False),
                fields=("provider_payment", "entry_type"),
                name="unique_provider_payment_ledger_entry_type",
            ),
        ),
    ]
