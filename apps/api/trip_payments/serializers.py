from __future__ import annotations

from pathlib import Path

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from organizers.models import Organizer
from trip_bookings.intake import prepare_public_booking_intake
from trip_payments import internal_admin_review
from trip_payments.adjustments import create_booking_adjustment, create_refund_record
from trip_payments.financial_ledger import (
    booking_reconciliation_payload,
    derived_payment_state,
)
from trip_payments.manual_review import (
    create_organizer_entered_manual_payment,
    create_public_qr_manual_payment_submission,
    create_traveler_submitted_manual_payment,
)
from trip_payments.models import (
    BookingAdjustment,
    ManualPayment,
    PaymentException,
    PlatformFeeStatement,
    RefundRecord,
)
from trip_payments.payment_exceptions import resolve_late_confirmed_payment_exception
from trip_payments.platform_fees import (
    apply_platform_fee_statement_aggregation,
    generate_platform_fee_statement,
)
from trip_travelers.models import TravelerSlot
from trips.models import TripPackage

ALLOWED_PAYMENT_PROOF_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}
ALLOWED_PAYMENT_PROOF_EXTENSIONS = {".jpg", ".jpeg", ".pdf", ".png", ".webp"}
MAX_PAYMENT_PROOF_BYTES = 5 * 1024 * 1024


def error_detail_from_django(exc: DjangoValidationError):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return exc.messages


def validate_payment_proof_upload(upload) -> None:
    if not upload:
        raise DjangoValidationError("Payment Proof is required.")
    if getattr(upload, "size", 0) > MAX_PAYMENT_PROOF_BYTES:
        raise DjangoValidationError("Payment Proof must be 5 MB or smaller.")

    extension = Path(upload.name).suffix.lower()
    if extension not in ALLOWED_PAYMENT_PROOF_EXTENSIONS:
        raise DjangoValidationError("Upload a PNG, JPG, WebP, or PDF Payment Proof.")

    content_type = getattr(upload, "content_type", "")
    if content_type not in ALLOWED_PAYMENT_PROOF_CONTENT_TYPES:
        raise DjangoValidationError("Upload a PNG, JPG, WebP, or PDF Payment Proof.")


def reconciliation_payload(booking) -> dict[str, int]:
    return booking_reconciliation_payload(booking)


