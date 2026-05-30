# Generated manually for TripOS issue 11.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import organizers.models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizers", "0007_access_links_and_traveler_identity"),
    ]

    operations = [
        migrations.AddField(
            model_name="trip",
            name="requires_emergency_contact",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="trip",
            name="requires_medical_disclosure",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="trip",
            name="requires_travel_logistics",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="trip",
            name="requires_traveler_documents",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="travelerslot",
            name="arrival_details",
            field=models.CharField(blank=True, max_length=240),
        ),
        migrations.AddField(
            model_name="travelerslot",
            name="departure_details",
            field=models.CharField(blank=True, max_length=240),
        ),
        migrations.AddField(
            model_name="travelerslot",
            name="emergency_contact_name",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="travelerslot",
            name="emergency_contact_phone",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="travelerslot",
            name="emergency_contact_relationship",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="travelerslot",
            name="logistics_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="travelerslot",
            name="medical_disclosure",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="travelerslot",
            name="medical_disclosure_submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="travelerslot",
            name="pickup_location",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.CreateModel(
            name="TravelerDocument",
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
                (
                    "document_kind",
                    models.CharField(
                        choices=[
                            ("identity", "Identity Traveler Document"),
                            ("eligibility", "Eligibility Traveler Document"),
                        ],
                        default="identity",
                        max_length=24,
                    ),
                ),
                ("label", models.CharField(default="Identity Document", max_length=120)),
                (
                    "document_state",
                    models.CharField(
                        choices=[
                            ("missing", "Missing"),
                            ("submitted", "Submitted"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ],
                        default="missing",
                        max_length=24,
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        blank=True,
                        upload_to=organizers.models.traveler_document_upload_path,
                    ),
                ),
                ("original_filename", models.CharField(blank=True, max_length=240)),
                ("content_type", models.CharField(blank=True, max_length=120)),
                ("file_size", models.PositiveIntegerField(default=0)),
                ("rejection_reason", models.TextField(blank=True)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_traveler_documents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "traveler_slot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="organizers.travelerslot",
                    ),
                ),
            ],
            options={
                "ordering": ["traveler_slot__position", "document_kind", "label", "id"],
            },
        ),
        migrations.CreateModel(
            name="ActivityLog",
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
                (
                    "action",
                    models.CharField(
                        choices=[
                            (
                                "sensitive_traveler_information_download",
                                "Sensitive Traveler Information Download",
                            ),
                            ("traveler_document_approved", "Traveler Document Approved"),
                            ("traveler_document_rejected", "Traveler Document Rejected"),
                        ],
                        max_length=80,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="activity_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activity_logs",
                        to="organizers.booking",
                    ),
                ),
                (
                    "organizer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activity_logs",
                        to="organizers.organizer",
                    ),
                ),
                (
                    "traveler_document",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="activity_logs",
                        to="organizers.travelerdocument",
                    ),
                ),
                (
                    "traveler_slot",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activity_logs",
                        to="organizers.travelerslot",
                    ),
                ),
                (
                    "trip",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activity_logs",
                        to="organizers.trip",
                    ),
                ),
            ],
            options={
                "ordering": ["-occurred_at", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="travelerdocument",
            constraint=models.UniqueConstraint(
                fields=("traveler_slot", "document_kind", "label"),
                name="unique_traveler_document_label_per_slot",
            ),
        ),
    ]
