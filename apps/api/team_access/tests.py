from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.exceptions import NotAuthenticated, PermissionDenied

from organizers.models import Organizer
from organizers.models import OrganizerMembership as LegacyOrganizerMembership
from team_access.invitations import (
    INVITATION_EXPIRES_AFTER,
    accept_organizer_invitation,
    create_organizer_invitation,
    invitation_expires_at,
    invitation_is_expired,
    resend_organizer_invitation,
    revoke_organizer_invitation,
    team_access_payload,
)
from team_access.memberships import (
    create_organizer_membership,
    create_owner_membership,
    membership_payload,
)
from team_access.models import OrganizerInvitation, OrganizerMembership
from team_access.permissions import get_active_membership, require_membership

pytestmark = pytest.mark.django_db


def create_user(email: str, **kwargs):
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        password="tripos-test-password",
        **kwargs,
    )


def test_team_access_creates_owner_and_operator_memberships():
    owner = create_user("owner@example.com")
    operator = create_user("operator@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")

    owner_membership = create_owner_membership(organizer=organizer, user=owner)
    operator_membership = create_organizer_membership(
        organizer=organizer,
        user=operator,
        role=OrganizerMembership.Role.OPERATOR,
    )

    assert owner_membership.role == OrganizerMembership.Role.OWNER
    assert operator_membership.role == OrganizerMembership.Role.OPERATOR
    assert list(organizer.memberships.order_by("role", "user__email")) == [
        operator_membership,
        owner_membership,
    ]


def test_membership_payload_exposes_role_visibility_and_user_identity():
    user = create_user(
        "operator@example.com",
        first_name="Asha",
        last_name="Nair",
    )
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    membership = create_organizer_membership(
        organizer=organizer,
        user=user,
        role=OrganizerMembership.Role.OPERATOR,
    )

    payload = membership_payload(membership)

    assert payload["role"] == OrganizerMembership.Role.OPERATOR
    assert payload["role_label"] == "Operator"
    assert payload["user"] == {
        "id": user.id,
        "email": "operator@example.com",
        "name": "Asha Nair",
        "first_name": "Asha",
        "last_name": "Nair",
    }


