import organizers.rich_text
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0033_provider_webhook_event"),
    ]

    operations = [
        migrations.AddField(
            model_name="trip",
            name="description_rich_text",
            field=models.JSONField(
                blank=True,
                default=organizers.rich_text.default_trip_rich_text,
            ),
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
                ],
                max_length=80,
            ),
        ),
    ]
