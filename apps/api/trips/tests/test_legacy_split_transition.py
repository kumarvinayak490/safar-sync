from __future__ import annotations

from datetime import date
from importlib import import_module

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from organizer_payments.models import ManualPaymentInstructions
from organizers.models import Organizer
from team_access.models import OrganizerMembership
from trip_bookings.models import Booking
from trip_payments.models import PaymentAttempt
from trip_payments.seat_holds import create_seat_hold_for_payment_attempt
from trip_travelers.models import TravelerSlot
from trips.booking_availability import (
    PublicBookingGateReason,
    available_seats,
    bookable_seats,
    effective_booking_availability,
    public_availability_band,
    public_booking_gate_decision,
)
from trips.duplication import duplicate_trip
from trips.models import (
    Trip,
    TripItineraryDay,
    TripMediaAsset,
    TripMediaItem,
    TripPackage,
    TripPaymentSchedule,
)
from trips.publication_readiness import trip_profile_publication_readiness
from trips.serializers import (
    PublicTripSerializer,
    TripItinerarySectionSerializer,
    TripMediaGallerySerializer,
    TripMediaUploadSerializer,
    TripPackageSectionSerializer,
    TripProfileCoreSerializer,
)

pytestmark = pytest.mark.django_db


def test_trip_profile_core_serializer_creates_reads_updates_and_validates():
    organizer = Organizer.objects.create(name="Himalayan Field Notes")
    serializer = TripProfileCoreSerializer(
        data={
            "title": "Spiti Winter Field Week",
            "start_date": "2026-10-10",
            "end_date": "2026-10-15",
            "capacity": 24,
            "description_rich_text": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "Traveler-facing field details.",
                                "marks": [{"type": "bold"}, {"type": "script"}],
                            }
                        ],
                    },
                    {"type": "image", "attrs": {"src": "https://example.test/image.jpg"}},
                ],
            },
        },
        context={"organizer": organizer},
    )

    assert serializer.is_valid(), serializer.errors
    trip = serializer.save()

    assert trip.organizer_id == organizer.id
    assert trip.slug == "spiti-winter-field-week"
    assert trip.public_url_path == f"/trips/{organizer.slug}/{trip.slug}"
    assert TripProfileCoreSerializer(trip).data["description_plain_text"] == (
        "Traveler-facing field details."
    )
    assert trip.description_rich_text["content"][0]["content"][0]["marks"] == [
        {"type": "bold"}
    ]

    update = TripProfileCoreSerializer(
        trip,
        data={"capacity": 18, "description_rich_text": rich_text_payload("Revised copy.")},
        partial=True,
    )
    assert update.is_valid(), update.errors
    trip = update.save()
    assert trip.capacity == 18
    assert TripProfileCoreSerializer(trip).data["description_plain_text"] == "Revised copy."

    invalid = TripProfileCoreSerializer(
        trip,
        data={"start_date": "2026-10-16", "end_date": "2026-10-15"},
        partial=True,
    )
    assert invalid.is_valid() is False
    assert "end_date" in invalid.errors


def test_existing_trip_profile_core_api_create_read_update_and_validate():
    organizer = Organizer.objects.create(name="Ladakh Alpine Collective")
    owner = create_user("trip-core-owner@example.com")
    OrganizerMembership.objects.create(
        user=owner,
        organizer=organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    client = APIClient()
    client.force_authenticate(owner)

    create_response = client.post(
        f"/api/organizers/{organizer.id}/trips/",
        {
            "title": "Markha Valley Field Week",
            "start_date": "2026-09-10",
            "end_date": "2026-09-16",
            "capacity": 16,
            "packages": [
                {
                    "name": "Shared room",
                    "description": "Twin-share field base.",
                    "price_inr": 42000,
                    "reservation_amount_inr": 10000,
                }
            ],
            "payment_schedule": {
                "balance_due_days_before_start": 21,
                "balance_reminder_lead_days": 5,
            },
        },
        format="json",
    )

    assert create_response.status_code == 201
    created_payload = create_response.json()
    assert created_payload["organizer"] == organizer.id
    assert created_payload["capacity"] == 16
    assert created_payload["publication_state"] == Trip.PublicationState.DRAFT
    assert created_payload["booking_availability"] == Trip.BookingAvailability.CLOSED

    trip_id = created_payload["id"]
    read_response = client.get(f"/api/organizers/{organizer.id}/trips/{trip_id}/")
    assert read_response.status_code == 200
    assert read_response.json()["title"] == "Markha Valley Field Week"

    description_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip_id}/description/",
        {"description_rich_text": rich_text_payload("High-altitude route notes.")},
        format="json",
    )
    assert description_response.status_code == 200
    assert description_response.json()["description_plain_text"] == "High-altitude route notes."

    update_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip_id}/",
        {"title": "Markha Valley Readiness Week", "capacity": 18},
        format="json",
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Markha Valley Readiness Week"
    assert update_response.json()["capacity"] == 18

    invalid_response = client.patch(
        f"/api/organizers/{organizer.id}/trips/{trip_id}/",
        {"end_date": "2026-09-01"},
        format="json",
    )
    assert invalid_response.status_code == 400
    assert "end_date" in invalid_response.json()


