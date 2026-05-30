from __future__ import annotations

from rest_framework.exceptions import PermissionDenied

from organizers.models import Organizer
from team_access.permissions import require_membership


def require_policy_view_access(user, organizer: Organizer):
    role = require_membership(user, organizer.id)
    if not role.can_view_organizer_policies:
        raise PermissionDenied("Owner or Operator access is required.")
    return role


def require_policy_edit_access(user, organizer: Organizer):
    role = require_membership(user, organizer.id)
    if not role.can_manage_organizer_policies:
        raise PermissionDenied("Only Owners can edit Organizer Policies.")
    return role
