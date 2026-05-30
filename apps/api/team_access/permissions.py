from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import NotAuthenticated, PermissionDenied

from organizers.models import Organizer
from team_access.models import OrganizerMembership


@dataclass(frozen=True)
class OrganizerRole:
    membership: OrganizerMembership

    @property
    def role(self) -> str:
        return self.membership.role

    @property
    def is_owner(self) -> bool:
        return self.role == OrganizerMembership.Role.OWNER

    @property
    def is_operator(self) -> bool:
        return self.role == OrganizerMembership.Role.OPERATOR

    @property
    def can_access_operations_dashboard(self) -> bool:
        return self.is_owner or self.is_operator

    @property
    def can_manage_organizer_identity(self) -> bool:
        return self.is_owner

    @property
    def can_view_organizer_profile(self) -> bool:
        return self.is_owner or self.is_operator

    @property
    def can_manage_organizer_profile(self) -> bool:
        return self.is_owner

    @property
    def can_publish_organizer_profile(self) -> bool:
        return self.is_owner

    @property
    def can_view_organizer_policies(self) -> bool:
        return self.is_owner or self.is_operator

    @property
    def can_manage_organizer_policies(self) -> bool:
        return self.is_owner

    @property
    def can_view_creative_setup(self) -> bool:
        return self.is_owner or self.is_operator

    @property
    def can_manage_creative_setup(self) -> bool:
        return self.is_owner

    @property
    def can_manage_payment_setup(self) -> bool:
        return self.is_owner

    @property
    def can_manage_team_access(self) -> bool:
        return self.is_owner

    @property
    def can_view_payout_status(self) -> bool:
        return self.is_owner or self.is_operator

    @property
    def can_use_operator_workflows(self) -> bool:
        return self.is_owner or self.is_operator

    @property
    def can_prepare_trip_content(self) -> bool:
        return self.is_owner or self.is_operator

    @property
    def can_create_trips(self) -> bool:
        return self.is_owner

    @property
    def can_publish_trip(self) -> bool:
        return self.is_owner

    @property
    def can_open_booking_availability(self) -> bool:
        return self.is_owner

    @property
    def can_close_booking_availability(self) -> bool:
        return self.is_owner or self.is_operator

    @property
    def can_manage_trip_capacity(self) -> bool:
        return self.is_owner

    @property
    def can_manage_trip_commercial_terms(self) -> bool:
        return self.is_owner

    @property
    def can_manage_post_booking_trip_dates(self) -> bool:
        return self.is_owner


def get_active_membership(user, organizer_id: int | None = None) -> OrganizerMembership | None:
    if (
        isinstance(user, AnonymousUser)
        or not user.is_authenticated
        or not getattr(user, "is_active", False)
    ):
        return None

    queryset = (
        OrganizerMembership.objects.select_related("organizer", "user")
        .filter(user=user, user__is_active=True)
        .order_by("organizer__name", "organizer_id")
    )
    if organizer_id is not None:
        queryset = queryset.filter(organizer_id=organizer_id)
    return queryset.first()


def require_membership(user, organizer_id: int | None = None) -> OrganizerRole:
    if isinstance(user, AnonymousUser) or not user.is_authenticated:
        raise NotAuthenticated("Authentication is required.")

    membership = get_active_membership(user, organizer_id)
    if membership is None:
        raise PermissionDenied("User does not belong to this Organizer.")
    return OrganizerRole(membership=membership)


def require_owner(user, organizer: Organizer) -> OrganizerRole:
    role = require_membership(user, organizer.id)
    if not role.can_manage_organizer_identity:
        raise PermissionDenied("Only Owners can manage this Organizer setting.")
    return role


def require_payment_status_access(user, organizer: Organizer) -> OrganizerRole:
    role = require_membership(user, organizer.id)
    if not role.can_view_payout_status:
        raise PermissionDenied("Owner or Operator access is required.")
    return role


def require_operator_workflow_access(user, organizer: Organizer) -> OrganizerRole:
    role = require_membership(user, organizer.id)
    if not role.can_use_operator_workflows:
        raise PermissionDenied("Owner or Operator access is required.")
    return role


def require_trip_content_access(user, organizer: Organizer) -> OrganizerRole:
    role = require_membership(user, organizer.id)
    if not role.can_prepare_trip_content:
        raise PermissionDenied("Owner or Operator access is required.")
    return role


def require_trip_creation_access(user, organizer: Organizer) -> OrganizerRole:
    role = require_membership(user, organizer.id)
    if not role.can_create_trips:
        raise PermissionDenied("Only Owners can create Trips for this Organizer.")
    return role
