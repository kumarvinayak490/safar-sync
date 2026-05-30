from __future__ import annotations

from rest_framework import serializers

from trip_bookings.models import Booking
from trip_operations.models import ActivityLog, Notification
from trip_operations.notifications import (
    send_announcement,
    send_balance_payment_link,
    send_manual_reminder,
)
from trip_payments.financial_ledger import (
    booking_reconciliation,
    derived_payment_state,
    platform_fee_for_provider_payment_ledger_amount_inr,
)
from trip_payments.models import ProviderPayment
from trip_payments.serializers import OperationsManualPaymentSerializer
from trip_travelers.models import TravelerSlot
from trip_travelers.readiness import confirmation_requirements_for_booking


class OperationalExportOptionsSerializer(serializers.Serializer):
    include_sensitive_traveler_information = serializers.BooleanField(default=False)
    include_sensitive_payment_information = serializers.BooleanField(default=False)
    include_draft_bookings = serializers.BooleanField(default=False)


class ActivityLogSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source="get_action_display", read_only=True)
    actor_email = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "organizer",
            "trip",
            "booking",
            "traveler_slot",
            "traveler_document",
            "actor",
            "actor_email",
            "action",
            "action_label",
            "metadata",
            "occurred_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_email(self, activity_log: ActivityLog) -> str:
        return activity_actor_email(activity_log)


def activity_actor_email(activity_log: ActivityLog) -> str:
    actor = activity_log.actor
    if actor is None:
        return ""
    return getattr(actor, "email", "") or getattr(actor, "username", "")


class ManualReminderSerializer(serializers.Serializer):
    reminder_kind = serializers.ChoiceField(
        choices=[
            ("payment_balance", "Payment Balance"),
            ("missing_requirements", "Missing Requirements"),
        ]
    )
    note = serializers.CharField(
        allow_blank=True,
        max_length=500,
        required=False,
        trim_whitespace=True,
    )

    def save(self, **kwargs):
        return send_manual_reminder(
            self.context["booking"],
            reminder_kind=self.validated_data["reminder_kind"],
            note=self.validated_data.get("note", ""),
            actor=self.context.get("actor"),
        )


class BalancePaymentLinkSendSerializer(serializers.Serializer):
    note = serializers.CharField(
        allow_blank=True,
        max_length=500,
        required=False,
        trim_whitespace=True,
    )

    def save(self, **kwargs):
        return send_balance_payment_link(
            self.context["booking"],
            note=self.validated_data.get("note", ""),
            actor=self.context.get("actor"),
        )


class AnnouncementSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=120, trim_whitespace=True)
    body = serializers.CharField(max_length=1000, trim_whitespace=True)

    def save(self, **kwargs):
        return send_announcement(
            self.context["trip"],
            subject=self.validated_data["subject"],
            body=self.validated_data["body"],
            actor=self.context.get("actor"),
        )


class NotificationSerializer(serializers.ModelSerializer):
    notification_type_label = serializers.CharField(
        source="get_notification_type_display",
        read_only=True,
    )
    channel_label = serializers.CharField(source="get_channel_display", read_only=True)
    recipient_type_label = serializers.CharField(
        source="get_recipient_type_display",
        read_only=True,
    )

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "notification_type_label",
            "channel",
            "channel_label",
            "recipient_type",
            "recipient_type_label",
            "recipient_name",
            "recipient_phone",
            "recipient_email",
            "organizer_identity_name",
            "organizer_identity_logo_url",
            "subject",
            "body",
            "status",
            "metadata",
            "sent_at",
            "created_at",
        ]
        read_only_fields = fields


class OperationsTravelerSlotSerializer(serializers.ModelSerializer):
    package_name = serializers.CharField(source="package.name", read_only=True)
    package_lifecycle_state = serializers.CharField(
        source="package.lifecycle_state",
        read_only=True,
    )
    package_lifecycle_state_label = serializers.CharField(
        source="package.get_lifecycle_state_display",
        read_only=True,
    )
    package_is_withdrawn = serializers.BooleanField(
        source="package.is_withdrawn",
        read_only=True,
    )
    traveler_state_label = serializers.CharField(
        source="get_traveler_state_display",
        read_only=True,
    )
    is_traveler = serializers.BooleanField(read_only=True)
    attendance_state_label = serializers.CharField(
        source="get_attendance_state_display",
        read_only=True,
    )
    attendance_actions_available = serializers.SerializerMethodField()

    class Meta:
        model = TravelerSlot
        fields = [
            "id",
            "position",
            "package",
            "package_name",
            "package_lifecycle_state",
            "package_lifecycle_state_label",
            "package_is_withdrawn",
            "traveler_state",
            "traveler_state_label",
            "booked_package_price_inr",
            "booked_reservation_amount_inr",
            "cancellation_reason",
            "cancelled_at",
            "replaced_by_slot",
            "addition_reserved_at",
            "traveler_full_name",
            "traveler_phone",
            "traveler_email",
            "is_traveler",
            "arrival_details",
            "departure_details",
            "pickup_location",
            "logistics_note",
            "rooming_notes",
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relationship",
            "attendance_state",
            "attendance_state_label",
            "attendance_marked_at",
            "attendance_marked_by",
            "attendance_actions_available",
        ]
        read_only_fields = fields

    def get_attendance_actions_available(self, traveler_slot: TravelerSlot) -> bool:
        return (
            traveler_slot.traveler_state == TravelerSlot.TravelerState.ACTIVE
            and traveler_slot.is_traveler
            and traveler_slot.booking.booking_state
            in {
                Booking.BookingState.RESERVED,
                Booking.BookingState.CONFIRMED,
            }
        )


class OperationsProviderPaymentSerializer(serializers.ModelSerializer):
    provider_label = serializers.CharField(source="get_provider_display", read_only=True)
    payment_purpose = serializers.CharField(source="payment_attempt.purpose", read_only=True)
    payment_purpose_label = serializers.CharField(
        source="payment_attempt.get_purpose_display",
        read_only=True,
    )
    provider_attempt_reference = serializers.CharField(
        source="payment_attempt.provider_attempt_reference",
        read_only=True,
    )
    gross_amount_inr = serializers.IntegerField(source="amount_inr", read_only=True)
    platform_fee_inr = serializers.SerializerMethodField()

    class Meta:
        model = ProviderPayment
        fields = [
            "id",
            "provider",
            "provider_label",
            "payment_purpose",
            "payment_purpose_label",
            "provider_attempt_reference",
            "provider_payment_reference",
            "gross_amount_inr",
            "provider_fee_amount_inr",
            "provider_net_settlement_amount_inr",
            "platform_fee_inr",
            "confirmed_at",
        ]
        read_only_fields = fields

    def get_platform_fee_inr(self, payment: ProviderPayment) -> int:
        return platform_fee_for_provider_payment_ledger_amount_inr(payment)


class OperationsBookingListItemSerializer(serializers.ModelSerializer):
    booking_state_label = serializers.CharField(source="get_booking_state_display", read_only=True)
    traveler_slot_count = serializers.IntegerField(read_only=True)
    booking_total_inr = serializers.IntegerField(read_only=True)
    booking_reservation_amount_inr = serializers.IntegerField(read_only=True)
    payment_state = serializers.SerializerMethodField()
    payment_state_label = serializers.SerializerMethodField()
    reconciliation = serializers.SerializerMethodField()
    confirmation_requirements = serializers.SerializerMethodField()
    provider_payments = serializers.SerializerMethodField()
    manual_payments = serializers.SerializerMethodField()
    traveler_slots = OperationsTravelerSlotSerializer(many=True, read_only=True)
    attendance_summary = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "booking_state",
            "booking_state_label",
            "booking_contact_name",
            "booking_contact_phone",
            "booking_contact_email",
            "traveler_slot_count",
            "booking_total_inr",
            "booking_reservation_amount_inr",
            "payment_state",
            "payment_state_label",
            "reconciliation",
            "confirmation_requirements",
            "provider_payments",
            "manual_payments",
            "traveler_slots",
            "attendance_summary",
            "draft_expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_payment_state(self, booking: Booking) -> str:
        return derived_payment_state(booking)

    def get_payment_state_label(self, booking: Booking) -> str:
        labels = {
            "unpaid": "Unpaid",
            "reservation_paid": "Reservation paid",
            "partially_paid": "Partially paid",
            "fully_paid": "Fully paid",
            "overdue": "Overdue",
            "refund_due": "Refund due",
            "refunded": "Refunded",
        }
        return labels[derived_payment_state(booking)]

    def get_reconciliation(self, booking: Booking) -> dict[str, int]:
        reconciliation = booking_reconciliation(booking)
        return {
            "collected_inr": reconciliation.collected_inr,
            "due_inr": reconciliation.due_inr,
            "overdue_inr": reconciliation.overdue_inr,
            "refund_due_inr": reconciliation.refund_due_inr,
            "platform_fee_inr": reconciliation.platform_fee_inr,
        }

    def get_confirmation_requirements(self, booking: Booking) -> dict:
        requirements = confirmation_requirements_for_booking(booking)
        return {
            "ready": requirements.ready,
            "unmet_count": len(requirements.unmet_requirements),
            "unmet": [
                {
                    "code": requirement.code,
                    "label": requirement.label,
                    "scope": requirement.scope,
                    "traveler_slot_id": requirement.traveler_slot_id,
                    "traveler_slot_position": requirement.traveler_slot_position,
                }
                for requirement in requirements.unmet_requirements
            ],
        }

    def get_manual_payments(self, booking: Booking) -> list[dict]:
        return OperationsManualPaymentSerializer(
            booking.manual_payments.select_related("booking").all(),
            many=True,
            context={"include_payment_proof_download_url": True},
        ).data

    def get_provider_payments(self, booking: Booking) -> list[dict]:
        return OperationsProviderPaymentSerializer(
            booking.provider_payments.select_related("payment_attempt").all(),
            many=True,
        ).data

    def get_attendance_summary(self, booking: Booking) -> dict[str, int]:
        summary = {
            TravelerSlot.AttendanceState.NOT_MARKED: 0,
            TravelerSlot.AttendanceState.CHECKED_IN: 0,
            TravelerSlot.AttendanceState.NO_SHOW: 0,
        }
        for traveler_slot in booking.traveler_slots.all():
            if traveler_slot.traveler_state != TravelerSlot.TravelerState.ACTIVE:
                continue
            summary[traveler_slot.attendance_state] = (
                summary.get(traveler_slot.attendance_state, 0) + 1
            )
        return {
            "not_marked": summary[TravelerSlot.AttendanceState.NOT_MARKED],
            "checked_in": summary[TravelerSlot.AttendanceState.CHECKED_IN],
            "no_show": summary[TravelerSlot.AttendanceState.NO_SHOW],
        }
