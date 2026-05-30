"""DRF views for the legacy Organizer API integration surface.

The Organizer app keeps URL/API compatibility here while concrete business
behavior moves to domain apps such as Team Access, Trips, and Payments.
"""

from __future__ import annotations

from django.contrib.auth import login, logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse, HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import NotAuthenticated, NotFound, PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizer_media.views import OrganizerMediaLibraryView  # noqa: F401
from organizer_payments.payment_setup_readiness import payment_setup_status_payload
from organizer_payments.provider_account_readiness import support_confirm_settlement_readiness
from organizer_payments.provider_authorization import (
    ProviderAccountReplacementError,
    ProviderAuthorizationExchangeError,
    ProviderAuthorizationStateError,
    complete_provider_authorization,
    confirm_provider_account_replacement,
    disconnect_provider_authorization,
    start_provider_authorization,
)
from organizer_payments.provider_connection_tests import run_provider_connection_test
from organizer_payments.provider_credentials import (
    SensitiveProviderCredentialStore,
    configure_assisted_api_key_credentials,
)
from organizer_payments.views import ManualPaymentInstructionsView  # noqa: F401
from organizer_profile.views import OrganizerIdentityView  # noqa: F401
from organizers.models import (
    Booking,
    Organizer,
    OrganizerInvitation,
    PaymentAttempt,
    PaymentException,
    ProviderConnectionTestResult,
    TravelerDocument,
    TravelerSlot,
    Trip,
    TripPaymentSchedule,
)
from organizers.onboarding.session import (
    anonymous_onboarding_payload,
    session_onboarding_payload,
)
from organizers.permissions import require_internal_admin
from organizers.serializers import (
    AccessLinkIssueSerializer,
    AnnouncementSerializer,
    BalancePaymentLinkSendSerializer,
    BookingCancellationSerializer,
    BookingContactUpdateSerializer,
    BrowserCheckoutSuccessSerializer,
    EmergencyContactSerializer,
    InternalAdminAssistedPaymentSetupSerializer,
    InternalAdminBookingSerializer,
    InternalAdminOrganizerDetailSerializer,
    InternalAdminOrganizerListSerializer,
    InternalAdminSettlementReadinessConfirmSerializer,
    InternalAdminTripSerializer,
    LoginSerializer,
    ManualReminderSerializer,
    MedicalDisclosureSerializer,
    NotificationSerializer,
    OperationsBookingDetailSerializer,
    OperationsBookingImportResultSerializer,
    OperationsBookingImportSubmitSerializer,
    OperationsManualBookingCreateSerializer,
    OrganizerInvitationCreateSerializer,
    OrganizerInvitationSerializer,
    OrganizerOnboardingSerializer,
    PaymentExceptionSerializer,
    PayoutAccountSerializer,
    ProviderAccountReplacementConfirmSerializer,
    ProviderAuthorizationCallbackSerializer,
    ProviderAuthorizationStartSerializer,
    ProviderConnectionTestResultSerializer,
    ProviderPaymentConfirmationSerializer,
    ProviderPaymentSerializer,
    ProviderPaymentSetupSerializer,
    PublicDraftBookingSerializer,
    PublicPaymentAttemptSerializer,
    PublicTripSerializer,
    SignupSerializer,
    TravelerAdditionSerializer,
    TravelerCancellationSerializer,
    TravelerDocumentReviewSerializer,
    TravelerDocumentSerializer,
    TravelerDocumentSubmissionSerializer,
    TravelerIdentitySerializer,
    TravelerPackageChangeSerializer,
    TravelerPortalSerializer,
    TravelerReplacementSerializer,
    TravelLogisticsSerializer,
    TripCancellationSerializer,
    TripCompletionSerializer,
    TripConfirmationRequirementsSectionSerializer,
    TripDateChangeSerializer,
    TripDescriptionSerializer,
    TripDuplicateSerializer,
    TripItinerarySectionSerializer,
    TripMediaGallerySerializer,
    TripMediaUploadSerializer,
    TripPackageSectionSerializer,
    TripPaymentScheduleSectionSerializer,
    TripSetupSerializer,
    UserSessionSerializer,
)
from organizers.services import (
    cancel_trip,
    complete_trip,
    confirm_booking,
    ensure_payment_setup_records,
    is_provider_payment_setup_complete,
    mark_traveler_attendance,
    online_payment_readiness,
    organizer_payment_method_readiness,
    public_booking_readiness,
    unconfirm_booking,
)
from team_access.invitations import (
    accept_organizer_invitation,
    invitation_public_payload,
    resend_organizer_invitation,
    revoke_organizer_invitation,
    team_access_payload,
)
from team_access.permissions import (
    require_operator_workflow_access,
    require_owner,
    require_payment_status_access,
    require_trip_content_access,
    require_trip_creation_access,
)
from trip_bookings.access_links import (
    resolve_active_access_link,
)
from trip_bookings.access_links import (
    traveler_slot_for_access_link as resolve_traveler_slot_for_access_link,
)
from trip_bookings.imports import parse_booking_import_upload
from trip_operations.dashboard import build_operations_dashboard_payload
from trip_operations.exports import generate_operational_export_csv
from trip_operations.serializers import (
    OperationalExportOptionsSerializer,
    OperationsBookingListItemSerializer,
)
from trip_operations.trip_overview import build_trip_overview_payload
from trip_payments.provider_payment_lifecycle import (
    confirm_provider_payment,
    create_balance_payment_checkout,
    create_public_reservation_checkout,
    process_browser_checkout_success,
)
from trip_payments.provider_webhooks import (
    ProviderWebhookProcessingResult,
    process_razorpay_webhook,
)
from trip_payments.views import (  # noqa: F401
    InternalAdminPlatformFeeStatementDetailView,
    InternalAdminPlatformFeeStatementListCreateView,
    OperationsBookingAdjustmentCreateView,
    OperationsManualPaymentApproveView,
    OperationsManualPaymentCreateView,
    OperationsManualPaymentProofDownloadView,
    OperationsManualPaymentRejectView,
    OperationsPaymentExceptionResolveView,
    OperationsRefundRecordCreateView,
    PublicQrManualPaymentSubmissionView,
    TravelerPortalManualPaymentSubmissionView,
)
from trip_travelers.documents import record_sensitive_traveler_document_download
from trips.activity import (
    confirmation_requirements_snapshot,
    payment_schedule_snapshot,
    record_trip_confirmation_requirements_update_if_changed,
    record_trip_description_update_if_changed,
    record_trip_itinerary_update_if_changed,
    record_trip_media_gallery_update_if_changed,
    record_trip_media_upload,
    record_trip_package_update_if_changed,
    record_trip_payment_schedule_update_if_changed,
    trip_itinerary_day_snapshot,
    trip_itinerary_submission_snapshot,
    trip_media_item_snapshot,
    trip_media_submission_snapshot,
    trip_package_snapshot,
    trip_package_submission_change,
)
from trips.locks import is_trip_profile_locked, published_trip_profile_lock_message
from trips.selectors import get_trip_profile_for_organizer_id


