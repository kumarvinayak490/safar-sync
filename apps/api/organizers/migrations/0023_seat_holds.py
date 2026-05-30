# Generated for TripOS connected-provider Seat Holds.

import django.db.models.deletion
from django.db import migrations, models

import organizers.models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0022_connected_provider_account_setup"),
    ]

    operations = [
        migrations.CreateModel(
            name="SeatHold",
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
                ("seat_count", models.PositiveIntegerField()),
                (
                    "expires_at",
                    models.DateTimeField(default=organizers.models.default_seat_hold_expiry),
                ),
                ("released_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="seat_holds",
                        to="organizers.booking",
                    ),
                ),
                (
                    "payment_attempt",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="seat_hold",
                        to="organizers.paymentattempt",
                    ),
                ),
                (
                    "trip",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="seat_holds",
                        to="organizers.trip",
                    ),
                ),
            ],
            options={
                "ordering": ["expires_at", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="seathold",
            constraint=models.CheckConstraint(
                condition=models.Q(("seat_count__gt", 0)),
                name="seat_hold_count_must_be_positive",
            ),
        ),
        migrations.AddIndex(
            model_name="seathold",
            index=models.Index(
                fields=["trip", "released_at", "expires_at"],
                name="seat_hold_active_lookup",
            ),
        ),
    ]