def test_legacy_trip_profile_core_imports_reexport_trips_owners():
    legacy_rich_text = import_module("organizers.trip_profile.rich_text")
    legacy_root_rich_text = import_module("organizers.rich_text")
    trips_rich_text = import_module("trips.rich_text")
    legacy_locks = import_module("organizers.trip_profile.locks")
    legacy_root_locks = import_module("organizers.trip_profile_lock")
    trips_locks = import_module("trips.locks")

    assert legacy_rich_text.default_trip_rich_text is trips_rich_text.default_trip_rich_text
    assert legacy_root_rich_text.default_trip_rich_text is trips_rich_text.default_trip_rich_text
    assert legacy_locks.is_trip_profile_locked is trips_locks.is_trip_profile_locked
    assert legacy_root_locks.is_trip_profile_locked is trips_locks.is_trip_profile_locked


def test_trip_package_section_serializer_saves_display_order_and_readiness():
    trip = create_trip_with_package()
    standard = trip.packages.get()
    premium = TripPackage.objects.create(
        trip=trip,
        name="Premium room",
        price_inr=52000,
        reservation_amount_inr=15000,
        position=2,
    )

    serializer = TripPackageSectionSerializer(
        data={
            "packages": [
                {
                    "id": premium.id,
                    "name": "Premium room updated",
                    "description": "Twin-share upgrade.",
                    "price_inr": 54000,
                    "reservation_amount_inr": 16000,
                },
                {
                    "name": "Single room",
                    "description": "",
                    "price_inr": 62000,
                    "reservation_amount_inr": 18000,
                },
            ]
        },
        context={"trip": trip},
    )

    assert serializer.is_valid(), serializer.errors
    serializer.save()

    assert not TripPackage.objects.filter(id=standard.id).exists()
    assert list(
        trip.packages.order_by("position", "id").values_list(
            "name",
            "price_inr",
            "reservation_amount_inr",
            "position",
        )
    ) == [
        ("Premium room updated", 54000, 16000, 1),
        ("Single room", 62000, 18000, 2),
    ]
    assert TripPackageSectionSerializer(trip, context={"trip": trip}).data["readiness"] == {
        "package_ready": True,
        "active_package_count": 2,
        "blockers": [],
    }


def test_trip_itinerary_section_serializer_validates_sequences_and_descriptions():
    trip = create_trip_with_package()
    duplicate_sequences = TripItinerarySectionSerializer(
        data={
            "itinerary_days": [
                itinerary_day_payload(1, "Arrival", "Arrive."),
                itinerary_day_payload(1, "Field day", "Walk."),
            ]
        },
        context={"trip": trip},
    )
    empty_description = TripItinerarySectionSerializer(
        data={"itinerary_days": [itinerary_day_payload(2, "Prep", "")]},
        context={"trip": trip},
    )
    valid = TripItinerarySectionSerializer(
        data={
            "itinerary_days": [
                itinerary_day_payload(2, "Field day", "Walk the route."),
                itinerary_day_payload(1, "Arrival", "Arrive and brief."),
            ]
        },
        context={"trip": trip},
    )

    assert duplicate_sequences.is_valid() is False
    assert "Itinerary Day sequences must be unique." in str(duplicate_sequences.errors)
    assert empty_description.is_valid() is False
    assert "Itinerary Day description is required." in str(empty_description.errors)
    assert valid.is_valid(), valid.errors
    valid.save()
    assert list(trip.itinerary_days.values_list("sequence", "title")) == [
        (1, "Arrival"),
        (2, "Field day"),
    ]


