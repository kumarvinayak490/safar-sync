from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0016_bookingimport_bookingimportrow_openingpaymentrecord_and_more"),
    ]

    operations = [
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
                ],
                max_length=80,
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("reservation_acknowledgement", "Reservation Acknowledgement"),
                    ("confirmation_notice", "Confirmation Notice"),
                    ("payment_acknowledgement", "Payment Acknowledgement"),
                    ("refund_acknowledgement", "Refund Acknowledgement"),
                    ("date_change_notice", "Date Change Notice"),
                    ("cancellation_notice", "Cancellation Notice"),
                ],
                max_length=40,
            ),
        ),
    ]
