"""Legacy Organizer API service facade.

This module preserves the old cross-domain service import surface for API
stability during the app split. New behavior should land in the target domain
app and be re-exported here only when old callers still need the import path.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from organizer_payments.manual_payment_instructions import (
    has_ready_manual_payment_instructions,
)
from organizer_payments.online_payment_readiness import (
    OnlinePaymentReadinessDecision,
    online_payment_readiness_for_organizer,
)
from organizer_payments.setup_records import (
    ensure_payment_setup_records as _ensure_payment_setup_records,
)
from organizers.models import (
    ActivityLog,
    Booking,
    BookingAccessLink,
    BookingAdjustment,
    ManualPayment,
    Organizer,
    OrganizerMembership,
    PaymentAttempt,
    PaymentException,
    ProviderPayment,
    RefundRecord,
    TravelerSlot,
    Trip,
    TripPackage,
)
from trip_bookings import access_links as booking_access_links
from trip_bookings import lifecycle as booking_lifecycle
from trip_bookings.imports import (
    BookingImportRowInput as BookingImportRowInput,
)
from trip_bookings.imports import (
    BookingImportTravelerSlotInput as BookingImportTravelerSlotInput,
)
from trip_bookings.imports import (
    create_booking_import as create_booking_import,
)
from trip_bookings.intake import (
    apply_booking_intake_to_booking as apply_booking_intake_to_booking,
)
from trip_bookings.intake import (
    create_booking_from_intake,
    prepare_manual_booking_intake,
)
from trip_operations import notifications as trip_operations_notifications
from trip_operations.activity import record_activity_log as record_activity_log
from trip_operations.exports import (
    OPERATIONAL_EXPORT_BASE_HEADERS as OPERATIONAL_EXPORT_BASE_HEADERS,
)
from trip_operations.exports import (
    OPERATIONAL_EXPORT_SENSITIVE_PAYMENT_HEADERS as OPERATIONAL_EXPORT_SENSITIVE_PAYMENT_HEADERS,
)
from trip_operations.exports import (
    OPERATIONAL_EXPORT_SENSITIVE_TRAVELER_HEADERS as OPERATIONAL_EXPORT_SENSITIVE_TRAVELER_HEADERS,
)
from trip_operations.exports import OperationalExport as OperationalExport
from trip_operations.exports import (
    generate_operational_export_csv as generate_operational_export_csv,
)
from trip_operations.metrics import OperationalMetrics as OperationalMetrics
from trip_operations.metrics import PublicBookingReadiness as PublicBookingReadiness
from trip_operations.metrics import (
    core_operational_booking_count as core_operational_booking_count,
)
from trip_operations.metrics import operational_metrics as operational_metrics
from trip_operations.metrics import public_booking_readiness as public_booking_readiness
from trip_payments.adjustments import (
    create_booking_adjustment as payment_create_booking_adjustment,
)
from trip_payments.adjustments import (
    create_refund_record as payment_create_refund_record,
)
from trip_payments.financial_ledger import (
    FinancialLedger,
    booking_reconciliation,
    booking_reconciliation_flags,
    derived_payment_state,
)
from trip_payments.financial_ledger import (
    collected_ledger_amount_inr as collected_ledger_amount_inr,
)
from trip_payments.financial_ledger import (
    collected_provider_payment_amount_inr as ledger_collected_provider_payment_amount_inr,
)
from trip_payments.manual_review import (
    PublicQrManualPaymentSubmissionBlocked as PublicQrManualPaymentSubmissionBlocked,
)
from trip_payments.manual_review import (
    approve_manual_payment as payment_approve_manual_payment,
)
from trip_payments.manual_review import (
    create_organizer_entered_manual_payment as payment_create_organizer_entered_manual_payment,
)
from trip_payments.manual_review import (
    create_public_qr_manual_payment_submission as payment_create_public_qr_submission,
)
from trip_payments.manual_review import (
    create_traveler_submitted_manual_payment as payment_create_traveler_submitted_manual_payment,
)
from trip_payments.manual_review import (
    reject_manual_payment as payment_reject_manual_payment,
)
from trip_payments.provider_adapters import (
    ProviderCheckoutAdapter,
    ProviderPaymentConfirmation,
    ProviderPaymentConfirmationAdapter,
)
from trip_payments.provider_payment_lifecycle import (
    BrowserCheckoutSuccessResult,
    ProviderCheckoutSession,
)
from trip_payments.seat_holds import (
    active_seat_hold_count as calculated_active_seat_hold_count,
)
from trip_payments.seat_holds import (
    bookable_seats as calculated_bookable_seats,
)
from trip_travelers import slots as traveler_slots
from trip_travelers.check_in import (
    mark_traveler_attendance as travelers_mark_traveler_attendance,
)
from trip_travelers.readiness import (
    BookingConfirmationRequirements,
    traveler_portal_readiness_payload,
)
from trip_travelers.readiness import (
    confirmation_requirements_for_booking as readiness_confirmation_requirements_for_booking,
)
from trip_travelers.slots import TravelerSlotIntakeInput
from trips.booking_availability import (
    available_seats as gate_available_seats,
)
from trips.booking_availability import (
    effective_booking_availability as gate_effective_booking_availability,
)
from trips.booking_availability import (
    is_provider_payment_setup_complete as gate_is_provider_payment_setup_complete,
)
from trips.booking_availability import (
    public_availability_band as gate_public_availability_band,
)
from trips.payment_method_readiness import (
    ManualPaymentMethodReadinessFacts,
    PaymentMethodReadinessDecision,
    manual_payment_method_readiness,
    provider_payment_method_readiness,
)

ACCESS_LINK_TOKEN_BYTES = booking_access_links.ACCESS_LINK_TOKEN_BYTES

AUTOMATIC_REMINDER_BOOKING_STATES = (
    trip_operations_notifications.AUTOMATIC_REMINDER_BOOKING_STATES
)
MANUAL_PAYMENT_REMINDER_BOOKING_STATES = (
    trip_operations_notifications.MANUAL_PAYMENT_REMINDER_BOOKING_STATES
)
MANUAL_REQUIREMENTS_REMINDER_BOOKING_STATES = (
    trip_operations_notifications.MANUAL_REQUIREMENTS_REMINDER_BOOKING_STATES
)
AutomaticReminderRun = trip_operations_notifications.AutomaticReminderRun
BalancePaymentLink = trip_operations_notifications.BalancePaymentLink
BalancePaymentLinkDelivery = trip_operations_notifications.BalancePaymentLinkDelivery
NotificationRecipient = trip_operations_notifications.NotificationRecipient


def ensure_payment_setup_records(organizer: Organizer) -> None:
    _ensure_payment_setup_records(organizer)


IssuedAccessLink = booking_access_links.IssuedAccessLink


def access_link_token_digest(token: str) -> str:
    return booking_access_links.access_link_token_digest(token)


def issue_booking_access_link(booking: Booking) -> IssuedAccessLink:
    return booking_access_links.issue_booking_access_link(booking)


def issue_traveler_access_link(traveler_slot: TravelerSlot) -> IssuedAccessLink:
    return booking_access_links.issue_traveler_access_link(traveler_slot)


def resolve_active_access_link(token: str) -> BookingAccessLink:
    return booking_access_links.resolve_active_access_link(token)


process_automatic_reminders = trip_operations_notifications.process_automatic_reminders
issue_balance_payment_link = trip_operations_notifications.issue_balance_payment_link
send_announcement = trip_operations_notifications.send_announcement
send_balance_payment_link = trip_operations_notifications.send_balance_payment_link
send_cancellation_notice = trip_operations_notifications.send_cancellation_notice
send_confirmation_notice = trip_operations_notifications.send_confirmation_notice
send_date_change_notice = trip_operations_notifications.send_date_change_notice
send_due_balance_due_reminders = trip_operations_notifications.send_due_balance_due_reminders
send_due_draft_recovery_reminders = (
    trip_operations_notifications.send_due_draft_recovery_reminders
)
send_due_missing_requirements_reminders = (
    trip_operations_notifications.send_due_missing_requirements_reminders
)
send_due_overdue_balance_reminders = (
    trip_operations_notifications.send_due_overdue_balance_reminders
)
send_manual_payment_acknowledgement = (
    trip_operations_notifications.send_manual_payment_acknowledgement
)
send_manual_reminder = trip_operations_notifications.send_manual_reminder
send_provider_payment_acknowledgement = (
    trip_operations_notifications.send_provider_payment_acknowledgement
)
send_refund_acknowledgement = trip_operations_notifications.send_refund_acknowledgement
send_reservation_acknowledgement = (
    trip_operations_notifications.send_reservation_acknowledgement
)


def readiness_summary_for_traveler_slot(traveler_slot: TravelerSlot) -> dict:
    return traveler_portal_readiness_payload(traveler_slot)


def is_provider_payment_setup_complete(organizer: Organizer) -> bool:
    return gate_is_provider_payment_setup_complete(organizer)


def online_payment_readiness(organizer: Organizer) -> OnlinePaymentReadinessDecision:
    return online_payment_readiness_for_organizer(organizer)


def is_online_payment_ready(organizer: Organizer) -> bool:
    return online_payment_readiness(organizer).ready


def organizer_payment_method_readiness(organizer: Organizer) -> PaymentMethodReadinessDecision:
    readiness = online_payment_readiness(organizer)
    return PaymentMethodReadinessDecision(
        provider_method=provider_payment_method_readiness(
            organizer,
            online_payment_readiness=readiness,
        ),
        manual_method=manual_payment_method_readiness(
            ManualPaymentMethodReadinessFacts(
                manual_payment_instructions_present=has_ready_manual_payment_instructions(
                    organizer
                ),
                booking_availability_open=True,
                capacity_available=True,
            )
        ),
    )


def is_manual_payment_capability_enabled(organizer: Organizer) -> bool:
    return True


def active_reserved_traveler_count(trip: Trip) -> int:
    return traveler_slots.active_reserved_traveler_count(trip)


def available_seats(trip: Trip) -> int:
    return gate_available_seats(trip)


def active_seat_hold_count(trip: Trip) -> int:
    return calculated_active_seat_hold_count(trip)


def bookable_seats(trip: Trip) -> int:
    return calculated_bookable_seats(trip)


def effective_booking_availability(trip: Trip) -> str:
    return gate_effective_booking_availability(trip)


def public_availability_band(trip: Trip) -> str:
    return gate_public_availability_band(trip)


def duplicate_trip(
    trip: Trip,
    *,
    actor=None,
    title: str = "",
    start_date: date | None = None,
    end_date: date | None = None,
) -> Trip:
    from trips.duplication import duplicate_trip as duplicate_trip_profile

    return duplicate_trip_profile(
        trip,
        actor=actor,
        title=title,
        start_date=start_date,
        end_date=end_date,
    )


def change_trip_dates(
    trip: Trip,
    *,
    start_date: date,
    end_date: date,
    actor=None,
    send_notice: bool = True,
) -> Trip:
    if end_date < start_date:
        raise ValidationError("Trip end date cannot be before Trip Start Date.")

    with transaction.atomic():
        trip = (
            Trip.objects.select_for_update()
            .select_related("organizer", "payment_schedule")
            .prefetch_related("bookings__traveler_slots")
            .get(pk=trip.pk)
        )
        old_start_date = trip.start_date
        old_end_date = trip.end_date
        if old_start_date == start_date and old_end_date == end_date:
            return trip

        active_bookings = _active_trip_bookings(trip)
        trip.start_date = start_date
        trip.end_date = end_date
        trip.save(update_fields=["start_date", "end_date", "updated_at"])
        record_activity_log(
            action=ActivityLog.Action.TRIP_DATE_CHANGED,
            trip=trip,
            actor=actor,
            metadata={
                "old_start_date": old_start_date.isoformat(),
                "old_end_date": old_end_date.isoformat(),
                "new_start_date": start_date.isoformat(),
                "new_end_date": end_date.isoformat(),
                "date_change_notice_sent": send_notice and bool(active_bookings),
                "active_booking_count": len(active_bookings),
            },
        )
        if send_notice:
            for booking in active_bookings:
                send_date_change_notice(
                    booking,
                    old_start_date=old_start_date,
                    old_end_date=old_end_date,
                    new_start_date=start_date,
                    new_end_date=end_date,
                )
        return trip


def cancel_trip(
    trip: Trip,
    *,
    cancellation_reason: str,
    actor=None,
    send_notice: bool = True,
) -> Trip:
    if not cancellation_reason.strip():
        raise ValidationError("Trip Cancellation requires Cancellation Reason.")

    with transaction.atomic():
        trip = (
            Trip.objects.select_for_update()
            .select_related("organizer")
            .prefetch_related("bookings__traveler_slots")
            .get(pk=trip.pk)
        )
        active_bookings = _active_trip_bookings(trip)
        trip.booking_availability = Trip.BookingAvailability.CLOSED
        trip.save(update_fields=["booking_availability", "updated_at"])

        if send_notice:
            for booking in active_bookings:
                send_cancellation_notice(booking, cancellation_reason=cancellation_reason)

        for booking in active_bookings:
            booking.booking_state = Booking.BookingState.CANCELLED
            booking.save(update_fields=["booking_state", "updated_at"])
            record_activity_log(
                action=ActivityLog.Action.BOOKING_CANCELLED,
                booking=booking,
                actor=actor,
                metadata={
                    "cancellation_reason": cancellation_reason,
                    "trip_cancellation": True,
                },
            )

        record_activity_log(
            action=ActivityLog.Action.TRIP_CANCELLED,
            trip=trip,
            actor=actor,
            metadata={
                "cancellation_reason": cancellation_reason,
                "cancelled_booking_count": len(active_bookings),
                "cancellation_notice_sent": send_notice and bool(active_bookings),
            },
        )
        return trip


def complete_trip(
    trip: Trip,
    *,
    actor=None,
) -> TripCompletionResult:
    with transaction.atomic():
        trip = (
            Trip.objects.select_for_update()
            .select_related("organizer", "payment_schedule")
            .prefetch_related(
                "bookings__traveler_slots__package",
                "bookings__ledger_entries",
            )
            .get(pk=trip.pk)
        )
        active_bookings = _active_trip_bookings(trip)
        unchanged_count = trip.bookings.exclude(
            booking_state__in=[
                Booking.BookingState.RESERVED,
                Booking.BookingState.CONFIRMED,
            ]
        ).count()
        reconciliation_flags = []
        for booking in active_bookings:
            reconciliation = booking_reconciliation(booking)
            flags = booking_reconciliation_flags(reconciliation)
            if flags:
                reconciliation_flags.append(
                    {
                        "booking_id": booking.id,
                        "payment_state": derived_payment_state(booking),
                        "flags": flags,
                        "due_inr": reconciliation.due_inr,
                        "refund_due_inr": reconciliation.refund_due_inr,
                    }
                )
            booking.booking_state = Booking.BookingState.COMPLETED
            booking.save(update_fields=["booking_state", "updated_at"])
            record_activity_log(
                action=ActivityLog.Action.BOOKING_COMPLETED,
                booking=booking,
                actor=actor,
                metadata={"trip_completed": True, "reconciliation_flags": flags},
            )

        record_activity_log(
            action=ActivityLog.Action.TRIP_COMPLETED,
            trip=trip,
            actor=actor,
            metadata={
                "completed_booking_count": len(active_bookings),
                "unchanged_booking_count": unchanged_count,
                "reconciliation_flag_count": len(reconciliation_flags),
            },
        )
        return TripCompletionResult(
            trip=trip,
            completed_booking_count=len(active_bookings),
            unchanged_booking_count=unchanged_count,
            reconciliation_flags=reconciliation_flags,
        )


def _active_trip_bookings(trip: Trip) -> list[Booking]:
    return [
        booking
        for booking in trip.bookings.all()
        if booking.booking_state
        in {
            Booking.BookingState.RESERVED,
            Booking.BookingState.CONFIRMED,
        }
    ]


def booking_reservation_amount_inr(booking: Booking) -> int:
    return booking.booking_reservation_amount_inr


def booking_total_inr(booking: Booking) -> int:
    return booking.booking_total_inr


def collected_provider_payment_amount_inr(booking: Booking) -> int:
    return ledger_collected_provider_payment_amount_inr(booking)


def platform_fee_for_provider_payment_inr(provider_payment: ProviderPayment) -> int:
    return FinancialLedger.platform_fee_for_provider_payment_inr(provider_payment)


def effective_booking_total_inr(booking: Booking) -> int:
    return FinancialLedger.for_booking(booking).effective_booking_total_inr()


@dataclass(frozen=True)
class TripCompletionResult:
    trip: Trip
    completed_booking_count: int
    unchanged_booking_count: int
    reconciliation_flags: list[dict]


def confirmation_requirements_for_booking(booking: Booking) -> BookingConfirmationRequirements:
    return readiness_confirmation_requirements_for_booking(booking)


def confirm_booking(booking: Booking) -> Booking:
    return booking_lifecycle.confirm_booking(
        booking,
        send_confirmation_notice=send_confirmation_notice,
    )


def unconfirm_booking(booking: Booking) -> Booking:
    return booking_lifecycle.unconfirm_booking(booking)


def cancel_booking(
    booking: Booking,
    *,
    cancellation_reason: str,
    actor=None,
) -> Booking:
    return booking_lifecycle.cancel_booking(
        booking,
        cancellation_reason=cancellation_reason,
        actor=actor,
    )


def cancel_traveler(
    traveler_slot: TravelerSlot,
    *,
    cancellation_reason: str,
    actor=None,
) -> TravelerSlot:
    return traveler_slots.cancel_traveler(
        traveler_slot,
        cancellation_reason=cancellation_reason,
        actor=actor,
    )


def replace_traveler(
    traveler_slot: TravelerSlot,
    *,
    traveler_full_name: str,
    traveler_phone: str,
    traveler_email: str = "",
    actor=None,
) -> TravelerSlot:
    return traveler_slots.replace_traveler(
        traveler_slot,
        traveler_full_name=traveler_full_name,
        traveler_phone=traveler_phone,
        traveler_email=traveler_email,
        actor=actor,
    )


def add_traveler_to_booking(
    booking: Booking,
    *,
    package: TripPackage,
    traveler_full_name: str = "",
    traveler_phone: str = "",
    traveler_email: str = "",
    actor=None,
) -> TravelerSlot:
    return traveler_slots.add_traveler_to_booking(
        booking,
        package=package,
        traveler_full_name=traveler_full_name,
        traveler_phone=traveler_phone,
        traveler_email=traveler_email,
        actor=actor,
    )


def reserve_pending_traveler_additions_if_ready(
    booking: Booking,
    *,
    actor=None,
) -> list[TravelerSlot]:
    return traveler_slots.reserve_pending_traveler_additions_if_ready(
        booking,
        actor=actor,
    )


def change_traveler_package(
    traveler_slot: TravelerSlot,
    *,
    package: TripPackage,
    actor=None,
) -> TravelerSlot:
    return traveler_slots.change_traveler_package(
        traveler_slot,
        package=package,
        actor=actor,
    )


def mark_traveler_attendance(
    traveler_slot: TravelerSlot,
    *,
    attendance_state: str,
    actor=None,
) -> TravelerSlot:
    return travelers_mark_traveler_attendance(
        traveler_slot,
        attendance_state=attendance_state,
        actor=actor,
    )


def required_amount_to_reserve_inr(booking: Booking) -> int:
    return booking_lifecycle.required_amount_to_reserve_inr(booking)


def current_balance_due_inr(booking: Booking) -> int:
    return booking_reconciliation(booking).due_inr


def balance_payment_availability_payload(
    booking: Booking,
    *,
    access_scope: str = BookingAccessLink.Scope.BOOKING,
    token: str = "",
) -> dict:
    amount_inr = current_balance_due_inr(booking)
    available = True
    blocker_code = "ready"
    message = "Balance Payment Link is ready."

    if access_scope != BookingAccessLink.Scope.BOOKING:
        available = False
        blocker_code = "booking_access_required"
        message = "Balance Payment Links require Booking-Level Access."
    elif booking.booking_state == Booking.BookingState.DRAFT:
        available = False
        blocker_code = "booking_not_reserved"
        message = "Balance Payment Links are available after reservation."
    elif booking.booking_state == Booking.BookingState.CANCELLED:
        available = False
        blocker_code = "booking_cancelled"
        message = "Cancelled Bookings cannot start Balance Payment Attempts."
    elif amount_inr <= 0:
        available = False
        blocker_code = "fully_paid"
        message = "No balance is currently due."
    elif not is_online_payment_ready(booking.trip.organizer):
        readiness = online_payment_readiness(booking.trip.organizer)
        available = False
        blocker_code = "online_payment_readiness_missing"
        message = f"Online Payment Readiness is blocked: {readiness.message}"

    return {
        "available": available,
        "blocker_code": blocker_code,
        "message": message,
        "amount_inr": amount_inr,
        "currency": "INR",
        "payment_purpose": PaymentAttempt.Purpose.BALANCE,
        "payment_link_path": f"/portal/{token}/" if token else "",
    }


def create_public_reservation_checkout(
    booking: Booking,
    *,
    provider_adapter: ProviderCheckoutAdapter | None = None,
) -> ProviderCheckoutSession:
    from trip_payments.provider_payment_lifecycle import (
        create_public_reservation_checkout as lifecycle_create_checkout,
    )

    return lifecycle_create_checkout(booking, provider_adapter=provider_adapter)


def create_public_payment_attempt(booking: Booking) -> PaymentAttempt:
    return create_public_reservation_checkout(booking).payment_attempt


def create_balance_payment_checkout(
    booking: Booking,
    *,
    provider_adapter: ProviderCheckoutAdapter | None = None,
) -> ProviderCheckoutSession:
    from trip_payments.provider_payment_lifecycle import (
        create_balance_payment_checkout as lifecycle_create_checkout,
    )

    return lifecycle_create_checkout(booking, provider_adapter=provider_adapter)


def fail_payment_attempt(
    payment_attempt: PaymentAttempt,
    *,
    failure_reason: str = "",
) -> PaymentAttempt:
    from trip_payments.provider_payment_lifecycle import fail_payment_attempt as lifecycle_fail

    return lifecycle_fail(payment_attempt, failure_reason=failure_reason)


def record_frontend_checkout_success(payment_attempt: PaymentAttempt) -> PaymentAttempt:
    from trip_payments.provider_payment_lifecycle import record_frontend_checkout_success

    return record_frontend_checkout_success(payment_attempt)


def process_browser_checkout_success(
    payment_attempt: PaymentAttempt,
    *,
    provider_payment_reference: str,
    provider_attempt_reference: str,
    checkout_signature: str,
    provider_adapter: ProviderPaymentConfirmationAdapter | None = None,
) -> BrowserCheckoutSuccessResult:
    from trip_payments.provider_payment_lifecycle import (
        process_browser_checkout_success as lifecycle_process_checkout_success,
    )

    return lifecycle_process_checkout_success(
        payment_attempt,
        provider_payment_reference=provider_payment_reference,
        provider_attempt_reference=provider_attempt_reference,
        checkout_signature=checkout_signature,
        provider_adapter=provider_adapter,
    )


def ingest_provider_payment_confirmation(
    payment_attempt: PaymentAttempt,
    confirmation: ProviderPaymentConfirmation,
    *,
    source: str = "",
) -> PaymentAttempt | ProviderPayment | PaymentException:
    from trip_payments.provider_payment_lifecycle import (
        ingest_provider_payment_confirmation as lifecycle_ingest_confirmation,
    )

    result = lifecycle_ingest_confirmation(
        confirmation,
        payment_attempt=payment_attempt,
        source=source,
    )
    return result.confirmation_result or payment_attempt


def confirm_provider_payment(
    payment_attempt: PaymentAttempt,
    *,
    provider_payment_reference: str,
    amount_inr: int | None = None,
    provider_fee_amount_inr: int | None = None,
    provider_net_settlement_amount_inr: int | None = None,
    payment_attempt_id: int | None = None,
    booking_id: int | None = None,
    provider: str | None = None,
    provider_attempt_reference: str | None = None,
    purpose: str | None = None,
    require_reported_metadata: bool = False,
) -> ProviderPayment | PaymentException:
    from trip_payments.provider_payment_lifecycle import (
        confirm_provider_payment as lifecycle_confirm_provider_payment,
    )

    return lifecycle_confirm_provider_payment(
        payment_attempt,
        provider_payment_reference=provider_payment_reference,
        amount_inr=amount_inr,
        provider_fee_amount_inr=provider_fee_amount_inr,
        provider_net_settlement_amount_inr=provider_net_settlement_amount_inr,
        payment_attempt_id=payment_attempt_id,
        booking_id=booking_id,
        provider=provider,
        provider_attempt_reference=provider_attempt_reference,
        purpose=purpose,
        require_reported_metadata=require_reported_metadata,
    )


def record_provider_dispute_exception(
    provider_payment: ProviderPayment,
    *,
    provider_event_type: str,
    provider_dispute_reference: str,
    amount_inr: int | None = None,
    details: dict | None = None,
) -> PaymentException:
    from trip_payments.payment_exceptions import (
        record_provider_dispute_exception as payment_record_provider_dispute_exception,
    )

    return payment_record_provider_dispute_exception(
        provider_payment,
        provider_event_type=provider_event_type,
        provider_dispute_reference=provider_dispute_reference,
        amount_inr=amount_inr,
        details=details,
    )


def resolve_late_confirmed_payment_exception(
    payment_exception: PaymentException,
    *,
    actor,
    resolution_note: str = "",
) -> PaymentException:
    from trip_payments.payment_exceptions import (
        resolve_late_confirmed_payment_exception as payment_resolve_late_confirmed_exception,
    )

    return payment_resolve_late_confirmed_exception(
        payment_exception,
        actor=actor,
        resolution_note=resolution_note,
    )


def create_manual_booking(
    *,
    trip: Trip,
    booking_contact_name: str,
    booking_contact_phone: str,
    booking_contact_email: str = "",
    package_ids: list[int],
) -> Booking:
    with transaction.atomic():
        trip = Trip.objects.select_for_update().prefetch_related("packages").get(pk=trip.pk)
        intake = prepare_manual_booking_intake(
            trip=trip,
            booking_contact_name=booking_contact_name,
            booking_contact_phone=booking_contact_phone,
            booking_contact_email=booking_contact_email,
            traveler_slots=[
                TravelerSlotIntakeInput(package_id=package_id) for package_id in package_ids
            ],
        )
        return create_booking_from_intake(
            trip=trip,
            intake=intake,
            booking_state=Booking.BookingState.DRAFT,
        )


def create_public_qr_manual_payment_submission(
    *,
    trip: Trip,
    booking_contact_name: str,
    booking_contact_phone: str,
    payment_proof,
    booking_contact_email: str = "",
    selected_package_id: int | None = None,
    traveler_count: int | None = None,
    payment_reference: str = "",
    note: str = "",
    initial_data=None,
) -> ManualPayment:
    return payment_create_public_qr_submission(
        trip=trip,
        booking_contact_name=booking_contact_name,
        booking_contact_phone=booking_contact_phone,
        payment_proof=payment_proof,
        booking_contact_email=booking_contact_email,
        selected_package_id=selected_package_id,
        traveler_count=traveler_count,
        payment_reference=payment_reference,
        note=note,
        initial_data=initial_data,
    )


def create_organizer_entered_manual_payment(
    *,
    booking: Booking,
    amount_inr: int,
    actor=None,
    payment_reference: str = "",
    note: str = "",
    payment_proof=None,
    send_payment_acknowledgement: bool = False,
) -> ManualPayment:
    return payment_create_organizer_entered_manual_payment(
        booking=booking,
        amount_inr=amount_inr,
        actor=actor,
        payment_reference=payment_reference,
        note=note,
        payment_proof=payment_proof,
        send_payment_acknowledgement=send_payment_acknowledgement,
    )


def create_traveler_submitted_manual_payment(
    *,
    booking: Booking,
    amount_inr: int,
    payment_proof,
    payment_reference: str = "",
    note: str = "",
) -> ManualPayment:
    return payment_create_traveler_submitted_manual_payment(
        booking=booking,
        amount_inr=amount_inr,
        payment_proof=payment_proof,
        payment_reference=payment_reference,
        note=note,
    )


def approve_manual_payment(
    *,
    manual_payment: ManualPayment,
    actor=None,
) -> ManualPayment:
    return payment_approve_manual_payment(
        manual_payment=manual_payment,
        actor=actor,
    )


def reject_manual_payment(
    *,
    manual_payment: ManualPayment,
    actor=None,
    rejection_reason: str = "",
) -> ManualPayment:
    return payment_reject_manual_payment(
        manual_payment=manual_payment,
        actor=actor,
        rejection_reason=rejection_reason,
    )


def create_booking_adjustment(
    *,
    booking: Booking,
    amount_inr: int,
    adjustment_reason: str,
    actor=None,
) -> BookingAdjustment:
    return payment_create_booking_adjustment(
        booking=booking,
        amount_inr=amount_inr,
        adjustment_reason=adjustment_reason,
        actor=actor,
    )


def create_refund_record(
    *,
    booking: Booking,
    amount_inr: int,
    refund_reason: str,
    actor=None,
    refund_reference: str = "",
    send_acknowledgement: bool = False,
) -> RefundRecord:
    return payment_create_refund_record(
        booking=booking,
        amount_inr=amount_inr,
        refund_reason=refund_reason,
        actor=actor,
        refund_reference=refund_reference,
        send_acknowledgement=send_acknowledgement,
    )


def _actor_is_owner_for_booking(actor, booking: Booking) -> bool:
    if not getattr(actor, "is_authenticated", False):
        return False
    return OrganizerMembership.objects.filter(
        organizer_id=booking.trip.organizer_id,
        user=actor,
        role=OrganizerMembership.Role.OWNER,
    ).exists()


def _actor_can_use_operator_workflow_for_booking(actor, booking: Booking) -> bool:
    if not getattr(actor, "is_authenticated", False):
        return False
    return OrganizerMembership.objects.filter(
        organizer_id=booking.trip.organizer_id,
        user=actor,
        role__in=[
            OrganizerMembership.Role.OWNER,
            OrganizerMembership.Role.OPERATOR,
        ],
    ).exists()


def reserve_booking_if_ready(
    booking: Booking,
    *,
    payment_attempt: PaymentAttempt | None = None,
    provider_payment: ProviderPayment | None = None,
) -> bool:
    from trip_payments.reservation_rules import (
        reserve_booking_if_ready as payment_reserve_booking_if_ready,
    )

    return payment_reserve_booking_if_ready(
        booking,
        payment_attempt=payment_attempt,
        provider_payment=provider_payment,
    )


def _bookable_capacity_available_for_reservation(
    booking: Booking,
    *,
    payment_attempt: PaymentAttempt | None = None,
) -> bool:
    from trip_payments.reservation_rules import (
        bookable_capacity_available_for_reservation,
    )

    return bookable_capacity_available_for_reservation(
        booking,
        payment_attempt=payment_attempt,
        now=timezone.now(),
    )


def _validate_balance_payment_link_available(
    booking: Booking,
    *,
    amount_inr: int,
) -> None:
    if booking.booking_state == Booking.BookingState.DRAFT:
        raise ValidationError("Balance Payment Links are available after reservation.")
    if booking.booking_state == Booking.BookingState.CANCELLED:
        raise ValidationError("Cancelled Bookings cannot start Balance Payment Attempts.")
    if amount_inr <= 0:
        raise ValidationError("No balance is currently due.")
    if not is_online_payment_ready(booking.trip.organizer):
        readiness = online_payment_readiness(booking.trip.organizer)
        raise ValidationError(f"Online Payment Readiness is blocked: {readiness.message}")
