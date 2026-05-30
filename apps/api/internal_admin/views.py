from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from internal_admin.permissions import IsInternalAdminStaff
from internal_admin.shell import build_internal_admin_shell_payload
from public_discovery.models import DemandPage
from public_discovery.serializers import DemandPageAdminSerializer
from trip_payments import internal_admin_review
from trip_payments.serializers import (
    InternalAdminPaymentExceptionResolutionSerializer,
    InternalAdminPaymentExceptionSerializer,
    InternalAdminPlatformFeeStatementManageSerializer,
    InternalAdminPlatformFeeStatementSerializer,
    error_detail_from_django,
)


class InternalAdminShellView(APIView):
    permission_classes = [IsInternalAdminStaff]

    def get(self, request):
        return Response(build_internal_admin_shell_payload(request.user))


class InternalAdminPlatformFeeStatementListCreateView(APIView):
    permission_classes = [IsInternalAdminStaff]

    def get(self, request):
        statements = internal_admin_review.platform_fee_statement_review_queryset()
        organizer_id = request.query_params.get("organizer")
        status = request.query_params.get("status")
        if organizer_id:
            statements = statements.filter(organizer_id=organizer_id)
        if status:
            statements = statements.filter(status=status)
        return Response(InternalAdminPlatformFeeStatementSerializer(statements, many=True).data)

    def post(self, request):
        serializer = InternalAdminPlatformFeeStatementManageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            statement = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(error_detail_from_django(exc)) from exc
        return Response(
            InternalAdminPlatformFeeStatementSerializer(statement).data,
            status=201,
        )


class InternalAdminPlatformFeeStatementDetailView(APIView):
    permission_classes = [IsInternalAdminStaff]

    def get(self, request, statement_id: int):
        statement = get_object_or_404(
            internal_admin_review.platform_fee_statement_review_queryset(),
            pk=statement_id,
        )
        return Response(InternalAdminPlatformFeeStatementSerializer(statement).data)

    def patch(self, request, statement_id: int):
        statement = get_object_or_404(
            internal_admin_review.platform_fee_statement_review_queryset(),
            pk=statement_id,
        )
        serializer = InternalAdminPlatformFeeStatementManageSerializer(
            statement,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        try:
            statement = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(error_detail_from_django(exc)) from exc
        return Response(InternalAdminPlatformFeeStatementSerializer(statement).data)


class InternalAdminPaymentExceptionListView(APIView):
    permission_classes = [IsInternalAdminStaff]

    def get(self, request):
        payment_exceptions = internal_admin_review.payment_exception_review_queryset()
        organizer_id = request.query_params.get("organizer")
        trip_id = request.query_params.get("trip")
        booking_id = request.query_params.get("booking")
        status = request.query_params.get("status")
        exception_type = request.query_params.get("exception_type")
        if organizer_id:
            payment_exceptions = payment_exceptions.filter(organizer_id=organizer_id)
        if trip_id:
            payment_exceptions = payment_exceptions.filter(trip_id=trip_id)
        if booking_id:
            payment_exceptions = payment_exceptions.filter(booking_id=booking_id)
        if status:
            payment_exceptions = payment_exceptions.filter(status=status)
        if exception_type:
            payment_exceptions = payment_exceptions.filter(exception_type=exception_type)
        return Response(InternalAdminPaymentExceptionSerializer(payment_exceptions, many=True).data)


class InternalAdminPaymentExceptionDetailView(APIView):
    permission_classes = [IsInternalAdminStaff]

    def get(self, request, payment_exception_id: int):
        payment_exception = get_object_or_404(
            internal_admin_review.payment_exception_review_queryset(),
            pk=payment_exception_id,
        )
        return Response(InternalAdminPaymentExceptionSerializer(payment_exception).data)


class InternalAdminPaymentExceptionResolveView(APIView):
    permission_classes = [IsInternalAdminStaff]

    def post(self, request, payment_exception_id: int):
        payment_exception = get_object_or_404(
            internal_admin_review.payment_exception_review_queryset(),
            pk=payment_exception_id,
        )
        serializer = InternalAdminPaymentExceptionResolutionSerializer(
            data=request.data,
            context={"payment_exception": payment_exception, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            payment_exception = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"payment_exception": exc.messages}) from exc
        return Response(InternalAdminPaymentExceptionSerializer(payment_exception).data)


class InternalAdminDemandPageListCreateView(APIView):
    permission_classes = [IsInternalAdminStaff]

    def get(self, request):
        demand_pages = DemandPage.objects.prefetch_related(
            "selected_organizers",
            "selected_trips",
        ).order_by("slug", "id")
        return Response(
            DemandPageAdminSerializer(demand_pages, many=True).data,
        )

    def post(self, request):
        serializer = DemandPageAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        demand_page = serializer.save()
        return Response(DemandPageAdminSerializer(demand_page).data, status=201)


class InternalAdminDemandPageDetailView(APIView):
    permission_classes = [IsInternalAdminStaff]

    def get(self, request, demand_page_id: int):
        demand_page = get_object_or_404(
            DemandPage.objects.prefetch_related(
                "selected_organizers",
                "selected_trips",
            ),
            pk=demand_page_id,
        )
        return Response(DemandPageAdminSerializer(demand_page).data)

    def patch(self, request, demand_page_id: int):
        demand_page = get_object_or_404(
            DemandPage.objects.prefetch_related(
                "selected_organizers",
                "selected_trips",
            ),
            pk=demand_page_id,
        )
        serializer = DemandPageAdminSerializer(
            demand_page,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        demand_page = serializer.save()
        return Response(DemandPageAdminSerializer(demand_page).data)