class PaymentExceptionSerializer(serializers.ModelSerializer):
    exception_type_label = serializers.CharField(
        source="get_exception_type_display",
        read_only=True,
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    booking_state = serializers.CharField(source="booking.booking_state", read_only=True)
    provider_event_type_label = serializers.CharField(
        source="get_provider_event_type_display",
        read_only=True,
    )

    class Meta:
        model = PaymentException
        fields = [
            "id",
            "organizer",
            "trip",
            "booking",
            "booking_state",
            "payment_attempt",
            "provider_payment",
            "exception_type",
            "exception_type_label",
            "status",
            "status_label",
            "provider",
            "amount_inr",
            "provider_attempt_reference",
            "provider_payment_reference",
            "provider_event_type",
            "provider_event_type_label",
            "provider_dispute_reference",
            "mismatch_reasons",
            "details",
            "resolution_note",
            "resolved_by",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PaymentExceptionResolutionSerializer(serializers.Serializer):
    resolution_note = serializers.CharField(
        allow_blank=True,
        required=False,
        max_length=1000,
        trim_whitespace=True,
    )

    def save(self, **kwargs):
        return resolve_late_confirmed_payment_exception(
            self.context["payment_exception"],
            actor=self.context.get("actor"),
            resolution_note=self.validated_data.get("resolution_note", ""),
        )


class InternalAdminPaymentExceptionSerializer(PaymentExceptionSerializer):
    organizer_name = serializers.CharField(source="organizer.name", read_only=True)
    trip_title = serializers.CharField(source="trip.title", read_only=True)
    booking_contact_name = serializers.CharField(
        source="booking.booking_contact_name",
        read_only=True,
    )
    available_review_actions = serializers.SerializerMethodField()

    class Meta(PaymentExceptionSerializer.Meta):
        fields = PaymentExceptionSerializer.Meta.fields + [
            "organizer_name",
            "trip_title",
            "booking_contact_name",
            "available_review_actions",
        ]
        read_only_fields = fields

    def get_available_review_actions(self, payment_exception: PaymentException) -> list[str]:
        if (
            payment_exception.exception_type
            == PaymentException.ExceptionType.LATE_CONFIRMED_PAYMENT
            and payment_exception.status == PaymentException.Status.OPEN
        ):
            return ["resolve_booking_operations"]
        return []


class InternalAdminPaymentExceptionResolutionSerializer(serializers.Serializer):
    resolution_note = serializers.CharField(
        allow_blank=True,
        required=False,
        max_length=1000,
        trim_whitespace=True,
    )

    def save(self, **kwargs):
        return internal_admin_review.resolve_payment_exception_for_staff_review(
            self.context["payment_exception"],
            actor=self.context.get("actor"),
            resolution_note=self.validated_data.get("resolution_note", ""),
        )


class InternalAdminPlatformFeeStatementSerializer(serializers.ModelSerializer):
    organizer_name = serializers.CharField(source="organizer.name", read_only=True)
    period_end = serializers.DateField(read_only=True)
    period_label = serializers.CharField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PlatformFeeStatement
        fields = [
            "id",
            "organizer",
            "organizer_name",
            "period_start",
            "period_end",
            "period_label",
            "currency",
            "provider_payment_count",
            "gross_provider_payment_amount_inr",
            "platform_fee_amount_inr",
            "status",
            "status_label",
            "notes",
            "generated_at",
            "issued_at",
            "collected_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class InternalAdminPlatformFeeStatementManageSerializer(serializers.ModelSerializer):
    organizer = serializers.PrimaryKeyRelatedField(queryset=Organizer.objects.all())
    refresh_totals = serializers.BooleanField(required=False, default=False, write_only=True)

    class Meta:
        model = PlatformFeeStatement
        fields = [
            "organizer",
            "period_start",
            "status",
            "notes",
            "issued_at",
            "collected_at",
            "refresh_totals",
        ]
        extra_kwargs = {
            "period_start": {"required": False},
            "status": {"required": False},
            "notes": {"required": False},
            "issued_at": {"required": False},
            "collected_at": {"required": False},
        }

    def create(self, validated_data):
        validated_data.pop("refresh_totals", None)
        organizer = validated_data.pop("organizer")
        period_start = validated_data.pop("period_start", None)
        if period_start is None:
            raise serializers.ValidationError(
                {"period_start": "Platform Fee Statement requires a monthly period."}
            )
        status = validated_data.pop("status", None)
        notes = validated_data.pop("notes", None)
        statement = generate_platform_fee_statement(
            organizer,
            period_start,
            status=status,
            notes=notes,
        )
        for field in ("issued_at", "collected_at"):
            if field in validated_data:
                setattr(statement, field, validated_data[field])
        if validated_data:
            statement.save()
        return statement

    def update(self, instance, validated_data):
        refresh_totals = validated_data.pop("refresh_totals", False)
        validated_data.pop("organizer", None)
        validated_data.pop("period_start", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if refresh_totals:
            apply_platform_fee_statement_aggregation(instance)
        instance.save()
        return instance


class PublicQrManualPaymentSubmissionSerializer(serializers.Serializer):
    booking_contact_name = serializers.CharField(max_length=160, trim_whitespace=True)
    booking_contact_phone = serializers.CharField(max_length=40, trim_whitespace=True)
    booking_contact_email = serializers.EmailField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    traveler_count = serializers.IntegerField(min_value=1)
    package = serializers.PrimaryKeyRelatedField(queryset=TripPackage.objects.all())
    payment_reference = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=160,
        trim_whitespace=True,
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        trim_whitespace=True,
    )
    payment_proof = serializers.FileField(required=True, allow_empty_file=False)

    def validate_payment_proof(self, value):
        try:
            validate_payment_proof_upload(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    def validate(self, attrs):
        trip = self.context["trip"]
        try:
            prepare_public_booking_intake(
                trip=trip,
                booking_contact_name=attrs.get("booking_contact_name", ""),
                booking_contact_phone=attrs.get("booking_contact_phone", ""),
                booking_contact_email=attrs.get("booking_contact_email", ""),
                selected_package_id=attrs["package"].id if attrs.get("package") else None,
                traveler_count=attrs.get("traveler_count"),
                initial_data=self.initial_data,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(error_detail_from_django(exc)) from exc
        return attrs

    def create(self, validated_data):
        trip = self.context["trip"]
        return create_public_qr_manual_payment_submission(
            trip=trip,
            booking_contact_name=validated_data["booking_contact_name"],
            booking_contact_phone=validated_data["booking_contact_phone"],
            booking_contact_email=validated_data.get("booking_contact_email", ""),
            selected_package_id=validated_data["package"].id,
            traveler_count=validated_data["traveler_count"],
            payment_reference=validated_data.get("payment_reference", ""),
            note=validated_data.get("note", ""),
            payment_proof=validated_data["payment_proof"],
            initial_data=self.initial_data,
        )


class OperationsManualPaymentSerializer(serializers.ModelSerializer):
    payment_proof = serializers.FileField(
        write_only=True,
        required=False,
        allow_empty_file=False,
    )
    source_label = serializers.CharField(source="get_source_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    has_payment_proof = serializers.SerializerMethodField()
    payment_proof_status_label = serializers.SerializerMethodField()
    payment_proof_download_url = serializers.SerializerMethodField()
    is_sensitive_payment_information = serializers.BooleanField(read_only=True)
    exclude_from_default_exports = serializers.BooleanField(read_only=True)
    booking_state = serializers.CharField(source="booking.booking_state", read_only=True)
    booking_contact_name = serializers.CharField(
        source="booking.booking_contact_name",
        read_only=True,
    )
    traveler_count = serializers.IntegerField(
        source="booking.traveler_slot_count",
        read_only=True,
    )
    package_context = serializers.SerializerMethodField()
    payment_state = serializers.SerializerMethodField()
    reconciliation = serializers.SerializerMethodField()
    send_payment_acknowledgement = serializers.BooleanField(
        required=False,
        default=False,
        write_only=True,
    )

    class Meta:
        model = ManualPayment
        fields = [
            "id",
            "booking",
            "booking_state",
            "source",
            "source_label",
            "status",
            "status_label",
            "amount_inr",
            "payment_reference",
            "payment_proof",
            "has_payment_proof",
            "payment_proof_status_label",
            "payment_proof_download_url",
            "original_filename",
            "content_type",
            "file_size",
            "booking_contact_name",
            "traveler_count",
            "package_context",
            "note",
            "payment_state",
            "reconciliation",
            "is_sensitive_payment_information",
            "exclude_from_default_exports",
            "approved_by",
            "approved_at",
            "submitted_at",
            "created_at",
            "send_payment_acknowledgement",
        ]
        read_only_fields = [
            "id",
            "booking",
            "booking_state",
            "source",
            "source_label",
            "status",
            "status_label",
            "has_payment_proof",
            "payment_proof_status_label",
            "payment_proof_download_url",
            "original_filename",
            "content_type",
            "file_size",
            "booking_contact_name",
            "traveler_count",
            "package_context",
            "payment_state",
            "reconciliation",
            "is_sensitive_payment_information",
            "exclude_from_default_exports",
            "approved_by",
            "approved_at",
            "submitted_at",
            "created_at",
        ]
        extra_kwargs = {
            "amount_inr": {"required": True, "min_value": 1},
            "payment_reference": {"required": False, "allow_blank": True},
            "payment_proof": {"required": False, "allow_empty_file": False},
            "note": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data):
        send_payment_acknowledgement = validated_data.pop("send_payment_acknowledgement", False)
        return create_organizer_entered_manual_payment(
            booking=self.context["booking"],
            amount_inr=validated_data["amount_inr"],
            actor=self.context.get("actor"),
            payment_reference=validated_data.get("payment_reference", ""),
            note=validated_data.get("note", ""),
            payment_proof=validated_data.get("payment_proof"),
            send_payment_acknowledgement=send_payment_acknowledgement,
        )

    def get_has_payment_proof(self, payment: ManualPayment) -> bool:
        return bool(payment.payment_proof)

    def get_payment_proof_status_label(self, payment: ManualPayment) -> str:
        if not payment.payment_proof:
            return "No Payment Proof"
        if payment.is_sensitive_payment_information:
            return "Payment Proof attached, Sensitive Payment Information"
        return "Payment Proof attached"

    def get_payment_proof_download_url(self, payment: ManualPayment) -> str:
        if not payment.payment_proof or not self.context.get(
            "include_payment_proof_download_url",
            False,
        ):
            return ""
        organizer_id = payment.booking.trip.organizer_id
        return (
            f"/api/operations/organizers/{organizer_id}/manual-payments/"
            f"{payment.id}/proof-download/"
        )

    def get_package_context(self, payment: ManualPayment) -> str:
        package_counts: dict[str, int] = {}
        for slot in payment.booking.traveler_slots.select_related("package").all():
            if slot.traveler_state == TravelerSlot.TravelerState.REPLACED:
                continue
            package_name = slot.package.name if slot.package_id else "Package"
            package_counts[package_name] = package_counts.get(package_name, 0) + 1

        if not package_counts:
            return "No Package selected"

        return ", ".join(
            f"{name} x {count}"
            for name, count in sorted(package_counts.items(), key=lambda item: item[0])
        )

    def get_payment_state(self, payment: ManualPayment) -> str:
        return derived_payment_state(payment.booking)

    def get_reconciliation(self, payment: ManualPayment) -> dict[str, int]:
        return booking_reconciliation_payload(payment.booking)


class TravelerManualPaymentSubmissionSerializer(serializers.ModelSerializer):
    payment_proof = serializers.FileField(required=True, allow_empty_file=False)

    class Meta:
        model = ManualPayment
        fields = [
            "id",
            "amount_inr",
            "payment_reference",
            "payment_proof",
            "note",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "amount_inr": {"required": True, "min_value": 1},
            "payment_reference": {"required": False, "allow_blank": True},
            "note": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data):
        return create_traveler_submitted_manual_payment(
            booking=self.context["booking"],
            amount_inr=validated_data["amount_inr"],
            payment_reference=validated_data.get("payment_reference", ""),
            note=validated_data.get("note", ""),
            payment_proof=validated_data.get("payment_proof"),
        )


class ManualPaymentDecisionSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class BookingAdjustmentSerializer(serializers.ModelSerializer):
    booking_state = serializers.CharField(source="booking.booking_state", read_only=True)
    payment_state = serializers.SerializerMethodField()
    reconciliation = serializers.SerializerMethodField()

    class Meta:
        model = BookingAdjustment
        fields = [
            "id",
            "booking",
            "booking_state",
            "amount_inr",
            "adjustment_reason",
            "payment_state",
            "reconciliation",
            "recorded_by",
            "occurred_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "booking",
            "booking_state",
            "payment_state",
            "reconciliation",
            "recorded_by",
            "occurred_at",
            "created_at",
        ]
        extra_kwargs = {
            "amount_inr": {"required": True},
            "adjustment_reason": {"required": True, "allow_blank": False},
        }

    def validate_amount_inr(self, value: int) -> int:
        if value == 0:
            raise serializers.ValidationError("Booking Adjustment amount cannot be zero.")
        return value

    def create(self, validated_data):
        return create_booking_adjustment(
            booking=self.context["booking"],
            amount_inr=validated_data["amount_inr"],
            adjustment_reason=validated_data["adjustment_reason"],
            actor=self.context.get("actor"),
        )

    def get_payment_state(self, adjustment: BookingAdjustment) -> str:
        return derived_payment_state(adjustment.booking)

    def get_reconciliation(self, adjustment: BookingAdjustment) -> dict[str, int]:
        return reconciliation_payload(adjustment.booking)


class RefundRecordSerializer(serializers.ModelSerializer):
    booking_state = serializers.CharField(source="booking.booking_state", read_only=True)
    payment_state = serializers.SerializerMethodField()
    reconciliation = serializers.SerializerMethodField()
    send_refund_acknowledgement = serializers.BooleanField(
        required=False,
        default=False,
        write_only=True,
    )

    class Meta:
        model = RefundRecord
        fields = [
            "id",
            "booking",
            "booking_state",
            "amount_inr",
            "refund_reason",
            "refund_reference",
            "payment_state",
            "reconciliation",
            "recorded_by",
            "occurred_at",
            "created_at",
            "send_refund_acknowledgement",
        ]
        read_only_fields = [
            "id",
            "booking",
            "booking_state",
            "payment_state",
            "reconciliation",
            "recorded_by",
            "occurred_at",
            "created_at",
        ]
        extra_kwargs = {
            "amount_inr": {"required": True, "min_value": 1},
            "refund_reason": {"required": True, "allow_blank": False},
            "refund_reference": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data):
        send_refund_acknowledgement = validated_data.pop("send_refund_acknowledgement", False)
        return create_refund_record(
            booking=self.context["booking"],
            amount_inr=validated_data["amount_inr"],
            refund_reason=validated_data["refund_reason"],
            refund_reference=validated_data.get("refund_reference", ""),
            actor=self.context.get("actor"),
            send_acknowledgement=send_refund_acknowledgement,
        )

    def get_payment_state(self, refund_record: RefundRecord) -> str:
        return derived_payment_state(refund_record.booking)

    def get_reconciliation(self, refund_record: RefundRecord) -> dict[str, int]:
        return reconciliation_payload(refund_record.booking)
