from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0042_trip_manual_payment_availability"),
    ]

    operations = [
        migrations.AddField(
            model_name="organizer",
            name="identity_whatsapp_number",
            field=models.CharField(blank=True, max_length=40),
        ),
    ]