def test_owner_role_visibility_exposes_owner_permissions():
    owner = create_user("owner@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    create_owner_membership(organizer=organizer, user=owner)

    role = require_membership(owner, organizer.id)

    assert role.role == OrganizerMembership.Role.OWNER
    assert role.can_access_operations_dashboard is True
    assert role.can_manage_team_access is True
    assert role.can_manage_payment_setup is True
    assert role.can_create_trips is True


def test_operator_role_visibility_exposes_operator_permissions():
    operator = create_user("operator@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    create_organizer_membership(
        organizer=organizer,
        user=operator,
        role=OrganizerMembership.Role.OPERATOR,
    )

    role = require_membership(operator, organizer.id)

    assert role.role == OrganizerMembership.Role.OPERATOR
    assert role.can_access_operations_dashboard is True
    assert role.can_manage_team_access is False
    assert role.can_manage_payment_setup is False
    assert role.can_create_trips is False
    assert role.can_use_operator_workflows is True


def test_access_checks_require_active_authenticated_membership():
    active_user = create_user("active@example.com")
    inactive_user = create_user("inactive@example.com", is_active=False)
    outsider = create_user("outsider@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    active_membership = create_owner_membership(organizer=organizer, user=active_user)
    create_owner_membership(organizer=organizer, user=inactive_user)

    assert get_active_membership(active_user, organizer.id) == active_membership
    assert get_active_membership(inactive_user, organizer.id) is None

    with pytest.raises(PermissionDenied, match="does not belong"):
        require_membership(inactive_user, organizer.id)
    with pytest.raises(PermissionDenied, match="does not belong"):
        require_membership(outsider, organizer.id)
    with pytest.raises(NotAuthenticated, match="Authentication is required"):
        require_membership(AnonymousUser(), organizer.id)


def test_team_access_creates_and_accepts_operator_invitation():
    owner = create_user("owner@example.com")
    invited_user = create_user("operator@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    create_owner_membership(organizer=organizer, user=owner)

    invitation = create_organizer_invitation(
        organizer=organizer,
        email=" Operator@Example.com ",
        invited_by=owner,
    )
    accepted_invitation, membership = accept_organizer_invitation(
        token=invitation.token,
        user=invited_user,
    )

    assert invitation.email == "operator@example.com"
    assert membership.role == OrganizerMembership.Role.OPERATOR
    assert accepted_invitation.status == OrganizerInvitation.Status.ACCEPTED
    assert accepted_invitation.accepted_by == invited_user


def test_owner_invitation_requires_explicit_owner_confirmation():
    owner = create_user("owner@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    create_owner_membership(organizer=organizer, user=owner)

    with pytest.raises(ValidationError, match="Confirm that this Owner can manage"):
        create_organizer_invitation(
            organizer=organizer,
            email="cofounder@example.com",
            invited_by=owner,
            role=OrganizerMembership.Role.OWNER,
        )

    invitation = create_organizer_invitation(
        organizer=organizer,
        email="cofounder@example.com",
        invited_by=owner,
        role=OrganizerMembership.Role.OWNER,
        confirm_owner_powers=True,
    )

    assert invitation.role == OrganizerMembership.Role.OWNER


def test_invitation_prevents_duplicate_membership_and_pending_invite():
    owner = create_user("owner@example.com")
    operator = create_user("operator@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    create_owner_membership(organizer=organizer, user=owner)
    create_organizer_membership(
        organizer=organizer,
        user=operator,
        role=OrganizerMembership.Role.OPERATOR,
    )

    with pytest.raises(ValidationError, match="already has an Organizer Membership"):
        create_organizer_invitation(
            organizer=organizer,
            email="OPERATOR@example.com",
            invited_by=owner,
        )

    create_organizer_invitation(
        organizer=organizer,
        email="pending@example.com",
        invited_by=owner,
    )
    with pytest.raises(ValidationError, match="pending Organizer Invitation"):
        create_organizer_invitation(
            organizer=organizer,
            email="Pending@Example.com",
            invited_by=owner,
        )


def test_invitation_expiry_blocks_acceptance_until_resend():
    owner = create_user("owner@example.com")
    invited_user = create_user("operator@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    create_owner_membership(organizer=organizer, user=owner)
    invitation = create_organizer_invitation(
        organizer=organizer,
        email=invited_user.email,
        invited_by=owner,
    )
    expired_sent_at = timezone.now() - INVITATION_EXPIRES_AFTER - timedelta(minutes=1)
    OrganizerInvitation.objects.filter(pk=invitation.pk).update(last_sent_at=expired_sent_at)
    invitation.refresh_from_db()

    assert invitation_is_expired(invitation) is True
    with pytest.raises(ValidationError, match="has expired"):
        accept_organizer_invitation(token=invitation.token, user=invited_user)

    resent = resend_organizer_invitation(invitation)
    assert invitation_is_expired(resent) is False
    accepted_invitation, membership = accept_organizer_invitation(
        token=invitation.token,
        user=invited_user,
    )

    assert membership.role == OrganizerMembership.Role.OPERATOR
    assert accepted_invitation.status == OrganizerInvitation.Status.ACCEPTED


def test_pending_invitation_revocation_blocks_acceptance():
    owner = create_user("owner@example.com")
    invited_user = create_user("operator@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    create_owner_membership(organizer=organizer, user=owner)
    invitation = create_organizer_invitation(
        organizer=organizer,
        email=invited_user.email,
        invited_by=owner,
    )

    revoked = revoke_organizer_invitation(invitation)

    assert revoked.status == OrganizerInvitation.Status.REVOKED
    with pytest.raises(ValidationError, match="no longer pending"):
        accept_organizer_invitation(token=invitation.token, user=invited_user)


def test_team_access_payload_exposes_pending_invitation_expiry_facts():
    owner = create_user("owner@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    create_owner_membership(organizer=organizer, user=owner)
    invitation = create_organizer_invitation(
        organizer=organizer,
        email="pending@example.com",
        invited_by=owner,
    )

    payload = team_access_payload(organizer)

    assert payload["pending_invitations"] == [
        {
            "id": invitation.id,
            "email": "pending@example.com",
            "role": OrganizerMembership.Role.OPERATOR,
            "role_label": "Operator",
            "status": OrganizerInvitation.Status.PENDING,
            "status_label": "Pending",
            "expires_at": invitation_expires_at(invitation).isoformat(),
            "is_expired": False,
            "organizer": {
                "id": organizer.id,
                "name": organizer.display_identity_name,
                "slug": organizer.slug,
            },
            "token": invitation.token,
            "invite_url_path": f"/team-access/invitations/{invitation.token}",
            "invited_by": {
                "id": owner.id,
                "email": owner.email,
                "name": owner.email,
                "first_name": "",
                "last_name": "",
            },
            "last_sent_at": invitation.last_sent_at.isoformat(),
            "resend_count": 0,
            "created_at": invitation.created_at.isoformat(),
        }
    ]


def test_owner_invariants_cannot_be_bypassed_through_legacy_model_import():
    owner = create_user("owner@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon Cohort")
    membership = LegacyOrganizerMembership.objects.create(
        organizer=organizer,
        user=owner,
        role=LegacyOrganizerMembership.Role.OWNER,
    )

    membership.role = LegacyOrganizerMembership.Role.OPERATOR
    with pytest.raises(ValidationError, match="at least one Owner"):
        membership.save()

    membership.refresh_from_db()
    with pytest.raises(ValidationError, match="at least one Owner"):
        membership.delete()
