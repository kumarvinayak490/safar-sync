"""DRF serializers for the legacy Organizer API integration surface.

These serializers keep existing API responses stable while delegating business
rules to the relevant domain modules during the staged backend app split.
"""

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers

from organizer_payments.manual_payment_instructions import (
    has_ready_manual_payment_instructions,
)
from organizer_payments.serializers import ManualPaymentInstructionsSerializer  # noqa: F401
from organizer_profile.identity import (
    organizer_profile_identity_payload as organizer_identity_payload,
)
from organizer_profile.serializers import OrganizerIdentitySerializer  # noqa: F401
from organizers.models import (
    Booking,
    BookingAccessLink,
    LedgerEntry,
    Organizer,
    OrganizerInvitation,
    OrganizerMembership,
    PaymentAttempt,
    PayoutAccount,
    ProviderConnectionTestResult,
    ProviderPayment,
    ProviderPaymentSetup,
    TravelerDocument,
    TravelerSlot,
    Trip,
    TripPackage,
    TripPaymentSchedule,
)
from organizers.services import (
    add_traveler_to_booking,
    available_seats,
    balance_payment_availability_payload,
    booking_reconciliation,
    cancel_booking,
    cancel_traveler,
    change_traveler_package,
    change_trip_dates,
    collected_provider_payment_amount_inr,
    create_manual_booking,
    derived_payment_state,
    duplicate_trip,
    online_payment_readiness,
    public_booking_readiness,
    replace_traveler,
    required_amount_to_reserve_inr,
)
from team_access.invitations import create_organizer_invitation
from team_access.memberships import create_owner_membership
from trip_bookings.access_links import (
    issue_access_link,
    traveler_slots_for_access_link,
    validate_access_link_issue_request,
)
from trip_bookings.intake import (
    create_booking_from_intake,
    prepare_manual_booking_intake,
    prepare_public_booking_intake,
)
from trip_bookings.serializers import (  # noqa: F401
    BookingImportRowSerializer,
    OperationsBookingImportResultSerializer,
    OperationsBookingImportSubmitSerializer,
    OperationsBookingImportTravelerSlotSerializer,
)
from trip_operations.serializers import ActivityLogSerializer as ActivityLogSerializer
from trip_operations.serializers import AnnouncementSerializer as AnnouncementSerializer
from trip_operations.serializers import (
    BalancePaymentLinkSendSerializer as BalancePaymentLinkSendSerializer,
)
from trip_operations.serializers import ManualReminderSerializer as ManualReminderSerializer
from trip_operations.serializers import NotificationSerializer as NotificationSerializer
from trip_operations.serializers import (
    OperationalExportOptionsSerializer as OperationalExportOptionsSerializer,
)
from trip_operations.serializers import (
    OperationsBookingListItemSerializer as OperationsBookingListItemSerializer,
)
from trip_operations.serializers import (
    OperationsProviderPaymentSerializer as OperationsProviderPaymentSerializer,
)
from trip_operations.serializers import (
    OperationsTravelerSlotSerializer as OperationsTravelerSlotSerializer,
)
from trip_payments.financial_ledger import (
    booking_reconciliation_flags_for_booking as payment_reconciliation_flags_for_booking,
)
from trip_payments.financial_ledger import (
    booking_reconciliation_payload,
    platform_fee_for_provider_payment_ledger_amount_inr,
)
from trip_payments.serializers import (
    BookingAdjustmentSerializer as BookingAdjustmentSerializer,
)
from trip_payments.serializers import (
    InternalAdminPlatformFeeStatementManageSerializer as InternalAdminPlatformFeeStatementManageSerializer,  # noqa: E501
)
from trip_payments.serializers import (
    InternalAdminPlatformFeeStatementSerializer as InternalAdminPlatformFeeStatementSerializer,
)
from trip_payments.serializers import (
    ManualPaymentDecisionSerializer as ManualPaymentDecisionSerializer,
)
from trip_payments.serializers import (
    OperationsManualPaymentSerializer as OperationsManualPaymentSerializer,
)
from trip_payments.serializers import (
    PaymentExceptionResolutionSerializer as PaymentExceptionResolutionSerializer,
)
from trip_payments.serializers import (
    PaymentExceptionSerializer as PaymentExceptionSerializer,
)
from trip_payments.serializers import (
    PublicQrManualPaymentSubmissionSerializer as PublicQrManualPaymentSubmissionSerializer,
)
from trip_payments.serializers import (
    RefundRecordSerializer as RefundRecordSerializer,
)
from trip_payments.serializers import (
    TravelerManualPaymentSubmissionSerializer as TravelerManualPaymentSubmissionSerializer,
)
from trip_payments.serializers import (
    validate_payment_proof_upload as validate_payment_proof_upload,
)
from trip_travelers.documents import (
    review_traveler_document,
    submit_traveler_document,
)
from trip_travelers.readiness import (
    traveler_portal_readiness_payload,
    update_emergency_contact,
    update_medical_disclosure,
    update_travel_logistics,
    update_traveler_identity_details,
)
from trip_travelers.slots import TravelerSlotIntakeInput
from trips import serializers as trip_content_serializers
from trips.activity import record_public_trip_page_published
from trips.locks import is_trip_profile_locked, published_trip_profile_lock_message
from trips.payment_method_readiness import (
    ManualPaymentMethodReadinessFacts,
    payment_method_readiness_for_trip,
)
from trips.publication_readiness import trip_profile_publication_readiness


def error_detail_from_django(exc: DjangoValidationError):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return exc.messages