def test_trip_media_serializers_validate_uploads_and_preserve_display_order(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    trip = create_trip_with_package()
    upload = TripMediaUploadSerializer(
        data={
            "images": [
                png_upload("cover.png"),
                png_upload("gallery.png"),
            ]
        },
        context={"trip": trip, "actor": None},
    )

    assert upload.is_valid(), upload.errors
    upload.save()
    items = list(trip.media_items.order_by("position", "id"))
    assert [(item.position, item.is_cover, item.is_public) for item in items] == [
        (1, True, True),
        (2, False, True),
    ]

    reorder = TripMediaGallerySerializer(
        data={
            "media_items": [
                {
                    "id": items[1].id,
                    "caption": "Public gallery",
                    "alt_text": "Camp kitchen",
                    "is_public": True,
                    "is_cover": True,
                },
                {
                    "id": items[0].id,
                    "caption": "Private reference",
                    "alt_text": "Trailhead",
                    "is_public": False,
                    "is_cover": False,
                },
            ]
        },
        context={"trip": trip},
    )

    assert reorder.is_valid(), reorder.errors
    reorder.save()
    assert [
        (item["id"], item["caption"], item["is_public"], item["is_cover"])
        for item in TripMediaGallerySerializer(trip, context={"trip": trip}).data[
            "media_items"
        ]
    ] == [
        (items[1].id, "Public gallery", True, True),
        (items[0].id, "Private reference", False, False),
    ]

    invalid_upload = TripMediaUploadSerializer(
        data={"images": [SimpleUploadedFile("bad.gif", b"GIF89a", content_type="image/gif")]},
        context={"trip": trip},
    )
    assert invalid_upload.is_valid() is False
    assert "Upload PNG, JPG, or WebP Trip Media Item images." in str(invalid_upload.errors)


def test_trip_duplicate_reuses_media_assets_but_creates_independent_items(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    organizer = Organizer.objects.create(name="Duplicate Media Collective")
    source = create_trip_with_package(organizer=organizer)
    asset = TripMediaAsset.objects.create(
        organizer=organizer,
        uploaded_for_trip=source,
        image=png_upload("cover.png"),
        original_filename="cover.png",
        content_type="image/png",
        file_size=16,
    )
    source_item = TripMediaItem.objects.create(
        trip=source,
        asset=asset,
        position=1,
        caption="Original cover",
        alt_text="Snow field",
        is_public=True,
        is_cover=True,
    )
    TripItineraryDay.objects.create(
        trip=source,
        sequence=1,
        title="Arrival",
        description_rich_text=rich_text_payload("Arrive."),
    )

    duplicate = duplicate_trip(
        source,
        title="Duplicate Media Revision",
        start_date=date(2027, 1, 10),
        end_date=date(2027, 1, 15),
    )
    duplicate_item = duplicate.media_items.get()

    assert duplicate.publication_state == Trip.PublicationState.DRAFT
    assert duplicate_item.asset_id == source_item.asset_id
    assert duplicate_item.id != source_item.id
    duplicate_item.caption = "Duplicate cover"
    duplicate_item.save()
    source_item.refresh_from_db()
    assert source_item.caption == "Original cover"


def test_trip_publication_readiness_reports_blockers_and_success_state():
    organizer = Organizer.objects.create(name="Publication Readiness Collective")
    blocked_trip = Trip.objects.create(
        organizer=organizer,
        title="Incomplete Spiti Trip",
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 15),
        capacity=20,
    )
    TripPaymentSchedule.objects.create(
        trip=blocked_trip,
        balance_due_days_before_start=14,
    )
    ready_trip = create_publication_ready_trip(
        organizer=organizer,
        reviewer=create_user("trip-readiness-reviewer@example.com"),
    )

    blocked = trip_profile_publication_readiness(blocked_trip)
    ready = trip_profile_publication_readiness(ready_trip)

    assert blocked.publish_eligible is False
    assert [item.id for item in blocked.blockers] == [
        "description",
        "packages",
        "payment-schedule",
        "itinerary",
        "requirements",
    ]
    assert blocked.to_payload()["lock_acknowledgement_required"] is True
    assert ready.publish_eligible is True
    assert ready.blockers == ()
    assert [item.id for item in ready.encouraged] == ["media-gallery"]


def test_public_trip_serializer_uses_trip_profile_content_and_public_media(
    settings,
    tmp_path,
):
    settings.MEDIA_ROOT = tmp_path
    organizer = Organizer.objects.create(name="Public Page Collective")
    trip = create_publication_ready_trip(
        organizer=organizer,
        reviewer=create_user("public-page-reviewer@example.com"),
    )
    TripPackage.objects.create(
        trip=trip,
        name="Withdrawn single room",
        price_inr=62000,
        reservation_amount_inr=18000,
        position=2,
        lifecycle_state=TripPackage.LifecycleState.WITHDRAWN,
    )
    public_asset = TripMediaAsset.objects.create(
        organizer=organizer,
        uploaded_for_trip=trip,
        image=png_upload("public-cover.png"),
        original_filename="public-cover.png",
        content_type="image/png",
        file_size=16,
    )
    private_asset = TripMediaAsset.objects.create(
        organizer=organizer,
        uploaded_for_trip=trip,
        image=png_upload("private-reference.png"),
        original_filename="private-reference.png",
        content_type="image/png",
        file_size=16,
    )
    TripMediaItem.objects.create(
        trip=trip,
        asset=public_asset,
        position=1,
        caption="Public cover",
        is_public=True,
        is_cover=True,
    )
    TripMediaItem.objects.create(
        trip=trip,
        asset=private_asset,
        position=2,
        caption="Private reference",
        is_public=False,
    )
    trip.publication_state = Trip.PublicationState.PUBLISHED
    trip.save(update_fields=["publication_state", "updated_at"])

    payload = PublicTripSerializer(trip).data

    assert payload["publication_state"] == Trip.PublicationState.PUBLISHED
    assert payload["organizer_identity"]["name"] == organizer.name
    assert payload["description_rich_text"] == rich_text_payload(
        "Traveler-facing Spiti details."
    )
    assert [package["name"] for package in payload["packages"]] == ["Standard room"]
    assert [day["title"] for day in payload["itinerary_days"]] == [
        "Arrival and readiness review"
    ]
    assert [item["caption"] for item in payload["media_items"]] == ["Public cover"]
    assert payload["manual_payment_instructions"] is None


def test_trips_public_booking_gate_blocks_unpublished_and_closed_trips():
    organizer = Organizer.objects.create(name="Gate State Collective")
    create_ready_manual_payment_instructions(organizer)
    trip = create_publication_ready_trip(
        organizer=organizer,
        reviewer=create_user("gate-state-reviewer@example.com"),
    )
    trip.booking_availability = Trip.BookingAvailability.OPEN
    trip.manual_payment_availability = Trip.ManualPaymentAvailability.OPEN
    trip.save(update_fields=["booking_availability", "manual_payment_availability"])

    draft_gate = public_booking_gate_decision(trip)
    trip.publication_state = Trip.PublicationState.PUBLISHED
    trip.booking_availability = Trip.BookingAvailability.CLOSED
    trip.save(update_fields=["publication_state", "booking_availability"])
    closed_gate = public_booking_gate_decision(trip)

    assert draft_gate.ready is False
    assert draft_gate.reason_code == PublicBookingGateReason.PUBLICATION_NOT_PUBLISHED
    assert draft_gate.publication_ready is False
    assert closed_gate.ready is False
    assert closed_gate.reason_code == PublicBookingGateReason.BOOKING_CLOSED
    assert closed_gate.publication_ready is True
    assert closed_gate.booking_availability_open is False


def test_trips_public_booking_gate_blocks_missing_payment_setup_and_opens_with_manual_method():
    organizer = Organizer.objects.create(name="Manual Gate Collective")
    trip = create_publication_ready_trip(
        organizer=organizer,
        reviewer=create_user("manual-gate-reviewer@example.com"),
    )
    trip.publication_state = Trip.PublicationState.PUBLISHED
    trip.booking_availability = Trip.BookingAvailability.OPEN
    trip.manual_payment_availability = Trip.ManualPaymentAvailability.OPEN
    trip.save(
        update_fields=[
            "publication_state",
            "booking_availability",
            "manual_payment_availability",
        ]
    )

    blocked_gate = public_booking_gate_decision(trip)
    create_ready_manual_payment_instructions(organizer)
    open_gate = public_booking_gate_decision(trip)

    assert blocked_gate.ready is False
    assert blocked_gate.reason_code == PublicBookingGateReason.PAYMENT_METHOD_READINESS_MISSING
    assert blocked_gate.online_payment_readiness_ready is False
    assert blocked_gate.provider_payment_setup_complete is False
    assert blocked_gate.payment_method_readiness.manual_method.ready is False
    assert open_gate.ready is True
    assert open_gate.reason_code == PublicBookingGateReason.READY
    assert open_gate.payment_method_readiness_ready is True
    assert open_gate.online_payment_readiness_ready is False
    assert open_gate.provider_payment_setup_complete is False
    assert open_gate.payment_method_readiness.ready_method_ids == ["qr_manual_payments"]
    assert open_gate.payment_method_readiness.manual_method.ready is True


def test_trips_booking_availability_derives_sold_out_from_reserved_travelers():
    organizer = Organizer.objects.create(name="Sold Out Gate Collective")
    create_ready_manual_payment_instructions(organizer)
    trip = create_publication_ready_trip(
        organizer=organizer,
        reviewer=create_user("sold-out-gate-reviewer@example.com"),
    )
    trip.capacity = 1
    trip.publication_state = Trip.PublicationState.PUBLISHED
    trip.booking_availability = Trip.BookingAvailability.OPEN
    trip.manual_payment_availability = Trip.ManualPaymentAvailability.OPEN
    trip.save(
        update_fields=[
            "capacity",
            "publication_state",
            "booking_availability",
            "manual_payment_availability",
        ]
    )
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Rahul Menon",
        booking_contact_phone="+919123456789",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.get(),
        position=1,
    )

    gate = public_booking_gate_decision(trip)

    assert available_seats(trip) == 0
    assert bookable_seats(trip) == 0
    assert effective_booking_availability(trip) == "sold_out"
    assert public_availability_band(trip) == "sold_out"
    assert gate.ready is False
    assert gate.reason_code == PublicBookingGateReason.SOLD_OUT
    assert gate.available_seats == 0
    assert gate.bookable_seats == 0
    assert gate.availability_band == "sold_out"


