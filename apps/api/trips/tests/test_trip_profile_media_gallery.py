from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from organizers.models import (
    Organizer,
    OrganizerMembership,
    Trip,
    TripMediaItem,
    TripPackage,
    TripPaymentSchedule,
)

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "role",
    [OrganizerMembership.Role.OWNER, OrganizerMembership.Role.OPERATOR],
)
def test_owner_and_operator_can_upload_trip_media_images(role, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    organizer = create_organizer()
    actor = create_user(f"{role}-media@example.com")
    OrganizerMembership.objects.create(user=actor, organizer=organizer, role=role)
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(actor)

    response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {"images": [png_upload("cover.png"), webp_upload("valley.webp")]},
        format="multipart",
    )

    assert response.status_code == 201
    assert response.json()["trip_profile_locked"] is False
    assert response.json()["readiness"]["encouraged"] == []
    assert [
        (item["position"], item["is_cover"], item["is_public"])
        for item in response.json()["media_items"]
    ] == [(1, True, True), (2, False, True)]
    assert TripMediaItem.objects.filter(trip=trip).count() == 2


def test_trip_media_gallery_save_orders_metadata_visibility_and_cover(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    organizer = create_organizer()
    owner = create_user("media-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(owner)
    upload_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {"images": [png_upload("arrival.png"), png_upload("trail.png")]},
        format="multipart",
    )
    first_item, second_item = upload_response.json()["media_items"]

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {
            "media_items": [
                {
                    "id": second_item["id"],
                    "caption": "High valley trail",
                    "alt_text": "Travelers walking toward a snowline pass",
                    "is_public": True,
                    "is_cover": True,
                },
                {
                    "id": first_item["id"],
                    "caption": "Arrival briefing",
                    "alt_text": "Organizer briefing the group",
                    "is_public": False,
                    "is_cover": False,
                },
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["readiness"]["encouraged"] == []
    assert response.json()["readiness"]["public_media_count"] == 1
    assert [
        (
            item["id"],
            item["position"],
            item["caption"],
            item["alt_text"],
            item["is_public"],
            item["is_cover"],
        )
        for item in response.json()["media_items"]
    ] == [
        (
            second_item["id"],
            1,
            "High valley trail",
            "Travelers walking toward a snowline pass",
            True,
            True,
        ),
        (first_item["id"], 2, "Arrival briefing", "Organizer briefing the group", False, False),
    ]


def test_trip_media_gallery_save_removes_omitted_rows(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    organizer = create_organizer()
    owner = create_user("media-remove-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(owner)
    upload_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {"images": [png_upload("keep.png"), png_upload("remove.png")]},
        format="multipart",
    )
    keep_item = upload_response.json()["media_items"][0]
    remove_item = upload_response.json()["media_items"][1]

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {
            "media_items": [
                {
                    "id": keep_item["id"],
                    "caption": "Kept image",
                    "alt_text": "",
                    "is_public": True,
                    "is_cover": True,
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["media_items"]] == [keep_item["id"]]
    assert TripMediaItem.objects.filter(id=keep_item["id"]).exists()
    assert not TripMediaItem.objects.filter(id=remove_item["id"]).exists()


def test_trip_media_gallery_rejects_non_images_urls_and_invalid_cover(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    organizer = create_organizer()
    owner = create_user("media-validation-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(owner)

    non_image_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {
            "images": [
                SimpleUploadedFile(
                    "notes.txt",
                    b"not an image",
                    content_type="text/plain",
                )
            ]
        },
        format="multipart",
    )
    external_url_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {"image_url": "https://example.test/photo.jpg"},
        format="json",
    )
    upload_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {"images": [png_upload("one.png"), png_upload("two.png")]},
        format="multipart",
    )
    first_item, second_item = upload_response.json()["media_items"]
    duplicate_cover_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {
            "media_items": [
                {"id": first_item["id"], "is_cover": True},
                {"id": second_item["id"], "is_cover": True},
            ]
        },
        format="json",
    )
    missing_cover_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {
            "media_items": [
                {"id": first_item["id"], "is_cover": False},
                {"id": second_item["id"], "is_cover": False},
            ]
        },
        format="json",
    )

    assert non_image_response.status_code == 400
    assert "PNG, JPG, or WebP" in str(non_image_response.json())
    assert external_url_response.status_code == 400
    assert "images" in external_url_response.json()
    assert duplicate_cover_response.status_code == 400
    assert "only one cover" in str(duplicate_cover_response.json())
    assert missing_cover_response.status_code == 400
    assert "Select one Trip Media cover image" in str(missing_cover_response.json())


def test_private_trip_media_is_hidden_from_public_trip_payload(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    organizer = create_organizer()
    owner = create_user("media-public-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer, publication_state=Trip.PublicationState.PUBLISHED)
    client = APIClient()
    client.force_authenticate(owner)
    upload_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {"images": [png_upload("public.png"), png_upload("private.png")]},
        format="multipart",
    )
    assert upload_response.status_code == 400

    trip.publication_state = Trip.PublicationState.DRAFT
    trip.save(update_fields=["publication_state", "updated_at"])
    upload_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {"images": [png_upload("public.png"), png_upload("private.png")]},
        format="multipart",
    )
    public_item, private_item = upload_response.json()["media_items"]
    client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {
            "media_items": [
                {
                    "id": public_item["id"],
                    "caption": "Public trail",
                    "alt_text": "Public trail image",
                    "is_public": True,
                    "is_cover": True,
                },
                {
                    "id": private_item["id"],
                    "caption": "Private staging",
                    "alt_text": "Private staging image",
                    "is_public": False,
                    "is_cover": False,
                },
            ]
        },
        format="json",
    )
    trip.publication_state = Trip.PublicationState.PUBLISHED
    trip.save(update_fields=["publication_state", "updated_at"])
    client.force_authenticate(user=None)

    response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    assert response.status_code == 200
    assert [item["caption"] for item in response.json()["media_items"]] == ["Public trail"]
    assert response.json()["media_items"][0]["is_public"] is True


def test_uploaded_trip_media_reflects_on_public_trip_payload_by_default(
    settings,
    tmp_path,
):
    settings.MEDIA_ROOT = tmp_path
    organizer = create_organizer()
    owner = create_user("media-default-public-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(owner)
    upload_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {"images": [png_upload("cover.png")]},
        format="multipart",
    )
    assert upload_response.status_code == 201

    trip.publication_state = Trip.PublicationState.PUBLISHED
    trip.save(update_fields=["publication_state", "updated_at"])
    client.force_authenticate(user=None)

    response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    assert response.status_code == 200
    assert [item["original_filename"] for item in response.json()["media_items"]] == [
        "cover.png"
    ]
    assert response.json()["media_items"][0]["is_public"] is True
    assert response.json()["media_items"][0]["is_cover"] is True


@pytest.mark.parametrize(
    "publication_state",
    [Trip.PublicationState.PUBLISHED, Trip.PublicationState.ARCHIVED],
)
def test_locked_trip_profile_allows_trip_media_edits(publication_state, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    organizer = create_organizer()
    owner = create_user("locked-media-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer, publication_state=publication_state)
    client = APIClient()
    client.force_authenticate(owner)

    upload_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {"images": [png_upload("locked.png")]},
        format="multipart",
    )

    assert upload_response.status_code == 201
    assert TripMediaItem.objects.filter(trip=trip).count() == 1
    assert upload_response.json()["media_items"][0]["is_public"] is True


def test_non_member_cannot_edit_trip_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    organizer = create_organizer()
    outsider = create_user("media-outsider@example.com")
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(outsider)

    response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {"images": [png_upload("outsider.png")]},
        format="multipart",
    )

    assert response.status_code == 403
    assert TripMediaItem.objects.filter(trip=trip).count() == 0


def create_user(email: str):
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        password="tripos-test-password",
    )


def create_organizer() -> Organizer:
    return Organizer.objects.create(name="Himalayan Monsoon Cohort")


def create_trip(organizer: Organizer, **overrides) -> Trip:
    trip = Trip.objects.create(
        organizer=organizer,
        title=overrides.pop("title", "Spiti Winter Field Week"),
        start_date=overrides.pop("start_date", date(2026, 10, 10)),
        end_date=overrides.pop("end_date", date(2026, 10, 15)),
        capacity=overrides.pop("capacity", 24),
        description_rich_text=rich_text_payload("A public Spiti trip."),
        **overrides,
    )
    TripPackage.objects.create(
        trip=trip,
        name="Standard shared room",
        price_inr=32000,
        reservation_amount_inr=8000,
    )
    TripPaymentSchedule.objects.create(
        trip=trip,
        balance_due_days_before_start=14,
    )
    return trip


def png_upload(name: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name,
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
        content_type="image/png",
    )


def webp_upload(name: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name,
        b"RIFF\x0c\x00\x00\x00WEBPVP8 ",
        content_type="image/webp",
    )


def rich_text_payload(text: str) -> dict:
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }
