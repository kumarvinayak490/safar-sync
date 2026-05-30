from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from organizers.models import (
    ActivityLog,
    Organizer,
    OrganizerMembership,
    Trip,
    TripItineraryDay,
    TripPackage,
    TripPaymentSchedule,
)

pytestmark = pytest.mark.django_db


def test_trip_profile_reads_and_local_draft_equivalent_do_not_create_activity_logs():
    organizer = create_organizer()
    owner = create_user("activity-no-local-log-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(owner)

    local_draft_payload = {"description_rich_text": rich_text_payload("Unsaved draft.")}
    response = client.get(f"/api/organizers/{organizer.id}/trips/{trip.id}/description/")

    assert response.status_code == 200
    assert local_draft_payload["description_rich_text"] != response.json()[
        "description_rich_text"
    ]
    assert ActivityLog.objects.filter(trip=trip).count() == 0


def test_trip_description_save_records_activity_log_metadata_without_rich_text_payload():
    organizer = create_organizer()
    operator = create_user("activity-description-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer, description_rich_text={"type": "doc", "content": []})
    client = APIClient()
    client.force_authenticate(operator)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/description/",
        {"description_rich_text": rich_text_payload("A field-ready Spiti trip.")},
        format="json",
    )

    assert response.status_code == 200
    log = ActivityLog.objects.get(
        trip=trip,
        actor=operator,
        action=ActivityLog.Action.TRIP_DESCRIPTION_UPDATED,
    )
    assert log.metadata == {
        "section": "description",
        "change_type": "created",
        "plain_text_length": len("A field-ready Spiti trip."),
    }
    assert "description_rich_text" not in log.metadata
    assert "A field-ready Spiti trip." not in str(log.metadata)


def test_itinerary_day_save_records_activity_log_metadata_without_rich_text_payload():
    organizer = create_organizer()
    operator = create_user("activity-itinerary-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(operator)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/itinerary/",
        {
            "itinerary_days": [
                {
                    "sequence": 1,
                    "title": "Arrival and readiness review",
                    "description_rich_text": rich_text_payload("Meet the group."),
                },
                {
                    "sequence": 2,
                    "title": "High valley field day",
                    "description_rich_text": rich_text_payload("Walk the ridge."),
                },
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    log = ActivityLog.objects.get(
        trip=trip,
        actor=operator,
        action=ActivityLog.Action.TRIP_ITINERARY_UPDATED,
    )
    assert log.metadata == {
        "section": "itinerary",
        "change_type": "created",
        "previous_day_count": 0,
        "day_count": 2,
    }
    assert "Meet the group." not in str(log.metadata)


def test_trip_media_gallery_saves_record_activity_log_counts_without_media_payload(
    settings,
    tmp_path,
):
    settings.MEDIA_ROOT = tmp_path
    organizer = create_organizer()
    operator = create_user("activity-media-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(operator)

    upload_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {"images": [png_upload("arrival.png"), png_upload("trail.png")]},
        format="multipart",
    )
    first_item, second_item = upload_response.json()["media_items"]
    save_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/media/",
        {
            "media_items": [
                {
                    "id": second_item["id"],
                    "caption": "High valley trail",
                    "alt_text": "Travelers walking toward the pass",
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

    assert upload_response.status_code == 201
    assert save_response.status_code == 200
    logs = list(
        ActivityLog.objects.filter(
            trip=trip,
            actor=operator,
            action=ActivityLog.Action.TRIP_MEDIA_GALLERY_UPDATED,
        ).order_by("created_at", "id")
    )
    assert [log.metadata["change_type"] for log in logs] == ["added", "updated"]
    assert logs[0].metadata == {
        "section": "media",
        "change_type": "added",
        "previous_item_count": 0,
        "item_count": 2,
        "uploaded_item_count": 2,
        "public_item_count": 0,
    }
    assert logs[1].metadata == {
        "section": "media",
        "change_type": "updated",
        "previous_item_count": 2,
        "item_count": 2,
        "removed_item_count": 0,
        "updated_item_count": 2,
        "public_item_count": 1,
    }
    assert "arrival.png" not in str(logs[0].metadata)
    assert "High valley trail" not in str(logs[1].metadata)


def test_package_section_save_records_activity_log_change_counts():
    organizer = create_organizer()
    owner = create_user("activity-packages-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    package = trip.packages.get()
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/packages/",
        {
            "packages": [
                {
                    "id": package.id,
                    "name": "Standard shared room updated",
                    "description": "Twin sharing base.",
                    "price_inr": 34000,
                    "reservation_amount_inr": 9000,
                },
                {
                    "name": "Premium room",
                    "description": "Smaller group rooming.",
                    "price_inr": 44000,
                    "reservation_amount_inr": 14000,
                },
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    log = ActivityLog.objects.get(
        trip=trip,
        actor=owner,
        action=ActivityLog.Action.TRIP_PACKAGES_UPDATED,
    )
    assert log.metadata == {
        "section": "packages",
        "change_type": "added",
        "previous_active_package_count": 1,
        "active_package_count": 2,
        "added_package_count": 1,
        "removed_package_count": 0,
        "withdrawn_package_count": 0,
        "updated_package_count": 1,
    }
    assert "Standard shared room updated" not in str(log.metadata)


def test_payment_schedule_save_records_activity_log_review_and_change_metadata():
    organizer = create_organizer()
    owner = create_user("activity-payment-schedule-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/payment-schedule/",
        {
            "has_balance_milestone": True,
            "balance_due_days_before_start": 21,
            "balance_reminder_lead_days": 5,
        },
        format="json",
    )

    assert response.status_code == 200
    log = ActivityLog.objects.get(
        trip=trip,
        actor=owner,
        action=ActivityLog.Action.TRIP_PAYMENT_SCHEDULE_UPDATED,
    )
    assert log.metadata == {
        "section": "payment_schedule",
        "change_type": "reviewed_and_updated",
        "changed_fields": [
            "balance_due_days_before_start",
            "balance_reminder_lead_days",
        ],
        "changed_field_count": 2,
        "has_balance_milestone": True,
        "balance_due_days_before_start": 21,
        "balance_reminder_lead_days": 5,
        "reviewed": True,
    }


def test_confirmation_requirements_save_records_activity_log_review_metadata_only():
    organizer = create_organizer()
    operator = create_user("activity-requirements-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(operator)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/confirmation-requirements/",
        {
            "confirmation_requirements_note": "Collect medical details privately.",
            "requires_traveler_identity_details": True,
            "requires_medical_disclosure": True,
            "requires_full_payment_before_confirmation": True,
        },
        format="json",
    )

    assert response.status_code == 200
    log = ActivityLog.objects.get(
        trip=trip,
        actor=operator,
        action=ActivityLog.Action.TRIP_CONFIRMATION_REQUIREMENTS_UPDATED,
    )
    assert log.metadata == {
        "section": "confirmation_requirements",
        "change_type": "reviewed_and_updated",
        "changed_fields": [
            "confirmation_requirements_note",
            "requires_traveler_identity_details",
            "requires_medical_disclosure",
            "requires_full_payment_before_confirmation",
        ],
        "changed_field_count": 4,
        "active_requirement_count": 3,
        "reviewed": True,
    }
    assert "Collect medical details privately." not in str(log.metadata)


def test_publish_records_owner_activity_log_with_lock_acknowledgement_metadata():
    owner = create_user("activity-publish-owner@example.com")
    organizer = create_organizer()
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_publication_ready_trip(organizer, owner)
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {
            "publication_state": Trip.PublicationState.PUBLISHED,
            "publish_lock_acknowledged": True,
        },
        format="json",
    )

    assert response.status_code == 200
    log = ActivityLog.objects.get(
        trip=trip,
        actor=owner,
        action=ActivityLog.Action.PUBLIC_TRIP_PAGE_PUBLISHED,
    )
    assert log.metadata == {
        "section": "publication",
        "change_type": "published",
        "published_trip_profile_lock_acknowledged": True,
        "previous_publication_state": Trip.PublicationState.DRAFT,
        "publication_state": Trip.PublicationState.PUBLISHED,
    }


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
        description_rich_text=overrides.pop(
            "description_rich_text",
            rich_text_payload("A public Spiti trip."),
        ),
        **overrides,
    )
    TripPackage.objects.create(
        trip=trip,
        name="Standard shared room",
        price_inr=32000,
        reservation_amount_inr=8000,
        position=1,
    )
    TripPaymentSchedule.objects.create(
        trip=trip,
        balance_due_days_before_start=14,
    )
    return trip


def create_publication_ready_trip(organizer: Organizer, reviewer) -> Trip:
    trip = create_trip(organizer)
    TripItineraryDay.objects.create(
        trip=trip,
        sequence=1,
        title="Arrival",
        description_rich_text=rich_text_payload("Meet the group."),
    )
    trip.requires_traveler_identity_details = True
    trip.confirmation_requirements_reviewed_at = timezone.now()
    trip.confirmation_requirements_reviewed_by = reviewer
    trip.save(
        update_fields=[
            "requires_traveler_identity_details",
            "confirmation_requirements_reviewed_at",
            "confirmation_requirements_reviewed_by",
            "updated_at",
        ]
    )
    trip.payment_schedule.reviewed_at = timezone.now()
    trip.payment_schedule.reviewed_by = reviewer
    trip.payment_schedule.save(update_fields=["reviewed_at", "reviewed_by", "updated_at"])
    return trip


def png_upload(name: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name,
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
        content_type="image/png",
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
