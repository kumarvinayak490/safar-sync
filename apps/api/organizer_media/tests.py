from __future__ import annotations

import importlib

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from organizer_media.media import validate_organizer_media_upload
from organizer_media.models import OrganizerMediaItem
from organizer_media.selectors import public_organizer_media_payload
from organizer_profile.serializers import OrganizerProfileIdentitySerializer
from organizers.models import Organizer, OrganizerMembership

pytestmark = pytest.mark.django_db

PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


def test_owner_uploads_organizer_media_with_metadata(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    owner, organizer = create_owner("media-owner@example.com")
    client = authenticated_client(owner)

    response = client.post(
        f"/api/organizers/{organizer.id}/media/",
        {
            "images": [
                SimpleUploadedFile(
                    "basecamp.png",
                    PNG_BYTES,
                    content_type="image/png",
                ),
                SimpleUploadedFile(
                    "summit.png",
                    PNG_BYTES,
                    content_type="image/png",
                ),
            ],
        },
        format="multipart",
    )

    payload = response.json()
    items = list(OrganizerMediaItem.objects.filter(organizer=organizer).order_by("position"))
    assert response.status_code == 201
    assert [item.original_filename for item in items] == ["basecamp.png", "summit.png"]
    assert [item.position for item in items] == [1, 2]
    assert [item.visibility for item in items] == [
        OrganizerMediaItem.Visibility.PRIVATE,
        OrganizerMediaItem.Visibility.PRIVATE,
    ]
    assert items[0].uploaded_by == owner
    assert items[0].content_type == "image/png"
    assert items[0].file_size == len(PNG_BYTES)
    assert "organizer-media/organizer-" in items[0].image.name
    assert payload["readiness"]["blockers"] == []
    assert payload["readiness"]["encouraged"] == [
        "Add at least one Public Organizer Media item."
    ]


def test_media_library_updates_visibility_ordering_and_copy(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    owner, organizer = create_owner("media-order-owner@example.com")
    first = create_media_item(organizer, "first.png", position=1)
    second = create_media_item(organizer, "second.png", position=2)
    client = authenticated_client(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/media/",
        {
            "media_items": [
                {
                    "id": second.id,
                    "caption": "  Summit morning  ",
                    "alt_text": "  Group at the summit  ",
                    "visibility": OrganizerMediaItem.Visibility.PUBLIC,
                },
                {
                    "id": first.id,
                    "caption": "Basecamp",
                    "visibility": OrganizerMediaItem.Visibility.PRIVATE,
                },
            ]
        },
        format="json",
    )

    first.refresh_from_db()
    second.refresh_from_db()
    payload = response.json()
    assert response.status_code == 200
    assert [item["id"] for item in payload["media_items"]] == [second.id, first.id]
    assert payload["media_items"][0]["caption"] == "Summit morning"
    assert payload["media_items"][0]["alt_text"] == "Group at the summit"
    assert payload["media_items"][0]["visibility"] == OrganizerMediaItem.Visibility.PUBLIC
    assert payload["media_items"][0]["is_public"] is True
    assert second.position == 1
    assert first.position == 2
    assert payload["readiness"]["public_media_count"] == 1
    assert payload["readiness"]["total_media_count"] == 2
    assert payload["readiness"]["encouraged"] == []
    assert payload["readiness"]["blockers"] == []


def test_profile_identity_displays_only_public_organizer_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    organizer = Organizer.objects.create(
        name="Himalayan Monsoon",
        identity_name="Kaza Field Collective",
    )
    private_item = create_media_item(
        organizer,
        "private.png",
        position=1,
        visibility=OrganizerMediaItem.Visibility.PRIVATE,
        caption="Private scouting",
    )
    public_item = create_media_item(
        organizer,
        "public.png",
        position=2,
        visibility=OrganizerMediaItem.Visibility.PUBLIC,
        caption="Public trust marker",
    )

    serializer = OrganizerProfileIdentitySerializer(organizer)
    payload = serializer.data
    selector_payload = public_organizer_media_payload(organizer)

    assert [item["id"] for item in payload["media_items"]] == [public_item.id]
    assert payload["media_items"][0]["caption"] == "Public trust marker"
    assert selector_payload[0]["id"] == public_item.id
    assert private_item.id not in {item["id"] for item in payload["media_items"]}


def test_operator_can_view_but_not_manage_organizer_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    _owner, organizer = create_owner("media-owner-access@example.com")
    operator = create_user("media-operator@example.com")
    OrganizerMembership.objects.create(
        organizer=organizer,
        user=operator,
        role=OrganizerMembership.Role.OPERATOR,
    )
    create_media_item(
        organizer,
        "public.png",
        visibility=OrganizerMediaItem.Visibility.PUBLIC,
    )
    client = authenticated_client(operator)

    get_response = client.get(f"/api/organizers/{organizer.id}/media/")
    post_response = client.post(
        f"/api/organizers/{organizer.id}/media/",
        {
            "images": [
                SimpleUploadedFile(
                    "blocked.png",
                    PNG_BYTES,
                    content_type="image/png",
                )
            ],
        },
        format="multipart",
    )

    assert get_response.status_code == 200
    assert post_response.status_code == 403
    assert OrganizerMediaItem.objects.filter(organizer=organizer).count() == 1


def test_organizer_media_upload_validation_rejects_mismatched_content():
    upload = SimpleUploadedFile(
        "not-media.png",
        b"not an image",
        content_type="image/png",
    )

    with pytest.raises(ValidationError, match="does not match"):
        validate_organizer_media_upload(upload)


def test_legacy_organizer_api_reexports_media_view():
    legacy_views = importlib.import_module("organizers.views")
    media_views = importlib.import_module("organizer_media.views")

    assert legacy_views.OrganizerMediaLibraryView is media_views.OrganizerMediaLibraryView


def create_user(email: str):
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        password="pass",
    )


def create_owner(email: str):
    owner = create_user(email)
    organizer = Organizer.objects.create(name=f"Organizer {email}")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    return owner, organizer


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def create_media_item(
    organizer: Organizer,
    filename: str,
    *,
    position: int = 1,
    visibility: str = OrganizerMediaItem.Visibility.PRIVATE,
    caption: str = "",
) -> OrganizerMediaItem:
    return OrganizerMediaItem.objects.create(
        organizer=organizer,
        image=SimpleUploadedFile(
            filename,
            PNG_BYTES,
            content_type="image/png",
        ),
        original_filename=filename,
        content_type="image/png",
        file_size=len(PNG_BYTES),
        position=position,
        visibility=visibility,
        caption=caption,
    )
