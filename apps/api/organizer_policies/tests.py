from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from organizer_policies.models import OrganizerPolicies
from organizer_policies.readiness import (
    organizer_policies_readiness,
    required_organizer_profile_policy_readiness,
)
from organizers.models import Organizer
from team_access.models import OrganizerMembership
from team_access.permissions import require_membership

pytestmark = pytest.mark.django_db


def test_owner_can_create_and_update_organizer_policies():
    owner = _create_user("policy-owner@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon")
    _create_membership(owner, organizer, OrganizerMembership.Role.OWNER)
    client = _authenticated_client(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/policies/",
        {
            "privacy_policy": "  We protect traveler data. ",
            "refund_policy": " Refunds are reviewed by the organizer. ",
            "cancellation_policy": " Cancellations follow trip-specific terms. ",
        },
        format="json",
    )

    assert response.status_code == 200
    policies = OrganizerPolicies.objects.get(organizer=organizer)
    assert policies.privacy_policy == "We protect traveler data."
    assert policies.refund_policy == "Refunds are reviewed by the organizer."
    assert policies.cancellation_policy == "Cancellations follow trip-specific terms."
    assert response.json()["readiness"] == {
        "organizer_policies_ready": True,
        "privacy_policy_ready": True,
        "refund_policy_ready": True,
        "cancellation_policy_ready": True,
        "missing_required_policies": [],
        "blockers": [],
    }


def test_operator_can_view_but_cannot_edit_organizer_policies():
    operator = _create_user("policy-operator@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon")
    _create_membership(operator, organizer, OrganizerMembership.Role.OPERATOR)
    OrganizerPolicies.objects.create(
        organizer=organizer,
        privacy_policy="Traveler privacy terms.",
        refund_policy="Refund terms.",
        cancellation_policy="Cancellation terms.",
    )
    client = _authenticated_client(operator)

    read_response = client.get(f"/api/organizers/{organizer.id}/policies/")
    write_response = client.patch(
        f"/api/organizers/{organizer.id}/policies/",
        {"refund_policy": "Operator edit attempt."},
        format="json",
    )

    assert read_response.status_code == 200
    assert read_response.json()["refund_policy"] == "Refund terms."
    assert write_response.status_code == 403
    assert OrganizerPolicies.objects.get(organizer=organizer).refund_policy == "Refund terms."


def test_organizer_policy_role_capabilities_are_explicit():
    owner = _create_user("policy-capability-owner@example.com")
    operator = _create_user("policy-capability-operator@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon")
    _create_membership(owner, organizer, OrganizerMembership.Role.OWNER)
    _create_membership(operator, organizer, OrganizerMembership.Role.OPERATOR)

    owner_role = require_membership(owner, organizer.id)
    operator_role = require_membership(operator, organizer.id)

    assert owner_role.can_view_organizer_policies is True
    assert owner_role.can_manage_organizer_policies is True
    assert operator_role.can_view_organizer_policies is True
    assert operator_role.can_manage_organizer_policies is False


def test_policy_readiness_reports_missing_required_profile_policies():
    organizer = Organizer.objects.create(name="Himalayan Monsoon")
    OrganizerPolicies.objects.create(
        organizer=organizer,
        privacy_policy="Traveler privacy terms.",
        refund_policy="",
        cancellation_policy="Cancellation terms.",
    )

    readiness = organizer_policies_readiness(organizer)
    profile_readiness = required_organizer_profile_policy_readiness(organizer)

    assert readiness.ready is False
    assert readiness.missing_required_policies == ("refund_policy",)
    assert readiness.blockers == ("Add Organizer Refund Policy.",)
    assert profile_readiness == readiness


def test_policy_readiness_treats_missing_record_as_not_ready():
    organizer = Organizer.objects.create(name="Himalayan Monsoon")

    readiness = organizer_policies_readiness(organizer)

    assert readiness.to_payload() == {
        "organizer_policies_ready": False,
        "privacy_policy_ready": False,
        "refund_policy_ready": False,
        "cancellation_policy_ready": False,
        "missing_required_policies": [
            "privacy_policy",
            "refund_policy",
            "cancellation_policy",
        ],
        "blockers": [
            "Add Organizer Privacy Policy.",
            "Add Organizer Refund Policy.",
            "Add Organizer Cancellation Policy.",
        ],
    }


def _create_user(email: str):
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        password="tripos-test-password",
    )


def _create_membership(user, organizer: Organizer, role: str) -> OrganizerMembership:
    return OrganizerMembership.objects.create(user=user, organizer=organizer, role=role)


def _authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client
