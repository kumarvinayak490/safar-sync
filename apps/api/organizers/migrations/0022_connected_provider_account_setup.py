# Generated for TripOS connected provider account setup.

from django.db import migrations, models


def backfill_connected_provider_account_facts(apps, schema_editor):
    ProviderPaymentSetup = apps.get_model("organizers", "ProviderPaymentSetup")

    for setup in ProviderPaymentSetup.objects.all().iterator():
        if setup.status == "complete":
            setup.authorization_state = "authorized"
            setup.provider_verification_status = "verified"
            setup.provider_payment_capability_enabled = True
            setup.provider_connection_state = "healthy"
            setup.provider_mode = "live"
        elif setup.status == "pending":
            setup.authorization_state = "pending"
            setup.provider_verification_status = "in_review"
        elif setup.status == "action_required":
            setup.authorization_state = "action_required"
            setup.provider_verification_status = "action_required"

        setup.save(
            update_fields=[
                "authorization_state",
                "provider_verification_status",
                "provider_payment_capability_enabled",
                "provider_connection_state",
                "provider_mode",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("organizers", "0021_organizer_invitation"),
    ]

    operations = [
        migrations.AddField(
            model_name="providerpaymentsetup",
            name="authorization_method",
            field=models.CharField(
                choices=[
                    ("oauth", "OAuth Provider Authorization"),
                    ("api_key", "API Key Provider Authorization"),
                    ("assisted", "Assisted Payment Setup"),
                ],
                default="oauth",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="providerpaymentsetup",
            name="authorization_state",
            field=models.CharField(
                choices=[
                    ("not_started", "Not started"),
                    ("pending", "Pending"),
                    ("authorized", "Authorized"),
                    ("action_required", "Action required"),
                    ("revoked", "Revoked"),
                ],
                default="not_started",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="providerpaymentsetup",
            name="provider_connection_state",
            field=models.CharField(
                choices=[
                    ("healthy", "Healthy"),
                    ("unhealthy", "Unhealthy"),
                ],
                default="unhealthy",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="providerpaymentsetup",
            name="provider_mode",
            field=models.CharField(
                choices=[
                    ("test", "Test"),
                    ("live", "Live"),
                ],
                default="test",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="providerpaymentsetup",
            name="provider_payment_capability_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="providerpaymentsetup",
            name="provider_verification_status",
            field=models.CharField(
                choices=[
                    ("not_started", "Not started"),
                    ("details_needed", "Details needed"),
                    ("submitted", "Submitted"),
                    ("in_review", "In review"),
                    ("action_required", "Action required"),
                    ("verified", "Verified"),
                ],
                default="not_started",
                max_length=24,
            ),
        ),
        migrations.RunPython(
            backfill_connected_provider_account_facts,
            migrations.RunPython.noop,
        ),
    ]
