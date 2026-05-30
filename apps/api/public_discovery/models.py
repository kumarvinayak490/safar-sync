from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.db import models

from organizer_profile.models import OrganizerProfile
from trips.models import Trip


class DemandPage(models.Model):
    class PublicationState(models.TextChoices):
        DRAFT = "draft", "Draft Demand Page"
        PUBLISHED = "published", "Published Demand Page"
        ARCHIVED = "archived", "Archived Demand Page"

    slug = models.SlugField(max_length=150, unique=True)
    title = models.CharField(max_length=180)
    seo_title = models.CharField(max_length=180, blank=True)
    seo_copy = models.TextField(blank=True)
    demand_pattern = models.CharField(max_length=260, blank=True)
    publication_state = models.CharField(
        max_length=24,
        choices=PublicationState.choices,
        default=PublicationState.DRAFT,
    )
    selected_organizers = models.ManyToManyField(
        "organizers.Organizer",
        related_name="demand_pages",
        blank=True,
    )
    selected_trips = models.ManyToManyField(
        Trip,
        related_name="demand_pages",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "public_discovery"
        ordering = ["slug", "id"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def demand_pattern_is_defined(self) -> bool:
        return bool((self.demand_pattern or "").strip())

    @property
    def has_discoverable_organizer_refs(self) -> bool:
        if self.pk is None:
            return False

        return self.selected_organizers.filter(
            organizer_profile__publication_state=OrganizerProfile.PublicationState.PUBLISHED,
        ).exists()

    @property
    def has_discoverable_trip_refs(self) -> bool:
        if self.pk is None:
            return False

        return self.selected_trips.filter(
            publication_state=Trip.PublicationState.PUBLISHED,
            organizer__organizer_profile__publication_state=(
                OrganizerProfile.PublicationState.PUBLISHED
            ),
        ).exists()

    @property
    def is_discoverable(self) -> bool:
        return bool(
            self.demand_pattern_is_defined
            or self.has_discoverable_organizer_refs
            or self.has_discoverable_trip_refs
        )

    def clean(self):
        super().clean()

        self.title = self.title.strip()
        self.slug = (self.slug or "").strip().lower()
        self.seo_title = self.seo_title.strip()
        self.seo_copy = self.seo_copy.strip()
        self.demand_pattern = self.demand_pattern.strip()

        if not self.title:
            raise ValidationError({"title": "Demand Page title is required."})
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.slug):
            raise ValidationError(
                {
                    "slug": (
                        "Demand Page slug must include only lowercase letters, "
                        "digits, and hyphens."
                    )
                }
            )
        if self.publication_state == self.PublicationState.PUBLISHED and not self.is_discoverable:
            raise ValidationError(
                {
                    "publication_state": (
                        "Published Demand Pages must include SEO-pattern "
                        "targeting or at least one discoverable organizer or "
                        "trip reference."
                    )
                }
            )
