from __future__ import annotations

from django.db import models

from organizers.models import Organizer


class OrganizerPolicies(models.Model):
    organizer = models.OneToOneField(
        Organizer,
        on_delete=models.CASCADE,
        related_name="organizer_policies",
    )
    privacy_policy = models.TextField(blank=True)
    refund_policy = models.TextField(blank=True)
    cancellation_policy = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organizer__name", "id"]

    def __str__(self) -> str:
        return f"Organizer Policies for {self.organizer}"

    def save(self, *args, **kwargs):
        self.privacy_policy = self.privacy_policy.strip()
        self.refund_policy = self.refund_policy.strip()
        self.cancellation_policy = self.cancellation_policy.strip()
        super().save(*args, **kwargs)
