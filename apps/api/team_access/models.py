from __future__ import annotations

import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from organizers.models import Organizer


def default_invitation_token():
    return secrets.token_urlsafe(32)


class OrganizerMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        OPERATOR = "operator", "Operator"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organizer_memberships",
    )
    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organizer"],
                name="unique_user_organizer_membership",
            )
        ]
        ordering = ["organizer__name", "user_id"]

    def __str__(self) -> str:
        return f"{self.user} as {self.get_role_display()} for {self.organizer}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.full_clean()
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            if self.role == self.Role.OWNER and self._is_last_owner():
                raise ValidationError("An Organizer must keep at least one Owner.")
            return super().delete(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.pk and self._would_remove_last_owner():
            raise ValidationError({"role": "An Organizer must keep at least one Owner."})

    def _would_remove_last_owner(self) -> bool:
        prior = type(self).objects.filter(pk=self.pk).only("role", "organizer_id").first()
        return (
            prior is not None
            and prior.role == self.Role.OWNER
            and (self.role != self.Role.OWNER or self.organizer_id != prior.organizer_id)
            and type(self)._owner_count(prior.organizer_id, for_update=True) <= 1
        )

    def _is_last_owner(self) -> bool:
        return type(self)._owner_count(self.organizer_id, for_update=True) <= 1

    @classmethod
    def _owner_count(cls, organizer_id: int, *, for_update: bool = False) -> int:
        queryset = cls.objects.filter(organizer_id=organizer_id, role=cls.Role.OWNER)
        if for_update:
            return len(list(queryset.select_for_update().values_list("id", flat=True)))
        return queryset.count()


class OrganizerInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REVOKED = "revoked", "Revoked"

    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=16,
        choices=OrganizerMembership.Role.choices,
        default=OrganizerMembership.Role.OPERATOR,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    token = models.CharField(max_length=96, unique=True, default=default_invitation_token)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="sent_organizer_invitations",
        null=True,
        blank=True,
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="accepted_organizer_invitations",
        null=True,
        blank=True,
    )
    last_sent_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    resend_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "organizers"
        ordering = ["organizer__name", "-created_at", "email"]
        indexes = [
            models.Index(fields=["organizer", "status"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} invited as {self.get_role_display()} for {self.organizer}"

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

