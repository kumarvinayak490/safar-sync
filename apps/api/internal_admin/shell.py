from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StaffOrchestrationSurface:
    key: str
    source_domain: str
    path: str
    methods: tuple[str, ...] = ("GET",)

    def to_payload(self) -> dict[str, object]:
        return {
            "key": self.key,
            "source_domain": self.source_domain,
            "path": self.path,
            "methods": list(self.methods),
        }


STAFF_ORCHESTRATION_SURFACES = (
    StaffOrchestrationSurface(
        key="organizer_support",
        source_domain="organizers",
        path="/api/internal-admin/organizers/",
    ),
    StaffOrchestrationSurface(
        key="trip_support",
        source_domain="trips",
        path="/api/internal-admin/trips/{trip_id}/",
    ),
    StaffOrchestrationSurface(
        key="booking_support",
        source_domain="trip_bookings",
        path="/api/internal-admin/bookings/{booking_id}/",
    ),
    StaffOrchestrationSurface(
        key="platform_fee_statement_review",
        source_domain="trip_payments",
        path="/api/internal-admin/platform-fee-statements/",
        methods=("GET", "POST", "PATCH"),
    ),
    StaffOrchestrationSurface(
        key="payment_exception_review",
        source_domain="trip_payments",
        path="/api/internal-admin/payment-exceptions/",
        methods=("GET", "POST"),
    ),
    StaffOrchestrationSurface(
        key="discovery_page_config",
        source_domain="public_discovery",
        path="/api/internal-admin/discovery-pages/",
        methods=("GET", "POST", "PATCH"),
    ),
)


def build_internal_admin_shell_payload(staff_user) -> dict[str, object]:
    return {
        "surface": "internal_admin",
        "purpose": "staff_orchestration",
        "business_state_owner": "source_domain_modules",
        "staff": {
            "id": staff_user.id,
            "email": staff_user.email,
            "is_staff": staff_user.is_staff,
        },
        "orchestration_surfaces": [
            surface.to_payload() for surface in STAFF_ORCHESTRATION_SURFACES
        ],
    }
