from __future__ import annotations

from django.db import models


class OrganizerProfile(models.Model):
    class PublicationState(models.TextChoices):
        DRAFT = "draft", "Draft Organizer Profile"
        PUBLISHED = "published", "Published Organizer Profile"
        ARCHIVED = "archived", "Archived Organizer Profile"

    organizer = models.OneToOneField(
        "organizers.Organizer",
        on_delete=models.CASCADE,
        related_name="organizer_profile",
    )
    public_description = models.TextField(blank=True)
    publication_state = models.CharField(
        max_length=16,
        choices=PublicationState.choices,
        default=PublicationState.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organizer__name", "id"]

    def __str__(self) -> str:
        return f"Organizer Profile for {self.organizer}"

    def save(self, *args, **kwargs):
        self.public_description = self.public_description.strip()
        super().save(*args, **kwargs)
