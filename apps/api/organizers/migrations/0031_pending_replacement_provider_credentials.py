# Generated for TripOS Connected Provider Account replacement confirmation.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0030_provider_connection_test_result"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sensitiveprovidercredential",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("pending_replacement", "Pending replacement"),
                    ("rotated", "Rotated"),
                    ("revoked", "Revoked"),
                ],
                default="active",
                max_length=24,
            ),
        ),
    ]
