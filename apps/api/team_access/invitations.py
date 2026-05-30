from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from organizers.models import Organizer
from team_access.memberships import (
    create_organizer_membership,
    membership_payload,
    owner_count_for_memberships,
    user_payload,
    validate_membership_role,
)
from team_access.models import OrganizerInvitation, OrganizerMembership

INVITATION_EXPIRES_AFTER = timedelta(days=14)
OWNER_CONFIRMATION_MESSAGE = (
    "Confirm that this Owner can manage Payment Setup, Organizer Identity, Team Access, "
    "and all Trips."
)

__all__ = [
    "INVITATION_EXPIRES_AFTER",
    "OWNER_CONFIRMATION_MESSAGE",
    "accept_organizer_invitation",
    "create_organizer_invitation",
    "invitation_expires_at",
    "invitation_is_expired",
    "invitation_payload",
    "invitation_public_payload",
    "normalize_invitation_email",
    "prevent_duplicate_membership",
    "prevent_duplicate_pending_invitation",
    "resend_organizer_invitation",
    "revoke_organizer_invitation",
    "team_access_payload",
    "validate_invitation_acceptance",
    "validate_invitation_role",
]


def normalize_invitation_email(email: str) -> str:
    return email.strip().lower()


def create_organizer_invitation(
    *,
    organizer: Organizer,
    email: str,
    invited_by,
    role: str = OrganizerMembership.Role.OPERATOR,
    confirm_owner_powers: bool = False,
) -> OrganizerInvitation:
    normalized_email = normalize_invitation_email(email)
    invite_role = role or OrganizerMembership.Role.OPERATOR
    validate_invitation_role(invite_role)

    if invite_role == OrganizerMembership.Role.OWNER and not confirm_owner_powers:
        raise ValidationError({"confirm_owner_powers": OWNER_CONFIRMATION_MESSAGE})

    with transaction.atomic():
        prevent_duplicate_membership(organizer=organizer, email=normalized_email)
        prevent_duplicate_pending_invitation(organizer=organizer, email=normalized_email)

        return OrganizerInvitation.objects.create(
            organizer=organizer,
            email=normalized_email,
            role=invite_role,
            invited_by=invited_by,
            last_sent_at=timezone.now(),
        )


def resend_organizer_invitation(invitation: OrganizerInvitation) -> OrganizerInvitation:
    if invitation.status != OrganizerInvitation.Status.PENDING:
        raise ValidationError("Only pending Organizer Invitations can be resent.")

    invitation.last_sent_at = timezone.now()
    invitation.resend_count += 1
    invitation.save(update_fields=["last_sent_at", "resend_count", "updated_at"])
    return invitation


def revoke_organizer_invitation(invitation: OrganizerInvitation) -> OrganizerInvitation:
    if invitation.status != OrganizerInvitation.Status.PENDING:
        raise ValidationError("Only pending Organizer Invitations can be revoked.")

    invitation.status = OrganizerInvitation.Status.REVOKED
    invitation.revoked_at = timezone.now()
    invitation.save(update_fields=["status", "revoked_at", "updated_at"])
    return invitation


def accept_organizer_invitation(
    *,
    token: str,
    user,
) -> tuple[OrganizerInvitation, OrganizerMembership]:
    with transaction.atomic():
        invitation = (
            OrganizerInvitation.objects.select_for_update()
            .select_related("organizer")
            .get(token=token)
        )
        validate_invitation_acceptance(invitation)
        if normalize_invitation_email(user.email) != invitation.email:
            raise ValidationError(
                "Sign in with the email address this Organizer Invitation was sent to."
            )

        existing_membership = (
            OrganizerMembership.objects.select_for_update()
            .filter(organizer=invitation.organizer, user=user)
            .first()
        )
        if existing_membership is not None:
            raise ValidationError("This User already has an Organizer Membership.")

        membership = create_organizer_membership(
            user=user,
            organizer=invitation.organizer,
            role=invitation.role,
        )
        invitation.status = OrganizerInvitation.Status.ACCEPTED
        invitation.accepted_by = user
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["status", "accepted_by", "accepted_at", "updated_at"])
        return invitation, membership


def validate_invitation_acceptance(invitation: OrganizerInvitation) -> None:
    if invitation.status != OrganizerInvitation.Status.PENDING:
        raise ValidationError("This Organizer Invitation is no longer pending.")
    if invitation_is_expired(invitation):
        raise ValidationError("This Organizer Invitation has expired.")


def invitation_expires_at(invitation: OrganizerInvitation):
    return invitation.last_sent_at + INVITATION_EXPIRES_AFTER


def invitation_is_expired(invitation: OrganizerInvitation, *, now=None) -> bool:
    current_time = now or timezone.now()
    return (
        invitation.status == OrganizerInvitation.Status.PENDING
        and invitation_expires_at(invitation) <= current_time
    )


def team_access_payload(organizer: Organizer) -> dict:
    memberships = list(
        organizer.memberships.select_related("user")
        .order_by("role", "user__first_name", "user__email", "id")
        .all()
    )
    pending_invitations = (
        organizer.invitations.select_related("invited_by")
        .filter(status=OrganizerInvitation.Status.PENDING)
        .order_by("-created_at", "email")
        .all()
    )

    return {
        "memberships": [membership_payload(membership) for membership in memberships],
        "pending_invitations": [
            invitation_payload(invitation) for invitation in pending_invitations
        ],
        "owner_count": owner_count_for_memberships(memberships),
    }


def invitation_public_payload(invitation: OrganizerInvitation) -> dict:
    return {
        "id": invitation.id,
        "email": invitation.email,
        "role": invitation.role,
        "role_label": invitation.get_role_display(),
        "status": invitation.status,
        "status_label": invitation.get_status_display(),
        "expires_at": invitation_expires_at(invitation).isoformat(),
        "is_expired": invitation_is_expired(invitation),
        "organizer": {
            "id": invitation.organizer_id,
            "name": invitation.organizer.display_identity_name,
            "slug": invitation.organizer.slug,
        },
    }


def invitation_payload(invitation: OrganizerInvitation) -> dict:
    invited_by = invitation.invited_by
    return {
        **invitation_public_payload(invitation),
        "token": invitation.token,
        "invite_url_path": f"/team-access/invitations/{invitation.token}",
        "invited_by": user_payload(invited_by) if invited_by is not None else None,
        "last_sent_at": invitation.last_sent_at.isoformat(),
        "resend_count": invitation.resend_count,
        "created_at": invitation.created_at.isoformat(),
    }


def validate_invitation_role(role: str) -> None:
    validate_membership_role(role)


def prevent_duplicate_membership(*, organizer: Organizer, email: str) -> None:
    user_model = get_user_model()
    matching_users = user_model.objects.filter(email__iexact=email)
    if OrganizerMembership.objects.filter(
        organizer=organizer,
        user__in=matching_users,
    ).exists():
        raise ValidationError({"email": "This User already has an Organizer Membership."})


def prevent_duplicate_pending_invitation(*, organizer: Organizer, email: str) -> None:
    if OrganizerInvitation.objects.filter(
        organizer=organizer,
        email__iexact=email,
        status=OrganizerInvitation.Status.PENDING,
    ).exists():
        raise ValidationError({"email": "A pending Organizer Invitation already exists."})
