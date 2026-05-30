from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError

from trip_operations.activity import record_activity_log
from trip_operations.models import ActivityLog
from trips.models import Trip, TripPaymentSchedule
from trips.rich_text import trip_rich_text_plain_text

CONFIRMATION_REQUIREMENT_FIELDS = [
    "requires_traveler_documents",
    "requires_traveler_identity_details",
    "requires_travel_logistics",
    "requires_emergency_contact",
    "requires_medical_disclosure",
    "requires_full_payment_before_confirmation",
]


def record_trip_profile_activity_log(
    *,
    action: str,
    trip: Trip,
    actor,
    metadata: dict | None = None,
) -> ActivityLog:
    if trip is None:
        raise ValidationError("Activity Log requires a Trip.")
    return record_activity_log(
        action=action,
        trip=trip,
        actor=actor,
        metadata=metadata or {},
    )


def record_public_trip_page_published(
    *,
    trip: Trip,
    actor,
    publish_lock_acknowledged: bool,
    previous_publication_state: str,
) -> None:
    record_trip_profile_activity_log(
        action=ActivityLog.Action.PUBLIC_TRIP_PAGE_PUBLISHED,
        trip=trip,
        actor=actor,
        metadata={
            "section": "publication",
            "change_type": "published",
            "published_trip_profile_lock_acknowledged": publish_lock_acknowledged,
            "previous_publication_state": previous_publication_state,
            "publication_state": trip.publication_state,
        },
    )


def trip_profile_section_change_type(
    *,
    previous_count: int,
    next_count: int,
    added_count: int = 0,
    removed_count: int = 0,
    updated_count: int = 0,
) -> str:
    if previous_count == 0 and next_count > 0:
        return "created"
    if previous_count > 0 and next_count == 0:
        return "cleared"
    if added_count and removed_count:
        return "replaced"
    if added_count:
        return "added"
    if removed_count:
        return "removed"
    if updated_count:
        return "updated"
    return "saved"


def trip_profile_review_change_type(
    *,
    changed_fields: list[str],
    review_changed: bool,
) -> str:
    if changed_fields and review_changed:
        return "reviewed_and_updated"
    if changed_fields:
        return "updated"
    if review_changed:
        return "reviewed"
    return "saved"


def trip_itinerary_day_snapshot(trip: Trip) -> list[dict[str, Any]]:
    return [
        {
            "sequence": day.sequence,
            "title": day.title,
            "date_label": day.date_label,
            "description_rich_text": day.description_rich_text,
        }
        for day in trip.itinerary_days.all()
    ]


def trip_itinerary_submission_snapshot(days: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "sequence": day["sequence"],
            "title": day["title"],
            "date_label": day.get("date_label", ""),
            "description_rich_text": day["description_rich_text"],
        }
        for day in days
    ]


def trip_media_item_snapshot(trip: Trip) -> dict[int, dict[str, Any]]:
    return {
        item.id: {
            "position": item.position,
            "caption": item.caption,
            "alt_text": item.alt_text,
            "is_public": item.is_public,
            "is_cover": item.is_cover,
        }
        for item in trip.media_items.all()
    }


