from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizer_profile.models import OrganizerProfile
from organizer_profile.permissions import (
    require_profile_edit_access,
    require_profile_view_access,
)
from organizer_profile.publication import (
    organizer_profile_for,
    organizer_profile_publication_readiness,
)
from organizer_profile.serializers import OrganizerProfileIdentitySerializer
from organizers.models import Organizer


class OrganizerProfileIdentityView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        role = require_profile_view_access(request.user, organizer)
        serializer = OrganizerProfileIdentitySerializer(
            organizer,
            context={"request": request, "role": role},
        )
        return Response(serializer.data)

    def patch(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        role = require_profile_edit_access(request.user, organizer)
        readiness_error = _profile_publish_readiness_error(organizer, request.data)
        if readiness_error is not None:
            return Response(readiness_error, status=status.HTTP_400_BAD_REQUEST)

        serializer = OrganizerProfileIdentitySerializer(
            organizer,
            data=request.data,
            partial=True,
            context={"request": request, "role": role},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


OrganizerIdentityView = OrganizerProfileIdentityView


def _profile_publish_readiness_error(organizer: Organizer, data) -> dict | None:
    if data.get("publication_state") != OrganizerProfile.PublicationState.PUBLISHED:
        return None

    profile = organizer_profile_for(organizer) or OrganizerProfile(organizer=organizer)
    if "public_description" in data:
        profile.public_description = data.get("public_description", "")

    readiness = organizer_profile_publication_readiness(organizer, profile=profile)
    if readiness.publish_eligible:
        return None

    return {
        "publication_state": ["Organizer Profile is not ready to publish."],
        "organizer_profile_readiness": readiness.to_payload(),
    }
