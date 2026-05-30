from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils.text import slugify

from trip_operations.models import ActivityLog
from trips.activity import record_trip_profile_activity_log
from trips.models import Trip, TripItineraryDay, TripMediaItem, TripPackage, TripPaymentSchedule


def duplicate_trip(
    trip: Trip,
    *,
    actor=None,
    title: str = "",
    start_date: date | None = None,
    end_date: date | None = None,
) -> Trip:
    with transaction.atomic():
        source = (
            Trip.objects.select_for_update()
            .select_related("organizer", "payment_schedule")
            .prefetch_related("packages", "itinerary_days", "media_items__asset")
            .get(pk=trip.pk)
        )
        duplicate_title = title.strip() or f"{source.title} Copy"
        duplicate = Trip.objects.create(
            organizer=source.organizer,
            title=duplicate_title,
            slug=unique_trip_slug(source.organizer_id, duplicate_title),
            start_date=start_date or source.start_date,
            end_date=end_date or source.end_date,
            capacity=source.capacity,
            confirmation_requirements_note=source.confirmation_requirements_note,
            requires_traveler_documents=source.requires_traveler_documents,
            requires_traveler_identity_details=source.requires_traveler_identity_details,
            requires_travel_logistics=source.requires_travel_logistics,
            requires_emergency_contact=source.requires_emergency_contact,
            requires_medical_disclosure=source.requires_medical_disclosure,
            requires_full_payment_before_confirmation=(
                source.requires_full_payment_before_confirmation
            ),
            confirmation_requirements_reviewed_at=source.confirmation_requirements_reviewed_at,
            confirmation_requirements_reviewed_by=source.confirmation_requirements_reviewed_by,
            description_rich_text=source.description_rich_text,
            itinerary=source.itinerary,
            publication_state=Trip.PublicationState.DRAFT,
            booking_availability=Trip.BookingAvailability.CLOSED,
        )
        for package in source.packages.active():
            TripPackage.objects.create(
                trip=duplicate,
                name=package.name,
                description=package.description,
                price_inr=package.price_inr,
                reservation_amount_inr=package.reservation_amount_inr,
                position=package.position,
            )
        for day in source.itinerary_days.all():
            TripItineraryDay.objects.create(
                trip=duplicate,
                sequence=day.sequence,
                title=day.title,
                date_label=day.date_label,
                description_rich_text=day.description_rich_text,
            )
        for media_item in source.media_items.all():
            TripMediaItem.objects.create(
                trip=duplicate,
                asset=media_item.asset,
                position=media_item.position,
                caption=media_item.caption,
                alt_text=media_item.alt_text,
                is_public=media_item.is_public,
                is_cover=media_item.is_cover,
            )
        source_schedule = getattr(source, "payment_schedule", None)
        TripPaymentSchedule.objects.create(
            trip=duplicate,
            balance_due_days_before_start=(
                source_schedule.balance_due_days_before_start if source_schedule else None
            ),
            balance_reminder_lead_days=(
                source_schedule.balance_reminder_lead_days if source_schedule else 3
            ),
            reviewed_at=source_schedule.reviewed_at if source_schedule else None,
            reviewed_by=source_schedule.reviewed_by if source_schedule else None,
        )
        record_trip_profile_activity_log(
            action=ActivityLog.Action.TRIP_DUPLICATED,
            trip=source,
            actor=actor,
            metadata={"duplicate_trip_id": duplicate.id},
        )
        return duplicate


def unique_trip_slug(organizer_id: int, title: str) -> str:
    base_slug = slugify(title)[:180] or "trip"
    candidate = base_slug
    suffix = 2
    while Trip.objects.filter(organizer_id=organizer_id, slug=candidate).exists():
        candidate = f"{base_slug[: 180 - len(str(suffix)) - 1]}-{suffix}"
        suffix += 1
    return candidate
