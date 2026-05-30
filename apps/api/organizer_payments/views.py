from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizer_payments.manual_payment_instructions import (
    manual_payment_instructions_payload,
)
from organizer_payments.models import ManualPaymentInstructions
from organizer_payments.serializers import ManualPaymentInstructionsSerializer
from organizers.models import Organizer
from team_access.permissions import require_owner, require_payment_status_access


class ManualPaymentInstructionsView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        role = require_payment_status_access(request.user, organizer)
        return Response(
            manual_payment_instructions_payload(
                organizer,
                request=request,
                can_manage=role.can_manage_payment_setup,
            )
        )

    def patch(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        try:
            instructions = organizer.manual_payment_instructions
        except ManualPaymentInstructions.DoesNotExist:
            instructions = ManualPaymentInstructions(organizer=organizer)
        serializer = ManualPaymentInstructionsSerializer(
            instructions,
            data=request.data,
            partial=True,
            context={"request": request, "can_manage": True},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        try:
            instructions = organizer.manual_payment_instructions
        except ManualPaymentInstructions.DoesNotExist:
            return Response(status=status.HTTP_204_NO_CONTENT)

        payment_qr_name = instructions.payment_qr.name if instructions.payment_qr else ""
        storage = instructions.payment_qr.storage if instructions.payment_qr else None
        instructions.delete()
        if payment_qr_name and storage is not None:
            storage.delete(payment_qr_name)
        return Response(status=status.HTTP_204_NO_CONTENT)
