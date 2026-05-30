from __future__ import annotations

import secrets

from django.conf import settings
from django.db import models


def organizer_media_storage_key() -> str:
    return secrets.token_urlsafe(18)


def organizer_media_upload_path(instance, filename: str) -> str:
    extension = filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else "image"
    return (
        f"organizer-media/organizer-{instance.organizer_id}/"
        f"{instance.storage_key}.{extension}"
    )


class OrganizerMediaItemQuerySet(models.QuerySet):
    def public(self):
        return self.filter(visibility=OrganizerMediaItem.Visibility.PUBLIC)

    def ordered_for_display(self):
        return self.order_by("position", "id")


class OrganizerMediaItem(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        PUBLIC = "public", "Public"

    organizer = models.ForeignKey(
        "organizers.Organizer",
        on_delete=models.CASCADE,
        related_name="organizer_media_items",
    )
    image = models.FileField(upload_to=organizer_media_upload_path, max_length=255)
    storage_key = models.CharField(
        max_length=48,
        unique=True,
        default=organizer_media_storage_key,
    )
    original_filename = models.CharField(max_length=240, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="uploaded_organizer_media_items",
    )
    position = models.PositiveIntegerField(default=1)
    caption = models.CharField(max_length=220, blank=True)
    alt_text = models.CharField(max_length=220, blank=True)
    visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrganizerMediaItemQuerySet.as_manager()

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(position__gt=0),
                name="organizer_media_item_position_must_be_positive",
            ),
        ]

    def __str__(self) -> str:
        return self.original_filename or f"Organizer Media Item {self.id}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        self.caption = self.caption.strip()
        self.alt_text = self.alt_text.strip()

    @property
    def is_public(self) -> bool:
        return self.visibility == self.Visibility.PUBLIC

    @property
    def image_url(self) -> str:
        if not self.image:
            return ""
        try:
            return self.image.url
        except ValueError:
            return ""
