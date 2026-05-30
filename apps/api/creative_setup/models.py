from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from organizers.models import Organizer


class CreativeSetup(models.Model):
    class ModelChoice(models.TextChoices):
        TRIPOS_DEFAULT = "tripos_default", "TripOS default"
        FAST_DRAFT = "fast_draft", "Fast draft"
        HIGH_DETAIL = "high_detail", "High detail"

    class LogoUsage(models.TextChoices):
        USE_WHEN_AVAILABLE = "use_when_available", "Use when available"
        AVOID_BY_DEFAULT = "avoid_by_default", "Avoid by default"
        NEVER_USE = "never_use", "Never use"

    organizer = models.OneToOneField(
        Organizer,
        on_delete=models.CASCADE,
        related_name="creative_setup",
    )
    model_choice = models.CharField(
        max_length=32,
        choices=ModelChoice.choices,
        default=ModelChoice.TRIPOS_DEFAULT,
    )
    brand_tone = models.CharField(max_length=240, blank=True)
    default_style = models.CharField(max_length=240, blank=True)
    logo_usage = models.CharField(
        max_length=32,
        choices=LogoUsage.choices,
        default=LogoUsage.USE_WHEN_AVAILABLE,
    )
    poster_defaults = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organizer__name", "id"]

    def __str__(self) -> str:
        return f"Creative Setup for {self.organizer}"

    def save(self, *args, **kwargs):
        self.brand_tone = self.brand_tone.strip()
        self.default_style = self.default_style.strip()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.poster_defaults is None:
            self.poster_defaults = {}
        if not isinstance(self.poster_defaults, dict):
            raise ValidationError({"poster_defaults": "Poster defaults must be an object."})
