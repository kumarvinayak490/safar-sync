from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0035_trip_itinerary_day"),
    ]

    operations = [
        migrations.AddField(
            model_name="trippackage",
            name="lifecycle_state",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("withdrawn", "Withdrawn"),
                ],
                default="active",
                max_length=16,
            ),
        ),
    ]