def test_trips_booking_gate_reads_trip_payments_bookable_seat_pressure():
    organizer = Organizer.objects.create(name="Hold-Aware Gate Collective")
    create_ready_manual_payment_instructions(organizer)
    trip = create_publication_ready_trip(
        organizer=organizer,
        reviewer=create_user("hold-aware-gate-reviewer@example.com"),
    )
    trip.capacity = 2
    trip.publication_state = Trip.PublicationState.PUBLISHED
    trip.booking_availability = Trip.BookingAvailability.OPEN
    trip.manual_payment_availability = Trip.ManualPaymentAvailability.OPEN
    trip.save(
        update_fields=[
            "capacity",
            "publication_state",
            "booking_availability",
            "manual_payment_availability",
        ]
    )
    held_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.DRAFT,
    )
    TravelerSlot.objects.create(booking=held_booking, package=trip.packages.get(), position=1)
    held_attempt = PaymentAttempt.objects.create(
        booking=held_booking,
        amount_inr=held_booking.booking_reservation_amount_inr,
    )
    create_seat_hold_for_payment_attempt(held_attempt)

    competing_gate = public_booking_gate_decision(trip, requested_seats=2)
    held_booking_gate = public_booking_gate_decision(
        trip,
        requested_seats=1,
        payment_attempt=held_attempt,
    )

    assert competing_gate.available_seats == 2
    assert competing_gate.active_seat_holds == 1
    assert competing_gate.bookable_seats == 1
    assert competing_gate.capacity_available is False
    assert competing_gate.reason_code == PublicBookingGateReason.INSUFFICIENT_CAPACITY
    assert held_booking_gate.bookable_seats == 2
    assert held_booking_gate.capacity_available is True
    assert held_booking_gate.ready is True


