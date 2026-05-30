from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from organizers.models import (
    ActivityLog,
    Booking,
    LedgerEntry,
    Organizer,
    OrganizerMembership,
    Trip,
    TripItineraryDay,
    TripPackage,
    TripPaymentSchedule,
)
from trips.duplication import duplicate_trip

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "role",
    [OrganizerMembership.Role.OWNER, OrganizerMembership.Role.OPERATOR],
)
def test_owner_and_operator_can_save_ordered_itinerary_days(role):
    organizer = create_organizer()
    actor = create_user(f"{role}-itinerary@example.com")
    OrganizerMembership.objects.create(user=actor, organizer=organizer, role=role)
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(actor)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/itinerary/",
        {
            "itinerary_days": [
                {
                    "sequence": 2,
                    "title": "High valley field day",
                    "date_label": "Day 2",
                    "description_rich_text": rich_text_payload("Acclimatized field work."),
                },
                {
                    "sequence": 1,
                    "title": "Arrival and readiness review",
                    "date_label": "Day 1",
                    "description_rich_text": rich_text_payload("Meet the group and review kit."),
                },
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    assert [day["sequence"] for day in response.json()["itinerary_days"]] == [1, 2]
    assert [day["title"] for day in response.json()["itinerary_days"]] == [
        "Arrival and readiness review",
        "High valley field day",
    ]
    assert list(trip.itinerary_days.values_list("sequence", "title")) == [
        (1, "Arrival and readiness review"),
        (2, "High valley field day"),
    ]
    assert ActivityLog.objects.filter(
        trip=trip,
        actor=actor,
        action=ActivityLog.Action.TRIP_ITINERARY_UPDATED,
        metadata__day_count=2,
    ).exists()


def test_itinerary_day_save_validates_sequences_title_and_rich_text():
    organizer = create_organizer()
    owner = create_user("itinerary-validation-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(owner)

    duplicate_sequence_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/itinerary/",
        {
            "itinerary_days": [
                {
                    "sequence": 1,
                    "title": "Arrival",
                    "description_rich_text": rich_text_payload("Arrive."),
                },
                {
                    "sequence": 1,
                    "title": "Field day",
                    "description_rich_text": rich_text_payload("Walk."),
                },
            ]
        },
        format="json",
    )
    invalid_content_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/itinerary/",
        {
            "itinerary_days": [
                {
                    "sequence": 1,
                    "title": " ",
                    "description_rich_text": "<h1>HTML is not accepted</h1>",
                }
            ]
        },
        format="json",
    )
    empty_description_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/itinerary/",
        {
            "itinerary_days": [
                {
                    "sequence": 1,
                    "title": "Arrival",
                    "description_rich_text": {"type": "doc", "content": []},
                }
            ]
        },
        format="json",
    )

    assert duplicate_sequence_response.status_code == 400
    assert "Itinerary Day sequences must be unique." in str(
        duplicate_sequence_response.json()
    )
    assert invalid_content_response.status_code == 400
    assert "Itinerary Day title is required." in str(invalid_content_response.json())
    assert "Trip Rich Text must be a structured document." in str(
        invalid_content_response.json()
    )
    assert empty_description_response.status_code == 400
    assert "Itinerary Day description is required." in str(
        empty_description_response.json()
    )
    assert trip.itinerary_days.count() == 0


