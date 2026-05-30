from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0041_manual_payment_instructions"),
    ]

    operations = [
        migrations.AddField(
            model_name="trip",
            name="manual_payment_availability",
            field=models.CharField(
                choices=[("closed", "Closed"), ("open", "Open")],
                default="closed",
                max_length=24,
            ),
        ),
    ]