def trip_media_submission_snapshot(items: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {
        item["id"]: {
            "position": item["position"],
            "caption": item.get("caption", ""),
            "alt_text": item.get("alt_text", ""),
            "is_public": item.get("is_public", False),
            "is_cover": item.get("is_cover", False),
        }
        for item in items
    }


def trip_package_snapshot(trip: Trip) -> dict[int, dict[str, Any]]:
    return {
        package.id: {
            "name": package.name,
            "description": package.description,
            "price_inr": package.price_inr,
            "reservation_amount_inr": package.reservation_amount_inr,
            "position": package.position,
        }
        for package in trip.packages.active()
    }


def payment_schedule_snapshot(schedule: TripPaymentSchedule) -> dict[str, Any]:
    return {
        "has_balance_milestone": schedule.has_balance_milestone,
        "balance_due_days_before_start": schedule.balance_due_days_before_start,
        "balance_reminder_lead_days": schedule.balance_reminder_lead_days,
        "reviewed": schedule.is_reviewed,
    }


def confirmation_requirements_snapshot(trip: Trip) -> dict[str, Any]:
    return {
        "confirmation_requirements_note": trip.confirmation_requirements_note,
        **{field: getattr(trip, field) for field in CONFIRMATION_REQUIREMENT_FIELDS},
        "reviewed": trip.confirmation_requirements_reviewed,
    }


@dataclass(frozen=True)
class TripPackageSubmissionChange:
    removed_package_ids: set[int]
    withdrawn_package_count: int
    added_package_count: int
    updated_package_count: int

    @property
    def changed(self) -> bool:
        return (
            self.added_package_count > 0
            or bool(self.removed_package_ids)
            or self.updated_package_count > 0
        )


def trip_package_submission_change(
    *,
    trip: Trip,
    previous_packages: dict[int, dict[str, Any]],
    submitted_packages: list[dict[str, Any]],
) -> TripPackageSubmissionChange:
    submitted_package_ids = {
        package["id"] for package in submitted_packages if package.get("id") is not None
    }
    removed_package_ids = set(previous_packages) - submitted_package_ids
    withdrawn_package_count = (
        trip.packages.active()
        .filter(id__in=removed_package_ids, traveler_slots__isnull=False)
        .distinct()
        .count()
    )
    added_package_count = sum(
        1 for package in submitted_packages if package.get("id") is None
    )
    updated_package_count = 0
    for position, package in enumerate(submitted_packages, start=1):
        package_id = package.get("id")
        if package_id is None or package_id not in previous_packages:
            continue
        next_package = {
            "name": package["name"],
            "description": package.get("description", ""),
            "price_inr": package["price_inr"],
            "reservation_amount_inr": package["reservation_amount_inr"],
            "position": position,
        }
        if previous_packages[package_id] != next_package:
            updated_package_count += 1

    return TripPackageSubmissionChange(
        removed_package_ids=removed_package_ids,
        withdrawn_package_count=withdrawn_package_count,
        added_package_count=added_package_count,
        updated_package_count=updated_package_count,
    )


def record_trip_description_update_if_changed(
    *,
    trip: Trip,
    actor,
    previous_description: Any,
    next_description: Any,
) -> None:
    if next_description == previous_description:
        return

    previous_plain_text_length = len(trip_rich_text_plain_text(previous_description))
    next_plain_text_length = len(trip_rich_text_plain_text(next_description))
    record_trip_profile_activity_log(
        action=ActivityLog.Action.TRIP_DESCRIPTION_UPDATED,
        trip=trip,
        actor=actor,
        metadata={
            "section": "description",
            "change_type": trip_profile_section_change_type(
                previous_count=previous_plain_text_length,
                next_count=next_plain_text_length,
            ),
            "plain_text_length": next_plain_text_length,
        },
    )


def record_trip_itinerary_update_if_changed(
    *,
    trip: Trip,
    actor,
    previous_days: list[dict[str, Any]],
    next_days: list[dict[str, Any]],
) -> None:
    if next_days == previous_days:
        return

    record_trip_profile_activity_log(
        action=ActivityLog.Action.TRIP_ITINERARY_UPDATED,
        trip=trip,
        actor=actor,
        metadata={
            "section": "itinerary",
            "change_type": trip_profile_section_change_type(
                previous_count=len(previous_days),
                next_count=len(next_days),
            ),
            "previous_day_count": len(previous_days),
            "day_count": len(next_days),
        },
    )


def record_trip_media_upload(
    *,
    trip: Trip,
    actor,
    previous_item_count: int,
    uploaded_item_count: int,
) -> None:
    if uploaded_item_count <= 0:
        return

    record_trip_profile_activity_log(
        action=ActivityLog.Action.TRIP_MEDIA_GALLERY_UPDATED,
        trip=trip,
        actor=actor,
        metadata={
            "section": "media",
            "change_type": "added",
            "previous_item_count": previous_item_count,
            "item_count": previous_item_count + uploaded_item_count,
            "uploaded_item_count": uploaded_item_count,
            "public_item_count": trip.media_items.filter(is_public=True).count(),
        },
    )


def record_trip_media_gallery_update_if_changed(
    *,
    trip: Trip,
    actor,
    previous_items: dict[int, dict[str, Any]],
    next_items: dict[int, dict[str, Any]],
) -> None:
    removed_item_ids = set(previous_items) - set(next_items)
    updated_item_count = sum(
        1
        for item_id, item in next_items.items()
        if item_id in previous_items and previous_items[item_id] != item
    )
    if not removed_item_ids and not updated_item_count:
        return

    record_trip_profile_activity_log(
        action=ActivityLog.Action.TRIP_MEDIA_GALLERY_UPDATED,
        trip=trip,
        actor=actor,
        metadata={
            "section": "media",
            "change_type": trip_profile_section_change_type(
                previous_count=len(previous_items),
                next_count=len(next_items),
                removed_count=len(removed_item_ids),
                updated_count=updated_item_count,
            ),
            "previous_item_count": len(previous_items),
            "item_count": len(next_items),
            "removed_item_count": len(removed_item_ids),
            "updated_item_count": updated_item_count,
            "public_item_count": sum(1 for item in next_items.values() if item["is_public"]),
        },
    )


def record_trip_package_update_if_changed(
    *,
    trip: Trip,
    actor,
    previous_packages: dict[int, dict[str, Any]],
    submitted_packages: list[dict[str, Any]],
    change: TripPackageSubmissionChange,
) -> None:
    if not change.changed:
        return

    record_trip_profile_activity_log(
        action=ActivityLog.Action.TRIP_PACKAGES_UPDATED,
        trip=trip,
        actor=actor,
        metadata={
            "section": "packages",
            "change_type": trip_profile_section_change_type(
                previous_count=len(previous_packages),
                next_count=len(submitted_packages),
                added_count=change.added_package_count,
                removed_count=len(change.removed_package_ids),
                updated_count=change.updated_package_count,
            ),
            "previous_active_package_count": len(previous_packages),
            "active_package_count": len(submitted_packages),
            "added_package_count": change.added_package_count,
            "removed_package_count": len(change.removed_package_ids),
            "withdrawn_package_count": change.withdrawn_package_count,
            "updated_package_count": change.updated_package_count,
        },
    )


def record_trip_payment_schedule_update_if_changed(
    *,
    trip: Trip,
    actor,
    previous_schedule: dict[str, Any],
    next_schedule: dict[str, Any],
) -> None:
    changed_fields = [
        field
        for field in [
            "has_balance_milestone",
            "balance_due_days_before_start",
            "balance_reminder_lead_days",
        ]
        if previous_schedule[field] != next_schedule[field]
    ]
    review_changed = not previous_schedule["reviewed"] and next_schedule["reviewed"]
    if not changed_fields and not review_changed:
        return

    record_trip_profile_activity_log(
        action=ActivityLog.Action.TRIP_PAYMENT_SCHEDULE_UPDATED,
        trip=trip,
        actor=actor,
        metadata={
            "section": "payment_schedule",
            "change_type": trip_profile_review_change_type(
                changed_fields=changed_fields,
                review_changed=review_changed,
            ),
            "changed_fields": changed_fields,
            "changed_field_count": len(changed_fields),
            "has_balance_milestone": next_schedule["has_balance_milestone"],
            "balance_due_days_before_start": next_schedule["balance_due_days_before_start"],
            "balance_reminder_lead_days": next_schedule["balance_reminder_lead_days"],
            "reviewed": next_schedule["reviewed"],
        },
    )


def record_trip_confirmation_requirements_update_if_changed(
    *,
    trip: Trip,
    actor,
    previous_requirements: dict[str, Any],
    next_requirements: dict[str, Any],
) -> None:
    changed_fields = [
        field
        for field in [
            "confirmation_requirements_note",
            *CONFIRMATION_REQUIREMENT_FIELDS,
        ]
        if previous_requirements[field] != next_requirements[field]
    ]
    review_changed = not previous_requirements["reviewed"] and next_requirements["reviewed"]
    if not changed_fields and not review_changed:
        return

    record_trip_profile_activity_log(
        action=ActivityLog.Action.TRIP_CONFIRMATION_REQUIREMENTS_UPDATED,
        trip=trip,
        actor=actor,
        metadata={
            "section": "confirmation_requirements",
            "change_type": trip_profile_review_change_type(
                changed_fields=changed_fields,
                review_changed=review_changed,
            ),
            "changed_fields": changed_fields,
            "changed_field_count": len(changed_fields),
            "active_requirement_count": _active_confirmation_requirement_count(trip),
            "reviewed": next_requirements["reviewed"],
        },
    )


def _active_confirmation_requirement_count(trip: Trip) -> int:
    return sum(1 for field in CONFIRMATION_REQUIREMENT_FIELDS if getattr(trip, field))
