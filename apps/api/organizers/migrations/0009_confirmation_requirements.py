# Generated manually for TripOS issue 12.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0008_traveler_readiness"),
    ]

    operations = [
        migrations.AddField(
            model_name="trip",
            name="requires_full_payment_before_confirmation",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="trip",
            name="requires_traveler_identity_details",
            field=models.BooleanField(default=False),
        ),
    ]
