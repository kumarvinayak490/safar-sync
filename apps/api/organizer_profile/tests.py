from __future__ import annotations

import importlib

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from organizer_policies.models import OrganizerPolicies
from organizer_profile.identity import (
    organizer_profile_identity_payload,
    public_organizer_logo_url,
    public_organizer_name,
    validate_organizer_logo_upload,
)
from organizer_profile.models import OrganizerProfile
from organizers.models import Organizer
from team_access.models import OrganizerMembership
from team_access.permissions import require_membership
from trips.models import Trip

PNG_LOGO_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


def test_public_identity_payload_prefers_profile_fields():
    organizer = Organizer(
        name="Himalayan Monsoon",
        identity_name="Kaza Field Collective",
        identity_whatsapp_number=" +91 98765 43210 ",
    )

    payload = organizer_profile_identity_payload(organizer)

    assert public_organizer_name(organizer) == "Kaza Field Collective"
    assert payload["name"] == "Kaza Field Collective"
    assert payload["identity_name"] == "Kaza Field Collective"
    assert payload["identity_whatsapp_number"] == "+91 98765 43210"
    assert payload["logo_uploaded"] is False
    assert payload["logo_url"] == ""
    assert payload["fallback"]["initials"] == "KF"
    assert payload["placeholder"] is False


def test_public_identity_payload_falls_back_to_organizer_root_name():
    organizer = Organizer(name="Himalayan Monsoon")

    payload = organizer_profile_identity_payload(organizer)

    assert payload["name"] == "Himalayan Monsoon"
    assert payload["fallback"]["initials"] == "HM"
    assert payload["placeholder"] is True


