from __future__ import annotations

from organizer_payments.online_payment_readiness import OnlinePaymentReadinessDecision
from organizers.models import Organizer, Trip


def individual_creator_payment_path_payload() -> dict[str, str | list[str]]:
    return {
        "title": "Individual Creator Payment Path",
        "summary": (
            "Creator-led Organizers can connect a provider account that matches how "
            "they already collect trip payments, including individual or "
            "unregistered-business accounts when the provider supports them."
        ),
        "steps": [
            (
                "Use a published TripOS Public Trip URL to show the provider where "
                "travelers will review the trip and pay."
            ),
            (
                "Complete provider-hosted verification with the organizer and "
                "payout details requested for that provider account."
            ),
            (
                "TripOS records Provider Verification, Settlement Readiness, "
                "connection, capability, and live-mode readiness without storing "
                "verification documents."
            ),
        ],
    }


def provider_verification_url_payload(organizer: Organizer) -> dict[str, bool | int | str | None]:
    trip = (
        organizer.trips.filter(publication_state=Trip.PublicationState.PUBLISHED)
        .order_by("-updated_at", "-id")
        .first()
    )

    if trip is None:
        return {
            "available": False,
            "source": "public_trip_url",
            "source_label": "TripOS Public Trip URL",
            "url_path": "",
            "trip_id": None,
            "trip_title": "",
            "status_label": "Publish a Public Trip Page",
            "message": (
                "Publish a Public Trip Page from Launch, then use that TripOS URL "
                "as the Provider Verification URL."
            ),
        }

    url_path = trip.public_url_path or f"/trips/{organizer.slug}/{trip.slug}"
    return {
        "available": True,
        "source": "public_trip_url",
        "source_label": "TripOS Public Trip URL",
        "url_path": url_path,
        "trip_id": trip.id,
        "trip_title": trip.title,
        "status_label": "Ready to share",
        "message": ("Use this published TripOS Public Trip URL as the Provider Verification URL."),
    }


def manual_payments_only_payload(
    readiness: OnlinePaymentReadinessDecision,
    *,
    manual_payment_capability_enabled: bool,
) -> dict[str, bool | str]:
    active = manual_payment_capability_enabled and not readiness.ready

    return {
        "supported": manual_payment_capability_enabled,
        "active": active,
        "status_label": ("Manual Payments Only" if active else "Provider payments ready"),
        "public_booking_message": (
            "Public Booking stays closed with Bookings Opening Soon until Online "
            "Payment Readiness is ready."
            if active
            else (
                "Public Booking can use provider-confirmed payments when booking "
                "availability is open."
            )
        ),
        "manual_operations_message": (
            "Manual Bookings and Manual Payments remain available in the Operations Dashboard."
            if manual_payment_capability_enabled
            else "Manual payment operations are unavailable for this Organizer."
        ),
    }
