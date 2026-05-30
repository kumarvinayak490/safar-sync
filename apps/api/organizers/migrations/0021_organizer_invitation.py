import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import organizers.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizers", "0020_organizer_identity_logo_file"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrganizerInvitation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("email", models.EmailField(max_length=254)),
                (
                    "role",
                    models.CharField(
                        choices=[("owner", "Owner"), ("operator", "Operator")],
                        default="operator",
                        max_length=16,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("revoked", "Revoked"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                (
                    "token",
                    models.CharField(
                        default=organizers.models.default_invitation_token,
                        max_length=96,
                        unique=True,
                    ),
                ),
                ("last_sent_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("resend_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "accepted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="accepted_organizer_invitations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "invited_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sent_organizer_invitations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organizer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="invitations",
                        to="organizers.organizer",
                    ),
                ),
            ],
            options={
                "ordering": ["organizer__name", "-created_at", "email"],
            },
        ),
        migrations.AddIndex(
            model_name="organizerinvitation",
            index=models.Index(
                fields=["organizer", "status"],
                name="organizers__organiz_c054b0_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="organizerinvitation",
            index=models.Index(fields=["email"], name="organizers__email_5f4a21_idx"),
        ),
    ]
