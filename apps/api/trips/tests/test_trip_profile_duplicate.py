from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from organizers.models import (
    ActivityLog,
    Booking,
    LedgerEntry,
    ManualPayment,
    Organizer,
    OrganizerMembership,
    PaymentAttempt,
    TravelerSlot,
    Trip,
    TripItineraryDay,
    TripMediaAsset,
    TripMediaItem,
    TripPackage,
    TripPaymentSchedule,
)

pytestmark = pytest.mark.django_db


def test_trip_duplicate_api_copies_profile_into_unlocked_draft_without_operations(
    settings,
    tmp_path,
):
    settings.MEDIA_ROOT = tmp_path
    organizer = create_organizer()
    owner = create_user("duplicate-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    source = create_full_profile_source_trip(organizer, reviewer=owner)
    booking = Booking.objects.create(
        trip=source,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    package = source.packages.get(position=1)
    TravelerSlot.objects.create(booking=booking, package=package, position=1)
    ManualPayment.objects.create(
        booking=booking,
        amount_inr=package.reservation_amount_inr,
        payment_reference="upi-source-001",
    )
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=package.reservation_amount_inr,
        description="Source trip payment.",
    )
    PaymentAttempt.objects.create(
        booking=booking,
        amount_inr=package.reservation_amount_inr,
        provider_attempt_reference="pay_source_001",
    )
    ActivityLog.objects.create(
        organizer=organizer,
        trip=source,
        booking=booking,
        action=ActivityLog.Action.TRAVELER_PACKAGE_CHANGED,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        f"/api/organizers/{organizer.id}/trips/{source.id}/duplicate/",
        {
            "title": "Spiti Winter Revision",
            "start_date": "2027-01-10",
            "end_date": "2027-01-15",
        },
        format="json",
    )

    assert response.status_code == 201
    duplicate = Trip.objects.get(pk=response.json()["id"])
    duplicate_schedule = duplicate.payment_schedule
    source_schedule = source.payment_schedule
    assert duplicate.publication_state == Trip.PublicationState.DRAFT
    assert duplicate.booking_availability == Trip.BookingAvailability.CLOSED
    assert duplicate.description_rich_text == source.description_rich_text
    assert duplicate.itinerary == source.itinerary
    assert duplicate.confirmation_requirements_note == source.confirmation_requirements_note
    assert duplicate.requires_traveler_documents is True
    assert duplicate.requires_traveler_identity_details is True
    assert duplicate.requires_travel_logistics is True
    assert duplicate.requires_emergency_contact is True
    assert duplicate.requires_medical_disclosure is True
    assert duplicate.requires_full_payment_before_confirmation is True
    assert duplicate.confirmation_requirements_reviewed_at == (
        source.confirmation_requirements_reviewed_at
    )
    assert duplicate.confirmation_requirements_reviewed_by == owner
    assert duplicate_schedule.balance_due_days_before_start == (
        source_schedule.balance_due_days_before_start
    )
    assert duplicate_schedule.balance_reminder_lead_days == (
        source_schedule.balance_reminder_lead_days
    )
    assert duplicate_schedule.reviewed_at == source_schedule.reviewed_at
    assert duplicate_schedule.reviewed_by == owner
    assert list(
        duplicate.itinerary_days.values_list("sequence", "title", "date_label")
    ) == [
        (1, "Arrival", "Day 1"),
        (2, "Field day", "Day 2"),
    ]
    assert list(
        duplicate.packages.values_list(
            "name",
            "description",
            "price_inr",
            "reservation_amount_inr",
            "position",
            "lifecycle_state",
        )
    ) == [
        (
            "Standard shared room",
            "Shared room package.",
            32000,
            8000,
            1,
            TripPackage.LifecycleState.ACTIVE,
        ),
        (
            "Premium room",
            "Twin sharing upgrade.",
            42000,
            12000,
            2,
            TripPackage.LifecycleState.ACTIVE,
        ),
    ]
    source_media = list(source.media_items.order_by("position", "id"))
    duplicate_media = list(duplicate.media_items.order_by("position", "id"))
    assert [
        (item.position, item.caption, item.alt_text, item.is_public, item.is_cover)
        for item in duplicate_media
    ] == [
        (1, "Cover caption", "Snow valley cover", True, True),
        (2, "Private prep image", "Packing table", False, False),
    ]
    assert [item.asset_id for item in duplicate_media] == [
        item.asset_id for item in source_media
    ]
    assert {item.id for item in duplicate_media}.isdisjoint({item.id for item in source_media})
    assert duplicate.bookings.count() == 0
    assert TravelerSlot.objects.filter(booking__trip=duplicate).count() == 0
    assert LedgerEntry.objects.filter(booking__trip=duplicate).count() == 0
    assert ManualPayment.objects.filter(booking__trip=duplicate).count() == 0
    assert PaymentAttempt.objects.filter(booking__trip=duplicate).count() == 0
    assert ActivityLog.objects.filter(trip=duplicate).count() == 0
    assert ActivityLog.objects.filter(
        trip=source,
        action=ActivityLog.Action.TRIP_DUPLICATED,
        metadata__duplicate_trip_id=duplicate.id,
    ).exists()

    package_read_response = client.get(
        f"/api/organizers/{organizer.id}/trips/{duplicate.id}/packages/"
    )
    media_read_response = client.get(
        f"/api/organizers/{organizer.id}/trips/{duplicate.id}/media/"
    )
    assert package_read_response.status_code == 200
    assert media_read_response.status_code == 200
    assert package_read_response.json()["trip_profile_locked"] is False
    assert media_read_response.json()["trip_profile_locked"] is False


def test_duplicated_media_and_packages_follow_unlocked_edit_rules(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    organizer = create_organizer()
    owner = create_user("duplicate-edit-owner@example.com")
    operator = create_user("duplicate-edit-operator@example.com")
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
    source = create_full_profile_source_trip(organizer, reviewer=owner)
    owner_client = APIClient()
    owner_client.force_authenticate(owner)
    duplicate_response = owner_client.post(
        f"/api/organizers/{organizer.id}/trips/{source.id}/duplicate/",
        {"title": "Spiti Editable Revision"},
        format="json",
    )
    duplicate = Trip.objects.get(pk=duplicate_response.json()["id"])
    operator_client = APIClient()
    operator_client.force_authenticate(operator)
    package = duplicate.packages.get(position=1)

    operator_package_response = operator_client.patch(
        f"/api/organizers/{organizer.id}/trips/{duplicate.id}/packages/",
        {
            "packages": [
                {
                    "id": package.id,
                    "name": "Operator package edit",
                    "description": "Should not save.",
                    "price_inr": 36000,
                    "reservation_amount_inr": 9000,
                }
            ]
        },
        format="json",
    )
    owner_package_response = owner_client.patch(
        f"/api/organizers/{organizer.id}/trips/{duplicate.id}/packages/",
        {
            "packages": [
                {
                    "id": package.id,
                    "name": "Owner revised shared room",
                    "description": "Updated package terms.",
                    "price_inr": 34000,
                    "reservation_amount_inr": 8500,
                }
            ]
        },
        format="json",
    )
    source_items = list(source.media_items.order_by("position", "id"))
    duplicate_items = list(duplicate.media_items.order_by("position", "id"))
    media_response = operator_client.patch(
        f"/api/organizers/{organizer.id}/trips/{duplicate.id}/media/",
        {
            "media_items": [
                {
                    "id": duplicate_items[1].id,
                    "caption": "Revision public cover",
                    "alt_text": "Travelers reviewing kit",
                    "is_public": True,
                    "is_cover": True,
                },
                {
                    "id": duplicate_items[0].id,
                    "caption": "Revision private reference",
                    "alt_text": "Snow valley internal reference",
                    "is_public": False,
                    "is_cover": False,
                },
            ]
        },
        format="json",
    )

    assert operator_package_response.status_code == 403
    assert owner_package_response.status_code == 200
    assert owner_package_response.json()["packages"] == [
        {
            "id": package.id,
            "name": "Owner revised shared room",
            "description": "Updated package terms.",
            "price_inr": 34000,
            "reservation_amount_inr": 8500,
            "position": 1,
        }
    ]
    assert media_response.status_code == 200
    assert [
        (item["id"], item["asset_id"], item["caption"], item["is_public"], item["is_cover"])
        for item in media_response.json()["media_items"]
    ] == [
        (
            duplicate_items[1].id,
            source_items[1].asset_id,
            "Revision public cover",
            True,
            True,
        ),
        (
            duplicate_items[0].id,
            source_items[0].asset_id,
            "Revision private reference",
            False,
            False,
        ),
    ]
    assert list(
        source.media_items.order_by("position", "id").values_list(
            "caption",
            "is_public",
            "is_cover",
        )
    ) == [
        ("Cover caption", True, True),
        ("Private prep image", False, False),
    ]


def create_full_profile_source_trip(organizer: Organizer, *, reviewer) -> Trip:
    reviewed_at = timezone.now()
    trip = Trip.objects.create(
        organizer=organizer,
        title="Spiti Winter Field Week",
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 15),
        capacity=24,
        confirmation_requirements_note="Identity details and emergency contact.",
        requires_traveler_documents=True,
        requires_traveler_identity_details=True,
        requires_travel_logistics=True,
        requires_emergency_contact=True,
        requires_medical_disclosure=True,
        requires_full_payment_before_confirmation=True,
        confirmation_requirements_reviewed_at=reviewed_at,
        confirmation_requirements_reviewed_by=reviewer,
        description_rich_text=rich_text_payload("Traveler-facing Spiti details."),
        itinerary="Day 1: Chandigarh arrival. Day 2: Transit to Kaza.",
        publication_state=Trip.PublicationState.ARCHIVED,
        booking_availability=Trip.BookingAvailability.OPEN,
    )
    TripPackage.objects.create(
        trip=trip,
        name="Standard shared room",
        description="Shared room package.",
        price_inr=32000,
        reservation_amount_inr=8000,
        position=1,
    )
    TripPackage.objects.create(
        trip=trip,
        name="Premium room",
        description="Twin sharing upgrade.",
        price_inr=42000,
        reservation_amount_inr=12000,
        position=2,
    )
    TripPaymentSchedule.objects.create(
        trip=trip,
        balance_due_days_before_start=14,
        balance_reminder_lead_days=5,
        reviewed_at=reviewed_at,
        reviewed_by=reviewer,
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
    cover_asset = create_media_asset(organizer, trip, "cover.png")
    prep_asset = create_media_asset(organizer, trip, "prep.png")
    TripMediaItem.objects.create(
        trip=trip,
        asset=cover_asset,
        position=1,
        caption="Cover caption",
        alt_text="Snow valley cover",
        is_public=True,
        is_cover=True,
    )
    TripMediaItem.objects.create(
        trip=trip,
        asset=prep_asset,
        position=2,
        caption="Private prep image",
        alt_text="Packing table",
        is_public=False,
        is_cover=False,
    )
    return trip


def create_media_asset(
    organizer: Organizer,
    trip: Trip,
    filename: str,
) -> TripMediaAsset:
    return TripMediaAsset.objects.create(
        organizer=organizer,
        uploaded_for_trip=trip,
        image=SimpleUploadedFile(
            filename,
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
            content_type="image/png",
        ),
        original_filename=filename,
        content_type="image/png",
        file_size=16,
    )


def create_user(email: str):
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        password="tripos-test-password",
    )


def create_organizer() -> Organizer:
    return Organizer.objects.create(name="Himalayan Monsoon Cohort")


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
