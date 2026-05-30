from __future__ import annotations

from collections.abc import Iterable

from django.core.exceptions import ValidationError

from team_access.models import OrganizerMembership


def validate_membership_role(role: str) -> None:
    allowed_roles = {choice for choice, _label in OrganizerMembership.Role.choices}
    if role not in allowed_roles:
        raise ValidationError({"role": "Choose Owner or Operator."})


def create_organizer_membership(
    *,
    organizer,
    user,
    role: str = OrganizerMembership.Role.OPERATOR,
) -> OrganizerMembership:
    membership_role = role or OrganizerMembership.Role.OPERATOR
    validate_membership_role(membership_role)
    return OrganizerMembership.objects.create(
        organizer=organizer,
        user=user,
        role=membership_role,
    )


def create_owner_membership(*, organizer, user) -> OrganizerMembership:
    return create_organizer_membership(
        organizer=organizer,
        user=user,
        role=OrganizerMembership.Role.OWNER,
    )


def membership_payload(membership: OrganizerMembership) -> dict:
    return {
        "id": membership.id,
        "role": membership.role,
        "role_label": membership.get_role_display(),
        "user": user_payload(membership.user),
        "created_at": membership.created_at.isoformat(),
    }


def owner_count_for_memberships(memberships: Iterable[OrganizerMembership]) -> int:
    return sum(
        1
        for membership in memberships
        if membership.role == OrganizerMembership.Role.OWNER
    )


def user_payload(user) -> dict:
    display_name = f"{user.first_name} {user.last_name}".strip()
    return {
        "id": user.id,
        "email": user.email,
        "name": display_name or user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }
