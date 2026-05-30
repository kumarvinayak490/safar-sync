from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from creative_setup.models import CreativeSetup
from organizers.models import Organizer
from team_access.models import OrganizerMembership
from team_access.permissions import require_membership

pytestmark = pytest.mark.django_db


def test_owner_can_create_and_update_creative_setup():
    owner = _create_user("creative-owner@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon")
    _create_membership(owner, organizer, OrganizerMembership.Role.OWNER)
    client = _authenticated_client(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/creative-setup/",
        {
            "model_choice": CreativeSetup.ModelChoice.HIGH_DETAIL,
            "brand_tone": "  Grounded, warm, and precise. ",
            "default_style": " Field-ready editorial poster ",
            "logo_usage": CreativeSetup.LogoUsage.AVOID_BY_DEFAULT,
            "poster_defaults": {
                "format": "instagram_story",
                "headline_style": "short",
            },
        },
        format="json",
    )

    assert response.status_code == 200
    setup = CreativeSetup.objects.get(organizer=organizer)
    assert setup.model_choice == CreativeSetup.ModelChoice.HIGH_DETAIL
    assert setup.brand_tone == "Grounded, warm, and precise."
    assert setup.default_style == "Field-ready editorial poster"
    assert setup.logo_usage == CreativeSetup.LogoUsage.AVOID_BY_DEFAULT
    assert setup.poster_defaults == {
        "format": "instagram_story",
        "headline_style": "short",
    }
    assert response.json() == {
        "model_choice": "high_detail",
        "brand_tone": "Grounded, warm, and precise.",
        "default_style": "Field-ready editorial poster",
        "logo_usage": "avoid_by_default",
        "poster_defaults": {
            "format": "instagram_story",
            "headline_style": "short",
        },
    }


def test_operator_can_view_defaults_but_cannot_edit_creative_setup():
    operator = _create_user("creative-operator@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon")
    _create_membership(operator, organizer, OrganizerMembership.Role.OPERATOR)
    client = _authenticated_client(operator)

    read_response = client.get(f"/api/organizers/{organizer.id}/creative-setup/")
    write_response = client.patch(
        f"/api/organizers/{organizer.id}/creative-setup/",
        {"brand_tone": "Operator edit attempt."},
        format="json",
    )

    assert read_response.status_code == 200
    assert read_response.json() == {
        "model_choice": "tripos_default",
        "brand_tone": "",
        "default_style": "",
        "logo_usage": "use_when_available",
        "poster_defaults": {},
    }
    assert CreativeSetup.objects.filter(organizer=organizer).exists() is False
    assert write_response.status_code == 403


def test_creative_setup_role_capabilities_are_explicit():
    owner = _create_user("creative-capability-owner@example.com")
    operator = _create_user("creative-capability-operator@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon")
    _create_membership(owner, organizer, OrganizerMembership.Role.OWNER)
    _create_membership(operator, organizer, OrganizerMembership.Role.OPERATOR)

    owner_role = require_membership(owner, organizer.id)
    operator_role = require_membership(operator, organizer.id)

    assert owner_role.can_view_creative_setup is True
    assert owner_role.can_manage_creative_setup is True
    assert operator_role.can_view_creative_setup is True
    assert operator_role.can_manage_creative_setup is False


def test_creative_setup_rejects_non_object_poster_defaults():
    owner = _create_user("creative-poster-defaults-owner@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon")
    _create_membership(owner, organizer, OrganizerMembership.Role.OWNER)
    client = _authenticated_client(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/creative-setup/",
        {"poster_defaults": ["story", "square"]},
        format="json",
    )

    assert response.status_code == 400
    assert "poster_defaults" in response.json()
    assert CreativeSetup.objects.filter(organizer=organizer).exists() is False


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
