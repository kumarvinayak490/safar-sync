from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizers.models import Organizer
from organizers.permissions import require_internal_admin
from team_access.permissions import require_operator_workflow_access, require_owner
from trip_bookings.access_links import resolve_active_access_link
from trip_bookings.models import Booking
from trip_payments.manual_review import (
    PublicQrManualPaymentSubmissionBlocked,
    approve_manual_payment,
    record_sensitive_payment_information_download,
    reject_manual_payment,
)
from trip_payments.models import ManualPayment, PaymentException, PlatformFeeStatement
from trip_payments.serializers import (
    BookingAdjustmentSerializer,
    InternalAdminPlatformFeeStatementManageSerializer,
    InternalAdminPlatformFeeStatementSerializer,
    ManualPaymentDecisionSerializer,
    OperationsManualPaymentSerializer,
    PaymentExceptionResolutionSerializer,
    PaymentExceptionSerializer,
    PublicQrManualPaymentSubmissionSerializer,
    RefundRecordSerializer,
    TravelerManualPaymentSubmissionSerializer,
    error_detail_from_django,
)
from trips.models import Trip


class PublicQrManualPaymentSubmissionView(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, organizer_slug: str, trip_slug: str):
        trip = get_object_or_404(
            Trip.objects.select_related("organizer", "payment_schedule").prefetch_related(
                "packages"
            ),
            organizer__slug=organizer_slug,
            slug=trip_slug,
            publication_state=Trip.PublicationState.PUBLISHED,
        )
        serializer = PublicQrManualPaymentSubmissionSerializer(
            data=request.data,
            context={"trip": trip},
        )
        serializer.is_valid(raise_exception=True)
        try:
            manual_payment = serializer.save()
        except PublicQrManualPaymentSubmissionBlocked as exc:
            raise serializers.ValidationError(exc.detail) from exc
        except DjangoValidationError as exc:
            raise serializers.ValidationError(error_detail_from_django(exc)) from exc
        return Response(OperationsManualPaymentSerializer(manual_payment).data, status=201)


class InternalAdminPlatformFeeStatementListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        require_internal_admin(request.user)
        statements = PlatformFeeStatement.objects.select_related("organizer").all()
        organizer_id = request.query_params.get("organizer")
        status = request.query_params.get("status")
        if organizer_id:
            statements = statements.filter(organizer_id=organizer_id)
        if status:
            statements = statements.filter(status=status)
        return Response(InternalAdminPlatformFeeStatementSerializer(statements, many=True).data)

    def post(self, request):
        require_internal_admin(request.user)
        serializer = InternalAdminPlatformFeeStatementManageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        statement = serializer.save()
        return Response(
            InternalAdminPlatformFeeStatementSerializer(statement).data,
            status=201,
        )


class InternalAdminPlatformFeeStatementDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, statement_id: int):
        require_internal_admin(request.user)
        statement = get_object_or_404(
            PlatformFeeStatement.objects.select_related("organizer"),
            pk=statement_id,
        )
        return Response(InternalAdminPlatformFeeStatementSerializer(statement).data)

    def patch(self, request, statement_id: int):
        require_internal_admin(request.user)
        statement = get_object_or_404(
            PlatformFeeStatement.objects.select_related("organizer"),
            pk=statement_id,
        )
        serializer = InternalAdminPlatformFeeStatementManageSerializer(
            statement,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        statement = serializer.save()
        return Response(InternalAdminPlatformFeeStatementSerializer(statement).data)


class OperationsManualPaymentCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request, organizer_id: int, booking_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        booking = get_object_or_404(
            Booking.objects.select_related("trip", "trip__payment_schedule").prefetch_related(
                "traveler_slots__package", "ledger_entries"
            ),
            pk=booking_id,
            trip__organizer=organizer,
        )
        serializer = OperationsManualPaymentSerializer(
            data=request.data,
            context={"booking": booking, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            manual_payment = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"manual_payment": exc.messages}) from exc
        return Response(OperationsManualPaymentSerializer(manual_payment).data, status=201)


class OperationsManualPaymentApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, manual_payment_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        manual_payment = get_object_or_404(
            ManualPayment.objects.select_related("booking", "booking__trip"),
            pk=manual_payment_id,
            booking__trip__organizer=organizer,
        )
        try:
            manual_payment = approve_manual_payment(
                manual_payment=manual_payment,
                actor=request.user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"manual_payment": exc.messages}) from exc
        return Response(OperationsManualPaymentSerializer(manual_payment).data)


class OperationsManualPaymentRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, manual_payment_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        manual_payment = get_object_or_404(
            ManualPayment.objects.select_related("booking", "booking__trip"),
            pk=manual_payment_id,
            booking__trip__organizer=organizer,
        )
        serializer = ManualPaymentDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            manual_payment = reject_manual_payment(
                manual_payment=manual_payment,
                actor=request.user,
                rejection_reason=serializer.validated_data.get("rejection_reason", ""),
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"manual_payment": exc.messages}) from exc
        return Response(OperationsManualPaymentSerializer(manual_payment).data)


class OperationsManualPaymentProofDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int, manual_payment_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        manual_payment = get_object_or_404(
            ManualPayment.objects.select_related("booking", "booking__trip"),
            pk=manual_payment_id,
            booking__trip__organizer=organizer,
        )
        if not manual_payment.payment_proof:
            raise serializers.ValidationError({"payment_proof": "Payment Proof file is missing."})

        record_sensitive_payment_information_download(
            manual_payment,
            actor=request.user,
        )

        filename = (
            manual_payment.original_filename or manual_payment.payment_proof.name.rsplit("/", 1)[-1]
        )
        return FileResponse(
            manual_payment.payment_proof.open("rb"),
            as_attachment=True,
            filename=filename,
            content_type=manual_payment.content_type or "application/octet-stream",
        )


class OperationsBookingAdjustmentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, booking_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        booking = get_object_or_404(
            Booking.objects.select_related("trip", "trip__payment_schedule").prefetch_related(
                "traveler_slots__package", "ledger_entries"
            ),
            pk=booking_id,
            trip__organizer=organizer,
        )
        serializer = BookingAdjustmentSerializer(
            data=request.data,
            context={"booking": booking, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            booking_adjustment = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"booking_adjustment": exc.messages}) from exc
        return Response(BookingAdjustmentSerializer(booking_adjustment).data, status=201)


class OperationsRefundRecordCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, booking_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        booking = get_object_or_404(
            Booking.objects.select_related("trip", "trip__payment_schedule").prefetch_related(
                "traveler_slots__package", "ledger_entries"
            ),
            pk=booking_id,
            trip__organizer=organizer,
        )
        serializer = RefundRecordSerializer(
            data=request.data,
            context={"booking": booking, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            refund_record = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"refund_record": exc.messages}) from exc
        return Response(RefundRecordSerializer(refund_record).data, status=201)


class OperationsPaymentExceptionResolveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, payment_exception_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        payment_exception = get_object_or_404(
            PaymentException.objects.select_related(
                "booking",
                "booking__trip",
                "payment_attempt",
                "provider_payment",
            ),
            pk=payment_exception_id,
            organizer=organizer,
        )
        serializer = PaymentExceptionResolutionSerializer(
            data=request.data,
            context={"payment_exception": payment_exception, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            payment_exception = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"payment_exception": exc.messages}) from exc
        return Response(PaymentExceptionSerializer(payment_exception).data)


class TravelerPortalManualPaymentSubmissionView(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, token: str):
        access_link = _resolve_access_link_or_error(token)
        serializer = TravelerManualPaymentSubmissionSerializer(
            data=request.data,
            context={"booking": access_link.booking},
        )
        serializer.is_valid(raise_exception=True)
        try:
            manual_payment = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"manual_payment": exc.messages}) from exc
        return Response(OperationsManualPaymentSerializer(manual_payment).data, status=201)


def _resolve_access_link_or_error(token: str):
    try:
        return resolve_active_access_link(token)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"access_link": exc.messages}) from exc
