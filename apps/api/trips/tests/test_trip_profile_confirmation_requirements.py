from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from organizers.models import (
    Booking,
    LedgerEntry,
    Organizer,
    OrganizerMembership,
    TravelerSlot,
    Trip,
    TripPackage,
)
from trip_bookings.lifecycle import confirmation_requirements_for_booking
from trip_travelers.readiness import TravelerReadiness

pytestmark = pytest.mark.django_db


def test_owner_and_operator_can_review_confirmation_requirements():
    organizer = create_organizer()
    owner = create_user("requirements-owner@example.com")
    operator = create_user("requirements-operator@example.com")
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
    trip = create_trip(organizer)
    owner_client = APIClient()
    owner_client.force_authenticate(owner)
    operator_client = APIClient()
    operator_client.force_authenticate(operator)

    owner_response = owner_client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/confirmation-requirements/",
        {
            "requires_traveler_documents": True,
            "requires_traveler_identity_details": True,
            "requires_travel_logistics": True,
        },
        format="json",
    )
    operator_response = operator_client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/confirmation-requirements/",
        {
            "requires_traveler_documents": False,
            "requires_traveler_identity_details": True,
            "requires_travel_logistics": True,
            "requires_emergency_contact": True,
            "requires_medical_disclosure": True,
            "requires_full_payment_before_confirmation": True,
        },
        format="json",
    )

    trip.refresh_from_db()
    assert owner_response.status_code == 200
    assert owner_response.json()["reviewed"] is True
    assert operator_response.status_code == 200
    assert operator_response.json()["requires_emergency_contact"] is True
    assert operator_response.json()["requires_full_payment_before_confirmation"] is True
    assert operator_response.json()["readiness"] == {
        "confirmation_requirements_reviewed": True,
        "active_requirements": [
            "traveler_identity_details",
            "travel_logistics",
            "emergency_contact",
            "medical_disclosure",
            "full_payment",
        ],
        "blockers": [],
    }
    assert trip.confirmation_requirements_reviewed is True
    assert trip.confirmation_requirements_reviewed_by == operator
    assert trip.confirmation_requirements_reviewed_at is not None


def test_confirmation_requirements_get_reports_review_blocker():
    organizer = create_organizer()
    operator = create_user("requirements-readiness-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer, requires_emergency_contact=True)
    client = APIClient()
    client.force_authenticate(operator)

    response = client.get(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/confirmation-requirements/"
    )

    assert response.status_code == 200
    assert response.json()["reviewed"] is False
    assert response.json()["readiness"] == {
        "confirmation_requirements_reviewed": False,
        "active_requirements": ["emergency_contact"],
        "blockers": ["Review Confirmation Requirements before publication."],
    }


def test_confirmation_requirements_save_surfaces_attention_without_booking_state_changes():
    organizer = create_organizer()
    operator = create_user("requirements-side-effects-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.CONFIRMED,
    )
    TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.first(),
        position=1,
    )
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=8000,
        description="Opening reservation amount.",
    )
    client = APIClient()
    client.force_authenticate(operator)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/confirmation-requirements/",
        {
            "requires_traveler_identity_details": True,
            "requires_full_payment_before_confirmation": True,
        },
        format="json",
    )

    booking.refresh_from_db()
    requirements = confirmation_requirements_for_booking(booking)
    assert response.status_code == 200
    assert booking.booking_state == Booking.BookingState.CONFIRMED
    assert requirements.ready is False
    assert {item.code for item in requirements.unmet_requirements} == {
        "full_payment",
        "traveler_identity_details",
    }


def test_confirmation_requirements_update_affects_traveler_readiness():
    organizer = create_organizer()
    operator = create_user("requirements-traveler-readiness-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer)
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    traveler_slot = TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.first(),
        position=1,
        traveler_full_name="Asha Nair",
        traveler_phone="+919876543210",
    )
    client = APIClient()
    client.force_authenticate(operator)

    before = TravelerReadiness().readiness_summary_for_traveler_slot(traveler_slot)
    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/confirmation-requirements/",
        {"requires_emergency_contact": True},
        format="json",
    )
    traveler_slot.refresh_from_db()
    after = TravelerReadiness().readiness_summary_for_traveler_slot(traveler_slot)

    assert before.emergency_contact_ready is True
    assert response.status_code == 200
    assert after.emergency_contact_ready is False
    assert after.ready is False


@pytest.mark.parametrize(
    "publication_state",
    [Trip.PublicationState.PUBLISHED, Trip.PublicationState.ARCHIVED],
)
def test_locked_trip_profile_rejects_confirmation_requirements_save(publication_state):
    organizer = create_organizer()
    owner = create_user("locked-requirements-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer, publication_state=publication_state)
    client = APIClient()
    client.force_authenticate(owner)

    read_response = client.get(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/confirmation-requirements/"
    )
    save_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/confirmation-requirements/",
        {"requires_traveler_documents": True},
        format="json",
    )

    trip.refresh_from_db()
    assert read_response.status_code == 200
    assert read_response.json()["trip_profile_locked"] is True
    assert save_response.status_code == 400
    assert "Published Trip Profile Lock" in str(save_response.json())
    assert trip.requires_traveler_documents is False
    assert trip.confirmation_requirements_reviewed is False


def test_legacy_trip_setup_cannot_bypass_confirmation_requirements_lock():
    organizer = create_organizer()
    owner = create_user("legacy-requirements-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer, publication_state=Trip.PublicationState.PUBLISHED)
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {"requires_traveler_documents": True},
        format="json",
    )

    trip.refresh_from_db()
    assert response.status_code == 400
    assert "Published Trip Profile Lock" in str(response.json())
    assert trip.requires_traveler_documents is False


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
    return trip