def test_legacy_trip_content_imports_reexport_trips_owners():
    legacy_media = import_module("organizers.trip_profile.media")
    trips_media = import_module("trips.media")
    legacy_activity = import_module("organizers.trip_profile.activity")
    trips_activity = import_module("trips.activity")

    assert legacy_media.validate_trip_media_upload is trips_media.validate_trip_media_upload
    assert (
        legacy_activity.record_trip_media_gallery_update_if_changed
        is trips_activity.record_trip_media_gallery_update_if_changed
    )


def test_legacy_trip_publication_imports_reexport_trips_owners():
    legacy_publication = import_module("organizers.trip_profile.publication_readiness")
    legacy_root_publication = import_module("organizers.trip_profile_publication_readiness")
    trips_publication = import_module("trips.publication_readiness")
    legacy_activity = import_module("organizers.trip_profile.activity")
    legacy_root_activity = import_module("organizers.trip_profile_activity")
    trips_activity = import_module("trips.activity")

    assert (
        legacy_publication.trip_profile_publication_readiness
        is trips_publication.trip_profile_publication_readiness
    )
    assert (
        legacy_root_publication.trip_profile_publication_readiness
        is trips_publication.trip_profile_publication_readiness
    )
    assert (
        legacy_activity.record_public_trip_page_published
        is trips_activity.record_public_trip_page_published
    )
    assert (
        legacy_root_activity.record_public_trip_page_published
        is trips_activity.record_public_trip_page_published
    )


