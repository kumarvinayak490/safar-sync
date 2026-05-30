# Generated manually for TripOS issue 10.

import django.db.models.deletion
from django.db import migrations, models

import organizers.models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0006_financial_ledger"),
    ]

    operations = [
        migrations.AddField(
            model_name="travelerslot",
            name="traveler_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="travelerslot",
            name="traveler_full_name",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="travelerslot",
            name="traveler_phone",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.CreateModel(
            name="BookingAccessLink",
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
                    "scope",
                    models.CharField(
                        choices=[
                            ("booking", "Booking-Level"),
                            ("traveler", "Traveler-Level"),
                        ],
                        max_length=16,
                    ),
                ),
                ("token_digest", models.CharField(max_length=64, unique=True)),
                (
                    "expires_at",
                    models.DateTimeField(default=organizers.models.default_access_link_expiry),
                ),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_links",
                        to="organizers.booking",
                    ),
                ),
                (
                    "traveler_slot",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_links",
                        to="organizers.travelerslot",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="bookingaccesslink",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(scope="booking", traveler_slot__isnull=True)
                    | models.Q(scope="traveler", traveler_slot__isnull=False)
                ),
                name="access_link_scope_matches_traveler_slot",
            ),
        ),
    ]
