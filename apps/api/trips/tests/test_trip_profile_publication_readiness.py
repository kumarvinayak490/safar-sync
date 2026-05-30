from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from organizers.models import (
    ActivityLog,
    Organizer,
    OrganizerMembership,
    ProviderPaymentSetup,
    Trip,
    TripItineraryDay,
    TripPackage,
    TripPaymentSchedule,
)
from trips.publication_readiness import (
    trip_profile_publication_readiness,
)

pytestmark = pytest.mark.django_db


def test_trip_profile_publication_readiness_returns_blockers_and_encouraged_items():
    organizer = create_organizer()
    trip = Trip.objects.create(
        organizer=organizer,
        title="Spiti Winter Field Week",
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 15),
        capacity=24,
    )
    TripPaymentSchedule.objects.create(trip=trip, balance_due_days_before_start=14)

    readiness = trip_profile_publication_readiness(trip)

    assert readiness.publish_eligible is False
    assert [item.id for item in readiness.blockers] == [
        "description",
        "packages",
        "payment-schedule",
        "itinerary",
        "requirements",
    ]
    assert [item.id for item in readiness.encouraged] == ["media-gallery"]


def test_trip_profile_publication_readiness_allows_publish_without_media():
    owner = create_user("ready-profile-owner@example.com")
    organizer = create_organizer()
    trip = create_publication_ready_trip(organizer, owner)

    readiness = trip_profile_publication_readiness(trip)

    assert readiness.publish_eligible is True
    assert readiness.blockers == ()
    assert [item.id for item in readiness.encouraged] == ["media-gallery"]


def test_publish_requires_owner_lock_acknowledgement_and_profile_readiness():
    owner = create_user("publish-owner@example.com")
    operator = create_user("publish-operator@example.com")
    organizer = create_organizer()
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    ready_trip = create_publication_ready_trip(organizer, owner)
    blocked_trip = create_publication_ready_trip(
        organizer,
        owner,
        title="Blocked Publication Trip",
    )
    blocked_trip.description_rich_text = {"type": "doc", "content": []}
    blocked_trip.save(update_fields=["description_rich_text", "updated_at"])
    client = APIClient()

    client.force_authenticate(operator)
    operator_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{ready_trip.id}/",
        {
            "publication_state": Trip.PublicationState.PUBLISHED,
            "publish_lock_acknowledged": True,
        },
        format="json",
    )

    client.force_authenticate(owner)
    missing_ack_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{ready_trip.id}/",
        {"publication_state": Trip.PublicationState.PUBLISHED},
        format="json",
    )
    blocked_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{blocked_trip.id}/",
        {
            "publication_state": Trip.PublicationState.PUBLISHED,
            "publish_lock_acknowledged": True,
        },
        format="json",
    )

    assert operator_response.status_code == 400
    assert "Only Owners can manage Publication State" in str(operator_response.json())
    assert missing_ack_response.status_code == 400
    assert "Published Trip Profile Lock" in str(missing_ack_response.json())
    assert blocked_response.status_code == 400
    assert "Trip Description" in str(blocked_response.json())


def test_publish_records_activity_log_with_actor_and_lock_acknowledgement():
    owner = create_user("published-log-owner@example.com")
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
    assert response.json()["publication_state"] == Trip.PublicationState.PUBLISHED
    log = ActivityLog.objects.get(
        trip=trip,
        actor=owner,
        action=ActivityLog.Action.PUBLIC_TRIP_PAGE_PUBLISHED,
    )
    assert log.metadata["published_trip_profile_lock_acknowledged"] is True
    assert log.metadata["previous_publication_state"] == Trip.PublicationState.DRAFT


def test_publishing_is_separate_from_online_payment_readiness():
    owner = create_user("publish-before-payment-ready-owner@example.com")
    organizer = create_organizer()
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_publication_ready_trip(organizer, owner)
    client = APIClient()
    client.force_authenticate(owner)

    publish_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {
            "publication_state": Trip.PublicationState.PUBLISHED,
            "publish_lock_acknowledged": True,
        },
        format="json",
    )
    open_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"booking_availability": Trip.BookingAvailability.OPEN},
        format="json",
    )

    assert organizer.provider_payment_setup.status == ProviderPaymentSetup.Status.NOT_STARTED
    assert publish_response.status_code == 200
    assert open_response.status_code == 400
    assert "Online Payment Readiness" in str(open_response.json())


def test_published_trip_profile_lock_blocks_core_fact_changes_and_unlock_path():
    owner = create_user("published-lock-core-owner@example.com")
    organizer = create_organizer()
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_publication_ready_trip(organizer, owner)
    trip.publication_state = Trip.PublicationState.PUBLISHED
    trip.save(update_fields=["publication_state", "updated_at"])
    client = APIClient()
    client.force_authenticate(owner)

    capacity_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"capacity": 28},
        format="json",
    )
    setup_date_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"start_date": "2026-11-10", "end_date": "2026-11-15"},
        format="json",
    )
    date_change_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/date-change/",
        {"start_date": "2026-11-10", "end_date": "2026-11-15"},
        format="json",
    )
    unlock_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"publication_state": Trip.PublicationState.DRAFT},
        format="json",
    )

    trip.refresh_from_db()
    assert capacity_response.status_code == 400
    assert "Trip Capacity" in str(capacity_response.json())
    assert setup_date_response.status_code == 400
    assert "Trip Date" in str(setup_date_response.json())
    assert date_change_response.status_code == 400
    assert "Trip Date" in str(date_change_response.json())
    assert unlock_response.status_code == 400
    assert "cannot be removed" in str(unlock_response.json())
    assert trip.capacity == 24
    assert trip.start_date == date(2026, 10, 10)
    assert trip.publication_state == Trip.PublicationState.PUBLISHED


