from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizers", "0018_alter_notification_notification_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("draft_recovery_reminder", "Draft Recovery Reminder"),
                    ("balance_due_reminder", "Balance Due Reminder"),
                    ("overdue_balance_reminder", "Overdue Balance Reminder"),
                    ("missing_requirements_reminder", "Missing Requirements Reminder"),
                    ("manual_reminder", "Manual Reminder"),
                    ("announcement", "Announcement"),
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
