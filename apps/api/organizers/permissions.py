from __future__ import annotations

from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import NotAuthenticated, PermissionDenied

from team_access.permissions import (
    OrganizerRole,
    get_active_membership,
    require_membership,
    require_operator_workflow_access,
    require_owner,
    require_payment_status_access,
    require_trip_content_access,
    require_trip_creation_access,
)

__all__ = [
    "OrganizerRole",
    "get_active_membership",
    "require_internal_admin",
    "require_membership",
    "require_operator_workflow_access",
    "require_owner",
    "require_payment_status_access",
    "require_trip_content_access",
    "require_trip_creation_access",
]


def require_internal_admin(user):
    if isinstance(user, AnonymousUser) or not user.is_authenticated:
        raise NotAuthenticated("Authentication is required.")
    if not user.is_staff:
        raise PermissionDenied("Internal TripOS staff access is required.")
    return user