TripDescriptionSerializer = trip_content_serializers.TripDescriptionSerializer


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "email", "first_name", "last_name"]


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        user_model = get_user_model()
        email_exists = user_model.objects.filter(email__iexact=email).exists()
        username_exists = user_model.objects.filter(username__iexact=email).exists()
        if email_exists or username_exists:
            raise serializers.ValidationError("A User with this email already exists.")
        return email

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def create(self, validated_data):
        email = validated_data["email"]
        return get_user_model().objects.create_user(
            username=email,
            email=email,
            password=validated_data["password"],
            first_name=validated_data.get("first_name", "").strip(),
            last_name=validated_data.get("last_name", "").strip(),
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs: dict) -> dict:
        email = attrs["email"].strip().lower()
        user_model = get_user_model()
        existing_user = user_model.objects.filter(email__iexact=email).first()
        user = authenticate(
            request=self.context.get("request"),
            username=existing_user.get_username() if existing_user is not None else email,
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This User is inactive.")
        attrs["user"] = user
        return attrs


class OrganizerOnboardingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organizer
        fields = ["id", "name", "slug"]
        read_only_fields = ["id", "slug"]

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Enter the Organizer name.")
        if not slugify(name):
            raise serializers.ValidationError("Use at least one letter or number.")
        return name

    def create(self, validated_data):
        user = self.context["user"]
        base_slug = slugify(validated_data["name"])[:170]
        slug = base_slug
        suffix = 2
        while Organizer.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{suffix}"[:180]
            suffix += 1

        with transaction.atomic():
            organizer = Organizer.objects.create(
                **validated_data,
                identity_name=validated_data["name"],
                slug=slug,
            )
            create_owner_membership(
                user=user,
                organizer=organizer,
            )
        return organizer


def reconciliation_payload(booking: Booking) -> dict[str, int]:
    return booking_reconciliation_payload(booking)


class OrganizerInvitationSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    invite_url_path = serializers.SerializerMethodField()
    invited_by = serializers.SerializerMethodField()

    class Meta:
        model = OrganizerInvitation
        fields = [
            "id",
            "email",
            "role",
            "role_label",
            "status",
            "status_label",
            "token",
            "invite_url_path",
            "invited_by",
            "last_sent_at",
            "resend_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_invite_url_path(self, invitation: OrganizerInvitation) -> str:
        return f"/team-access/invitations/{invitation.token}"

    def get_invited_by(self, invitation: OrganizerInvitation):
        if invitation.invited_by is None:
            return None
        display_name = (
            f"{invitation.invited_by.first_name} {invitation.invited_by.last_name}".strip()
        )
        return {
            "id": invitation.invited_by_id,
            "email": invitation.invited_by.email,
            "name": display_name or invitation.invited_by.email,
        }


class OrganizerInvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=OrganizerMembership.Role.choices,
        default=OrganizerMembership.Role.OPERATOR,
        required=False,
    )
    confirm_owner_powers = serializers.BooleanField(default=False, required=False)

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def create(self, validated_data):
        try:
            return create_organizer_invitation(
                organizer=self.context["organizer"],
                email=validated_data["email"],
                invited_by=self.context["actor"],
                role=validated_data.get("role", OrganizerMembership.Role.OPERATOR),
                confirm_owner_powers=validated_data.get("confirm_owner_powers", False),
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(error_detail_from_django(exc)) from exc


class PayoutAccountSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    settlement_readiness_source_label = serializers.CharField(
        source="get_settlement_readiness_source_display",
        read_only=True,
    )

    class Meta:
        model = PayoutAccount
        fields = [
            "holder_name",
            "provider_account_reference",
            "status",
            "status_label",
            "settlement_readiness_source",
            "settlement_readiness_source_label",
            "support_confirmed_at",
            "notes",
            "updated_at",
        ]
        read_only_fields = [
            "holder_name",
            "provider_account_reference",
            "status",
            "status_label",
            "settlement_readiness_source",
            "settlement_readiness_source_label",
            "support_confirmed_at",
            "notes",
            "updated_at",
        ]


class ProviderPaymentSetupSerializer(serializers.ModelSerializer):
    provider_label = serializers.CharField(source="get_provider_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    authorization_method_label = serializers.CharField(
        source="get_authorization_method_display",
        read_only=True,
    )
    authorization_state_label = serializers.CharField(
        source="get_authorization_state_display",
        read_only=True,
    )
    provider_verification_status_label = serializers.CharField(
        source="get_provider_verification_status_display",
        read_only=True,
    )
    provider_connection_state_label = serializers.CharField(
        source="get_provider_connection_state_display",
        read_only=True,
    )
    provider_mode_label = serializers.CharField(source="get_provider_mode_display", read_only=True)
    provider_disclosure = serializers.SerializerMethodField()
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProviderPaymentSetup
        fields = [
            "provider",
            "provider_label",
            "provider_disclosure",
            "status",
            "status_label",
            "provider_merchant_reference",
            "authorization_method",
            "authorization_method_label",
            "authorization_state",
            "authorization_state_label",
            "provider_verification_status",
            "provider_verification_status_label",
            "provider_payment_capability_enabled",
            "provider_connection_state",
            "provider_connection_state_label",
            "provider_mode",
            "provider_mode_label",
            "is_complete",
            "updated_at",
        ]
        read_only_fields = [
            "provider",
            "provider_label",
            "provider_disclosure",
            "status",
            "status_label",
            "provider_merchant_reference",
            "authorization_method",
            "authorization_method_label",
            "authorization_state",
            "authorization_state_label",
            "provider_verification_status",
            "provider_verification_status_label",
            "provider_payment_capability_enabled",
            "provider_connection_state",
            "provider_connection_state_label",
            "provider_mode",
            "provider_mode_label",
            "is_complete",
            "updated_at",
        ]

    def get_provider_disclosure(self, setup: ProviderPaymentSetup) -> str:
        return provider_disclosure_for(setup.provider)

    def validate_authorization_method(self, value: str) -> str:
        if value in {
            ProviderPaymentSetup.AuthorizationMethod.API_KEY,
            ProviderPaymentSetup.AuthorizationMethod.ASSISTED,
        }:
            raise serializers.ValidationError(
                "API Key Provider Authorization is available only through Assisted Payment Setup."
            )
        return value


class PaymentSetupStatusSerializer(serializers.Serializer):
    provider = serializers.CharField()
    provider_label = serializers.CharField()
    provider_disclosure = serializers.CharField()
    payout_status = serializers.CharField()
    payout_status_label = serializers.CharField()
    settlement_readiness_status = serializers.CharField()
    settlement_readiness_status_label = serializers.CharField()
    settlement_readiness_ready = serializers.BooleanField()
    settlement_readiness_source = serializers.CharField()
    settlement_readiness_source_label = serializers.CharField()
    settlement_readiness_support_confirmed = serializers.BooleanField()
    settlement_readiness_support_confirmed_at = serializers.DateTimeField(allow_null=True)
    provider_payment_setup_status = serializers.CharField()
    provider_payment_setup_status_label = serializers.CharField()
    provider_payment_setup_complete = serializers.BooleanField()
    provider_authorization_method = serializers.CharField()
    provider_authorization_method_label = serializers.CharField()
    provider_authorization_state = serializers.CharField()
    provider_authorization_state_label = serializers.CharField()
    online_payment_readiness_ready = serializers.BooleanField()
    online_payment_readiness_status_label = serializers.CharField()
    online_payment_readiness_blocker_code = serializers.CharField()
    online_payment_readiness_blocker_label = serializers.CharField()
    online_payment_readiness_message = serializers.CharField()
    payment_method_readiness_ready = serializers.BooleanField()
    payment_method_readiness_status_label = serializers.CharField()
    ready_payment_method_count = serializers.IntegerField()
    ready_payment_method_ids = serializers.ListField(child=serializers.CharField())
    payment_methods = serializers.ListField(child=serializers.DictField())
    provider_payment_method = serializers.DictField()
    manual_payment_method = serializers.DictField()
    provider_verification_status = serializers.CharField()
    provider_verification_status_label = serializers.CharField()
    payout_account_ready = serializers.BooleanField()
    provider_payment_capability_enabled = serializers.BooleanField()
    provider_connection_state = serializers.CharField()
    provider_connection_state_label = serializers.CharField()
    provider_mode = serializers.CharField()
    provider_mode_label = serializers.CharField()
    provider_order_creation_available = serializers.BooleanField()
    manual_payment_capability_enabled = serializers.BooleanField()
    can_manage_manual_payment_instructions = serializers.BooleanField()
    manual_payment_instructions = serializers.DictField()
    can_manage_provider_authorization = serializers.BooleanField()
    payment_setup_access_message = serializers.CharField()
    provider_authorization_actions = serializers.ListField(
        child=serializers.DictField(),
    )
    individual_creator_payment_path = serializers.DictField()
    provider_verification_url = serializers.DictField()
    manual_payments_only = serializers.DictField()


class ProviderAuthorizationStartSerializer(serializers.Serializer):
    provider_mode = serializers.ChoiceField(
        choices=ProviderPaymentSetup.ProviderMode.choices,
        required=False,
    )


class ProviderAuthorizationCallbackSerializer(serializers.Serializer):
    state = serializers.CharField(max_length=256, trim_whitespace=True)
    code = serializers.CharField(max_length=4096, trim_whitespace=True)

    def validate_state(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Provider Authorization state is required.")
        return value

    def validate_code(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Provider Authorization code is required.")
        return value


class ProviderAccountReplacementConfirmSerializer(serializers.Serializer):
    confirm_replacement = serializers.BooleanField()

    def validate_confirm_replacement(self, value: bool) -> bool:
        if value is not True:
            raise serializers.ValidationError("Explicit replacement confirmation is required.")
        return value


class ProviderConnectionTestResultSerializer(serializers.ModelSerializer):
    provider_label = serializers.CharField(source="get_provider_display", read_only=True)
    provider_mode_label = serializers.CharField(source="get_provider_mode_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    initiated_by_email = serializers.SerializerMethodField()

    class Meta:
        model = ProviderConnectionTestResult
        fields = [
            "id",
            "organizer",
            "provider",
            "provider_label",
            "provider_mode",
            "provider_mode_label",
            "status",
            "status_label",
            "provider_account_reference",
            "provider_order_reference",
            "provider_payment_reference",
            "checks",
            "checkout_payload",
            "failure_reason",
            "initiated_by",
            "initiated_by_email",
            "initiated_by_staff",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_initiated_by_email(self, result: ProviderConnectionTestResult) -> str:
        actor = result.initiated_by
        if actor is None:
            return ""
        return getattr(actor, "email", "") or getattr(actor, "username", "")


class InternalAdminAssistedPaymentSetupSerializer(serializers.Serializer):
    provider_mode = serializers.ChoiceField(
        choices=ProviderPaymentSetup.ProviderMode.choices,
        default=ProviderPaymentSetup.ProviderMode.TEST,
    )
    provider_account_reference = serializers.CharField(max_length=160, trim_whitespace=True)
    key_id = serializers.CharField(max_length=160, trim_whitespace=True, write_only=True)
    key_secret = serializers.CharField(
        max_length=4096,
        trim_whitespace=True,
        write_only=True,
    )
    webhook_secret = serializers.CharField(
        max_length=4096,
        allow_blank=True,
        required=False,
        trim_whitespace=True,
        write_only=True,
    )
    scopes = serializers.ListField(
        child=serializers.CharField(max_length=200, trim_whitespace=True),
        required=False,
        default=list,
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_provider_account_reference(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Provider account reference is required.")
        return value

    def validate_key_id(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("API key id is required.")
        return value

    def validate_key_secret(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("API key secret is required.")
        return value


class InternalAdminSettlementReadinessConfirmSerializer(serializers.Serializer):
    notes = serializers.CharField(
        allow_blank=True,
        max_length=2000,
        required=False,
        trim_whitespace=True,
    )


def provider_disclosure_for(provider: str) -> str:
    if provider == ProviderPaymentSetup.Provider.RAZORPAY:
        return (
            "Razorpay processes provider-confirmed payments and provider verification "
            "for the India MVP."
        )
    return "The connected payment provider processes provider-confirmed payments."


def support_payment_setup_payload(organizer: Organizer) -> dict:
    from organizer_payments.payment_setup_readiness import payment_setup_status_payload

    return payment_setup_status_payload(organizer)


def reconciliation_flags_for_booking(booking: Booking) -> list[str]:
    return payment_reconciliation_flags_for_booking(booking)


TripPackageSerializer = trip_content_serializers.TripPackageSerializer
TripPackageSectionSerializer = trip_content_serializers.TripPackageSectionSerializer
TripPaymentScheduleSerializer = trip_content_serializers.TripPaymentScheduleSerializer
TripPaymentScheduleSectionSerializer = trip_content_serializers.TripPaymentScheduleSectionSerializer
TripConfirmationRequirementsSectionSerializer = (
    trip_content_serializers.TripConfirmationRequirementsSectionSerializer
)
TripItineraryDaySerializer = trip_content_serializers.TripItineraryDaySerializer
TripItinerarySectionSerializer = trip_content_serializers.TripItinerarySectionSerializer
TripMediaItemSerializer = trip_content_serializers.TripMediaItemSerializer
TripMediaGallerySerializer = trip_content_serializers.TripMediaGallerySerializer
TripMediaUploadSerializer = trip_content_serializers.TripMediaUploadSerializer

class PublicBookingGateSerializerMixin:
    def public_booking_gate_decision(self, trip: Trip):
        cache = getattr(self, "_public_booking_gate_cache", None)
        if cache is None:
            cache = {}
            self._public_booking_gate_cache = cache
        if trip.pk not in cache:
            cache[trip.pk] = public_booking_readiness(trip)
        return cache[trip.pk]


class TripSetupSerializer(PublicBookingGateSerializerMixin, serializers.ModelSerializer):
    packages = TripPackageSerializer(many=True)
    payment_schedule = TripPaymentScheduleSerializer()
    itinerary_days = TripItineraryDaySerializer(many=True, read_only=True)
    media_items = TripMediaItemSerializer(many=True, read_only=True)
    publish_lock_acknowledged = serializers.BooleanField(write_only=True, required=False)
    publication_state_label = serializers.CharField(
        source="get_publication_state_display",
        read_only=True,
    )
    booking_availability_label = serializers.CharField(
        source="get_booking_availability_display",
        read_only=True,
    )
    manual_payment_availability_label = serializers.CharField(
        source="get_manual_payment_availability_display",
        read_only=True,
    )
    effective_booking_availability = serializers.SerializerMethodField()
    available_seats = serializers.SerializerMethodField()
    launch_readiness = serializers.SerializerMethodField()
    trip_profile_publication_readiness = serializers.SerializerMethodField()
    confirmation_requirements_reviewed = serializers.BooleanField(read_only=True)
    confirmation_requirements_reviewed_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Trip
        fields = [
            "id",
            "organizer",
            "title",
            "slug",
            "start_date",
            "end_date",
            "capacity",
            "available_seats",
            "confirmation_requirements_note",
            "requires_traveler_documents",
            "requires_traveler_identity_details",
            "requires_travel_logistics",
            "requires_emergency_contact",
            "requires_medical_disclosure",
            "requires_full_payment_before_confirmation",
            "confirmation_requirements_reviewed",
            "confirmation_requirements_reviewed_at",
            "description_rich_text",
            "itinerary",
            "itinerary_days",
            "media_items",
            "publication_state",
            "publish_lock_acknowledged",
            "publication_state_label",
            "booking_availability",
            "booking_availability_label",
            "manual_payment_availability",
            "manual_payment_availability_label",
            "effective_booking_availability",
            "public_url_path",
            "packages",
            "payment_schedule",
            "launch_readiness",
            "trip_profile_publication_readiness",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organizer",
            "slug",
            "available_seats",
            "publication_state_label",
            "booking_availability_label",
            "manual_payment_availability_label",
            "effective_booking_availability",
            "public_url_path",
            "launch_readiness",
            "trip_profile_publication_readiness",
            "confirmation_requirements_reviewed",
            "confirmation_requirements_reviewed_at",
            "description_rich_text",
            "media_items",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "Trip end date cannot be before Trip Start Date."}
            )

        packages = attrs.get("packages")
        if self.instance is None and not packages:
            raise serializers.ValidationError(
                {"packages": "Every Trip needs at least one Package."}
            )
        if packages is not None and len(packages) == 0:
            raise serializers.ValidationError(
                {"packages": "Every Trip needs at least one Package."}
            )

        role = self.context.get("role")
        if role is not None:
            self._validate_role_permissions(attrs, role)

        return attrs

    def _validate_role_permissions(self, attrs, role):
        if "capacity" in attrs and not role.can_manage_trip_capacity:
            raise serializers.ValidationError({"capacity": "Only Owners can manage Trip Capacity."})

        profile_locked = self.instance is not None and is_trip_profile_locked(self.instance)
        capacity_changed = (
            self.instance is not None
            and "capacity" in attrs
            and attrs["capacity"] != self.instance.capacity
        )
        date_fields_changed = self.instance is not None and any(
            field in attrs and attrs[field] != getattr(self.instance, field)
            for field in ["start_date", "end_date"]
        )
        if profile_locked and capacity_changed:
            raise serializers.ValidationError(
                {"capacity": published_trip_profile_lock_message("Trip Capacity")}
            )
        if profile_locked and date_fields_changed:
            raise serializers.ValidationError(
                {"start_date": published_trip_profile_lock_message("Trip Date")}
            )

        publication_state = attrs.get("publication_state")
        if publication_state and publication_state != getattr(
            self.instance,
            "publication_state",
            None,
        ):
            if not role.can_publish_trip:
                raise serializers.ValidationError(
                    {"publication_state": "Only Owners can manage Publication State."}
                )
            if publication_state == Trip.PublicationState.PUBLISHED and self.instance is not None:
                if not attrs.get("publish_lock_acknowledged", False):
                    raise serializers.ValidationError(
                        {
                            "publish_lock_acknowledged": (
                                "Acknowledge the Published Trip Profile Lock before publishing."
                            )
                        }
                    )
                readiness = trip_profile_publication_readiness(self.instance)
                if not readiness.publish_eligible:
                    raise serializers.ValidationError(
                        {
                            "publication_state": (
                                "Trip Profile Publication Readiness blockers remain."
                            ),
                            "trip_profile_publication_readiness": readiness.to_payload(),
                        }
                    )
            if profile_locked and publication_state == Trip.PublicationState.DRAFT:
                raise serializers.ValidationError(
                    {
                        "publication_state": (
                            "Published Trip Profile Lock cannot be removed in the MVP."
                        )
                    }
                )

        booking_availability = attrs.get("booking_availability")
        if (
            booking_availability == Trip.BookingAvailability.OPEN
            and not role.can_open_booking_availability
        ):
            raise serializers.ValidationError(
                {"booking_availability": "Only Owners can open Booking Availability."}
            )
        if booking_availability == Trip.BookingAvailability.OPEN:
            target_publication_state = attrs.get(
                "publication_state",
                getattr(self.instance, "publication_state", Trip.PublicationState.DRAFT),
            )
            organizer = self.context.get("organizer") or getattr(
                self.instance,
                "organizer",
                None,
            )
            if target_publication_state != Trip.PublicationState.PUBLISHED:
                raise serializers.ValidationError(
                    {
                        "booking_availability": (
                            "Publish the Public Trip Page before opening public booking."
                        )
                    }
                )
            if organizer is not None and self.instance is not None:
                readiness = self._target_payment_method_readiness(attrs, organizer)
                if not readiness.ready:
                    payload = readiness.to_payload()
                    method_messages = [
                        method["message"]
                        for method in payload["payment_methods"]
                        if not method["ready"]
                    ]
                    message = (
                        "At least one payment method must be ready before opening "
                        "public booking."
                    )
                    if method_messages:
                        message = f"{message} {' '.join(method_messages)}"
                    raise serializers.ValidationError(
                        {
                            "booking_availability": message,
                            "payment_method_readiness": payload,
                        }
                    )
        manual_payment_availability = attrs.get("manual_payment_availability")
        if (
            manual_payment_availability is not None
            and self.instance is not None
            and manual_payment_availability != self.instance.manual_payment_availability
        ):
            if not role.is_owner:
                raise serializers.ValidationError(
                    {
                        "manual_payment_availability": (
                            "Only Owners can manage Manual Payment Availability."
                        )
                    }
                )
            if manual_payment_availability == Trip.ManualPaymentAvailability.OPEN:
                target_booking_availability = attrs.get(
                    "booking_availability",
                    self.instance.booking_availability,
                )
                if target_booking_availability != Trip.BookingAvailability.OPEN:
                    raise serializers.ValidationError(
                        {
                            "manual_payment_availability": (
                                "Open Booking Availability before opening Manual "
                                "Payment Availability."
                            )
                        }
                    )
                organizer = self.context.get("organizer") or getattr(
                    self.instance,
                    "organizer",
                    None,
                )
                if organizer is not None and not has_ready_manual_payment_instructions(
                    organizer
                ):
                    raise serializers.ValidationError(
                        {
                            "manual_payment_availability": (
                                "Add Manual Payment Instructions in Payment Setup before "
                                "opening Manual Payment Availability."
                            )
                        }
                    )
        if (
            booking_availability == Trip.BookingAvailability.CLOSED
            and self.instance is not None
            and self.instance.booking_availability != Trip.BookingAvailability.CLOSED
            and not role.can_close_booking_availability
        ):
            raise serializers.ValidationError(
                {"booking_availability": "Owner or Operator access is required to close booking."}
            )

        if "packages" in attrs and not role.can_manage_trip_commercial_terms:
            raise serializers.ValidationError(
                {"packages": "Only Owners can manage Package commercial terms."}
            )
        if (
            "packages" in attrs
            and self.instance is not None
            and is_trip_profile_locked(self.instance)
        ):
            raise serializers.ValidationError(
                {"packages": published_trip_profile_lock_message("Package")}
            )

        if "payment_schedule" in attrs and not role.can_manage_trip_commercial_terms:
            raise serializers.ValidationError(
                {
                    "payment_schedule": (
                        "Only Owners can manage balance payment terms."
                    )
                }
            )
        if (
            "payment_schedule" in attrs
            and self.instance is not None
            and is_trip_profile_locked(self.instance)
        ):
            raise serializers.ValidationError(
                {
                    "payment_schedule": (
                        published_trip_profile_lock_message(
                            "balance payment schedule"
                        )
                    )
                }
            )

        confirmation_requirement_fields = {
            "confirmation_requirements_note",
            "requires_traveler_documents",
            "requires_traveler_identity_details",
            "requires_travel_logistics",
            "requires_emergency_contact",
            "requires_medical_disclosure",
            "requires_full_payment_before_confirmation",
        }
        if (
            confirmation_requirement_fields.intersection(attrs)
            and self.instance is not None
            and is_trip_profile_locked(self.instance)
        ):
            raise serializers.ValidationError(
                {
                    "confirmation_requirements": (
                        published_trip_profile_lock_message("Confirmation Requirements")
                    )
                }
            )

        if (
            date_fields_changed
            and self.instance is not None
            and self.instance.bookings.exists()
            and not role.can_manage_post_booking_trip_dates
        ):
            raise serializers.ValidationError(
                {"start_date": "Only Owners can change Trip Dates after Bookings exist."}
            )

    def _target_payment_method_readiness(self, attrs, organizer):
        target_booking_availability = attrs.get(
            "booking_availability",
            self.instance.booking_availability,
        )
        target_manual_payment_availability = attrs.get(
            "manual_payment_availability",
            self.instance.manual_payment_availability,
        )
        launch_gate = public_booking_readiness(self.instance)
        target_booking_open = target_booking_availability == Trip.BookingAvailability.OPEN
        capacity_available = launch_gate.bookable_seats >= 1

        return payment_method_readiness_for_trip(
            self.instance,
            online_payment_readiness=online_payment_readiness(organizer),
            manual_payment_facts=ManualPaymentMethodReadinessFacts(
                manual_payment_instructions_present=has_ready_manual_payment_instructions(
                    organizer
                ),
                manual_payment_availability_open=(
                    target_manual_payment_availability
                    == Trip.ManualPaymentAvailability.OPEN
                ),
                booking_availability_open=target_booking_open,
                capacity_available=capacity_available,
            ),
            booking_availability_open=target_booking_open,
            capacity_available=capacity_available,
        )

    def create(self, validated_data):
        validated_data.pop("publish_lock_acknowledged", None)
        packages = validated_data.pop("packages")
        payment_schedule = validated_data.pop("payment_schedule")
        organizer = self.context["organizer"]

        with transaction.atomic():
            trip = Trip.objects.create(organizer=organizer, **validated_data)
            for index, package in enumerate(packages, start=1):
                package.setdefault("position", index)
                TripPackage.objects.create(trip=trip, **package)
            TripPaymentSchedule.objects.create(trip=trip, **payment_schedule)
            return trip

    def update(self, instance, validated_data):
        publish_lock_acknowledged = validated_data.pop("publish_lock_acknowledged", False)
        previous_publication_state = instance.publication_state
        packages = validated_data.pop("packages", None)
        payment_schedule = validated_data.pop("payment_schedule", None)
        start_date = validated_data.pop("start_date", instance.start_date)
        end_date = validated_data.pop("end_date", instance.end_date)
        dates_changed = start_date != instance.start_date or end_date != instance.end_date

        with transaction.atomic():
            for field, value in validated_data.items():
                setattr(instance, field, value)
            instance.save()

            if dates_changed:
                instance = change_trip_dates(
                    instance,
                    start_date=start_date,
                    end_date=end_date,
                    actor=self.context.get("actor"),
                )

            if packages is not None:
                active_packages = instance.packages.active()
                package_ids_to_remove = set(active_packages.values_list("id", flat=True))
                package_ids_to_withdraw = set(
                    active_packages.filter(traveler_slots__isnull=False)
                    .distinct()
                    .values_list("id", flat=True)
                )
                if package_ids_to_withdraw:
                    TripPackage.objects.filter(id__in=package_ids_to_withdraw).update(
                        lifecycle_state=TripPackage.LifecycleState.WITHDRAWN,
                        updated_at=timezone.now(),
                    )
                package_ids_to_delete = package_ids_to_remove - package_ids_to_withdraw
                if package_ids_to_delete:
                    TripPackage.objects.filter(id__in=package_ids_to_delete).delete()
                for index, package in enumerate(packages, start=1):
                    package.setdefault("position", index)
                    TripPackage.objects.create(trip=instance, **package)

            if payment_schedule is not None:
                schedule, _ = TripPaymentSchedule.objects.get_or_create(trip=instance)
                for field, value in payment_schedule.items():
                    setattr(schedule, field, value)
                schedule.save()

            if (
                previous_publication_state != Trip.PublicationState.PUBLISHED
                and instance.publication_state == Trip.PublicationState.PUBLISHED
            ):
                record_public_trip_page_published(
                    trip=instance,
                    actor=self.context.get("actor"),
                    publish_lock_acknowledged=publish_lock_acknowledged,
                    previous_publication_state=previous_publication_state,
                )

        return instance

    def get_effective_booking_availability(self, trip: Trip) -> str:
        return self.public_booking_gate_decision(trip).effective_booking_availability

    def get_available_seats(self, trip: Trip) -> int:
        return self.public_booking_gate_decision(trip).available_seats

    def get_launch_readiness(self, trip: Trip) -> dict[str, bool | int | str]:
        return self.public_booking_gate_decision(trip).to_payload()

    def get_trip_profile_publication_readiness(
        self,
        trip: Trip,
    ) -> dict[str, bool | int | list[dict[str, bool | str]]]:
        return trip_profile_publication_readiness(trip).to_payload()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["packages"] = TripPackageSerializer(
            instance.packages.active().order_by("position", "id"),
            many=True,
        ).data
        return representation


PublicTripSerializer = trip_content_serializers.PublicTripSerializer


class PublicDraftTravelerSlotSerializer(serializers.ModelSerializer):
    package = serializers.PrimaryKeyRelatedField(queryset=TripPackage.objects.all())
    package_name = serializers.CharField(source="package.name", read_only=True)
    reservation_amount_inr = serializers.IntegerField(
        source="package.reservation_amount_inr",
        read_only=True,
    )

    class Meta:
        model = TravelerSlot
        fields = [
            "id",
            "position",
            "package",
            "package_name",
            "reservation_amount_inr",
            "traveler_full_name",
            "traveler_phone",
            "traveler_email",
            "is_traveler",
        ]
        read_only_fields = [
            "id",
            "position",
            "package_name",
            "reservation_amount_inr",
            "traveler_full_name",
            "traveler_phone",
            "traveler_email",
            "is_traveler",
        ]


class PublicDraftBookingSerializer(serializers.ModelSerializer):
    booking_contact = serializers.SerializerMethodField()
    package = serializers.PrimaryKeyRelatedField(
        queryset=TripPackage.objects.all(),
        required=False,
        write_only=True,
    )
    traveler_count = serializers.IntegerField(
        min_value=1,
        required=False,
        write_only=True,
    )
    traveler_slots = PublicDraftTravelerSlotSerializer(many=True, required=False)
    booking_reservation_amount_inr = serializers.IntegerField(read_only=True)
    booking_total_inr = serializers.IntegerField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "trip",
            "booking_state",
            "booking_contact",
            "booking_contact_name",
            "booking_contact_phone",
            "booking_contact_email",
            "traveler_count",
            "package",
            "traveler_slots",
            "booking_reservation_amount_inr",
            "booking_total_inr",
            "draft_expires_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "trip",
            "booking_state",
            "booking_contact",
            "booking_reservation_amount_inr",
            "booking_total_inr",
            "draft_expires_at",
            "created_at",
        ]
        extra_kwargs = {
            "booking_contact_name": {"write_only": True, "required": True, "allow_blank": False},
            "booking_contact_phone": {"write_only": True, "required": True, "allow_blank": False},
            "booking_contact_email": {"write_only": True, "required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        trip = self.context["trip"]
        try:
            intake = prepare_public_booking_intake(
                trip=trip,
                booking_contact_name=attrs.get("booking_contact_name", ""),
                booking_contact_phone=attrs.get("booking_contact_phone", ""),
                booking_contact_email=attrs.get("booking_contact_email", ""),
                selected_package_id=attrs["package"].id if attrs.get("package") else None,
                traveler_count=attrs.get("traveler_count"),
                traveler_slots=[
                    TravelerSlotIntakeInput(package_id=slot["package"].id)
                    for slot in attrs.get("traveler_slots", [])
                ],
                explicit_traveler_slots_supplied="traveler_slots" in self.initial_data,
                initial_data=self.initial_data,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(error_detail_from_django(exc)) from exc

        attrs["_booking_intake"] = intake

        readiness = public_booking_readiness(trip, requested_seats=intake.traveler_count)
        if not readiness.ready:
            raise serializers.ValidationError(
                {
                    "public_booking_gate": {
                        "reason_code": readiness.reason_code,
                        "message": readiness.message,
                    },
                }
            )

        return attrs

    def create(self, validated_data):
        intake = validated_data.pop("_booking_intake")
        validated_data.pop("package", None)
        validated_data.pop("traveler_count", None)
        validated_data.pop("traveler_slots", None)
        trip = self.context["trip"]
        return create_booking_from_intake(
            trip=trip,
            intake=intake,
            booking_state=Booking.BookingState.DRAFT,
        )

    def get_booking_contact(self, booking: Booking) -> dict[str, str]:
        return {
            "name": booking.booking_contact_name,
            "phone": booking.booking_contact_phone,
            "email": booking.booking_contact_email,
        }


class PublicPaymentAttemptSerializer(serializers.ModelSerializer):
    purpose_label = serializers.CharField(source="get_purpose_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    required_amount_to_reserve_inr = serializers.SerializerMethodField()
    collected_provider_payment_amount_inr = serializers.SerializerMethodField()
    checkout = serializers.SerializerMethodField()

    class Meta:
        model = PaymentAttempt
        fields = [
            "id",
            "booking",
            "provider",
            "purpose",
            "purpose_label",
            "status",
            "status_label",
            "amount_inr",
            "required_amount_to_reserve_inr",
            "collected_provider_payment_amount_inr",
            "provider_attempt_reference",
            "checkout_succeeded_at",
            "checkout",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "booking",
            "provider",
            "purpose",
            "purpose_label",
            "status",
            "status_label",
            "amount_inr",
            "required_amount_to_reserve_inr",
            "collected_provider_payment_amount_inr",
            "provider_attempt_reference",
            "checkout_succeeded_at",
            "checkout",
            "created_at",
        ]

    def get_required_amount_to_reserve_inr(self, attempt: PaymentAttempt) -> int:
        return required_amount_to_reserve_inr(attempt.booking)

    def get_collected_provider_payment_amount_inr(self, attempt: PaymentAttempt) -> int:
        return collected_provider_payment_amount_inr(attempt.booking)

    def get_checkout(self, attempt: PaymentAttempt) -> dict | None:
        checkout_payloads = self.context.get("checkout_payloads", {})
        if attempt.id in checkout_payloads:
            return checkout_payloads[attempt.id]
        return getattr(attempt, "checkout_payload", None)


class ProviderPaymentConfirmationSerializer(serializers.Serializer):
    payment_attempt = serializers.IntegerField(min_value=1)
    booking = serializers.IntegerField(min_value=1)
    provider = serializers.CharField(max_length=32)
    purpose = serializers.ChoiceField(choices=PaymentAttempt.Purpose.choices)
    provider_attempt_reference = serializers.CharField(max_length=160)
    provider_payment_reference = serializers.CharField(max_length=160)
    amount_inr = serializers.IntegerField(min_value=1)
    provider_fee_amount_inr = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
    )
    provider_net_settlement_amount_inr = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
    )


class BrowserCheckoutSuccessSerializer(serializers.Serializer):
    razorpay_payment_id = serializers.CharField(max_length=160, trim_whitespace=True)
    razorpay_order_id = serializers.CharField(max_length=160, trim_whitespace=True)
    razorpay_signature = serializers.CharField(max_length=256, trim_whitespace=True)


class ProviderPaymentSerializer(serializers.ModelSerializer):
    booking_state = serializers.CharField(source="booking.booking_state", read_only=True)
    collected_provider_payment_amount_inr = serializers.SerializerMethodField()
    required_amount_to_reserve_inr = serializers.SerializerMethodField()
    gross_amount_inr = serializers.IntegerField(source="amount_inr", read_only=True)
    platform_fee_inr = serializers.SerializerMethodField()

    class Meta:
        model = ProviderPayment
        fields = [
            "id",
            "booking",
            "booking_state",
            "payment_attempt",
            "provider",
            "amount_inr",
            "gross_amount_inr",
            "provider_fee_amount_inr",
            "provider_net_settlement_amount_inr",
            "platform_fee_inr",
            "collected_provider_payment_amount_inr",
            "required_amount_to_reserve_inr",
            "provider_payment_reference",
            "confirmed_at",
        ]
        read_only_fields = fields

    def get_collected_provider_payment_amount_inr(self, payment: ProviderPayment) -> int:
        return collected_provider_payment_amount_inr(payment.booking)

    def get_required_amount_to_reserve_inr(self, payment: ProviderPayment) -> int:
        return required_amount_to_reserve_inr(payment.booking)

    def get_platform_fee_inr(self, payment: ProviderPayment) -> int:
        return platform_fee_for_provider_payment_ledger_amount_inr(payment)


class OperationsManualBookingCreateSerializer(serializers.ModelSerializer):
    traveler_slots = PublicDraftTravelerSlotSerializer(many=True, write_only=True)

    class Meta:
        model = Booking
        fields = [
            "booking_contact_name",
            "booking_contact_phone",
            "booking_contact_email",
            "traveler_slots",
        ]
        extra_kwargs = {
            "booking_contact_name": {"required": True, "allow_blank": False},
            "booking_contact_phone": {"required": True, "allow_blank": False},
            "booking_contact_email": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        trip = self.context["trip"]
        try:
            attrs["_booking_intake"] = prepare_manual_booking_intake(
                trip=trip,
                booking_contact_name=attrs.get("booking_contact_name", ""),
                booking_contact_phone=attrs.get("booking_contact_phone", ""),
                booking_contact_email=attrs.get("booking_contact_email", ""),
                traveler_slots=[
                    TravelerSlotIntakeInput(package_id=slot["package"].id)
                    for slot in attrs.get("traveler_slots", [])
                ],
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(error_detail_from_django(exc)) from exc

        return attrs

    def create(self, validated_data):
        intake = validated_data.pop("_booking_intake")
        validated_data.pop("traveler_slots", None)
        return create_manual_booking(
            trip=self.context["trip"],
            booking_contact_name=validated_data["booking_contact_name"],
            booking_contact_phone=validated_data["booking_contact_phone"],
            booking_contact_email=validated_data.get("booking_contact_email", ""),
            package_ids=intake.package_ids,
        )


class LedgerEntrySerializer(serializers.ModelSerializer):
    entry_type_label = serializers.CharField(source="get_entry_type_display", read_only=True)

    class Meta:
        model = LedgerEntry
        fields = [
            "id",
            "entry_type",
            "entry_type_label",
            "amount_inr",
            "currency",
            "description",
            "provider_payment",
            "manual_payment",
            "opening_payment_record",
            "booking_adjustment",
            "refund_record",
            "occurred_at",
            "created_at",
        ]
        read_only_fields = fields


class BookingCancellationSerializer(serializers.Serializer):
    cancellation_reason = serializers.CharField(allow_blank=False)

    def save(self, **kwargs):
        return cancel_booking(
            self.context["booking"],
            cancellation_reason=self.validated_data["cancellation_reason"],
            actor=self.context.get("actor"),
        )


class TripDuplicateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if (start_date is None) != (end_date is None):
            raise serializers.ValidationError(
                {"end_date": "Trip Duplicate needs both start_date and end_date when dates change."}
            )
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "Trip end date cannot be before Trip Start Date."}
            )
        return attrs

    def save(self, **kwargs):
        return duplicate_trip(
            self.context["trip"],
            actor=self.context.get("actor"),
            title=self.validated_data.get("title", ""),
            start_date=self.validated_data.get("start_date"),
            end_date=self.validated_data.get("end_date"),
        )


class TripDateChangeSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    send_date_change_notice = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError(
                {"end_date": "Trip end date cannot be before Trip Start Date."}
            )
        return attrs

    def save(self, **kwargs):
        return change_trip_dates(
            self.context["trip"],
            start_date=self.validated_data["start_date"],
            end_date=self.validated_data["end_date"],
            actor=self.context.get("actor"),
            send_notice=self.validated_data.get("send_date_change_notice", True),
        )


class TripCancellationSerializer(serializers.Serializer):
    cancellation_reason = serializers.CharField(allow_blank=False)
    send_cancellation_notice = serializers.BooleanField(required=False, default=True)


class TripCompletionSerializer(serializers.Serializer):
    completed_booking_count = serializers.IntegerField(read_only=True)
    unchanged_booking_count = serializers.IntegerField(read_only=True)
    reconciliation_flags = serializers.ListField(read_only=True)

    @classmethod
    def from_result(cls, result):
        return cls(
            {
                "completed_booking_count": result.completed_booking_count,
                "unchanged_booking_count": result.unchanged_booking_count,
                "reconciliation_flags": result.reconciliation_flags,
            }
        )


class TravelerCancellationSerializer(serializers.Serializer):
    cancellation_reason = serializers.CharField(allow_blank=False)

    def save(self, **kwargs):
        return cancel_traveler(
            self.context["traveler_slot"],
            cancellation_reason=self.validated_data["cancellation_reason"],
            actor=self.context.get("actor"),
        )


class TravelerReplacementSerializer(serializers.Serializer):
    traveler_full_name = serializers.CharField(allow_blank=False)
    traveler_phone = serializers.CharField(allow_blank=False)
    traveler_email = serializers.EmailField(required=False, allow_blank=True)

    def save(self, **kwargs):
        return replace_traveler(
            self.context["traveler_slot"],
            traveler_full_name=self.validated_data["traveler_full_name"],
            traveler_phone=self.validated_data["traveler_phone"],
            traveler_email=self.validated_data.get("traveler_email", ""),
            actor=self.context.get("actor"),
        )


class TravelerAdditionSerializer(serializers.Serializer):
    package = serializers.PrimaryKeyRelatedField(queryset=TripPackage.objects.all())
    traveler_full_name = serializers.CharField(required=False, allow_blank=True)
    traveler_phone = serializers.CharField(required=False, allow_blank=True)
    traveler_email = serializers.EmailField(required=False, allow_blank=True)

    def validate_package(self, package: TripPackage) -> TripPackage:
        if package.trip_id != self.context["booking"].trip_id:
            raise serializers.ValidationError("Package must belong to the Booking Trip.")
        if package.is_withdrawn:
            raise serializers.ValidationError("Withdrawn Packages cannot be selected.")
        return package

    def save(self, **kwargs):
        return add_traveler_to_booking(
            self.context["booking"],
            package=self.validated_data["package"],
            traveler_full_name=self.validated_data.get("traveler_full_name", ""),
            traveler_phone=self.validated_data.get("traveler_phone", ""),
            traveler_email=self.validated_data.get("traveler_email", ""),
            actor=self.context.get("actor"),
        )


class TravelerPackageChangeSerializer(serializers.Serializer):
    package = serializers.PrimaryKeyRelatedField(queryset=TripPackage.objects.all())

    def validate_package(self, package: TripPackage) -> TripPackage:
        if package.trip_id != self.context["traveler_slot"].booking.trip_id:
            raise serializers.ValidationError("Package must belong to the Booking Trip.")
        if package.is_withdrawn:
            raise serializers.ValidationError("Withdrawn Packages cannot be selected.")
        return package

    def save(self, **kwargs):
        return change_traveler_package(
            self.context["traveler_slot"],
            package=self.validated_data["package"],
            actor=self.context.get("actor"),
        )


class InternalAdminPaymentAttemptSerializer(serializers.ModelSerializer):
    provider_label = serializers.CharField(source="get_provider_display", read_only=True)
    purpose_label = serializers.CharField(source="get_purpose_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PaymentAttempt
        fields = [
            "id",
            "booking",
            "provider",
            "provider_label",
            "purpose",
            "purpose_label",
            "status",
            "status_label",
            "amount_inr",
            "provider_attempt_reference",
            "checkout_succeeded_at",
            "failure_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class InternalAdminProviderPaymentSerializer(ProviderPaymentSerializer):
    class Meta(ProviderPaymentSerializer.Meta):
        fields = ProviderPaymentSerializer.Meta.fields + ["created_at", "updated_at"]
        read_only_fields = fields


class InternalAdminManualPaymentSerializer(OperationsManualPaymentSerializer):
    class Meta(OperationsManualPaymentSerializer.Meta):
        fields = OperationsManualPaymentSerializer.Meta.fields
        read_only_fields = fields


class InternalAdminBookingSerializer(serializers.ModelSerializer):
    traveler_slot_count = serializers.IntegerField(read_only=True)
    booking_total_inr = serializers.IntegerField(read_only=True)
    booking_reservation_amount_inr = serializers.IntegerField(read_only=True)
    payment_state = serializers.SerializerMethodField()
    reconciliation = serializers.SerializerMethodField()
    reconciliation_flags = serializers.SerializerMethodField()
    payment_attempts = serializers.SerializerMethodField()
    provider_payments = serializers.SerializerMethodField()
    manual_payments = serializers.SerializerMethodField()
    notifications = serializers.SerializerMethodField()
    booking_import_rows = serializers.SerializerMethodField()
    activity_logs = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "trip",
            "booking_state",
            "booking_contact_name",
            "booking_contact_phone",
            "booking_contact_email",
            "traveler_slot_count",
            "booking_total_inr",
            "booking_reservation_amount_inr",
            "payment_state",
            "reconciliation",
            "reconciliation_flags",
            "payment_attempts",
            "provider_payments",
            "manual_payments",
            "notifications",
            "booking_import_rows",
            "activity_logs",
            "draft_expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_payment_state(self, booking: Booking) -> str:
        return derived_payment_state(booking)

    def get_reconciliation(self, booking: Booking) -> dict[str, int]:
        return reconciliation_payload(booking)

    def get_reconciliation_flags(self, booking: Booking) -> list[str]:
        return reconciliation_flags_for_booking(booking)

    def get_payment_attempts(self, booking: Booking) -> list[dict]:
        return InternalAdminPaymentAttemptSerializer(booking.payment_attempts.all(), many=True).data

    def get_provider_payments(self, booking: Booking) -> list[dict]:
        return InternalAdminProviderPaymentSerializer(
            booking.provider_payments.all(),
            many=True,
        ).data

    def get_manual_payments(self, booking: Booking) -> list[dict]:
        return InternalAdminManualPaymentSerializer(booking.manual_payments.all(), many=True).data

    def get_notifications(self, booking: Booking) -> list[dict]:
        return NotificationSerializer(booking.notifications.all(), many=True).data

    def get_booking_import_rows(self, booking: Booking) -> list[dict]:
        return BookingImportRowSerializer(booking.import_rows.all(), many=True).data

    def get_activity_logs(self, booking: Booking) -> list[dict]:
        return ActivityLogSerializer(booking.activity_logs.all(), many=True).data


class InternalAdminTripSerializer(serializers.ModelSerializer):
    available_seats = serializers.SerializerMethodField()
    effective_booking_availability = serializers.SerializerMethodField()
    operational_metrics = serializers.SerializerMethodField()
    booking_count = serializers.IntegerField(source="bookings.count", read_only=True)
    reconciliation_flags = serializers.SerializerMethodField()
    booking_imports = serializers.SerializerMethodField()
    activity_logs = serializers.SerializerMethodField()
    bookings = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id",
            "organizer",
            "title",
            "slug",
            "start_date",
            "end_date",
            "capacity",
            "available_seats",
            "publication_state",
            "booking_availability",
            "effective_booking_availability",
            "public_url_path",
            "booking_count",
            "operational_metrics",
            "reconciliation_flags",
            "booking_imports",
            "activity_logs",
            "bookings",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_available_seats(self, trip: Trip) -> int:
        return available_seats(trip)

    def get_effective_booking_availability(self, trip: Trip) -> str:
        from organizers.services import effective_booking_availability

        return effective_booking_availability(trip)

    def get_operational_metrics(self, trip: Trip) -> dict:
        from trip_operations.metrics import operational_metrics

        metrics = operational_metrics(trip)
        return {
            "unpaid_bookings": metrics.unpaid_bookings,
            "overdue_amount_inr": metrics.overdue_amount_inr,
            "pending_manual_payments": metrics.pending_manual_payments,
            "missing_requirements": metrics.missing_requirements,
            "available_seats": metrics.available_seats,
            "reserved_travelers": metrics.reserved_travelers,
            "core_operational_booking_count": metrics.core_operational_booking_count,
            "booking_state_counts": metrics.booking_state_counts,
        }

    def get_reconciliation_flags(self, trip: Trip) -> list[dict]:
        flagged = []
        for booking in trip.bookings.all():
            flags = reconciliation_flags_for_booking(booking)
            if flags:
                flagged.append({"booking": booking.id, "flags": flags})
        return flagged

    def get_booking_imports(self, trip: Trip) -> list[dict]:
        return OperationsBookingImportResultSerializer(
            trip.booking_imports.all(),
            many=True,
        ).data

    def get_activity_logs(self, trip: Trip) -> list[dict]:
        return ActivityLogSerializer(trip.activity_logs.all(), many=True).data

    def get_bookings(self, trip: Trip) -> list[dict]:
        return InternalAdminBookingSerializer(trip.bookings.all(), many=True).data


class InternalAdminOrganizerListSerializer(serializers.ModelSerializer):
    identity_logo_url = serializers.SerializerMethodField()
    payment_setup = serializers.SerializerMethodField()
    trip_count = serializers.IntegerField(source="trips.count", read_only=True)
    booking_count = serializers.SerializerMethodField()
    reconciliation_flag_count = serializers.SerializerMethodField()

    class Meta:
        model = Organizer
        fields = [
            "id",
            "name",
            "slug",
            "identity_name",
            "identity_logo_url",
            "payment_setup",
            "trip_count",
            "booking_count",
            "reconciliation_flag_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_payment_setup(self, organizer: Organizer) -> dict:
        return support_payment_setup_payload(organizer)

    def get_identity_logo_url(self, organizer: Organizer) -> str:
        return organizer_identity_payload(
            organizer,
            request=self.context.get("request"),
        )["logo_url"]

    def get_booking_count(self, organizer: Organizer) -> int:
        return Booking.objects.filter(trip__organizer=organizer).count()

    def get_reconciliation_flag_count(self, organizer: Organizer) -> int:
        count = 0
        bookings = Booking.objects.filter(trip__organizer=organizer).prefetch_related(
            "payment_attempts",
            "manual_payments",
            "ledger_entries",
            "traveler_slots__package",
            "import_rows",
        )
        for booking in bookings:
            if reconciliation_flags_for_booking(booking):
                count += 1
        return count


class InternalAdminOrganizerDetailSerializer(InternalAdminOrganizerListSerializer):
    trips = serializers.SerializerMethodField()
    platform_fee_statements = serializers.SerializerMethodField()
    provider_connection_tests = serializers.SerializerMethodField()
    activity_logs = serializers.SerializerMethodField()

    class Meta(InternalAdminOrganizerListSerializer.Meta):
        fields = InternalAdminOrganizerListSerializer.Meta.fields + [
            "trips",
            "platform_fee_statements",
            "provider_connection_tests",
            "activity_logs",
        ]
        read_only_fields = fields

    def get_trips(self, organizer: Organizer) -> list[dict]:
        return InternalAdminTripSerializer(organizer.trips.all(), many=True).data

    def get_platform_fee_statements(self, organizer: Organizer) -> list[dict]:
        return InternalAdminPlatformFeeStatementSerializer(
            organizer.platform_fee_statements.all(),
            many=True,
        ).data

    def get_provider_connection_tests(self, organizer: Organizer) -> list[dict]:
        return ProviderConnectionTestResultSerializer(
            organizer.provider_connection_test_results.all(),
            many=True,
        ).data

    def get_activity_logs(self, organizer: Organizer) -> list[dict]:
        return ActivityLogSerializer(organizer.activity_logs.all(), many=True).data


class OperationsBookingDetailSerializer(serializers.ModelSerializer):
    traveler_slot_count = serializers.IntegerField(read_only=True)
    booking_total_inr = serializers.IntegerField(read_only=True)
    booking_reservation_amount_inr = serializers.IntegerField(read_only=True)
    payment_state = serializers.SerializerMethodField()
    reconciliation = serializers.SerializerMethodField()
    confirmation_requirements = serializers.SerializerMethodField()
    financial_ledger = serializers.SerializerMethodField()
    payment_exceptions = serializers.SerializerMethodField()
    manual_payments = serializers.SerializerMethodField()
    notifications = serializers.SerializerMethodField()
    traveler_slots = serializers.SerializerMethodField()
    attendance_summary = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "trip",
            "booking_state",
            "booking_contact_name",
            "booking_contact_phone",
            "booking_contact_email",
            "traveler_slot_count",
            "booking_total_inr",
            "booking_reservation_amount_inr",
            "payment_state",
            "reconciliation",
            "confirmation_requirements",
            "traveler_slots",
            "attendance_summary",
            "financial_ledger",
            "payment_exceptions",
            "manual_payments",
            "notifications",
            "draft_expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_payment_state(self, booking: Booking) -> str:
        return derived_payment_state(booking)

    def get_reconciliation(self, booking: Booking) -> dict[str, int]:
        reconciliation = booking_reconciliation(booking)
        return {
            "booking_total_inr": reconciliation.booking_total_inr,
            "effective_booking_total_inr": reconciliation.effective_booking_total_inr,
            "collected_inr": reconciliation.collected_inr,
            "due_inr": reconciliation.due_inr,
            "adjusted_inr": reconciliation.adjusted_inr,
            "refunded_inr": reconciliation.refunded_inr,
            "refund_due_inr": reconciliation.refund_due_inr,
            "overdue_inr": reconciliation.overdue_inr,
            "platform_fee_inr": reconciliation.platform_fee_inr,
        }

    def get_confirmation_requirements(self, booking: Booking) -> dict:
        return OperationsBookingListItemSerializer().get_confirmation_requirements(booking)

    def get_financial_ledger(self, booking: Booking) -> dict[str, list[dict]]:
        return {
            "currency": "INR",
            "entries": LedgerEntrySerializer(booking.ledger_entries.all(), many=True).data,
        }

    def get_payment_exceptions(self, booking: Booking) -> list[dict]:
        return PaymentExceptionSerializer(booking.payment_exceptions.all(), many=True).data

    def get_manual_payments(self, booking: Booking) -> list[dict]:
        return OperationsManualPaymentSerializer(
            booking.manual_payments.select_related("booking").all(),
            many=True,
            context={"include_payment_proof_download_url": True},
        ).data

    def get_notifications(self, booking: Booking) -> list[dict]:
        return NotificationSerializer(booking.notifications.all(), many=True).data

    def get_traveler_slots(self, booking: Booking) -> list[dict]:
        return OperationsTravelerSlotSerializer(booking.traveler_slots.all(), many=True).data

    def get_attendance_summary(self, booking: Booking) -> dict[str, int]:
        return OperationsBookingListItemSerializer().get_attendance_summary(booking)


class TravelerDocumentSerializer(serializers.ModelSerializer):
    document_kind_label = serializers.CharField(source="get_document_kind_display", read_only=True)
    document_state_label = serializers.CharField(
        source="get_document_state_display",
        read_only=True,
    )
    is_sensitive_traveler_information = serializers.BooleanField(read_only=True)
    exclude_from_default_exports = serializers.BooleanField(read_only=True)
    has_file = serializers.SerializerMethodField()

    class Meta:
        model = TravelerDocument
        fields = [
            "id",
            "traveler_slot",
            "document_kind",
            "document_kind_label",
            "label",
            "document_state",
            "document_state_label",
            "original_filename",
            "content_type",
            "file_size",
            "has_file",
            "rejection_reason",
            "is_sensitive_traveler_information",
            "exclude_from_default_exports",
            "submitted_at",
            "reviewed_at",
            "reviewed_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_has_file(self, document: TravelerDocument) -> bool:
        return bool(document.file)


class TravelerDocumentSubmissionSerializer(serializers.ModelSerializer):
    file = serializers.FileField(required=True)

    class Meta:
        model = TravelerDocument
        fields = ["document_kind", "label", "file"]

    def validate_label(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Traveler Document label is required.")
        return value

    def create(self, validated_data):
        traveler_slot = self.context["traveler_slot"]
        return submit_traveler_document(
            traveler_slot=traveler_slot,
            document_kind=validated_data.get(
                "document_kind",
                TravelerDocument.DocumentKind.IDENTITY,
            ),
            label=validated_data.get("label", "Identity Document"),
            uploaded_file=validated_data["file"],
        )


class TravelerDocumentReviewSerializer(serializers.Serializer):
    document_state = serializers.ChoiceField(
        choices=[
            TravelerDocument.DocumentState.APPROVED,
            TravelerDocument.DocumentState.REJECTED,
        ]
    )
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if (
            attrs["document_state"] == TravelerDocument.DocumentState.REJECTED
            and not attrs.get("rejection_reason", "").strip()
        ):
            raise serializers.ValidationError(
                {"rejection_reason": "Rejected Traveler Documents need a reason."}
            )
        return attrs

    def save(self, **kwargs):
        try:
            return review_traveler_document(
                document=self.context["document"],
                document_state=self.validated_data["document_state"],
                rejection_reason=self.validated_data.get("rejection_reason", ""),
                reviewer=self.context["reviewer"],
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc


class TravelLogisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelerSlot
        fields = ["arrival_details", "departure_details", "pickup_location", "logistics_note"]

    def update(self, instance, validated_data):
        return update_travel_logistics(
            instance,
            arrival_details=validated_data.get(
                "arrival_details",
                instance.arrival_details,
            ),
            departure_details=validated_data.get(
                "departure_details",
                instance.departure_details,
            ),
            pickup_location=validated_data.get(
                "pickup_location",
                instance.pickup_location,
            ),
            logistics_note=validated_data.get("logistics_note", instance.logistics_note),
        )


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelerSlot
        fields = [
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relationship",
        ]

    def update(self, instance, validated_data):
        try:
            return update_emergency_contact(
                instance,
                emergency_contact_name=validated_data.get(
                    "emergency_contact_name",
                    instance.emergency_contact_name,
                ),
                emergency_contact_phone=validated_data.get(
                    "emergency_contact_phone",
                    instance.emergency_contact_phone,
                ),
                emergency_contact_relationship=validated_data.get(
                    "emergency_contact_relationship",
                    instance.emergency_contact_relationship,
                ),
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc


class MedicalDisclosureSerializer(serializers.ModelSerializer):
    is_sensitive_traveler_information = serializers.BooleanField(read_only=True, default=True)
    exclude_from_default_exports = serializers.BooleanField(read_only=True, default=True)

    class Meta:
        model = TravelerSlot
        fields = [
            "medical_disclosure",
            "medical_disclosure_submitted_at",
            "is_sensitive_traveler_information",
            "exclude_from_default_exports",
        ]
        read_only_fields = [
            "medical_disclosure_submitted_at",
            "is_sensitive_traveler_information",
            "exclude_from_default_exports",
        ]

    def update(self, instance, validated_data):
        try:
            return update_medical_disclosure(
                instance,
                medical_disclosure=validated_data["medical_disclosure"],
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc


class TravelerIdentitySerializer(serializers.ModelSerializer):
    package_name = serializers.CharField(source="package.name", read_only=True)
    is_traveler = serializers.BooleanField(read_only=True)
    attendance_state_label = serializers.CharField(
        source="get_attendance_state_display",
        read_only=True,
    )
    documents = TravelerDocumentSerializer(many=True, read_only=True)
    readiness = serializers.SerializerMethodField()
    travel_logistics = serializers.SerializerMethodField()
    emergency_contact = serializers.SerializerMethodField()
    medical_disclosure_status = serializers.SerializerMethodField()

    class Meta:
        model = TravelerSlot
        fields = [
            "id",
            "position",
            "package_name",
            "traveler_full_name",
            "traveler_phone",
            "traveler_email",
            "is_traveler",
            "attendance_state",
            "attendance_state_label",
            "attendance_marked_at",
            "attendance_marked_by",
            "readiness",
            "documents",
            "travel_logistics",
            "emergency_contact",
            "rooming_notes",
            "medical_disclosure_status",
        ]
        read_only_fields = [
            "id",
            "position",
            "package_name",
            "is_traveler",
            "attendance_state",
            "attendance_state_label",
            "attendance_marked_at",
            "attendance_marked_by",
        ]

    def update(self, instance, validated_data):
        try:
            return update_traveler_identity_details(
                instance,
                traveler_full_name=validated_data.get(
                    "traveler_full_name",
                    instance.traveler_full_name,
                ),
                traveler_phone=validated_data.get("traveler_phone", instance.traveler_phone),
                traveler_email=validated_data.get("traveler_email", instance.traveler_email),
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def get_readiness(self, traveler_slot: TravelerSlot) -> dict:
        return traveler_portal_readiness_payload(traveler_slot)

    def get_travel_logistics(self, traveler_slot: TravelerSlot) -> dict:
        return {
            "arrival_details": traveler_slot.arrival_details,
            "departure_details": traveler_slot.departure_details,
            "pickup_location": traveler_slot.pickup_location,
            "logistics_note": traveler_slot.logistics_note,
        }

    def get_emergency_contact(self, traveler_slot: TravelerSlot) -> dict:
        return {
            "name": traveler_slot.emergency_contact_name,
            "phone": traveler_slot.emergency_contact_phone,
            "relationship": traveler_slot.emergency_contact_relationship,
        }

    def get_medical_disclosure_status(self, traveler_slot: TravelerSlot) -> dict:
        return {
            "submitted": traveler_slot.has_medical_disclosure,
            "submitted_at": traveler_slot.medical_disclosure_submitted_at,
            "is_sensitive_traveler_information": True,
            "exclude_from_default_exports": True,
        }


class TravelerPortalSerializer(serializers.Serializer):
    access_scope = serializers.CharField()
    access_expires_at = serializers.DateTimeField()
    organizer_identity = serializers.DictField()
    trip = serializers.DictField()
    booking = serializers.DictField()
    booking_contact = serializers.DictField()
    balance_payment = serializers.DictField()
    manual_payments = OperationsManualPaymentSerializer(many=True)
    traveler_slots = TravelerIdentitySerializer(many=True)

    @classmethod
    def from_access_link(cls, access_link: BookingAccessLink, request=None, token: str = ""):
        booking = access_link.booking
        traveler_slots = traveler_slots_for_access_link(access_link)

        return cls(
            {
                "access_scope": access_link.scope,
                "access_expires_at": access_link.expires_at,
                "organizer_identity": organizer_identity_payload(
                    booking.trip.organizer,
                    request=request,
                ),
                "trip": {
                    "id": booking.trip.id,
                    "title": booking.trip.title,
                    "start_date": booking.trip.start_date,
                    "end_date": booking.trip.end_date,
                    "confirmation_requirements": {
                        "traveler_documents": booking.trip.requires_traveler_documents,
                        "traveler_identity_details": (
                            booking.trip.requires_traveler_identity_details
                        ),
                        "travel_logistics": booking.trip.requires_travel_logistics,
                        "emergency_contact": booking.trip.requires_emergency_contact,
                        "medical_disclosure": booking.trip.requires_medical_disclosure,
                        "full_payment_before_confirmation": (
                            booking.trip.requires_full_payment_before_confirmation
                        ),
                    },
                },
                "booking": {
                    "id": booking.id,
                    "booking_state": booking.booking_state,
                    "booking_state_label": booking.get_booking_state_display(),
                    "booking_total_inr": booking.booking_total_inr,
                    "booking_reservation_amount_inr": booking.booking_reservation_amount_inr,
                },
                "balance_payment": balance_payment_availability_payload(
                    booking,
                    access_scope=access_link.scope,
                    token=token,
                ),
                "booking_contact": {
                    "name": booking.booking_contact_name,
                    "phone": booking.booking_contact_phone,
                    "email": booking.booking_contact_email,
                },
                "manual_payments": list(
                    booking.manual_payments.select_related("booking").order_by(
                        "-submitted_at",
                        "-id",
                    )
                ),
                "traveler_slots": traveler_slots,
            }
        )


class AccessLinkIssueSerializer(serializers.Serializer):
    scope = serializers.ChoiceField(choices=BookingAccessLink.Scope.choices)
    traveler_slot = serializers.PrimaryKeyRelatedField(
        queryset=TravelerSlot.objects.all(),
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        booking = self.context["booking"]
        scope = attrs["scope"]
        traveler_slot = attrs.get("traveler_slot")
        try:
            validate_access_link_issue_request(
                booking=booking,
                scope=scope,
                traveler_slot=traveler_slot,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(error_detail_from_django(exc)) from exc
        return attrs

    def save(self, **kwargs):
        booking = self.context["booking"]
        issued = issue_access_link(
            booking=booking,
            scope=self.validated_data["scope"],
            traveler_slot=self.validated_data.get("traveler_slot"),
        )
        return {
            "id": issued.access_link.id,
            "scope": issued.access_link.scope,
            "booking": booking.id,
            "traveler_slot": (
                issued.access_link.traveler_slot_id if issued.access_link.traveler_slot_id else None
            ),
            "token": issued.token,
            "expires_at": issued.access_link.expires_at,
            "revoked_at": issued.access_link.revoked_at,
        }


class BookingContactUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            "booking_contact_name",
            "booking_contact_phone",
            "booking_contact_email",
        ]
        extra_kwargs = {
            "booking_contact_name": {"required": True, "allow_blank": False},
            "booking_contact_phone": {"required": True, "allow_blank": False},
            "booking_contact_email": {"required": False, "allow_blank": True},
        }
