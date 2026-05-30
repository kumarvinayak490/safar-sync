from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from organizers.models import (
    Booking,
    Organizer,
    OrganizerMembership,
    TravelerSlot,
    Trip,
    TripPackage,
    TripPaymentSchedule,
)

pytestmark = pytest.mark.django_db


def test_operator_can_view_but_not_save_trip_profile_packages():
    organizer = create_organizer()
    operator = create_user("operator-packages@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer)
    package = trip.packages.get()
    client = APIClient()
    client.force_authenticate(operator)

    read_response = client.get(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/packages/"
    )
    save_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/packages/",
        {
            "packages": [
                {
                    "id": package.id,
                    "name": "Operator changed",
                    "price_inr": 36000,
                    "reservation_amount_inr": 9000,
                }
            ]
        },
        format="json",
    )

    package.refresh_from_db()
    assert read_response.status_code == 200
    assert read_response.json()["packages"][0]["name"] == "Standard shared room"
    assert save_response.status_code == 403
    assert "Only Owners can manage Package commercial terms" in str(save_response.json())
    assert package.name == "Standard shared room"
    assert package.price_inr == 32000


def test_owner_can_save_reorder_add_edit_and_remove_unused_packages():
    organizer = create_organizer()
    owner = create_user("owner-packages@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    standard = trip.packages.get()
    premium = TripPackage.objects.create(
        trip=trip,
        name="Premium room",
        price_inr=42000,
        reservation_amount_inr=12000,
        position=2,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/packages/",
        {
            "packages": [
                {
                    "id": premium.id,
                    "name": "Premium room updated",
                    "description": "Twin sharing upgrade.",
                    "price_inr": 44000,
                    "reservation_amount_inr": 14000,
                },
                {
                    "name": "Single room",
                    "description": "",
                    "price_inr": 52000,
                    "reservation_amount_inr": 18000,
                },
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    assert not TripPackage.objects.filter(id=standard.id).exists()
    assert list(
        trip.packages.order_by("position", "id").values_list(
            "name",
            "price_inr",
            "reservation_amount_inr",
            "position",
        )
    ) == [
        ("Premium room updated", 44000, 14000, 1),
        ("Single room", 52000, 18000, 2),
    ]
    assert [package["name"] for package in response.json()["packages"]] == [
        "Premium room updated",
        "Single room",
    ]


def test_trip_profile_package_save_validates_rows_and_readiness():
    organizer = create_organizer()
    owner = create_user("validation-packages@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    client = APIClient()
    client.force_authenticate(owner)

    invalid_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/packages/",
        {
            "packages": [
                {
                    "name": " ",
                    "price_inr": 0,
                    "reservation_amount_inr": 1000,
                },
                {
                    "name": "Premium",
                    "price_inr": 12000,
                    "reservation_amount_inr": 15000,
                },
            ]
        },
        format="json",
    )
    empty_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/packages/",
        {"packages": []},
        format="json",
    )
    trip.packages.all().delete()
    TripPackage.objects.create(
        trip=trip,
        name="Withdrawn shared room",
        price_inr=32000,
        reservation_amount_inr=8000,
        lifecycle_state=TripPackage.LifecycleState.WITHDRAWN,
    )
    readiness_response = client.get(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/packages/"
    )

    assert invalid_response.status_code == 400
    assert "Package name is required." in str(invalid_response.json())
    assert "Ensure this value is greater than or equal to 1." in str(
        invalid_response.json()
    )
    assert "Reservation Amount cannot exceed Package price." in str(
        invalid_response.json()
    )
    assert empty_response.status_code == 400
    assert "Every Trip needs at least one Package." in str(empty_response.json())
    assert readiness_response.status_code == 200
    assert readiness_response.json()["readiness"] == {
        "package_ready": False,
        "active_package_count": 0,
        "blockers": ["At least one active Package is required."],
    }


@pytest.mark.parametrize(
    "publication_state",
    [Trip.PublicationState.PUBLISHED, Trip.PublicationState.ARCHIVED],
)
def test_locked_trip_profile_rejects_package_save(publication_state):
    organizer = create_organizer()
    owner = create_user("locked-packages@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer, publication_state=publication_state)
    package = trip.packages.get()
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/packages/",
        {
            "packages": [
                {
                    "id": package.id,
                    "name": "Changed after publication",
                    "price_inr": 36000,
                    "reservation_amount_inr": 9000,
                }
            ]
        },
        format="json",
    )

    package.refresh_from_db()
    assert response.status_code == 400
    assert "Published Trip Profile Lock" in str(response.json())
    assert package.name == "Standard shared room"
    assert package.price_inr == 32000


def test_locked_trip_profile_rejects_legacy_trip_setup_package_mutation():
    organizer = create_organizer()
    owner = create_user("locked-legacy-packages@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer, publication_state=Trip.PublicationState.PUBLISHED)
    package = trip.packages.get()
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/",
        {
            "packages": [
                {
                    "id": package.id,
                    "name": "Changed through legacy setup",
                    "price_inr": 36000,
                    "reservation_amount_inr": 9000,
                }
            ]
        },
        format="json",
    )

    package.refresh_from_db()
    assert response.status_code == 400
    assert "Published Trip Profile Lock" in str(response.json())
    assert package.name == "Standard shared room"
    assert package.price_inr == 32000


def test_package_catalog_edits_do_not_reprice_reserved_or_confirmed_travelers():
    organizer = create_organizer()
    owner = create_user("snapshots-packages@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    package = trip.packages.get()
    reserved_booking = create_booking(
        trip,
        booking_state=Booking.BookingState.RESERVED,
        contact_name="Asha Nair",
    )
    confirmed_booking = create_booking(
        trip,
        booking_state=Booking.BookingState.CONFIRMED,
        contact_name="Kabir Mehta",
    )
    reserved_slot = TravelerSlot.objects.create(
        booking=reserved_booking,
        package=package,
        position=1,
    )
    confirmed_slot = TravelerSlot.objects.create(
        booking=confirmed_booking,
        package=package,
        position=1,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/packages/",
        {
            "packages": [
                {
                    "id": package.id,
                    "name": "Standard shared room repriced",
                    "price_inr": 42000,
                    "reservation_amount_inr": 12000,
                }
            ]
        },
        format="json",
    )

    reserved_slot.refresh_from_db()
    confirmed_slot.refresh_from_db()
    reserved_booking.refresh_from_db()
    confirmed_booking.refresh_from_db()
    package.refresh_from_db()
    assert response.status_code == 200
    assert package.price_inr == 42000
    assert package.reservation_amount_inr == 12000
    assert reserved_slot.booked_package_price_inr == 32000
    assert reserved_slot.booked_reservation_amount_inr == 8000
    assert confirmed_slot.booked_package_price_inr == 32000
    assert confirmed_slot.booked_reservation_amount_inr == 8000
    assert reserved_booking.booking_total_inr == 32000
    assert reserved_booking.booking_reservation_amount_inr == 8000
    assert confirmed_booking.booking_total_inr == 32000
    assert confirmed_booking.booking_reservation_amount_inr == 8000


def test_selected_package_removal_withdraws_and_preserves_historical_booking_context():
    organizer = create_organizer()
    owner = create_user("selected-removal-packages@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    trip = create_trip(organizer)
    selected_package = trip.packages.get()
    other_package = TripPackage.objects.create(
        trip=trip,
        name="Premium",
        price_inr=42000,
        reservation_amount_inr=12000,
        position=2,
    )
    booking = create_booking(
        trip,
        booking_state=Booking.BookingState.RESERVED,
        contact_name="Asha Nair",
    )
    TravelerSlot.objects.create(booking=booking, package=selected_package, position=1)
    client = APIClient()
    client.force_authenticate(owner)

    response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/packages/",
        {
            "packages": [
                {
                    "id": other_package.id,
                    "name": "Premium",
                    "price_inr": 42000,
                    "reservation_amount_inr": 12000,
                }
            ]
        },
        format="json",
    )

    selected_package.refresh_from_db()
    detail_response = client.get(
        f"/api/operations/organizers/{organizer.id}/bookings/{booking.id}/"
    )

    assert response.status_code == 200
    assert selected_package.lifecycle_state == TripPackage.LifecycleState.WITHDRAWN
    assert TripPackage.objects.filter(id=selected_package.id).exists()
    assert [package["id"] for package in response.json()["packages"]] == [other_package.id]
    assert response.json()["readiness"]["active_package_count"] == 1
    assert detail_response.status_code == 200
    assert detail_response.json()["traveler_slots"][0]["package"] == selected_package.id
    assert detail_response.json()["traveler_slots"][0]["package_name"] == (
        "Standard shared room"
    )
    assert detail_response.json()["traveler_slots"][0]["package_is_withdrawn"] is True


def test_withdrawn_packages_are_excluded_from_public_and_manual_booking_selection():
    organizer = create_organizer()
    owner = create_user("selection-exclusion-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    operator = create_user("selection-exclusion-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    trip = create_trip(organizer)
    selected_package = trip.packages.get()
    active_package = TripPackage.objects.create(
        trip=trip,
        name="Premium",
        price_inr=42000,
        reservation_amount_inr=12000,
        position=2,
    )
    booking = create_booking(
        trip,
        booking_state=Booking.BookingState.RESERVED,
        contact_name="Asha Nair",
    )
    TravelerSlot.objects.create(booking=booking, package=selected_package, position=1)
    owner_client = APIClient()
    owner_client.force_authenticate(owner)
    withdrawal_response = owner_client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip.id}/packages/",
        {
            "packages": [
                {
                    "id": active_package.id,
                    "name": "Premium",
                    "price_inr": 42000,
                    "reservation_amount_inr": 12000,
                }
            ]
        },
        format="json",
    )
    assert withdrawal_response.status_code == 200
    trip.publication_state = Trip.PublicationState.PUBLISHED
    trip.booking_availability = Trip.BookingAvailability.OPEN
    trip.save()

    public_client = APIClient()
    public_response = public_client.get(f"/api/public/trips/{organizer.slug}/{trip.slug}/")
    public_draft_response = public_client.post(
        f"/api/public/trips/{organizer.slug}/{trip.slug}/draft-bookings/",
        {
            "booking_contact_name": "New Public Contact",
            "booking_contact_phone": "+919876543211",
            "traveler_count": 1,
            "package": selected_package.id,
        },
        format="json",
    )
    operator_client = APIClient()
    operator_client.force_authenticate(operator)
    manual_response = operator_client.post(
        f"/api/operations/organizers/{organizer.id}/trips/{trip.id}/manual-bookings/",
        {
            "booking_contact_name": "Manual Contact",
            "booking_contact_phone": "+919876543212",
            "traveler_slots": [{"package": selected_package.id}],
        },
        format="json",
    )

    assert public_response.status_code == 200
    assert [package["id"] for package in public_response.json()["packages"]] == [
        active_package.id
    ]
    assert public_draft_response.status_code == 400
    assert "Every selected Package must belong to this Trip." in str(
        public_draft_response.json()
    )
    assert manual_response.status_code == 400
    assert "Every Traveler Slot Package must belong to this Trip." in str(
        manual_response.json()
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


def create_booking(
    trip: Trip,
    *,
    booking_state: str,
    contact_name: str,
) -> Booking:
    return Booking.objects.create(
        trip=trip,
        booking_contact_name=contact_name,
        booking_contact_phone="+919876543210",
        booking_state=booking_state,
    )