def test_archived_public_trip_page_keeps_profile_lock_and_read_only_get():
    owner = create_user("archive-lock-owner@example.com")
    operator = create_user("archive-lock-operator@example.com")
    organizer = create_organizer()
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_publication_ready_trip(organizer, owner)
    trip.publication_state = Trip.PublicationState.PUBLISHED
    trip.save(update_fields=["publication_state", "updated_at"])
    client = APIClient()
    client.force_authenticate(owner)

    archive_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"publication_state": Trip.PublicationState.ARCHIVED},
        format="json",
    )
    description_edit_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/description/",
        {"description_rich_text": rich_text_payload("Archived edit attempt.")},
        format="json",
    )
    archived_unlock_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"publication_state": Trip.PublicationState.DRAFT},
        format="json",
    )

    client.force_authenticate(operator)
    operator_get_response = client.get(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/description/",
    )
    operator_edit_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/description/",
        {"description_rich_text": rich_text_payload("Operator edit attempt.")},
        format="json",
    )

    trip.refresh_from_db()
    assert archive_response.status_code == 200
    assert archive_response.json()["publication_state"] == Trip.PublicationState.ARCHIVED
    assert description_edit_response.status_code == 400
    assert "Published Trip Profile Lock" in str(description_edit_response.json())
    assert archived_unlock_response.status_code == 400
    assert "cannot be removed" in str(archived_unlock_response.json())
    assert operator_get_response.status_code == 200
    assert operator_get_response.json()["trip_profile_locked"] is True
    assert operator_get_response.json()["description_plain_text"] == (
        "Traveler-facing Spiti details."
    )
    assert operator_edit_response.status_code == 400
    assert trip.publication_state == Trip.PublicationState.ARCHIVED


def test_locked_trip_still_allows_operational_workflows():
    owner = create_user("locked-operations-owner@example.com")
    operator = create_user("locked-operations-operator@example.com")
    organizer = create_organizer()
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    closing_trip = create_publication_ready_trip(
        organizer,
        owner,
        title="Published Closing Trip",
    )
    closing_trip.publication_state = Trip.PublicationState.PUBLISHED
    closing_trip.booking_availability = Trip.BookingAvailability.OPEN
    closing_trip.save(
        update_fields=["publication_state", "booking_availability", "updated_at"]
    )
    cancellation_trip = create_publication_ready_trip(
        organizer,
        owner,
        title="Published Cancellation Trip",
    )
    cancellation_trip.publication_state = Trip.PublicationState.PUBLISHED
    cancellation_trip.save(update_fields=["publication_state", "updated_at"])
    completion_trip = create_publication_ready_trip(
        organizer,
        owner,
        title="Published Completion Trip",
    )
    completion_trip.publication_state = Trip.PublicationState.PUBLISHED
    completion_trip.save(update_fields=["publication_state", "updated_at"])
    client = APIClient()

    client.force_authenticate(operator)
    close_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{closing_trip.id}/",
        {"booking_availability": Trip.BookingAvailability.CLOSED},
        format="json",
    )
    complete_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{completion_trip.id}/complete/",
        format="json",
    )

    client.force_authenticate(owner)
    cancel_response = client.post(
        f"/api/organizers/{organizer.id}/trips/{cancellation_trip.id}/cancel/",
        {"cancellation_reason": "Unsafe weather window."},
        format="json",
    )

    closing_trip.refresh_from_db()
    cancellation_trip.refresh_from_db()
    completion_trip.refresh_from_db()
    assert close_response.status_code == 200
    assert closing_trip.booking_availability == Trip.BookingAvailability.CLOSED
    assert complete_response.status_code == 200
    assert completion_trip.publication_state == Trip.PublicationState.PUBLISHED
    assert cancel_response.status_code == 200
    assert cancellation_trip.publication_state == Trip.PublicationState.PUBLISHED


def create_user(email: str):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=email,
        email=email,
        password="correct horse battery staple",
    )


def create_organizer() -> Organizer:
    return Organizer.objects.create(name="Himalayan Monsoon Cohort")


def create_publication_ready_trip(
    organizer: Organizer,
    reviewer,
    *,
    title: str = "Spiti Winter Field Week",
) -> Trip:
    trip = Trip.objects.create(
        organizer=organizer,
        title=title,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 15),
        capacity=24,
        description_rich_text=rich_text_payload("Traveler-facing Spiti details."),
        confirmation_requirements_note="Identity details and emergency contact.",
        confirmation_requirements_reviewed_at=timezone.now(),
        confirmation_requirements_reviewed_by=reviewer,
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
        reviewed_at=timezone.now(),
        reviewed_by=reviewer,
    )
    TripItineraryDay.objects.create(
        trip=trip,
        sequence=1,
        title="Arrival and readiness review",
        description_rich_text=rich_text_payload("Meet the group and review kit."),
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
