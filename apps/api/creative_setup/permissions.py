from __future__ import annotations

from rest_framework.exceptions import PermissionDenied

from organizers.models import Organizer
from team_access.permissions import require_membership


def require_creative_setup_view_access(user, organizer: Organizer):
    role = require_membership(user, organizer.id)
    if not role.can_view_creative_setup:
        raise PermissionDenied("Owner or Operator access is required.")
    return role


def require_creative_setup_edit_access(user, organizer: Organizer):
    role = require_membership(user, organizer.id)
    if not role.can_manage_creative_setup:
        raise PermissionDenied("Only Owners can edit Creative Setup.")
    return role
