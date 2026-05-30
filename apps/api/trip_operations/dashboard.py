from __future__ import annotations

from dataclasses import dataclass

from organizer_payments.payment_setup_readiness import payment_setup_status_payload
from organizer_profile.identity import organizer_profile_identity_payload
from organizers.models import Organizer
from team_access.permissions import OrganizerRole, require_membership
from trip_bookings.models import Booking
from trip_operations.metrics import (
    core_operational_booking_count,
    operational_metrics,
    public_booking_readiness,
)
from trip_operations.serializers import OperationsBookingListItemSerializer
from trips.models import Trip


@dataclass(frozen=True)
class OperationsDashboardReadModel:
    role: OrganizerRole

    @property
    def organizer(self) -> Organizer:
        return self.role.membership.organizer

    def to_payload(self) -> dict:
        organizer = self.organizer
        return {
            "active_organizer": active_organizer_payload(organizer),
            "membership": membership_payload(self.role),
            "permissions": permissions_payload(self.role),
            "payment_setup": payment_setup_status_payload(organizer, role=self.role),
            "trips": trips_dashboard_payload(organizer),
        }


def build_operations_dashboard_payload(user, organizer_id: int | None = None) -> dict:
    role = require_membership(user, organizer_id)
    return OperationsDashboardReadModel(role=role).to_payload()


def active_organizer_payload(organizer: Organizer) -> dict:
    return {
        "id": organizer.id,
        "name": organizer.name,
        "slug": organizer.slug,
        "identity": organizer_profile_identity_payload(organizer),
    }


def membership_payload(role: OrganizerRole) -> dict[str, str]:
    return {
        "role": role.role,
        "label": role.membership.get_role_display(),
    }


def permissions_payload(role: OrganizerRole) -> dict[str, bool]:
    return {
        "can_access_operations_dashboard": role.can_access_operations_dashboard,
        "can_manage_organizer_identity": role.can_manage_organizer_identity,
        "can_manage_payment_setup": role.can_manage_payment_setup,
        "can_manage_team_access": role.can_manage_team_access,
        "can_use_operator_workflows": role.can_use_operator_workflows,
        "can_prepare_trip_content": role.can_prepare_trip_content,
        "can_publish_trip": role.can_publish_trip,
        "can_open_booking_availability": role.can_open_booking_availability,
        "can_close_booking_availability": role.can_close_booking_availability,
        "can_manage_trip_capacity": role.can_manage_trip_capacity,
        "can_manage_trip_commercial_terms": role.can_manage_trip_commercial_terms,
        "can_manage_post_booking_trip_dates": role.can_manage_post_booking_trip_dates,
    }


def trips_dashboard_payload(organizer: Organizer) -> dict:
    trips = operations_dashboard_trip_queryset(organizer)
    latest_trip = trips.order_by("-updated_at", "-id").first()
    active_summaries = [
        trip_dashboard_summary_payload(trip) for trip in trips.order_by("start_date", "title", "id")
    ]
    payload = {
        "count": len(active_summaries),
        "latest": None,
        "active_summaries": active_summaries,
        "attention_items": cross_trip_attention_items(active_summaries),
    }
    if latest_trip is not None:
        payload["latest"] = trip_dashboard_payload(latest_trip)
    return payload


def trip_dashboard_payload(trip: Trip) -> dict:
    payload = trip_dashboard_summary_payload(trip)
    payload["bookings"] = OperationsBookingListItemSerializer(
        operations_dashboard_booking_queryset(trip),
        many=True,
    ).data
    return payload


def trip_dashboard_summary_payload(trip: Trip) -> dict:
    readiness = public_booking_readiness(trip)
    metrics = operational_metrics(trip)
    return {
        "id": trip.id,
        "title": trip.title,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "capacity": trip.capacity,
        "publication_state": trip.publication_state,
        "booking_availability": trip.booking_availability,
        "effective_booking_availability": readiness.effective_booking_availability,
        "available_seats": readiness.available_seats,
        "core_operational_booking_count": core_operational_booking_count(trip),
        "operational_metrics": {
            "unpaid_bookings": metrics.unpaid_bookings,
            "overdue_amount_inr": metrics.overdue_amount_inr,
            "pending_manual_payments": metrics.pending_manual_payments,
            "pending_manual_payments_supported": metrics.pending_manual_payments_supported,
            "missing_requirements": metrics.missing_requirements,
            "missing_requirements_supported": metrics.missing_requirements_supported,
            "available_seats": metrics.available_seats,
            "reserved_travelers": metrics.reserved_travelers,
            "core_operational_booking_count": metrics.core_operational_booking_count,
            "booking_state_counts": metrics.booking_state_counts,
        },
        "launch_readiness": readiness.to_payload(),
    }


def cross_trip_attention_items(active_summaries: list[dict]) -> list[dict]:
    items = []
    for trip in active_summaries:
        metrics = trip["operational_metrics"]
        readiness = trip["launch_readiness"]
        trip_context = {
            "trip_id": trip["id"],
            "trip_title": trip["title"],
        }

        if metrics["pending_manual_payments"] > 0:
            items.append(
                {
                    **trip_context,
                    "id": f"trip-{trip['id']}-payment-approvals",
                    "kind": "payment_approvals",
                    "count": metrics["pending_manual_payments"],
                    "amount_inr": 0,
                    "message": "Manual Payments are waiting for approval.",
                    "tone": "attention",
                }
            )

        if metrics["overdue_amount_inr"] > 0:
            items.append(
                {
                    **trip_context,
                    "id": f"trip-{trip['id']}-overdue-balances",
                    "kind": "overdue_balances",
                    "count": 0,
                    "amount_inr": metrics["overdue_amount_inr"],
                    "message": "Booking balances are past due.",
                    "tone": "attention",
                }
            )

        if metrics["missing_requirements"] > 0:
            items.append(
                {
                    **trip_context,
                    "id": f"trip-{trip['id']}-missing-requirements",
                    "kind": "missing_requirements",
                    "count": metrics["missing_requirements"],
                    "amount_inr": 0,
                    "message": "Traveler readiness has missing Confirmation Requirements.",
                    "tone": "attention",
                }
            )

        if not readiness["ready"]:
            items.append(
                {
                    **trip_context,
                    "id": f"trip-{trip['id']}-launch-blocker",
                    "kind": "launch_blocker",
                    "count": 0,
                    "amount_inr": 0,
                    "message": readiness["message"],
                    "tone": "blocked",
                }
            )

    return items


def operations_dashboard_trip_queryset(organizer: Organizer):
    return organizer.trips.select_related("payment_schedule").prefetch_related("packages")


def operations_dashboard_booking_queryset(trip: Trip):
    return (
        Booking.objects.filter(trip=trip)
        .select_related("trip", "trip__payment_schedule")
        .prefetch_related(
            "traveler_slots__package",
            "traveler_slots__documents",
            "ledger_entries",
            "manual_payments",
        )
        .all()
    )
