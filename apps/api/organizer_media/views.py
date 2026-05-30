from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizer_media.serializers import (
    OrganizerMediaLibrarySerializer,
    OrganizerMediaUploadSerializer,
)
from organizers.models import Organizer
from team_access.permissions import require_operator_workflow_access, require_owner


class OrganizerMediaLibraryView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        return Response(
            OrganizerMediaLibrarySerializer(
                organizer,
                context={"organizer": organizer, "request": request},
            ).data
        )

    def post(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)

        images = request.FILES.getlist("images")
        serializer = OrganizerMediaUploadSerializer(
            data={"images": images},
            context={"organizer": organizer, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        organizer.refresh_from_db()
        return Response(
            OrganizerMediaLibrarySerializer(
                organizer,
                context={"organizer": organizer, "request": request},
            ).data,
            status=201,
        )

    def patch(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)

        serializer = OrganizerMediaLibrarySerializer(
            data=request.data,
            context={"organizer": organizer, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        organizer = serializer.save()
        return Response(
            OrganizerMediaLibrarySerializer(
                organizer,
                context={"organizer": organizer, "request": request},
            ).data
        )
