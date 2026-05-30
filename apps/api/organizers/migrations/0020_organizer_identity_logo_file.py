from django.db import migrations, models

import organizers.models


class Migration(migrations.Migration):

    dependencies = [
        ("organizers", "0019_manual_reminders_announcements"),
    ]

    operations = [
        migrations.AddField(
            model_name="organizer",
            name="identity_logo",
            field=models.FileField(
                blank=True,
                max_length=255,
                upload_to=organizers.models.organizer_logo_upload_path,
            ),
        ),
    ]
