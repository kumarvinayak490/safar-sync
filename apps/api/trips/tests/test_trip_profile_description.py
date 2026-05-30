from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from organizers.models import (
    ActivityLog,
    Organizer,
    OrganizerMembership,
    Trip,
    TripPackage,
    TripPaymentSchedule,
)
from trips.rich_text import is_trip_rich_text_empty, sanitize_trip_rich_text

pytestmark = pytest.mark.django_db


def test_trip_rich_text_sanitizes_unsupported_nodes_marks_and_links():
    sanitized = sanitize_trip_rich_text(
        {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 1, "style": "color:red"},
                    "content": [{"type": "text", "text": "What travelers see"}],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Carry layers.",
                            "marks": [
                                {"type": "bold"},
                                {"type": "script"},
                                {"type": "link", "attrs": {"href": "javascript:alert(1)"}},
                            ],
                        }
                    ],
                },
                {"type": "image", "attrs": {"src": "https://example.test/image.png"}},
                {"type": "table", "content": [{"type": "text", "text": "No tables"}]},
                {
                    "type": "bullet_list",
                    "content": [
                        {
                            "type": "list_item",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": "Read packing notes",
                                            "marks": [
                                                {
                                                    "type": "link",
                                                    "attrs": {"href": "https://tripos.test/notes"},
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                },
            ],
        }
    )

    assert [node["type"] for node in sanitized["content"]] == [
        "heading",
        "paragraph",
        "bullet_list",
    ]
    assert sanitized["content"][0]["attrs"] == {"level": 2}
    assert sanitized["content"][1]["content"][0]["marks"] == [{"type": "bold"}]
    link_marks = sanitized["content"][2]["content"][0]["content"][0]["content"][0]["marks"]
    assert link_marks == [{"type": "link", "attrs": {"href": "https://tripos.test/notes"}}]

    with pytest.raises(ValidationError):
        sanitize_trip_rich_text("<script>alert(1)</script>")


@pytest.mark.parametrize(
    "role",
    [OrganizerMembership.Role.OWNER, OrganizerMembership.Role.OPERATOR],
)
def test_owner_and_operator_can_save_unlocked_trip_description(role):
    organizer = create_organizer()
    actor = create_user(f"{role}-description@example.com")
    OrganizerMembership.objects.create(user=actor, organizer=organizer, role=role)
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(actor)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/description/",
        {"description_rich_text": rich_text_payload("A field-ready Spiti trip.")},
        format="json",
    )

    trip.refresh_from_db()
    assert response.status_code == 200
    assert response.json()["description_plain_text"] == "A field-ready Spiti trip."
    assert is_trip_rich_text_empty(trip.description_rich_text) is False
    assert ActivityLog.objects.filter(
        trip=trip,
        actor=actor,
        action=ActivityLog.Action.TRIP_DESCRIPTION_UPDATED,
    ).exists()


def test_trip_description_save_rejects_invalid_payload():
    organizer = create_organizer()
    owner = create_user("invalid-description-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/description/",
        {"description_rich_text": "<h1>Arbitrary HTML</h1>"},
        format="json",
    )

    assert response.status_code == 400
    assert "description_rich_text" in response.json()


@pytest.mark.parametrize(
    "publication_state",
    [Trip.PublicationState.PUBLISHED, Trip.PublicationState.ARCHIVED],
)
def test_locked_trip_profile_rejects_trip_description_save(publication_state):
    organizer = create_organizer()
    owner = create_user("locked-description-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(
        organizer,
        publication_state=publication_state,
        description_rich_text=rich_text_payload("Locked original."),
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/description/",
        {"description_rich_text": rich_text_payload("Changed after publication.")},
        format="json",
    )

    trip.refresh_from_db()
    assert response.status_code == 400
    assert "Published Trip Profile Lock" in str(response.json())
    assert trip.description_rich_text == rich_text_payload("Locked original.")


def test_public_trip_payload_exposes_sanitized_trip_description():
    organizer = create_organizer()
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        description_rich_text={
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Traveler-facing detail.",
                            "marks": [{"type": "italic"}, {"type": "fontSize"}],
                        }
                    ],
                },
                {"type": "embed", "attrs": {"src": "https://example.test/embed"}},
            ],
        },
    )
    client = APIClient()

    response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    assert response.status_code == 200
    assert response.json()["description_rich_text"] == {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "Traveler-facing detail.",
                        "marks": [{"type": "italic"}],
                    }
                ],
            }
        ],
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
        confirmation_requirements_note="Identity details and emergency contact.",
        itinerary="Day 1: Chandigarh arrival. Day 2: Transit to Kaza.",
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