def session_payload(user) -> dict:
    return {
        "authenticated": True,
        "user": UserSessionSerializer(user).data,
        "onboarding": session_onboarding_payload(user),
    }


def anonymous_session_payload() -> dict:
    return {
        "authenticated": False,
        "user": None,
        "onboarding": anonymous_onboarding_payload(),
    }


def django_validation_detail(exc: DjangoValidationError):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return exc.messages


def provider_webhook_result_payload(result: ProviderWebhookProcessingResult) -> dict:
    lifecycle_result = result.lifecycle_result
    return {
        "provider": result.webhook_event.provider,
        "event_reference": result.webhook_event.provider_event_reference,
        "event_type": result.webhook_event.event_type,
        "processing_status": result.webhook_event.processing_status,
        "ignored_reason": result.webhook_event.ignored_reason,
        "duplicate": result.duplicate,
        "payment_attempt": (
            result.payment_attempt.id if result.payment_attempt is not None else None
        ),
        "provider_payment": (
            result.provider_payment.id if result.provider_payment is not None else None
        ),
        "payment_exception": (
            result.payment_exception.id if result.payment_exception is not None else None
        ),
        "lifecycle": (
            {
                "authorization_state": lifecycle_result.provider_setup.authorization_state,
                "provider_connection_state": (
                    lifecycle_result.provider_setup.provider_connection_state
                ),
                "revoked_credentials": lifecycle_result.revoked_credentials,
                "closed_public_booking_trips": lifecycle_result.closed_public_booking_trips,
                "deactivated_payment_attempts": lifecycle_result.deactivated_payment_attempts,
                "released_seat_holds": lifecycle_result.released_seat_holds,
            }
            if lifecycle_result is not None
            else None
        ),
    }


class SignupView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        get_token(request)
        return Response(session_payload(user), status=201)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        get_token(request)
        return Response(session_payload(user))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=204)


class CurrentSessionView(APIView):
    permission_classes = []

    def get(self, request):
        if not request.user.is_authenticated:
            return Response(anonymous_session_payload())
        get_token(request)
        return Response(session_payload(request.user))


class OrganizerOnboardingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.organizer_memberships.exists():
            raise PermissionDenied(
                "Organizer onboarding is only available before your User belongs to an Organizer."
            )

        serializer = OrganizerOnboardingSerializer(
            data=request.data,
            context={"user": request.user},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(session_payload(request.user), status=201)


class OperationsDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organizer_id = request.query_params.get("organizer")
        payload = build_operations_dashboard_payload(
            request.user,
            int(organizer_id) if organizer_id else None,
        )
        return Response(payload)


class OperationsTripOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int, trip_id: int):
        return Response(build_trip_overview_payload(request.user, organizer_id, trip_id))


class InternalAdminOrganizerListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        require_internal_admin(request.user)
        organizers = (
            Organizer.objects.select_related(
                "payout_account",
                "provider_payment_setup",
            )
            .prefetch_related("trips")
            .all()
        )
        return Response(InternalAdminOrganizerListSerializer(organizers, many=True).data)


class InternalAdminOrganizerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int):
        require_internal_admin(request.user)
        organizer = get_object_or_404(
            Organizer.objects.select_related(
                "payout_account",
                "provider_payment_setup",
            ).prefetch_related(*internal_admin_organizer_prefetches()),
            pk=organizer_id,
        )
        return Response(InternalAdminOrganizerDetailSerializer(organizer).data)


class InternalAdminAssistedPaymentSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int):
        require_internal_admin(request.user)
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        serializer = InternalAdminAssistedPaymentSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credential = configure_assisted_api_key_credentials(
            organizer=organizer,
            actor=request.user,
            key_id=serializer.validated_data["key_id"],
            key_secret=serializer.validated_data["key_secret"],
            webhook_secret=serializer.validated_data.get("webhook_secret", ""),
            provider_account_reference=serializer.validated_data["provider_account_reference"],
            provider_mode=serializer.validated_data["provider_mode"],
            scopes=serializer.validated_data.get("scopes", []),
            expires_at=serializer.validated_data.get("expires_at"),
        )
        organizer.refresh_from_db()
        return Response(
            {
                "payment_setup": payment_setup_status_payload(organizer),
                "credential": SensitiveProviderCredentialStore().safe_summary(credential),
            },
            status=status.HTTP_201_CREATED,
        )


class InternalAdminSettlementReadinessConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int):
        require_internal_admin(request.user)
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        serializer = InternalAdminSettlementReadinessConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = support_confirm_settlement_readiness(
                organizer=organizer,
                actor=request.user,
                notes=serializer.validated_data.get("notes", ""),
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(django_validation_detail(exc)) from exc
        organizer.refresh_from_db()
        return Response(
            {
                "payment_setup": payment_setup_status_payload(organizer),
                "readiness_regression": result.to_payload(),
            }
        )


class InternalAdminProviderConnectionTestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int):
        require_internal_admin(request.user)
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        results = provider_connection_test_results_for(organizer)
        return Response(ProviderConnectionTestResultSerializer(results, many=True).data)

    def post(self, request, organizer_id: int):
        require_internal_admin(request.user)
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        try:
            result = run_provider_connection_test(
                organizer=organizer,
                actor=request.user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(django_validation_detail(exc)) from exc
        return Response(ProviderConnectionTestResultSerializer(result).data, status=201)


class InternalAdminTripDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id: int):
        require_internal_admin(request.user)
        trip = get_object_or_404(
            Trip.objects.select_related(
                "organizer",
                "payment_schedule",
            ).prefetch_related(*internal_admin_trip_prefetches()),
            pk=trip_id,
        )
        return Response(InternalAdminTripSerializer(trip).data)


class InternalAdminBookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id: int):
        require_internal_admin(request.user)
        booking = get_object_or_404(
            Booking.objects.select_related(
                "trip",
                "trip__organizer",
                "trip__payment_schedule",
            ).prefetch_related(*internal_admin_booking_prefetches()),
            pk=booking_id,
        )
        return Response(InternalAdminBookingSerializer(booking).data)


