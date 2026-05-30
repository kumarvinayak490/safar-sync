from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from organizers.models import (
    Booking,
    LedgerEntry,
    Organizer,
    OrganizerMembership,
    Trip,
    TripPackage,
    TripPaymentSchedule,
)

pytestmark = pytest.mark.django_db


def test_default_trip_payment_schedule_is_unreviewed_after_draft_creation():
    organizer = create_organizer()
    owner = create_user("draft-payment-schedule-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        f"/api/organizers/{organizer.id}/trips/",
        {
            "title": "Spiti Winter Field Week",
            "start_date": "2026-10-10",
            "end_date": "2026-10-15",
            "capacity": 24,
            "itinerary": "",
            "confirmation_requirements_note": "",
            "publication_state": Trip.PublicationState.DRAFT,
            "booking_availability": Trip.BookingAvailability.CLOSED,
            "packages": [
                {
                    "name": "Standard shared room",
                    "price_inr": 32000,
                    "reservation_amount_inr": 8000,
                    "position": 1,
                }
            ],
            "payment_schedule": {
                "balance_due_days_before_start": None,
                "balance_reminder_lead_days": 3,
            },
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["payment_schedule"]["reviewed"] is False
    trip = Trip.objects.get(pk=response.json()["id"])
    assert trip.payment_schedule.reviewed_at is None


def test_owner_can_review_and_edit_payment_schedule():
    organizer = create_organizer()
    owner = create_user("payment-schedule-owner@example.com")
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

    trip.payment_schedule.refresh_from_db()
    assert response.status_code == 200
    assert response.json()["has_balance_milestone"] is True
    assert response.json()["balance_due_days_before_start"] == 21
    assert response.json()["balance_due_date"] == "2026-09-19"
    assert response.json()["balance_reminder_lead_days"] == 5
    assert response.json()["reviewed"] is True
    assert response.json()["readiness"] == {
        "payment_schedule_reviewed": True,
        "blockers": [],
    }
    assert trip.payment_schedule.reviewed_at is not None
    assert trip.payment_schedule.reviewed_by == owner


def test_owner_can_review_payment_schedule_without_balance_milestone():
    organizer = create_organizer()
    owner = create_user("no-balance-payment-schedule-owner@example.com")
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
            "has_balance_milestone": False,
            "balance_reminder_lead_days": 0,
        },
        format="json",
    )

    trip.payment_schedule.refresh_from_db()
    assert response.status_code == 200
    assert response.json()["has_balance_milestone"] is False
    assert response.json()["balance_due_days_before_start"] is None
    assert response.json()["balance_due_date"] is None
    assert response.json()["reviewed"] is True
    assert trip.payment_schedule.balance_due_days_before_start is None


def test_operator_can_view_but_not_review_or_edit_payment_schedule():
    organizer = create_organizer()
    operator = create_user("payment-schedule-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(operator)

    read_response = client.get(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/payment-schedule/"
    )
    save_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/payment-schedule/",
        {
            "has_balance_milestone": True,
            "balance_due_days_before_start": 30,
            "balance_reminder_lead_days": 4,
        },
        format="json",
    )

    trip.payment_schedule.refresh_from_db()
    assert read_response.status_code == 200
    assert read_response.json()["reviewed"] is False
    assert read_response.json()["readiness"]["blockers"] == [
        "Owner review of balance payment schedule is required."
    ]
    assert save_response.status_code == 403
    assert "Only Owners can manage balance payment terms" in str(
        save_response.json()
    )
    assert trip.payment_schedule.balance_due_days_before_start == 14
    assert trip.payment_schedule.reviewed_at is None


def test_payment_schedule_save_validates_balance_milestone_and_reminder():
    organizer = create_organizer()
    owner = create_user("payment-schedule-validation-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(owner)

    missing_due_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/payment-schedule/",
        {
            "has_balance_milestone": True,
            "balance_due_days_before_start": None,
            "balance_reminder_lead_days": 3,
        },
        format="json",
    )
    late_reminder_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/payment-schedule/",
        {
            "has_balance_milestone": True,
            "balance_due_days_before_start": 5,
            "balance_reminder_lead_days": 8,
        },
        format="json",
    )

    assert missing_due_response.status_code == 400
    assert "Enter when the final balance is due" in str(
        missing_due_response.json()
    )
    assert late_reminder_response.status_code == 400
    assert "cannot exceed final balance due days" in str(
        late_reminder_response.json()
    )


@pytest.mark.parametrize(
    "publication_state",
    [Trip.PublicationState.PUBLISHED, Trip.PublicationState.ARCHIVED],
)
def test_locked_trip_profile_rejects_payment_schedule_save(publication_state):
    organizer = create_organizer()
    owner = create_user("locked-payment-schedule-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer, publication_state=publication_state)
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/payment-schedule/",
        {
            "has_balance_milestone": True,
            "balance_due_days_before_start": 30,
            "balance_reminder_lead_days": 4,
        },
        format="json",
    )

    trip.payment_schedule.refresh_from_db()
    assert response.status_code == 400
    assert "Published Trip Profile Lock" in str(response.json())
    assert trip.payment_schedule.balance_due_days_before_start == 14
    assert trip.payment_schedule.reviewed_at is None


def test_legacy_trip_setup_cannot_bypass_payment_schedule_permissions_or_lock():
    organizer = create_organizer()
    operator = create_user("legacy-payment-schedule-operator@example.com")
    owner = create_user("legacy-payment-schedule-owner@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    operator_client = APIClient()
    operator_client.force_authenticate(operator)
    owner_client = APIClient()
    owner_client.force_authenticate(owner)

    operator_response = operator_client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {
            "payment_schedule": {
                "balance_due_days_before_start": 30,
                "balance_reminder_lead_days": 4,
            }
        },
        format="json",
    )
    trip.publication_state = Trip.PublicationState.PUBLISHED
    trip.save()
    locked_response = owner_client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {
            "payment_schedule": {
                "balance_due_days_before_start": 30,
                "balance_reminder_lead_days": 4,
            }
        },
        format="json",
    )

    trip.payment_schedule.refresh_from_db()
    assert operator_response.status_code == 400
    assert "Only Owners can manage balance payment terms" in str(
        operator_response.json()
    )
    assert locked_response.status_code == 400
    assert "Published Trip Profile Lock" in str(locked_response.json())
    assert trip.payment_schedule.balance_due_days_before_start == 14


def test_payment_schedule_edit_does_not_create_ledger_or_payment_side_effects():
    organizer = create_organizer()
    owner = create_user("payment-schedule-side-effects-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=8000,
        description="Opening reservation amount.",
    )
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
    assert LedgerEntry.objects.filter(booking=booking).count() == 1


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
        position=1,
    )
    TripPaymentSchedule.objects.create(
        trip=trip,
        balance_due_days_before_start=14,
    )
    return trip
