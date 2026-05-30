from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizer_policies.models import OrganizerPolicies
from organizer_policies.permissions import (
    require_policy_edit_access,
    require_policy_view_access,
)
from organizer_policies.readiness import organizer_policies_for
from organizer_policies.serializers import OrganizerPoliciesSerializer
from organizers.models import Organizer


class OrganizerPoliciesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_policy_view_access(request.user, organizer)

        policies = organizer_policies_for(organizer) or OrganizerPolicies(organizer=organizer)
        serializer = OrganizerPoliciesSerializer(policies)
        return Response(serializer.data)

    def patch(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_policy_edit_access(request.user, organizer)

        policies = organizer_policies_for(organizer, create=True)
        serializer = OrganizerPoliciesSerializer(
            policies,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