def test_legacy_public_booking_gate_imports_reexport_trips_owner():
    legacy_gate = import_module("organizers.public_booking_gate")
    legacy_payments_gate = import_module("organizers.payments.public_booking_gate")
    legacy_payment_methods = import_module("organizers.payments.payment_method_readiness")
    trips_availability = import_module("trips.booking_availability")
    trips_payment_methods = import_module("trips.payment_method_readiness")

    assert (
        legacy_gate.public_booking_gate_decision
        is trips_availability.public_booking_gate_decision
    )
    assert (
        legacy_payments_gate.public_booking_gate_decision
        is trips_availability.public_booking_gate_decision
    )
    assert (
        legacy_payment_methods.payment_method_readiness_for_trip
        is trips_payment_methods.payment_method_readiness_for_trip
    )


def create_publication_ready_trip(
    *,
    organizer: Organizer,
    reviewer,
) -> Trip:
    trip = Trip.objects.create(
        organizer=organizer,
        title="Spiti Winter Field Week",
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 15),
        capacity=20,
        description_rich_text=rich_text_payload("Traveler-facing Spiti details."),
        confirmation_requirements_note="Identity details and emergency contact.",
        confirmation_requirements_reviewed_at=timezone.now(),
        confirmation_requirements_reviewed_by=reviewer,
    )
    TripPackage.objects.create(
        trip=trip,
        name="Standard room",
        price_inr=42000,
        reservation_amount_inr=10000,
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


def create_user(email: str):
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        password="tripos-test-password",
    )


def create_trip_with_package(*, organizer: Organizer | None = None) -> Trip:
    organizer = organizer or Organizer.objects.create(name="Trips Content Collective")
    trip = Trip.objects.create(
        organizer=organizer,
        title="Spiti Winter Field Week",
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 15),
        capacity=20,
    )
    TripPackage.objects.create(
        trip=trip,
        name="Standard room",
        price_inr=42000,
        reservation_amount_inr=10000,
        position=1,
    )
    return trip


def create_ready_manual_payment_instructions(organizer: Organizer) -> ManualPaymentInstructions:
    return ManualPaymentInstructions.objects.create(
        organizer=organizer,
        payment_qr="manual-payment-qr/payment-qr.png",
        original_filename="payment-qr.png",
        content_type="image/png",
        file_size=16,
    )


def itinerary_day_payload(sequence: int, title: str, description: str) -> dict:
    return {
        "sequence": sequence,
        "title": title,
        "date_label": f"Day {sequence}",
        "description_rich_text": rich_text_payload(description),
    }


def png_upload(filename: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        filename,
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
