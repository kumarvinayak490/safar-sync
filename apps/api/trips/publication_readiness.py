from __future__ import annotations

from dataclasses import dataclass

from trips.models import Trip
from trips.rich_text import is_trip_rich_text_empty


@dataclass(frozen=True)
class TripProfilePublicationReadinessItem:
    id: str
    label: str
    detail: str
    section_id: str
    blocking: bool

    @property
    def tone(self) -> str:
        return "blocked" if self.blocking else "attention"

    def to_payload(self) -> dict[str, bool | str]:
        return {
            "id": self.id,
            "label": self.label,
            "detail": self.detail,
            "section_id": self.section_id,
            "blocking": self.blocking,
            "tone": self.tone,
        }


@dataclass(frozen=True)
class TripProfilePublicationReadinessDecision:
    blockers: tuple[TripProfilePublicationReadinessItem, ...]
    encouraged: tuple[TripProfilePublicationReadinessItem, ...]

    @property
    def publish_eligible(self) -> bool:
        return len(self.blockers) == 0

    def to_payload(self) -> dict[str, bool | int | list[dict[str, bool | str]]]:
        return {
            "blockers": [item.to_payload() for item in self.blockers],
            "encouraged": [item.to_payload() for item in self.encouraged],
            "blocker_count": len(self.blockers),
            "encouraged_count": len(self.encouraged),
            "publish_eligible": self.publish_eligible,
            "lock_acknowledgement_required": True,
        }


def trip_profile_publication_readiness(
    trip: Trip,
) -> TripProfilePublicationReadinessDecision:
    blockers: list[TripProfilePublicationReadinessItem] = []
    encouraged: list[TripProfilePublicationReadinessItem] = []

    if is_trip_rich_text_empty(trip.description_rich_text):
        blockers.append(
            TripProfilePublicationReadinessItem(
                id="description",
                label="Trip Description",
                detail="Add traveler-facing trip details.",
                section_id="description",
                blocking=True,
            )
        )

    if not trip.packages.active().exists():
        blockers.append(
            TripProfilePublicationReadinessItem(
                id="packages",
                label="Packages",
                detail="Add at least one active Package.",
                section_id="packages",
                blocking=True,
            )
        )

    if not _payment_schedule_reviewed(trip):
        blockers.append(
            TripProfilePublicationReadinessItem(
                id="payment-schedule",
                label="Balance payment schedule",
                detail="Owner review required before publication.",
                section_id="payment-schedule",
                blocking=True,
            )
        )

    if not trip.itinerary_days.exists():
        blockers.append(
            TripProfilePublicationReadinessItem(
                id="itinerary",
                label="Itinerary Days",
                detail="Add at least one structured Itinerary Day.",
                section_id="itinerary",
                blocking=True,
            )
        )

    if not trip.confirmation_requirements_reviewed:
        blockers.append(
            TripProfilePublicationReadinessItem(
                id="requirements",
                label="Confirmation Requirements",
                detail="Review traveler readiness requirements.",
                section_id="requirements",
                blocking=True,
            )
        )

    if not trip.media_items.filter(is_public=True).exists():
        encouraged.append(
            TripProfilePublicationReadinessItem(
                id="media-gallery",
                label="Add public media",
                detail="Media is encouraged for the Public Trip Page.",
                section_id="media",
                blocking=False,
            )
        )

    return TripProfilePublicationReadinessDecision(
        blockers=tuple(blockers),
        encouraged=tuple(encouraged),
    )


def _payment_schedule_reviewed(trip: Trip) -> bool:
    try:
        return trip.payment_schedule.is_reviewed
    except Trip.payment_schedule.RelatedObjectDoesNotExist:
        return False
