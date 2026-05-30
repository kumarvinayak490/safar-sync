from __future__ import annotations

from rest_framework.exceptions import PermissionDenied

from organizers.models import Organizer
from team_access.permissions import require_membership


def require_profile_view_access(user, organizer: Organizer):
    role = require_membership(user, organizer.id)
    if not role.can_view_organizer_profile:
        raise PermissionDenied("Owner or Operator access is required.")
    return role


def require_profile_edit_access(user, organizer: Organizer):
    role = require_membership(user, organizer.id)
    if not role.can_manage_organizer_profile:
        raise PermissionDenied("Only Owners can edit Organizer Profile.")
    return role


def require_profile_publication_access(user, organizer: Organizer):
    role = require_membership(user, organizer.id)
    if not role.can_publish_organizer_profile:
        raise PermissionDenied("Only Owners can publish Organizer Profile.")
    return role
