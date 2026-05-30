# Generated manually for TripOS issue 04.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0002_payment_setup"),
    ]

    operations = [
        migrations.CreateModel(
            name="Trip",
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
                ("title", models.CharField(max_length=180)),
                ("slug", models.SlugField(blank=True, max_length=200)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("capacity", models.PositiveIntegerField()),
                ("confirmation_requirements_note", models.TextField(blank=True)),
                ("itinerary", models.TextField(blank=True)),
                (
                    "publication_state",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("published", "Published"),
                            ("archived", "Archived"),
                        ],
                        default="draft",
                        max_length=24,
                    ),
                ),
                (
                    "booking_availability",
                    models.CharField(
                        choices=[("closed", "Closed"), ("open", "Open")],
                        default="closed",
                        max_length=24,
                    ),
                ),
                ("public_url_path", models.CharField(blank=True, max_length=240)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organizer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trips",
                        to="organizers.organizer",
                    ),
                ),
            ],
            options={
                "ordering": ["start_date", "title", "id"],
            },
        ),
        migrations.CreateModel(
            name="TripPackage",
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
                ("name", models.CharField(max_length=140)),
                ("price_inr", models.PositiveIntegerField()),
                ("reservation_amount_inr", models.PositiveIntegerField()),
                ("description", models.TextField(blank=True)),
                ("position", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "trip",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="packages",
                        to="organizers.trip",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "id"],
            },
        ),
        migrations.CreateModel(
            name="TripPaymentSchedule",
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
                    "balance_due_days_before_start",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                ("balance_reminder_lead_days", models.PositiveIntegerField(default=3)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "trip",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_schedule",
                        to="organizers.trip",
                    ),
                ),
            ],
            options={
                "ordering": ["trip__start_date", "trip__title", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="trip",
            constraint=models.UniqueConstraint(
                fields=("organizer", "slug"),
                name="unique_trip_slug_per_organizer",
            ),
        ),
        migrations.AddConstraint(
            model_name="trip",
            constraint=models.CheckConstraint(
                condition=models.Q(capacity__gt=0),
                name="trip_capacity_must_be_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="trippackage",
            constraint=models.CheckConstraint(
                condition=models.Q(price_inr__gt=0),
                name="trip_package_price_must_be_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="trippackage",
            constraint=models.CheckConstraint(
                condition=models.Q(reservation_amount_inr__gt=0),
                name="trip_package_reservation_amount_must_be_positive",
            ),
        ),
    ]
