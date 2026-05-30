# Generated for TripOS Settlement Readiness support confirmation.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizers", "0031_pending_replacement_provider_credentials"),
    ]

    operations = [
        migrations.AddField(
            model_name="payoutaccount",
            name="settlement_readiness_source",
            field=models.CharField(
                choices=[
                    ("provider_derived", "Provider derived"),
                    ("support_confirmed", "Support confirmed"),
                ],
                default="provider_derived",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="payoutaccount",
            name="support_confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="payoutaccount",
            name="support_confirmed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="support_confirmed_settlement_readiness",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="payoutaccount",
            name="support_confirmation_notes",
            field=models.TextField(blank=True),
        ),
    ]
