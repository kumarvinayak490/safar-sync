# Generated manually for TripOS issue 08.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0037_trip_payment_schedule_reviewed"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="trip",
            name="confirmation_requirements_reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="trip",
            name="confirmation_requirements_reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_trip_confirmation_requirements",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
