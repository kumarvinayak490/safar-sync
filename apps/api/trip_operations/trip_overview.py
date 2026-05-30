from __future__ import annotations

from dataclasses import dataclass

from django.shortcuts import get_object_or_404

from organizer_payments.payment_setup_readiness import payment_setup_status_payload
from organizers.models import Organizer
from team_access.permissions import OrganizerRole, require_operator_workflow_access
from trip_bookings.models import Booking
from trip_operations.metrics import (
    core_operational_booking_count,
    operational_metrics,
    public_booking_readiness,
)
from trip_operations.serializers import OperationsBookingListItemSerializer
from trip_operations.timeline import recent_activity_payload
from trip_payments.financial_ledger import booking_payment_summary_payload
from trips.models import Trip


@dataclass(frozen=True)
class TripOverviewReadModel:
    role: OrganizerRole
    trip: Trip

    def to_payload(self) -> dict:
        trip = self.trip
        organizer = self.role.membership.organizer
        readiness = public_booking_readiness(trip)
        readiness_payload = readiness.to_payload()
        metrics = operational_metrics(trip)
        bookings = trip_overview_booking_queryset(trip)
        payment_setup = payment_setup_status_payload(organizer, role=self.role)

        return {
            "trip": trip_basics_payload(trip),
            "capacity": {
                "total_seats": trip.capacity,
                "available_seats": readiness.available_seats,
                "reserved_travelers": metrics.reserved_travelers,
                "core_operational_booking_count": core_operational_booking_count(trip),
            },
            "packages": [
                trip_package_payload(package)
                for package in trip.packages.active().order_by("position", "id")
            ],
            "booking_progress": {
                "core_operational_booking_count": metrics.core_operational_booking_count,
                "booking_state_counts": metrics.booking_state_counts,
                "bookings": OperationsBookingListItemSerializer(bookings, many=True).data,
            },
            "payment_readiness": {
                "provider_payment_setup_complete": payment_setup["provider_payment_setup_complete"],
                "provider_payment_setup_status_label": payment_setup[
                    "provider_payment_setup_status_label"
                ],
                "online_payment_readiness_ready": payment_setup["online_payment_readiness_ready"],
                "online_payment_readiness_status_label": payment_setup[
                    "online_payment_readiness_status_label"
                ],
                "online_payment_readiness_message": payment_setup[
                    "online_payment_readiness_message"
                ],
                "payment_method_readiness_ready": readiness_payload[
                    "payment_method_readiness_ready"
                ],
                "payment_method_readiness_status_label": readiness_payload[
                    "payment_method_readiness_status_label"
                ],
                "ready_payment_method_count": readiness_payload["ready_payment_method_count"],
                "ready_payment_method_ids": readiness_payload["ready_payment_method_ids"],
                "payment_methods": readiness_payload["payment_methods"],
                "provider_payment_method": readiness_payload["provider_payment_method"],
                "manual_payment_method": readiness_payload["manual_payment_method"],
                "payment_setup": payment_setup,
                **payment_summary_payload(bookings),
            },
            "traveler_readiness": {
                "reserved_travelers": metrics.reserved_travelers,
                "missing_requirements": metrics.missing_requirements,
                "missing_requirements_supported": metrics.missing_requirements_supported,
                "ready": metrics.missing_requirements_supported
                and metrics.missing_requirements == 0,
            },
            "launch_context": {
                "publication_state": trip.publication_state,
                "publication_state_label": trip.get_publication_state_display(),
                "booking_availability": readiness.booking_availability,
                "booking_availability_label": readiness.booking_availability_label,
                "effective_booking_availability": readiness.effective_booking_availability,
                "effective_booking_availability_label": (
                    readiness.effective_booking_availability_label
                ),
                "message": readiness.message,
            },
            "recent_activity": recent_activity_payload(trip),
        }


def build_trip_overview_payload(user, organizer_id: int, trip_id: int) -> dict:
    organizer = get_object_or_404(Organizer, pk=organizer_id)
    role = require_operator_workflow_access(user, organizer)
    trip = get_object_or_404(trip_overview_trip_queryset(organizer), pk=trip_id)
    return TripOverviewReadModel(role=role, trip=trip).to_payload()


def trip_overview_trip_queryset(organizer: Organizer):
    return organizer.trips.select_related(
        "organizer",
        "organizer__provider_payment_setup",
        "organizer__payout_account",
        "payment_schedule",
    ).prefetch_related("packages")


def trip_overview_booking_queryset(trip: Trip):
    return (
        Booking.objects.filter(trip=trip)
        .select_related("trip", "trip__payment_schedule")
        .prefetch_related(
            "traveler_slots__package",
            "traveler_slots__documents",
            "ledger_entries",
            "provider_payments__payment_attempt",
            "provider_payments__ledger_entries",
            "manual_payments",
        )
        .all()
    )


def trip_basics_payload(trip: Trip) -> dict:
    return {
        "id": trip.id,
        "title": trip.title,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "publication_state": trip.publication_state,
        "publication_state_label": trip.get_publication_state_display(),
        "booking_availability": trip.booking_availability,
        "booking_availability_label": trip.get_booking_availability_display(),
        "public_url_path": trip.public_url_path,
    }


def trip_package_payload(package) -> dict:
    return {
        "id": package.id,
        "name": package.name,
        "description": package.description,
        "price_inr": package.price_inr,
        "reservation_amount_inr": package.reservation_amount_inr,
        "position": package.position,
        "lifecycle_state": package.lifecycle_state,
        "lifecycle_state_label": package.get_lifecycle_state_display(),
        "is_withdrawn": package.is_withdrawn,
    }


def payment_summary_payload(bookings) -> dict:
    return booking_payment_summary_payload(bookings)
