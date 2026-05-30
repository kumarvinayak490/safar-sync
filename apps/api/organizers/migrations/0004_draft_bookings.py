# Generated manually for TripOS issue 06.

import django.db.models.deletion
from django.db import migrations, models

import organizers.models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0003_trip_setup"),
    ]

    operations = [
        migrations.CreateModel(
            name="Booking",
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
                ("booking_contact_name", models.CharField(max_length=160)),
                ("booking_contact_phone", models.CharField(max_length=40)),
                ("booking_contact_email", models.EmailField(blank=True, max_length=254)),
                (
                    "booking_state",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("reserved", "Reserved"),
                            ("confirmed", "Confirmed"),
                            ("cancelled", "Cancelled"),
                            ("completed", "Completed"),
                        ],
                        default="draft",
                        max_length=24,
                    ),
                ),
                (
                    "draft_expires_at",
                    models.DateTimeField(default=organizers.models.default_draft_expiry),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "trip",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bookings",
                        to="organizers.trip",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="TravelerSlot",
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
                ("position", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="traveler_slots",
                        to="organizers.booking",
                    ),
                ),
                (
                    "package",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="traveler_slots",
                        to="organizers.trippackage",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="travelerslot",
            constraint=models.UniqueConstraint(
                fields=("booking", "position"),
                name="unique_traveler_slot_position_per_booking",
            ),
        ),
    ]
