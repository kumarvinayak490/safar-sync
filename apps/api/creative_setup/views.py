from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from creative_setup.models import CreativeSetup
from creative_setup.permissions import (
    require_creative_setup_edit_access,
    require_creative_setup_view_access,
)
from creative_setup.selectors import creative_setup_for
from creative_setup.serializers import CreativeSetupSerializer
from organizers.models import Organizer


class CreativeSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_creative_setup_view_access(request.user, organizer)

        setup = creative_setup_for(organizer) or CreativeSetup(organizer=organizer)
        serializer = CreativeSetupSerializer(setup)
        return Response(serializer.data)

    def patch(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_creative_setup_edit_access(request.user, organizer)

        setup = creative_setup_for(organizer) or CreativeSetup(organizer=organizer)
        serializer = CreativeSetupSerializer(setup, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