class OrganizerTeamAccessView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        return Response(team_access_payload(organizer))

    def post(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        serializer = OrganizerInvitationCreateSerializer(
            data=request.data,
            context={"organizer": organizer, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()
        return Response(OrganizerInvitationSerializer(invitation).data, status=201)


class OrganizerInvitationResendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, invitation_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        invitation = get_object_or_404(
            OrganizerInvitation,
            pk=invitation_id,
            organizer=organizer,
        )
        try:
            resend_organizer_invitation(invitation)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(django_validation_detail(exc)) from exc
        return Response(OrganizerInvitationSerializer(invitation).data)


class OrganizerInvitationRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, invitation_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        invitation = get_object_or_404(
            OrganizerInvitation,
            pk=invitation_id,
            organizer=organizer,
        )
        try:
            revoke_organizer_invitation(invitation)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(django_validation_detail(exc)) from exc
        return Response(OrganizerInvitationSerializer(invitation).data)


class OrganizerInvitationAcceptView(APIView):
    permission_classes = []

    def get(self, request, token: str):
        invitation = (
            OrganizerInvitation.objects.select_related("organizer").filter(token=token).first()
        )
        if invitation is None:
            raise NotFound("Organizer Invitation was not found.")
        return Response(invitation_public_payload(invitation))

    def post(self, request, token: str):
        if not request.user.is_authenticated:
            raise NotAuthenticated("Log in or create your User before accepting.")
        try:
            invitation, membership = accept_organizer_invitation(
                token=token,
                user=request.user,
            )
        except OrganizerInvitation.DoesNotExist as exc:
            raise NotFound("Organizer Invitation was not found.") from exc
        except DjangoValidationError as exc:
            raise serializers.ValidationError(django_validation_detail(exc)) from exc

        return Response(
            {
                "invitation": invitation_public_payload(invitation),
                "membership": {
                    "id": membership.id,
                    "role": membership.role,
                    "role_label": membership.get_role_display(),
                    "organizer": membership.organizer_id,
                },
                "session": session_payload(request.user),
            }
        )


class OperatorWorkflowAccessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        role = require_operator_workflow_access(request.user, organizer)

        return Response(
            {
                "ok": True,
                "organizer": organizer.id,
                "role": role.role,
            }
        )


class PayoutAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        ensure_payment_setup_records(organizer)
        return Response(PayoutAccountSerializer(organizer.payout_account).data)

    def patch(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        return Response(
            {
                "detail": (
                    "Settlement Readiness is provider-derived and cannot be "
                    "edited from organizer-facing Payment Setup."
                )
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class ProviderPaymentSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        ensure_payment_setup_records(organizer)
        return Response(ProviderPaymentSetupSerializer(organizer.provider_payment_setup).data)

    def patch(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        return Response(
            {
                "detail": (
                    "Provider-derived Payment Setup facts are read-only. Use "
                    "Provider Authorization actions to change the connection."
                )
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class PaymentSetupStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        role = require_payment_status_access(request.user, organizer)
        return Response(
            payment_setup_status_payload(
                organizer,
                can_manage_provider_authorization=role.can_manage_payment_setup,
            )
        )


class ProviderConnectionTestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        results = provider_connection_test_results_for(organizer)
        return Response(ProviderConnectionTestResultSerializer(results, many=True).data)

    def post(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        try:
            result = run_provider_connection_test(
                organizer=organizer,
                actor=request.user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(django_validation_detail(exc)) from exc
        return Response(ProviderConnectionTestResultSerializer(result).data, status=201)


class ProviderAuthorizationStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        serializer = ProviderAuthorizationStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            started = start_provider_authorization(
                organizer=organizer,
                actor=request.user,
                request=request,
                provider_mode=serializer.validated_data.get("provider_mode"),
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(django_validation_detail(exc)) from exc
        organizer.refresh_from_db()
        return Response(
            {
                "provider": started.session.provider,
                "provider_mode": started.session.provider_mode,
                "authorization_url": started.authorization_url,
                "state": started.state,
                "expires_at": started.session.expires_at,
                "payment_setup": payment_setup_status_payload(
                    organizer,
                    can_manage_provider_authorization=True,
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class ProviderAuthorizationCallbackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int):
        return self._complete(request, organizer_id, data=request.query_params)

    def post(self, request, organizer_id: int):
        return self._complete(request, organizer_id, data=request.data)

    def _complete(self, request, organizer_id: int, *, data):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        if data.get("error"):
            raise serializers.ValidationError(
                {"provider": "Provider Authorization was not approved."}
            )
        serializer = ProviderAuthorizationCallbackSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        try:
            completion = complete_provider_authorization(
                organizer=organizer,
                actor=request.user,
                state=serializer.validated_data["state"],
                code=serializer.validated_data["code"],
            )
        except ProviderAuthorizationStateError as exc:
            raise serializers.ValidationError({"state": str(exc)}) from exc
        except ProviderAuthorizationExchangeError as exc:
            raise serializers.ValidationError({"code": str(exc)}) from exc
        except DjangoValidationError as exc:
            raise serializers.ValidationError(django_validation_detail(exc)) from exc
        organizer.refresh_from_db()
        response_payload = {
            "provider": completion.session.provider,
            "provider_mode": completion.session.provider_mode,
            "provider_authorization_session": completion.session.id,
            "provider_account_reference": completion.provider_account_reference,
            "provider_authorization_state": completion.provider_setup.authorization_state,
            "provider_connection_state": completion.provider_setup.provider_connection_state,
            "replacement_required": completion.replacement_required,
            "payment_setup": payment_setup_status_payload(
                organizer,
                can_manage_provider_authorization=True,
            ),
        }
        if completion.lifecycle_result is not None:
            response_payload["lifecycle"] = provider_authorization_lifecycle_payload(
                completion.lifecycle_result
            )
        if completion.replacement_required:
            response_payload["detail"] = (
                "A different connected provider account was authorized. "
                "Replacement confirmation is required before TripOS can use it."
            )
            return Response(response_payload, status=status.HTTP_409_CONFLICT)
        return Response(response_payload)


class ProviderAuthorizationDisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        result = disconnect_provider_authorization(
            organizer=organizer,
            actor=request.user,
        )
        organizer.refresh_from_db()
        return Response(
            {
                "provider_authorization_state": result.provider_setup.authorization_state,
                "provider_connection_state": result.provider_setup.provider_connection_state,
                "lifecycle": provider_authorization_lifecycle_payload(result),
                "payment_setup": payment_setup_status_payload(
                    organizer,
                    can_manage_provider_authorization=True,
                ),
            }
        )


class ProviderAccountReplacementConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, session_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        serializer = ProviderAccountReplacementConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            confirmation = confirm_provider_account_replacement(
                organizer=organizer,
                actor=request.user,
                session_id=session_id,
            )
        except ProviderAccountReplacementError as exc:
            raise serializers.ValidationError({"replacement": str(exc)}) from exc
        organizer.refresh_from_db()
        return Response(
            {
                "provider": confirmation.session.provider,
                "provider_mode": confirmation.session.provider_mode,
                "provider_authorization_session": confirmation.session.id,
                "provider_account_reference": (
                    confirmation.provider_setup.provider_merchant_reference
                ),
                "provider_authorization_state": (confirmation.provider_setup.authorization_state),
                "provider_connection_state": (
                    confirmation.provider_setup.provider_connection_state
                ),
                "replacement_confirmed": True,
                "lifecycle": provider_authorization_lifecycle_payload(
                    confirmation.lifecycle_result
                ),
                "payment_setup": payment_setup_status_payload(
                    organizer,
                    can_manage_provider_authorization=True,
                ),
            }
        )


def provider_authorization_lifecycle_payload(result) -> dict[str, int]:
    return {
        "revoked_credentials": result.revoked_credentials,
        "closed_public_booking_trips": result.closed_public_booking_trips,
        "deactivated_payment_attempts": result.deactivated_payment_attempts,
        "released_seat_holds": result.released_seat_holds,
    }


class TripSetupListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_trip_content_access(request.user, organizer)
        trips = (
            organizer.trips.select_related("organizer", "payment_schedule")
            .prefetch_related("packages", "itinerary_days", "media_items__asset")
            .all()
        )
        return Response(TripSetupSerializer(trips, many=True).data)

    def post(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        role = require_trip_creation_access(request.user, organizer)
        serializer = TripSetupSerializer(
            data=request.data,
            context={"organizer": organizer, "role": role},
        )
        serializer.is_valid(raise_exception=True)
        trip = serializer.save()
        return Response(TripSetupSerializer(trip).data, status=201)


class TripSetupDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_trip_content_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        return Response(TripSetupSerializer(trip).data)

    def patch(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        role = require_trip_content_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        serializer = TripSetupSerializer(
            trip,
            data=request.data,
            partial=True,
            context={"organizer": organizer, "role": role, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        trip = serializer.save()
        return Response(TripSetupSerializer(trip).data)


class TripDescriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_trip_content_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        return Response(TripDescriptionSerializer(trip).data)

    def patch(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_trip_content_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        if is_trip_profile_locked(trip):
            raise serializers.ValidationError(
                {
                    "description_rich_text": (
                        published_trip_profile_lock_message("Trip Description")
                    )
                }
            )

        previous_description = trip.description_rich_text
        serializer = TripDescriptionSerializer(trip, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        next_description = serializer.validated_data.get(
            "description_rich_text",
            previous_description,
        )
        trip = serializer.save()

        record_trip_description_update_if_changed(
            trip=trip,
            actor=request.user,
            previous_description=previous_description,
            next_description=next_description,
        )

        return Response(TripDescriptionSerializer(trip).data)


class TripItineraryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_trip_content_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        return Response(TripItinerarySectionSerializer(trip, context={"trip": trip}).data)

    def patch(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_trip_content_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        if is_trip_profile_locked(trip):
            raise serializers.ValidationError(
                {
                    "itinerary_days": (
                        published_trip_profile_lock_message("Itinerary Day")
                    )
                }
            )

        previous_days = trip_itinerary_day_snapshot(trip)
        serializer = TripItinerarySectionSerializer(
            data=request.data,
            context={"trip": trip},
        )
        serializer.is_valid(raise_exception=True)
        next_days = trip_itinerary_submission_snapshot(
            serializer.validated_data["itinerary_days"]
        )
        trip = serializer.save()

        record_trip_itinerary_update_if_changed(
            trip=trip,
            actor=request.user,
            previous_days=previous_days,
            next_days=next_days,
        )

        trip = get_trip_for_organizer(organizer, trip_id)
        return Response(TripItinerarySectionSerializer(trip, context={"trip": trip}).data)


class TripMediaGalleryView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_trip_content_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        return Response(
            TripMediaGallerySerializer(
                trip,
                context={"trip": trip, "request": request},
            ).data
        )

    def post(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_trip_content_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)

        previous_item_count = trip.media_items.count()
        images = request.FILES.getlist("images")
        serializer = TripMediaUploadSerializer(
            data={"images": images},
            context={"trip": trip, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        created_items = serializer.save()
        record_trip_media_upload(
            trip=trip,
            actor=request.user,
            previous_item_count=previous_item_count,
            uploaded_item_count=len(created_items),
        )
        trip = get_trip_for_organizer(organizer, trip_id)
        return Response(
            TripMediaGallerySerializer(
                trip,
                context={"trip": trip, "request": request},
            ).data,
            status=201,
        )

    def patch(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_trip_content_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)

        previous_items = trip_media_item_snapshot(trip)
        serializer = TripMediaGallerySerializer(
            data=request.data,
            context={"trip": trip, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        next_items = trip_media_submission_snapshot(serializer.validated_data["media_items"])
        trip = serializer.save()
        record_trip_media_gallery_update_if_changed(
            trip=trip,
            actor=request.user,
            previous_items=previous_items,
            next_items=next_items,
        )
        trip = get_trip_for_organizer(organizer, trip.id)
        return Response(
            TripMediaGallerySerializer(
                trip,
                context={"trip": trip, "request": request},
            ).data
        )


class TripPackageSectionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_trip_content_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        return Response(TripPackageSectionSerializer(trip, context={"trip": trip}).data)

    def patch(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        role = require_trip_content_access(request.user, organizer)
        if not role.can_manage_trip_commercial_terms:
            raise PermissionDenied("Only Owners can manage Package commercial terms.")

        trip = get_trip_for_organizer(organizer, trip_id)
        if is_trip_profile_locked(trip):
            raise serializers.ValidationError(
                {"packages": published_trip_profile_lock_message("Package")}
            )

        previous_packages = trip_package_snapshot(trip)
        serializer = TripPackageSectionSerializer(
            data=request.data,
            context={"trip": trip},
        )
        serializer.is_valid(raise_exception=True)
        submitted_packages = serializer.validated_data["packages"]
        package_change = trip_package_submission_change(
            trip=trip,
            previous_packages=previous_packages,
            submitted_packages=submitted_packages,
        )
        try:
            trip = serializer.save()
        except serializers.ValidationError:
            raise
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"packages": django_validation_detail(exc)}) from exc

        record_trip_package_update_if_changed(
            trip=trip,
            actor=request.user,
            previous_packages=previous_packages,
            submitted_packages=submitted_packages,
            change=package_change,
        )

        trip = get_trip_for_organizer(organizer, trip_id)
        return Response(TripPackageSectionSerializer(trip, context={"trip": trip}).data)


class TripPaymentScheduleSectionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_trip_content_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        schedule, _ = TripPaymentSchedule.objects.get_or_create(trip=trip)
        return Response(TripPaymentScheduleSectionSerializer(schedule).data)

    def patch(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        role = require_trip_content_access(request.user, organizer)
        if not role.can_manage_trip_commercial_terms:
            raise PermissionDenied("Only Owners can manage balance payment terms.")

        trip = get_trip_for_organizer(organizer, trip_id)
        if is_trip_profile_locked(trip):
            raise serializers.ValidationError(
                {
                    "payment_schedule": (
                        published_trip_profile_lock_message("balance payment schedule")
                    )
                }
            )

        schedule, _ = TripPaymentSchedule.objects.get_or_create(trip=trip)
        previous_schedule = payment_schedule_snapshot(schedule)
        serializer = TripPaymentScheduleSectionSerializer(
            schedule,
            data=request.data,
            partial=True,
            context={"actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        schedule = serializer.save()
        next_schedule = payment_schedule_snapshot(schedule)
        record_trip_payment_schedule_update_if_changed(
            trip=trip,
            actor=request.user,
            previous_schedule=previous_schedule,
            next_schedule=next_schedule,
        )
        return Response(TripPaymentScheduleSectionSerializer(schedule).data)


class TripConfirmationRequirementsSectionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_trip_content_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        return Response(TripConfirmationRequirementsSectionSerializer(trip).data)

    def patch(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_trip_content_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        if is_trip_profile_locked(trip):
            raise serializers.ValidationError(
                {
                    "confirmation_requirements": (
                        published_trip_profile_lock_message("Confirmation Requirements")
                    )
                }
            )

        previous_requirements = confirmation_requirements_snapshot(trip)
        serializer = TripConfirmationRequirementsSectionSerializer(
            trip,
            data=request.data,
            partial=True,
            context={"actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        trip = serializer.save()
        next_requirements = confirmation_requirements_snapshot(trip)
        record_trip_confirmation_requirements_update_if_changed(
            trip=trip,
            actor=request.user,
            previous_requirements=previous_requirements,
            next_requirements=next_requirements,
        )
        return Response(TripConfirmationRequirementsSectionSerializer(trip).data)


class TripDuplicateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_trip_content_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        serializer = TripDuplicateSerializer(
            data=request.data,
            context={"trip": trip, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            duplicate = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"trip_duplicate": exc.messages}) from exc
        return Response(TripSetupSerializer(duplicate).data, status=201)


class TripDateChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        trip = get_trip_for_organizer(organizer, trip_id)
        if is_trip_profile_locked(trip):
            raise serializers.ValidationError(
                {"trip_date_change": published_trip_profile_lock_message("Trip Date")}
            )
        if trip.bookings.exists():
            require_owner(request.user, organizer)
        else:
            require_trip_content_access(request.user, organizer)
        serializer = TripDateChangeSerializer(
            data=request.data,
            context={"trip": trip, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            trip = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"trip_date_change": exc.messages}) from exc
        return Response(TripSetupSerializer(trip).data)


class TripCancellationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_owner(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        serializer = TripCancellationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            trip = cancel_trip(
                trip,
                cancellation_reason=serializer.validated_data["cancellation_reason"],
                actor=request.user,
                send_notice=serializer.validated_data.get("send_cancellation_notice", True),
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"trip_cancellation": exc.messages}) from exc
        return Response(TripSetupSerializer(trip).data)


class TripCompletionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        try:
            result = complete_trip(trip, actor=request.user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"completed_trip": exc.messages}) from exc
        return Response(TripCompletionSerializer.from_result(result).data)


class PublicBookingReadinessView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, organizer_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        readiness = online_payment_readiness(organizer)
        return Response(
            {
                "organizer": organizer.id,
                "provider_payment_setup_complete": is_provider_payment_setup_complete(organizer),
                **organizer_payment_method_readiness(organizer).to_payload(),
                **readiness.to_payload(),
            }
        )


class PublicTripBookingReadinessView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, trip_id: int):
        trip = get_object_or_404(Trip.objects.select_related("organizer"), pk=trip_id)
        requested_seats = parse_requested_seats(request.query_params.get("requested_seats"))
        readiness = public_booking_readiness(trip, requested_seats=requested_seats)
        return Response({"trip": trip.id, **readiness.to_payload()})


class PublicTripDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, organizer_slug: str, trip_slug: str):
        trip = get_object_or_404(
            Trip.objects.select_related("organizer", "payment_schedule").prefetch_related(
                "packages",
                "itinerary_days",
                "media_items__asset",
            ),
            organizer__slug=organizer_slug,
            slug=trip_slug,
            publication_state=Trip.PublicationState.PUBLISHED,
        )
        return Response(PublicTripSerializer(trip, context={"request": request}).data)


class PublicDraftBookingCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, organizer_slug: str, trip_slug: str):
        trip = get_object_or_404(
            Trip.objects.select_related("organizer", "payment_schedule").prefetch_related(
                "packages"
            ),
            organizer__slug=organizer_slug,
            slug=trip_slug,
            publication_state=Trip.PublicationState.PUBLISHED,
        )
        serializer = PublicDraftBookingSerializer(
            data=request.data,
            context={"trip": trip},
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(PublicDraftBookingSerializer(booking).data, status=201)


class PublicPaymentAttemptCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, booking_id: int):
        booking = get_object_or_404(
            Booking.objects.select_related("trip", "trip__organizer", "trip__payment_schedule"),
            pk=booking_id,
        )
        try:
            checkout_session = create_public_reservation_checkout(booking)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"payment_attempt": exc.messages}) from exc

        return Response(
            PublicPaymentAttemptSerializer(
                checkout_session.payment_attempt,
                context={
                    "checkout_payloads": {
                        checkout_session.payment_attempt.id: checkout_session.checkout_payload,
                    }
                },
            ).data,
            status=201,
        )


class PublicPaymentAttemptCheckoutSuccessView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, payment_attempt_id: int):
        payment_attempt = get_object_or_404(PaymentAttempt, pk=payment_attempt_id)
        serializer = BrowserCheckoutSuccessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            checkout_result = process_browser_checkout_success(
                payment_attempt,
                provider_payment_reference=serializer.validated_data["razorpay_payment_id"],
                provider_attempt_reference=serializer.validated_data["razorpay_order_id"],
                checkout_signature=serializer.validated_data["razorpay_signature"],
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"payment_attempt": exc.messages}) from exc

        return Response(PublicPaymentAttemptSerializer(checkout_result.payment_attempt).data)


class TravelerPortalBalancePaymentAttemptCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, token: str):
        if "amount_inr" in request.data:
            raise serializers.ValidationError(
                {"amount_inr": ("Balance Payment Links collect the current balance due only.")}
            )
        access_link = resolve_access_link_or_error(token)
        if access_link.scope != access_link.Scope.BOOKING:
            raise serializers.ValidationError(
                {"access_link": "Balance Payment Links require Booking-Level Access."}
            )
        try:
            checkout_session = create_balance_payment_checkout(access_link.booking)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"payment_attempt": exc.messages}) from exc

        return Response(
            PublicPaymentAttemptSerializer(
                checkout_session.payment_attempt,
                context={
                    "checkout_payloads": {
                        checkout_session.payment_attempt.id: checkout_session.checkout_payload,
                    }
                },
            ).data,
            status=201,
        )


class ProviderPaymentConfirmationView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, payment_attempt_id: int):
        payment_attempt = get_object_or_404(PaymentAttempt, pk=payment_attempt_id)
        serializer = ProviderPaymentConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            provider_confirmation_result = confirm_provider_payment(
                payment_attempt,
                payment_attempt_id=serializer.validated_data["payment_attempt"],
                booking_id=serializer.validated_data["booking"],
                provider=serializer.validated_data["provider"],
                purpose=serializer.validated_data["purpose"],
                provider_attempt_reference=serializer.validated_data["provider_attempt_reference"],
                provider_payment_reference=serializer.validated_data["provider_payment_reference"],
                amount_inr=serializer.validated_data["amount_inr"],
                provider_fee_amount_inr=serializer.validated_data.get("provider_fee_amount_inr"),
                provider_net_settlement_amount_inr=serializer.validated_data.get(
                    "provider_net_settlement_amount_inr"
                ),
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"provider_payment": exc.messages}) from exc

        if isinstance(provider_confirmation_result, PaymentException):
            return Response(
                PaymentExceptionSerializer(provider_confirmation_result).data,
                status=202,
            )

        return Response(ProviderPaymentSerializer(provider_confirmation_result).data, status=201)


class RazorpayWebhookView(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = []

    def post(self, request):
        signature = request.headers.get("X-Razorpay-Signature", "")
        try:
            result = process_razorpay_webhook(
                body=request.body,
                signature=signature,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"webhook": django_validation_detail(exc)}) from exc
        return Response(provider_webhook_result_payload(result))


class OperationsBookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int, booking_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        booking = get_object_or_404(
            Booking.objects.select_related("trip", "trip__payment_schedule").prefetch_related(
                "traveler_slots__package",
                "ledger_entries",
                "manual_payments",
                "notifications",
            ),
            pk=booking_id,
            trip__organizer=organizer,
        )
        return Response(OperationsBookingDetailSerializer(booking).data)

    def patch(self, request, organizer_id: int, booking_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        booking = get_object_or_404(
            Booking.objects.select_related("trip", "trip__payment_schedule").prefetch_related(
                "traveler_slots__package",
                "ledger_entries",
                "manual_payments",
                "notifications",
            ),
            pk=booking_id,
            trip__organizer=organizer,
        )
        serializer = BookingContactUpdateSerializer(booking, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(OperationsBookingDetailSerializer(booking).data)


class OperationsManualBookingCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        serializer = OperationsManualBookingCreateSerializer(
            data=request.data,
            context={"trip": trip},
        )
        serializer.is_valid(raise_exception=True)
        try:
            booking = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"manual_booking": exc.messages}) from exc
        return Response(OperationsBookingListItemSerializer(booking).data, status=201)


class OperationsBookingImportCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        serializer = OperationsBookingImportSubmitSerializer(
            data=self._request_data(request),
            context={"trip": trip, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            booking_import = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"booking_import": exc.messages}) from exc
        return Response(OperationsBookingImportResultSerializer(booking_import).data, status=201)

    def _request_data(self, request) -> dict:
        upload = request.FILES.get("file")
        if not upload:
            return request.data

        return parse_booking_import_upload(upload)


class OperationsManualReminderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, booking_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        booking = get_object_or_404(
            Booking.objects.select_related("trip", "trip__payment_schedule").prefetch_related(
                "traveler_slots__package",
                "traveler_slots__documents",
                "ledger_entries",
            ),
            pk=booking_id,
            trip__organizer=organizer,
        )
        serializer = ManualReminderSerializer(
            data=request.data,
            context={"booking": booking, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            notifications = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"manual_reminder": exc.messages}) from exc
        return Response(
            {
                "sent_count": len(notifications),
                "notifications": NotificationSerializer(notifications, many=True).data,
            },
            status=201,
        )


class OperationsBalancePaymentLinkSendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, booking_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        booking = get_object_or_404(
            Booking.objects.select_related("trip", "trip__payment_schedule").prefetch_related(
                "traveler_slots__package",
                "ledger_entries",
            ),
            pk=booking_id,
            trip__organizer=organizer,
        )
        serializer = BalancePaymentLinkSendSerializer(
            data=request.data,
            context={"booking": booking, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            delivery = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"balance_payment_link": exc.messages}) from exc
        balance_payment_link = delivery.balance_payment_link
        return Response(
            {
                "balance_payment_link": {
                    "id": balance_payment_link.access_link.id,
                    "scope": balance_payment_link.access_link.scope,
                    "booking": booking.id,
                    "token": balance_payment_link.token,
                    "path": balance_payment_link.path,
                    "amount_inr": balance_payment_link.amount_inr,
                    "expires_at": balance_payment_link.access_link.expires_at,
                    "revoked_at": balance_payment_link.access_link.revoked_at,
                },
                "sent_count": len(delivery.notifications),
                "notifications": NotificationSerializer(delivery.notifications, many=True).data,
            },
            status=201,
        )


class OperationsAnnouncementCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        serializer = AnnouncementSerializer(
            data=request.data,
            context={"trip": trip, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            notifications = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"announcement": exc.messages}) from exc
        return Response(
            {
                "sent_count": len(notifications),
                "notifications": NotificationSerializer(notifications, many=True).data,
            },
            status=201,
        )


class OperationsTripOperationalExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int, trip_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        trip = get_trip_for_organizer(organizer, trip_id)
        serializer = OperationalExportOptionsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        export = generate_operational_export_csv(
            trip,
            actor=request.user,
            **serializer.validated_data,
        )
        response = HttpResponse(export.csv_content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{export.filename}"'
        response["X-TripOS-Export-Rows"] = str(export.row_count)
        response["X-TripOS-Excluded-Draft-Bookings"] = str(export.excluded_draft_booking_count)
        return response


class OperationsBookingCancellationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, booking_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        booking = get_object_or_404(
            Booking.objects.select_related("trip", "trip__organizer").prefetch_related(
                "traveler_slots__package",
                "ledger_entries",
            ),
            pk=booking_id,
            trip__organizer=organizer,
        )
        serializer = BookingCancellationSerializer(
            data=request.data,
            context={"booking": booking, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            booking = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"booking_cancellation": exc.messages}) from exc
        return Response(OperationsBookingDetailSerializer(booking).data)


class OperationsTravelerCancellationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, traveler_slot_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        traveler_slot = get_object_or_404(
            TravelerSlot.objects.select_related("booking", "booking__trip", "package"),
            pk=traveler_slot_id,
            booking__trip__organizer=organizer,
        )
        serializer = TravelerCancellationSerializer(
            data=request.data,
            context={"traveler_slot": traveler_slot, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            traveler_slot = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"traveler_cancellation": exc.messages}) from exc
        return Response(OperationsBookingDetailSerializer(traveler_slot.booking).data)


class OperationsTravelerReplacementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, traveler_slot_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        traveler_slot = get_object_or_404(
            TravelerSlot.objects.select_related("booking", "booking__trip", "package"),
            pk=traveler_slot_id,
            booking__trip__organizer=organizer,
        )
        serializer = TravelerReplacementSerializer(
            data=request.data,
            context={"traveler_slot": traveler_slot, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            replacement = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"traveler_replacement": exc.messages}) from exc
        return Response(OperationsBookingDetailSerializer(replacement.booking).data, status=201)


class OperationsTravelerAdditionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, booking_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        booking = get_object_or_404(
            Booking.objects.select_related("trip", "trip__payment_schedule").prefetch_related(
                "traveler_slots__package",
                "ledger_entries",
            ),
            pk=booking_id,
            trip__organizer=organizer,
        )
        serializer = TravelerAdditionSerializer(
            data=request.data,
            context={"booking": booking, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            traveler_slot = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"traveler_addition": exc.messages}) from exc
        return Response(OperationsBookingDetailSerializer(traveler_slot.booking).data, status=201)


class OperationsTravelerPackageChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, traveler_slot_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        traveler_slot = get_object_or_404(
            TravelerSlot.objects.select_related("booking", "booking__trip", "package"),
            pk=traveler_slot_id,
            booking__trip__organizer=organizer,
        )
        serializer = TravelerPackageChangeSerializer(
            data=request.data,
            context={"traveler_slot": traveler_slot, "actor": request.user},
        )
        serializer.is_valid(raise_exception=True)
        try:
            traveler_slot = serializer.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"traveler_package_change": exc.messages}) from exc
        return Response(OperationsBookingDetailSerializer(traveler_slot.booking).data)


class OperationsBookingConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, booking_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        booking = get_object_or_404(
            Booking.objects.select_related("trip", "trip__payment_schedule").prefetch_related(
                "traveler_slots__package",
                "traveler_slots__documents",
                "ledger_entries",
                "manual_payments",
                "notifications",
            ),
            pk=booking_id,
            trip__organizer=organizer,
        )
        try:
            booking = confirm_booking(booking)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"booking": exc.messages}) from exc
        return Response(OperationsBookingDetailSerializer(booking).data)


class OperationsBookingUnconfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, booking_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        booking = get_object_or_404(
            Booking.objects.select_related("trip", "trip__payment_schedule"),
            pk=booking_id,
            trip__organizer=organizer,
        )
        try:
            booking = unconfirm_booking(booking)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"booking": exc.messages}) from exc
        return Response(OperationsBookingDetailSerializer(booking).data)


class OperationsTravelerCheckInView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, traveler_slot_id: int):
        return self._mark_attendance(
            request,
            organizer_id,
            traveler_slot_id,
            TravelerSlot.AttendanceState.CHECKED_IN,
        )

    def _mark_attendance(self, request, organizer_id: int, traveler_slot_id: int, state: str):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        traveler_slot = get_object_or_404(
            TravelerSlot.objects.select_related(
                "booking",
                "booking__trip",
                "booking__trip__organizer",
                "package",
            ),
            pk=traveler_slot_id,
            booking__trip__organizer=organizer,
        )
        try:
            mark_traveler_attendance(
                traveler_slot,
                attendance_state=state,
                actor=request.user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"traveler_attendance": exc.messages}) from exc

        booking = get_object_or_404(
            Booking.objects.select_related("trip", "trip__payment_schedule").prefetch_related(
                "traveler_slots__package",
                "traveler_slots__documents",
                "ledger_entries",
                "notifications",
            ),
            pk=traveler_slot.booking_id,
        )
        return Response(OperationsBookingDetailSerializer(booking).data)


class OperationsTravelerNoShowView(OperationsTravelerCheckInView):
    def post(self, request, organizer_id: int, traveler_slot_id: int):
        return self._mark_attendance(
            request,
            organizer_id,
            traveler_slot_id,
            TravelerSlot.AttendanceState.NO_SHOW,
        )


class OperationsBookingAccessLinkIssueView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organizer_id: int, booking_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        booking = get_object_or_404(
            Booking.objects.select_related("trip").prefetch_related("traveler_slots"),
            pk=booking_id,
            trip__organizer=organizer,
        )
        serializer = AccessLinkIssueSerializer(data=request.data, context={"booking": booking})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=201)


class OperationsTravelerDocumentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int, booking_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        booking = get_object_or_404(
            Booking.objects.prefetch_related("traveler_slots__documents"),
            pk=booking_id,
            trip__organizer=organizer,
        )
        documents = TravelerDocument.objects.filter(traveler_slot__booking=booking).select_related(
            "traveler_slot", "reviewed_by"
        )
        return Response(TravelerDocumentSerializer(documents, many=True).data)


class OperationsTravelerDocumentReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, organizer_id: int, document_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        document = get_object_or_404(
            TravelerDocument.objects.select_related(
                "traveler_slot",
                "traveler_slot__booking",
                "traveler_slot__booking__trip",
                "traveler_slot__booking__trip__organizer",
            ),
            pk=document_id,
            traveler_slot__booking__trip__organizer=organizer,
        )
        serializer = TravelerDocumentReviewSerializer(
            data=request.data,
            context={"document": document, "reviewer": request.user},
        )
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        return Response(TravelerDocumentSerializer(document).data)


class OperationsTravelerDocumentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organizer_id: int, document_id: int):
        organizer = get_object_or_404(Organizer, pk=organizer_id)
        require_operator_workflow_access(request.user, organizer)
        document = get_object_or_404(
            TravelerDocument.objects.select_related(
                "traveler_slot",
                "traveler_slot__booking",
                "traveler_slot__booking__trip",
                "traveler_slot__booking__trip__organizer",
            ),
            pk=document_id,
            traveler_slot__booking__trip__organizer=organizer,
        )
        if not document.file:
            raise serializers.ValidationError({"file": "Traveler Document file is missing."})

        record_sensitive_traveler_document_download(document=document, actor=request.user)

        filename = document.original_filename or document.file.name.rsplit("/", 1)[-1]
        return FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=filename,
            content_type=document.content_type or "application/octet-stream",
        )


class TravelerPortalDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, token: str):
        try:
            access_link = resolve_active_access_link(token)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"access_link": exc.messages}) from exc
        return Response(
            TravelerPortalSerializer.from_access_link(
                access_link,
                request=request,
                token=token,
            ).data
        )


class TravelerPortalTravelerIdentityView(APIView):
    authentication_classes = []
    permission_classes = []

    def patch(self, request, token: str, traveler_slot_id: int):
        access_link = resolve_access_link_or_error(token)
        traveler_slot = traveler_slot_for_access_link(access_link, traveler_slot_id)

        serializer = TravelerIdentitySerializer(traveler_slot, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        traveler_slot = serializer.save()
        return Response(TravelerIdentitySerializer(traveler_slot).data)


class TravelerPortalTravelerDocumentSubmissionView(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, token: str, traveler_slot_id: int):
        access_link = resolve_access_link_or_error(token)
        traveler_slot = traveler_slot_for_access_link(access_link, traveler_slot_id)
        serializer = TravelerDocumentSubmissionSerializer(
            data=request.data,
            context={"traveler_slot": traveler_slot},
        )
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        return Response(TravelerDocumentSerializer(document).data, status=201)


class TravelerPortalTravelLogisticsView(APIView):
    authentication_classes = []
    permission_classes = []

    def patch(self, request, token: str, traveler_slot_id: int):
        access_link = resolve_access_link_or_error(token)
        traveler_slot = traveler_slot_for_access_link(access_link, traveler_slot_id)
        serializer = TravelLogisticsSerializer(traveler_slot, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        traveler_slot = serializer.save()
        return Response(TravelerIdentitySerializer(traveler_slot).data)


class TravelerPortalEmergencyContactView(APIView):
    authentication_classes = []
    permission_classes = []

    def patch(self, request, token: str, traveler_slot_id: int):
        access_link = resolve_access_link_or_error(token)
        traveler_slot = traveler_slot_for_access_link(access_link, traveler_slot_id)
        serializer = EmergencyContactSerializer(traveler_slot, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        traveler_slot = serializer.save()
        return Response(TravelerIdentitySerializer(traveler_slot).data)


class TravelerPortalMedicalDisclosureView(APIView):
    authentication_classes = []
    permission_classes = []

    def patch(self, request, token: str, traveler_slot_id: int):
        access_link = resolve_access_link_or_error(token)
        traveler_slot = traveler_slot_for_access_link(access_link, traveler_slot_id)
        serializer = MedicalDisclosureSerializer(traveler_slot, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        traveler_slot = serializer.save()
        return Response(TravelerIdentitySerializer(traveler_slot).data)


def resolve_access_link_or_error(token: str):
    try:
        return resolve_active_access_link(token)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"access_link": exc.messages}) from exc


def traveler_slot_for_access_link(access_link, traveler_slot_id: int) -> TravelerSlot:
    try:
        return resolve_traveler_slot_for_access_link(access_link, traveler_slot_id)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"traveler_slot": exc.messages}) from exc


def internal_admin_booking_prefetches() -> tuple[str, ...]:
    return (
        "traveler_slots__package",
        "ledger_entries",
        "payment_attempts",
        "provider_payments",
        "provider_payments__ledger_entries",
        "provider_payments__payment_attempt",
        "manual_payments",
        "notifications",
        "import_rows",
        "activity_logs__actor",
    )


def internal_admin_trip_prefetches() -> tuple[str, ...]:
    return (
        "booking_imports__rows",
        "booking_imports__opening_payment_records",
        "activity_logs__actor",
        "bookings__traveler_slots__package",
        "bookings__ledger_entries",
        "bookings__payment_attempts",
        "bookings__provider_payments",
        "bookings__provider_payments__ledger_entries",
        "bookings__provider_payments__payment_attempt",
        "bookings__manual_payments",
        "bookings__notifications",
        "bookings__import_rows",
        "bookings__activity_logs__actor",
    )


def internal_admin_organizer_prefetches() -> tuple[str, ...]:
    return (
        "activity_logs__actor",
        "platform_fee_statements",
        "provider_connection_test_results__initiated_by",
        "trips__payment_schedule",
        "trips__booking_imports__rows",
        "trips__booking_imports__opening_payment_records",
        "trips__activity_logs__actor",
        "trips__bookings__traveler_slots__package",
        "trips__bookings__ledger_entries",
        "trips__bookings__payment_attempts",
        "trips__bookings__provider_payments",
        "trips__bookings__provider_payments__ledger_entries",
        "trips__bookings__provider_payments__payment_attempt",
        "trips__bookings__manual_payments",
        "trips__bookings__notifications",
        "trips__bookings__import_rows",
        "trips__bookings__activity_logs__actor",
    )


def provider_connection_test_results_for(organizer: Organizer):
    return (
        ProviderConnectionTestResult.objects.select_related("initiated_by")
        .filter(organizer=organizer)
        .order_by("-started_at", "-id")
    )


def get_trip_for_organizer(organizer: Organizer, trip_id: int) -> Trip:
    return get_trip_profile_for_organizer_id(
        organizer_id=organizer.id,
        trip_id=trip_id,
    )


def parse_requested_seats(raw_value: str | None) -> int:
    if raw_value is None:
        return 1
    try:
        return max(int(raw_value), 1)
    except (TypeError, ValueError):
        return 1