@pytest.mark.django_db
def test_profile_identity_api_preserves_legacy_route_and_response_shape(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    owner = _create_user("profile-owner@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/identity/",
        {
            "identity_name": "Kaza Field Collective",
            "identity_whatsapp_number": " +91 98765 43210 ",
            "identity_logo": SimpleUploadedFile(
                "kaza.png",
                PNG_LOGO_BYTES,
                content_type="image/png",
            ),
        },
        format="multipart",
    )

    organizer.refresh_from_db()
    payload = response.json()
    assert response.status_code == 200
    assert payload["name"] == "Kaza Field Collective"
    assert payload["identity_name"] == "Kaza Field Collective"
    assert payload["identity_whatsapp_number"] == "+91 98765 43210"
    assert payload["logo_uploaded"] is True
    assert "/media/organizer-logos/" in payload["logo_url"]
    assert public_organizer_logo_url(organizer).endswith(".png")
    assert payload["public_description"] == ""
    assert payload["publication_state"] == OrganizerProfile.PublicationState.DRAFT
    assert payload["organizer_profile_readiness"]["publish_eligible"] is False


@pytest.mark.django_db
def test_owner_can_publish_ready_organizer_profile_without_public_media():
    owner = _create_user("profile-publication-owner@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon")
    _create_membership(owner, organizer, OrganizerMembership.Role.OWNER)
    _create_required_policies(organizer)
    client = _authenticated_client(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/identity/",
        {
            "public_description": " Field-tested group trips through Spiti. ",
            "publication_state": OrganizerProfile.PublicationState.PUBLISHED,
        },
        format="json",
    )

    profile = OrganizerProfile.objects.get(organizer=organizer)
    payload = response.json()
    assert response.status_code == 200
    assert profile.public_description == "Field-tested group trips through Spiti."
    assert profile.publication_state == OrganizerProfile.PublicationState.PUBLISHED
    assert payload["publication_state"] == OrganizerProfile.PublicationState.PUBLISHED
    assert payload["organizer_profile_readiness"]["publish_eligible"] is True
    assert payload["organizer_profile_readiness"]["public_media_count"] == 0
    assert payload["organizer_profile_readiness"]["encouraged"] == [
        "Add at least one Public Organizer Media item."
    ]


@pytest.mark.django_db
def test_organizer_profile_publish_reports_missing_description_and_policies():
    owner = _create_user("profile-blocked-owner@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon")
    _create_membership(owner, organizer, OrganizerMembership.Role.OWNER)
    OrganizerPolicies.objects.create(
        organizer=organizer,
        privacy_policy="Traveler data is handled carefully.",
        refund_policy="",
        cancellation_policy="Organizer cancellation terms.",
    )
    client = _authenticated_client(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/identity/",
        {"publication_state": OrganizerProfile.PublicationState.PUBLISHED},
        format="json",
    )

    payload = response.json()
    readiness = payload["organizer_profile_readiness"]
    assert response.status_code == 400
    assert payload["publication_state"] == ["Organizer Profile is not ready to publish."]
    assert readiness["publish_eligible"] is False
    assert readiness["missing_required_policies"] == ["refund_policy"]
    assert readiness["blockers"] == [
        "Add Public Organizer Description.",
        "Add Organizer Refund Policy.",
    ]
    assert OrganizerProfile.objects.filter(organizer=organizer).exists() is False


@pytest.mark.django_db
def test_operator_can_view_but_cannot_publish_organizer_profile():
    owner = _create_user("profile-role-owner@example.com")
    operator = _create_user("profile-role-operator@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon")
    _create_membership(owner, organizer, OrganizerMembership.Role.OWNER)
    _create_membership(operator, organizer, OrganizerMembership.Role.OPERATOR)
    _create_required_policies(organizer)
    OrganizerProfile.objects.create(
        organizer=organizer,
        public_description="Operator-visible public description.",
    )
    client = _authenticated_client(operator)

    read_response = client.get(f"/api/organizers/{organizer.id}/identity/")
    publish_response = client.patch(
        f"/api/organizers/{organizer.id}/identity/",
        {"publication_state": OrganizerProfile.PublicationState.PUBLISHED},
        format="json",
    )

    profile = OrganizerProfile.objects.get(organizer=organizer)
    owner_role = require_membership(owner, organizer.id)
    operator_role = require_membership(operator, organizer.id)
    assert read_response.status_code == 200
    assert read_response.json()["organizer_profile_readiness"]["publish_eligible"] is True
    assert publish_response.status_code == 403
    assert profile.publication_state == OrganizerProfile.PublicationState.DRAFT
    assert owner_role.can_publish_organizer_profile is True
    assert operator_role.can_view_organizer_profile is True
    assert operator_role.can_publish_organizer_profile is False


@pytest.mark.django_db
def test_organizer_profile_publication_state_is_separate_from_trip_publication():
    owner = _create_user("profile-trip-separate-owner@example.com")
    organizer = Organizer.objects.create(name="Himalayan Monsoon")
    _create_membership(owner, organizer, OrganizerMembership.Role.OWNER)
    _create_required_policies(organizer)
    trip = Trip.objects.create(
        organizer=organizer,
        title="Spiti Winter Field Week",
        start_date="2026-10-10",
        end_date="2026-10-15",
        capacity=24,
        publication_state=Trip.PublicationState.DRAFT,
    )
    client = _authenticated_client(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/identity/",
        {
            "public_description": "Organizer-level trust profile.",
            "publication_state": OrganizerProfile.PublicationState.PUBLISHED,
        },
        format="json",
    )

    trip.refresh_from_db()
    assert response.status_code == 200
    assert response.json()["publication_state"] == OrganizerProfile.PublicationState.PUBLISHED
    assert trip.publication_state == Trip.PublicationState.DRAFT


def test_profile_logo_validation_rejects_mismatched_content():
    upload = SimpleUploadedFile(
        "not-a-logo.png",
        b"not an image",
        content_type="image/png",
    )

    with pytest.raises(ValidationError, match="does not match"):
        validate_organizer_logo_upload(upload)


def test_legacy_identity_imports_reexport_organizer_profile_behavior():
    profile_identity = importlib.import_module("organizer_profile.identity")
    profile_serializers = importlib.import_module("organizer_profile.serializers")
    profile_views = importlib.import_module("organizer_profile.views")
    legacy_flat_identity = importlib.import_module("organizers.organizer_identity")
    legacy_settings_identity = importlib.import_module("organizers.organizer_settings.identity")
    legacy_serializers = importlib.import_module("organizers.serializers")
    legacy_views = importlib.import_module("organizers.views")

    assert (
        legacy_flat_identity.organizer_identity_payload
        is profile_identity.organizer_identity_payload
    )
    assert (
        legacy_settings_identity.organizer_identity_payload
        is profile_identity.organizer_identity_payload
    )
    assert (
        legacy_serializers.OrganizerIdentitySerializer
        is profile_serializers.OrganizerIdentitySerializer
    )
    assert legacy_views.OrganizerIdentityView is profile_views.OrganizerIdentityView


def _create_user(email: str):
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        password="pass",
    )


def _create_membership(user, organizer: Organizer, role: str) -> OrganizerMembership:
    return OrganizerMembership.objects.create(user=user, organizer=organizer, role=role)


def _create_required_policies(organizer: Organizer) -> OrganizerPolicies:
    return OrganizerPolicies.objects.create(
        organizer=organizer,
        privacy_policy="Traveler privacy terms.",
        refund_policy="Refund terms.",
        cancellation_policy="Cancellation terms.",
    )


def _authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client