def test_itinerary_day_save_replaces_removed_days_and_allows_empty_readiness_blocker():
    organizer = create_organizer()
    owner = create_user("itinerary-empty-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    TripItineraryDay.objects.create(
        trip=trip,
        sequence=1,
        title="Arrival",
        date_label="Day 1",
        description_rich_text=rich_text_payload("Arrive."),
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/itinerary/",
        {"itinerary_days": []},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["itinerary_days"] == []
    assert trip.itinerary_days.count() == 0


@pytest.mark.parametrize(
    "publication_state",
    [Trip.PublicationState.PUBLISHED, Trip.PublicationState.ARCHIVED],
)
def test_locked_trip_profile_rejects_itinerary_day_save(publication_state):
    organizer = create_organizer()
    owner = create_user("locked-itinerary-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer, publication_state=publication_state)
    TripItineraryDay.objects.create(
        trip=trip,
        sequence=1,
        title="Locked original",
        description_rich_text=rich_text_payload("Visible to travelers."),
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/itinerary/",
        {
            "itinerary_days": [
                {
                    "sequence": 1,
                    "title": "Changed after publication",
                    "description_rich_text": rich_text_payload("Should not save."),
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 400
    assert "Published Trip Profile Lock" in str(response.json())
    assert list(trip.itinerary_days.values_list("title", flat=True)) == [
        "Locked original"
    ]


def test_non_member_cannot_save_itinerary_days():
    organizer = create_organizer()
    outsider = create_user("outsider-itinerary@example.com")
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(outsider)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/itinerary/",
        {"itinerary_days": []},
        format="json",
    )

    assert response.status_code == 403


def test_itinerary_edits_do_not_change_booking_or_financial_state():
    organizer = create_organizer()
    owner = create_user("itinerary-side-effects-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    package = trip.packages.get()
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=package.reservation_amount_inr,
        description="Opening reservation amount.",
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/itinerary/",
        {
            "itinerary_days": [
                {
                    "sequence": 1,
                    "title": "Arrival",
                    "description_rich_text": rich_text_payload("Arrive and settle."),
                }
            ]
        },
        format="json",
    )

    booking.refresh_from_db()
    package.refresh_from_db()
    assert response.status_code == 200
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert package.price_inr == 32000
    assert package.reservation_amount_inr == 8000
    assert LedgerEntry.objects.filter(booking=booking).count() == 1


def test_trip_duplicate_copies_structured_itinerary_days_without_operations():
    organizer = create_organizer()
    actor = create_user("duplicate-itinerary-owner@example.com")
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
    )
    TripItineraryDay.objects.create(
        trip=trip,
        sequence=1,
        title="Arrival",
        date_label="Day 1",
        description_rich_text=rich_text_payload("Arrive and review readiness."),
    )
    TripItineraryDay.objects.create(
        trip=trip,
        sequence=2,
        title="Field day",
        date_label="Day 2",
        description_rich_text=rich_text_payload("Field work."),
    )
    Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )

    duplicate = duplicate_trip(
        trip,
        title="Spiti Second Run",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 15),
        actor=actor,
    )

    assert duplicate.publication_state == Trip.PublicationState.DRAFT
    assert duplicate.booking_availability == Trip.BookingAvailability.CLOSED
    assert duplicate.bookings.count() == 0
    assert list(
        duplicate.itinerary_days.values_list("sequence", "title", "date_label")
    ) == [
        (1, "Arrival", "Day 1"),
        (2, "Field day", "Day 2"),
    ]


def test_public_trip_payload_exposes_structured_itinerary_days_and_keeps_legacy_fallback():
    organizer = create_organizer()
    trip = create_trip(
        organizer,
        publication_state=Trip.PublicationState.PUBLISHED,
        itinerary="Day 1: legacy arrival. Day 2: legacy transfer.",
    )
    TripItineraryDay.objects.create(
        trip=trip,
        sequence=2,
        title="Field day",
        date_label="Day 2",
        description_rich_text=rich_text_payload("Public structured field work."),
    )
    TripItineraryDay.objects.create(
        trip=trip,
        sequence=1,
        title="Arrival",
        date_label="Day 1",
        description_rich_text=rich_text_payload("Public structured arrival."),
    )
    client = APIClient()

    response = client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["itinerary"] == "Day 1: legacy arrival. Day 2: legacy transfer."
    assert [day["title"] for day in payload["itinerary_days"]] == [
        "Arrival",
        "Field day",
    ]
    assert payload["itinerary_days"][0]["description_plain_text"] == (
        "Public structured arrival."
    )


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
        itinerary=overrides.pop(
            "itinerary",
            "Day 1: Chandigarh arrival. Day 2: Transit to Kaza.",
        ),
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
