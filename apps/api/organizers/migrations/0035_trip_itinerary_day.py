import organizers.rich_text
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0034_trip_description_rich_text"),
    ]

    operations = [
        migrations.CreateModel(
            name="TripItineraryDay",
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
                ("sequence", models.PositiveIntegerField()),
                ("title", models.CharField(max_length=140)),
                ("date_label", models.CharField(blank=True, max_length=80)),
                (
                    "description_rich_text",
                    models.JSONField(
                        blank=True,
                        default=organizers.rich_text.default_trip_rich_text,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "trip",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="itinerary_days",
                        to="organizers.trip",
                    ),
                ),
            ],
            options={
                "ordering": ["sequence", "id"],
            },
        ),
        migrations.AlterField(
            model_name="activitylog",
            name="action",
            field=models.CharField(
                choices=[
                    ("notification_sent", "Notification Sent"),
                    ("booking_cancelled", "Booking Cancelled"),
                    ("traveler_cancelled", "Traveler Cancelled"),
                    ("traveler_replaced", "Traveler Replaced"),
                    ("traveler_addition_created", "Traveler Addition Created"),
                    ("traveler_addition_reserved", "Traveler Addition Reserved"),
                    ("traveler_package_changed", "Traveler Package Changed"),
                    ("booking_adjustment_recorded", "Booking Adjustment Recorded"),
                    ("refund_record_recorded", "Refund Record Recorded"),
                    ("payment_exception_created", "Payment Exception Created"),
                    ("payment_exception_resolved", "Payment Exception Resolved"),
                    ("traveler_checked_in", "Traveler Checked In"),
                    ("traveler_marked_no_show", "Traveler Marked No-Show"),
                    (
                        "sensitive_traveler_information_download",
                        "Sensitive Traveler Information Download",
                    ),
                    (
                        "sensitive_payment_information_download",
                        "Sensitive Payment Information Download",
                    ),
                    ("traveler_document_approved", "Traveler Document Approved"),
                    ("traveler_document_rejected", "Traveler Document Rejected"),
                    ("operational_export_generated", "Operational Export Generated"),
                    ("trip_duplicated", "Trip Duplicated"),
                    ("trip_date_changed", "Trip Date Changed"),
                    ("trip_cancelled", "Trip Cancelled"),
                    ("trip_completed", "Trip Completed"),
                    ("booking_completed", "Booking Completed"),
                    ("trip_description_updated", "Trip Description Updated"),
                    ("trip_itinerary_updated", "Trip Itinerary Updated"),
                ],
                max_length=80,
            ),
        ),
        migrations.AddConstraint(
            model_name="tripitineraryday",
            constraint=models.UniqueConstraint(
                fields=("trip", "sequence"),
                name="unique_itinerary_day_sequence_per_trip",
            ),
        ),
        migrations.AddConstraint(
            model_name="tripitineraryday",
            constraint=models.CheckConstraint(
                condition=models.Q(sequence__gt=0),
                name="itinerary_day_sequence_must_be_positive",
            ),
        ),
    ]
