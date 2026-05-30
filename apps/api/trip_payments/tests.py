from __future__ import annotations

import hashlib
import hmac
import json
from datetime import date, datetime, timedelta
from importlib import import_module

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from organizer_payments.models import (
    ManualPaymentInstructions,
    PayoutAccount,
    ProviderPaymentSetup,
)
from organizer_payments.provider_credentials import SensitiveProviderCredentialStore
from organizers.models import Organizer
from organizers.operations.trip_overview import payment_summary_payload
from organizers.serializers import (
    reconciliation_flags_for_booking,
    reconciliation_payload,
)
from team_access.models import OrganizerMembership
from trip_bookings.models import Booking, BookingImport, BookingImportRow
from trip_operations.models import ActivityLog
from trip_payments.adjustments import create_booking_adjustment, create_refund_record
from trip_payments.financial_ledger import (
    FinancialLedger,
    booking_reconciliation,
    collected_provider_payment_amount_inr,
    derived_payment_state,
    effective_booking_total_inr,
)
from trip_payments.manual_review import (
    approve_manual_payment,
    record_sensitive_payment_information_download,
    reject_manual_payment,
)
from trip_payments.models import (
    BookingAdjustment,
    LedgerEntry,
    ManualPayment,
    OpeningPaymentRecord,
    PaymentAttempt,
    PaymentException,
    PlatformFeeStatement,
    ProviderPayment,
    RefundRecord,
    SeatHold,
)
from trip_payments.payment_exceptions import (
    record_late_confirmed_payment_exception,
    record_provider_dispute_exception,
    resolve_late_confirmed_payment_exception,
)
from trip_payments.platform_fees import generate_platform_fee_statement
from trip_payments.provider_adapters import ProviderCheckout, ProviderPaymentConfirmation
from trip_payments.provider_payment_lifecycle import (
    confirm_provider_payment,
    create_public_reservation_checkout,
    fail_payment_attempt,
    process_browser_checkout_success,
)
from trip_payments.provider_webhooks import process_razorpay_webhook
from trip_payments.seat_holds import active_seat_hold_count, bookable_seats
from trip_travelers.models import TravelerSlot
from trip_travelers.slots import active_reserved_traveler_count, available_seats
from trips.models import Trip, TripPackage, TripPaymentSchedule


class FakeProviderCheckoutAdapter:
    def __init__(self, provider_order_reference: str = "order_trip_payments_checkout_001"):
        self.provider_order_reference = provider_order_reference
        self.last_checkout_request = None

    def create_checkout(self, request):
        self.last_checkout_request = request
        return ProviderCheckout(
            provider=request.provider,
            provider_order_reference=self.provider_order_reference,
            checkout_payload={
                "provider": request.provider,
                "provider_order_reference": self.provider_order_reference,
                "amount_inr": request.amount_inr,
                "amount_minor": request.amount_inr * 100,
                "currency": request.currency,
                "payment_attempt": request.payment_attempt_id,
                "booking": request.booking_id,
                "payment_purpose": request.payment_purpose,
                "provider_payload": {
                    "order_id": self.provider_order_reference,
                    "amount": request.amount_inr * 100,
                    "currency": request.currency,
                },
            },
        )

    def verify_checkout_signature(self, request) -> bool:
        return request.checkout_signature == "valid-signature"

    def fetch_payment(self, request):
        checkout_request = self.last_checkout_request
        return ProviderPaymentConfirmation(
            provider=request.provider,
            provider_payment_reference=request.provider_payment_reference,
            provider_attempt_reference=self.provider_order_reference,
            amount_inr=checkout_request.amount_inr,
            status="captured",
            payment_attempt_id=checkout_request.payment_attempt_id,
            booking_id=checkout_request.booking_id,
            purpose=checkout_request.payment_purpose,
            provider_fee_amount_inr=120,
            provider_net_settlement_amount_inr=checkout_request.amount_inr - 120,
        )


@pytest.mark.django_db
def test_trip_payments_records_supported_ledger_events_and_provider_fees(monkeypatch):
    monkeypatch.setattr(
        "organizers.signals.send_manual_payment_acknowledgement",
        lambda manual_payment: [],
    )
    booking = create_reserved_booking()
    provider_attempt = PaymentAttempt.objects.create(
        booking=booking,
        amount_inr=5000,
        status=PaymentAttempt.Status.CONFIRMED,
        provider_attempt_reference="order_ledger_provider_001",
    )
    provider_payment = ProviderPayment.objects.create(
        booking=booking,
        payment_attempt=provider_attempt,
        amount_inr=5000,
        provider_fee_amount_inr=150,
        provider_net_settlement_amount_inr=4850,
        provider_payment_reference="pay_ledger_provider_001",
    )
    manual_payment = ManualPayment.objects.create(
        booking=booking,
        amount_inr=2000,
        payment_reference="upi-ledger-001",
    )
    opening_payment_record = OpeningPaymentRecord.objects.create(
        booking=booking,
        amount_inr=3000,
        payment_reference="opening-ledger-001",
        note="Imported before TripOS.",
    )
    booking_adjustment = BookingAdjustment.objects.create(
        booking=booking,
        amount_inr=-1000,
        adjustment_reason="Goodwill correction.",
    )
    refund_record = RefundRecord.objects.create(
        booking=booking,
        amount_inr=500,
        refund_reason="Partial refund.",
    )

    for event in (
        provider_payment,
        manual_payment,
        opening_payment_record,
        booking_adjustment,
        refund_record,
    ):
        first_entries = FinancialLedger.record_event(event)
        second_entries = FinancialLedger.record_event(event)
        assert [entry.id for entry in second_entries] == [entry.id for entry in first_entries]

    reconciliation = booking_reconciliation(booking)
    assert collected_provider_payment_amount_inr(booking) == 5000
    assert booking.collected_provider_payment_amount_inr == 5000
    assert reconciliation.collected_inr == 10000
    assert reconciliation.adjusted_inr == -1000
    assert reconciliation.refunded_inr == 500
    assert reconciliation.due_inr == 21500
    assert reconciliation.platform_fee_inr == 100
    assert LedgerEntry.objects.filter(provider_payment=provider_payment).count() == 2
    assert LedgerEntry.objects.filter(manual_payment=manual_payment).count() == 1
    assert LedgerEntry.objects.filter(opening_payment_record=opening_payment_record).count() == 1
    assert LedgerEntry.objects.filter(booking_adjustment=booking_adjustment).count() == 1
    assert LedgerEntry.objects.filter(refund_record=refund_record).count() == 1


@pytest.mark.django_db
def test_trip_payments_confirms_browser_checkout_and_records_provider_ledger():
    booking = create_checkout_ready_booking()
    adapter = FakeProviderCheckoutAdapter()
    checkout_session = create_public_reservation_checkout(booking, provider_adapter=adapter)

    checkout_result = process_browser_checkout_success(
        checkout_session.payment_attempt,
        provider_payment_reference="pay_browser_success_trip_payments_001",
        provider_attempt_reference=adapter.provider_order_reference,
        checkout_signature="valid-signature",
        provider_adapter=adapter,
    )

    checkout_result.payment_attempt.refresh_from_db()
    booking.refresh_from_db()
    provider_payment = ProviderPayment.objects.get(payment_attempt=checkout_result.payment_attempt)

    assert checkout_result.provider_state_verified is True
    assert checkout_result.provider_payment == provider_payment
    assert checkout_result.payment_attempt.status == PaymentAttempt.Status.CONFIRMED
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert provider_payment.amount_inr == checkout_session.payment_attempt.amount_inr
    assert provider_payment.provider_fee_amount_inr == 120
    assert collected_provider_payment_amount_inr(booking) == provider_payment.amount_inr
    assert LedgerEntry.objects.filter(provider_payment=provider_payment).count() == 2


@pytest.mark.django_db
def test_trip_payments_failed_provider_checkout_releases_attempt_without_payment():
    booking = create_checkout_ready_booking(title="Failed Checkout")
    checkout_session = create_public_reservation_checkout(
        booking,
        provider_adapter=FakeProviderCheckoutAdapter("order_trip_payments_failed_001"),
    )

    with pytest.raises(ValidationError):
        process_browser_checkout_success(
            checkout_session.payment_attempt,
            provider_payment_reference="pay_browser_failed_trip_payments_001",
            provider_attempt_reference=checkout_session.payment_attempt.provider_attempt_reference,
            checkout_signature="bad-signature",
            provider_adapter=FakeProviderCheckoutAdapter("order_trip_payments_failed_001"),
        )
    failed_attempt = fail_payment_attempt(
        checkout_session.payment_attempt,
        failure_reason="Provider declined the payment.",
    )

    failed_attempt.refresh_from_db()
    assert failed_attempt.status == PaymentAttempt.Status.FAILED
    assert failed_attempt.failure_reason == "Provider declined the payment."
    assert not ProviderPayment.objects.filter(payment_attempt=failed_attempt).exists()
    assert failed_attempt.seat_hold.released_at is not None


@pytest.mark.django_db
@override_settings(TRIPOS_SEAT_HOLD_SECONDS=300)
def test_trip_payments_owns_seat_hold_creation_expiry_and_release():
    booking = create_checkout_ready_booking(title="Seat Hold Lifecycle", capacity=2, slot_count=2)
    trip = booking.trip

    before_create = timezone.now()
    checkout_session = create_public_reservation_checkout(
        booking,
        provider_adapter=FakeProviderCheckoutAdapter("order_trip_payments_hold_001"),
    )
    after_create = timezone.now()
    seat_hold = SeatHold.objects.get(payment_attempt=checkout_session.payment_attempt)

    assert seat_hold.booking == booking
    assert seat_hold.trip == trip
    assert seat_hold.seat_count == 2
    assert seat_hold.released_at is None
    assert before_create + timedelta(seconds=300) <= seat_hold.expires_at
    assert seat_hold.expires_at <= after_create + timedelta(seconds=300)
    assert available_seats(trip) == 2
    assert active_seat_hold_count(trip) == 2
    assert bookable_seats(trip) == 0

    SeatHold.objects.filter(payment_attempt=checkout_session.payment_attempt).update(
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    assert active_seat_hold_count(trip) == 0
    assert bookable_seats(trip) == 2

    released_attempt = fail_payment_attempt(
        checkout_session.payment_attempt,
        failure_reason="Traveler abandoned checkout.",
    )
    seat_hold.refresh_from_db()
    assert released_attempt.status == PaymentAttempt.Status.FAILED
    assert seat_hold.released_at is not None


@pytest.mark.django_db
def test_trip_payments_captured_provider_payment_reserves_seats_and_releases_hold():
    booking = create_checkout_ready_booking(title="Captured Reservation", capacity=1)
    checkout_session = create_public_reservation_checkout(
        booking,
        provider_adapter=FakeProviderCheckoutAdapter("order_trip_payments_capture_001"),
    )
    seat_hold = SeatHold.objects.get(payment_attempt=checkout_session.payment_attempt)

    provider_payment = confirm_provider_payment(
        checkout_session.payment_attempt,
        provider_payment_reference="pay_trip_payments_capture_001",
        amount_inr=checkout_session.payment_attempt.amount_inr,
    )

    booking.refresh_from_db()
    seat_hold.refresh_from_db()
    assert isinstance(provider_payment, ProviderPayment)
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert seat_hold.released_at is not None
    assert active_seat_hold_count(booking.trip) == 0
    assert active_reserved_traveler_count(booking.trip) == 1
    assert available_seats(booking.trip) == 0
    assert bookable_seats(booking.trip) == 0


@pytest.mark.django_db
def test_trip_payments_late_expired_hold_creates_exception_when_capacity_is_taken():
    booking = create_checkout_ready_booking(title="Late Capacity Exception", capacity=1)
    trip = booking.trip
    package = trip.packages.get()
    checkout_session = create_public_reservation_checkout(
        booking,
        provider_adapter=FakeProviderCheckoutAdapter("order_trip_payments_late_001"),
    )
    SeatHold.objects.filter(payment_attempt=checkout_session.payment_attempt).update(
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    competing_booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Competing Contact",
        booking_contact_phone="+919111111111",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=competing_booking, package=package, position=1)

    payment_exception = confirm_provider_payment(
        checkout_session.payment_attempt,
        provider_payment_reference="pay_trip_payments_late_001",
        amount_inr=checkout_session.payment_attempt.amount_inr,
    )

    booking.refresh_from_db()
    checkout_session.payment_attempt.refresh_from_db()
    assert isinstance(payment_exception, PaymentException)
    assert payment_exception.exception_type == PaymentException.ExceptionType.LATE_CONFIRMED_PAYMENT
    assert booking.booking_state == Booking.BookingState.DRAFT
    assert checkout_session.payment_attempt.status == PaymentAttempt.Status.CONFIRMED
    assert ProviderPayment.objects.filter(payment_attempt=checkout_session.payment_attempt).exists()
    assert active_reserved_traveler_count(trip) == 1
    assert available_seats(trip) == 0


@pytest.mark.django_db
def test_trip_payments_records_mismatched_provider_payment_exception_facts():
    booking = create_checkout_ready_booking(title="Mismatched Provider Payment")
    checkout_session = create_public_reservation_checkout(
        booking,
        provider_adapter=FakeProviderCheckoutAdapter("order_trip_payments_mismatch_001"),
    )

    payment_exception = confirm_provider_payment(
        checkout_session.payment_attempt,
        provider_payment_reference="pay_trip_payments_mismatch_001",
        amount_inr=checkout_session.payment_attempt.amount_inr + 100,
    )

    assert isinstance(payment_exception, PaymentException)
    assert payment_exception.exception_type == (
        PaymentException.ExceptionType.MISMATCHED_PROVIDER_PAYMENT
    )
    assert payment_exception.status == PaymentException.Status.OPEN
    assert payment_exception.booking == booking
    assert payment_exception.provider_payment is None
    assert payment_exception.provider_payment_reference == "pay_trip_payments_mismatch_001"
    assert payment_exception.mismatch_reasons == ["amount"]
    assert payment_exception.details["expected"]["amount_inr"] == (
        checkout_session.payment_attempt.amount_inr
    )
    assert payment_exception.details["reported"]["amount_inr"] == (
        checkout_session.payment_attempt.amount_inr + 100
    )
    assert not ProviderPayment.objects.filter(
        provider_payment_reference="pay_trip_payments_mismatch_001",
    ).exists()
    assert ActivityLog.objects.filter(
        booking=booking,
        action=ActivityLog.Action.PAYMENT_EXCEPTION_CREATED,
        metadata__payment_exception_id=payment_exception.id,
    ).exists()


@pytest.mark.django_db
@override_settings(TRIPOS_RAZORPAY_WEBHOOK_SECRET="trip-payments-webhook-secret")
def test_trip_payments_razorpay_webhook_duplicate_is_idempotent():
    booking = create_checkout_ready_booking(title="Webhook Idempotency")
    checkout_session = create_public_reservation_checkout(
        booking,
        provider_adapter=FakeProviderCheckoutAdapter("order_trip_payments_webhook_001"),
    )
    body = razorpay_payment_webhook_body(
        checkout_session.payment_attempt,
        event_reference="evt_trip_payments_duplicate_001",
        provider_payment_reference="pay_trip_payments_duplicate_001",
        provider_fee_amount_inr=80,
    )
    signature = razorpay_webhook_signature(body, "trip-payments-webhook-secret")

    first_result = process_razorpay_webhook(body=body, signature=signature)
    second_result = process_razorpay_webhook(body=body, signature=signature)

    assert first_result.duplicate is False
    assert second_result.duplicate is True
    assert second_result.webhook_event.id == first_result.webhook_event.id
    assert ProviderPayment.objects.count() == 1
    provider_payment = ProviderPayment.objects.get()
    assert provider_payment.provider_payment_reference == "pay_trip_payments_duplicate_001"
    assert provider_payment.provider_fee_amount_inr == 80
    assert LedgerEntry.objects.filter(provider_payment=provider_payment).count() == 2


@pytest.mark.django_db
def test_legacy_provider_payment_confirmation_api_stays_compatible():
    booking = create_checkout_ready_booking(title="Provider API Compatibility")
    checkout_session = create_public_reservation_checkout(
        booking,
        provider_adapter=FakeProviderCheckoutAdapter("order_trip_payments_api_001"),
    )
    attempt = checkout_session.payment_attempt

    response = APIClient().post(
        f"/api/public/payment-attempts/{attempt.id}/provider-confirmation/",
        data={
            "payment_attempt": attempt.id,
            "booking": booking.id,
            "provider": attempt.provider,
            "purpose": attempt.purpose,
            "provider_attempt_reference": attempt.provider_attempt_reference,
            "provider_payment_reference": "pay_trip_payments_api_001",
            "amount_inr": attempt.amount_inr,
            "provider_fee_amount_inr": 90,
            "provider_net_settlement_amount_inr": attempt.amount_inr - 90,
        },
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    provider_payment = ProviderPayment.objects.get(payment_attempt=attempt)
    assert payload["id"] == provider_payment.id
    assert payload["gross_amount_inr"] == attempt.amount_inr
    assert payload["provider_fee_amount_inr"] == 90
    assert payload["platform_fee_inr"] == 160
    assert LedgerEntry.objects.filter(provider_payment=provider_payment).count() == 2


@pytest.mark.django_db
def test_trip_payments_generates_platform_fee_statement_from_ledger_facts():
    booking = create_reserved_booking(title="Platform Fee Statement")
    may_15 = timezone.make_aware(datetime(2026, 5, 15, 10, 30))
    may_20 = timezone.make_aware(datetime(2026, 5, 20, 10, 30))
    june_1 = timezone.make_aware(datetime(2026, 6, 1, 10, 30))
    reservation_attempt = PaymentAttempt.objects.create(
        booking=booking,
        amount_inr=8000,
        status=PaymentAttempt.Status.CONFIRMED,
        provider_attempt_reference="order_statement_reservation_001",
    )
    balance_attempt = PaymentAttempt.objects.create(
        booking=booking,
        purpose=PaymentAttempt.Purpose.BALANCE,
        amount_inr=4000,
        status=PaymentAttempt.Status.CONFIRMED,
        provider_attempt_reference="order_statement_balance_001",
    )
    outside_period_attempt = PaymentAttempt.objects.create(
        booking=booking,
        purpose=PaymentAttempt.Purpose.BALANCE,
        amount_inr=2000,
        status=PaymentAttempt.Status.CONFIRMED,
        provider_attempt_reference="order_statement_june_001",
    )
    ProviderPayment.objects.create(
        booking=booking,
        payment_attempt=reservation_attempt,
        amount_inr=8000,
        provider_payment_reference="pay_statement_reservation_001",
        confirmed_at=may_15,
    )
    ProviderPayment.objects.create(
        booking=booking,
        payment_attempt=balance_attempt,
        amount_inr=4000,
        provider_payment_reference="pay_statement_balance_001",
        confirmed_at=may_20,
    )
    ProviderPayment.objects.create(
        booking=booking,
        payment_attempt=outside_period_attempt,
        amount_inr=2000,
        provider_payment_reference="pay_statement_june_001",
        confirmed_at=june_1,
    )

    statement = generate_platform_fee_statement(
        booking.trip.organizer,
        date(2026, 5, 29),
        status=PlatformFeeStatement.Status.ISSUED,
        notes="May pilot statement.",
    )

    assert statement.period_start == date(2026, 5, 1)
    assert statement.period_end == date(2026, 6, 1)
    assert statement.status == PlatformFeeStatement.Status.ISSUED
    assert statement.notes == "May pilot statement."
    assert statement.provider_payment_count == 2
    assert statement.gross_provider_payment_amount_inr == 12000
    assert statement.platform_fee_amount_inr == 240

    refreshed = generate_platform_fee_statement(
        booking.trip.organizer,
        date(2026, 5, 1),
        status=PlatformFeeStatement.Status.COLLECTED,
    )

    assert refreshed.id == statement.id
    assert refreshed.status == PlatformFeeStatement.Status.COLLECTED
    assert refreshed.provider_payment_count == 2
    assert PlatformFeeStatement.objects.count() == 1


@pytest.mark.django_db
def test_internal_admin_platform_fee_statement_api_uses_trip_payments_hooks():
    booking = create_reserved_booking(title="Internal Admin Fee Statement")
    confirmed_at = timezone.make_aware(datetime(2026, 5, 15, 10, 30))
    attempt = PaymentAttempt.objects.create(
        booking=booking,
        amount_inr=8000,
        status=PaymentAttempt.Status.CONFIRMED,
        provider_attempt_reference="order_internal_admin_statement_001",
    )
    ProviderPayment.objects.create(
        booking=booking,
        payment_attempt=attempt,
        amount_inr=8000,
        provider_payment_reference="pay_internal_admin_statement_001",
        confirmed_at=confirmed_at,
    )
    staff = create_user("fee-staff@example.com")
    staff.is_staff = True
    staff.save(update_fields=["is_staff"])
    client = APIClient()
    client.force_authenticate(staff)

    create_response = client.post(
        "/api/internal-admin/platform-fee-statements/",
        data={
            "organizer": booking.trip.organizer_id,
            "period_start": "2026-05-01",
            "status": PlatformFeeStatement.Status.ISSUED,
            "notes": "Ready for collection.",
        },
        format="json",
    )

    assert create_response.status_code == 201
    created_payload = create_response.json()
    statement_id = created_payload["id"]
    assert created_payload["platform_fee_amount_inr"] == 160
    assert created_payload["provider_payment_count"] == 1
    assert created_payload["status"] == PlatformFeeStatement.Status.ISSUED

    patch_response = client.patch(
        f"/api/internal-admin/platform-fee-statements/{statement_id}/",
        data={"status": PlatformFeeStatement.Status.COLLECTED},
        format="json",
    )
    list_response = client.get(
        "/api/internal-admin/platform-fee-statements/",
        data={"organizer": booking.trip.organizer_id},
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == PlatformFeeStatement.Status.COLLECTED
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == statement_id


@pytest.mark.django_db
def test_trip_payments_records_provider_disputes_and_resolves_late_exceptions():
    booking = create_reserved_booking(title="Payment Exception Review")
    operator = create_user("exception-operator@example.com")
    OrganizerMembership.objects.create(
        user=operator,
        organizer=booking.trip.organizer,
        role=OrganizerMembership.Role.OPERATOR,
    )
    attempt = PaymentAttempt.objects.create(
        booking=booking,
        amount_inr=8000,
        status=PaymentAttempt.Status.CONFIRMED,
        provider_attempt_reference="order_exception_review_001",
    )
    provider_payment = ProviderPayment.objects.create(
        booking=booking,
        payment_attempt=attempt,
        amount_inr=8000,
        provider_payment_reference="pay_exception_review_001",
    )

    late_exception = record_late_confirmed_payment_exception(
        provider_payment,
        payment_attempt=attempt,
    )
    resolved = resolve_late_confirmed_payment_exception(
        late_exception,
        actor=operator,
        resolution_note="Manually confirmed the booking outcome.",
    )
    dispute_exception = record_provider_dispute_exception(
        provider_payment,
        provider_event_type=PaymentException.ProviderEventType.CHARGEBACK,
        provider_dispute_reference="disp_exception_review_001",
        amount_inr=4000,
        details={"provider_reason": "chargeback_opened"},
    )
    duplicate_dispute = record_provider_dispute_exception(
        provider_payment,
        provider_event_type=PaymentException.ProviderEventType.CHARGEBACK,
        provider_dispute_reference="disp_exception_review_001",
    )

    assert resolved.status == PaymentException.Status.BOOKING_OPERATIONS_RESOLVED
    assert resolved.resolved_by == operator
    assert resolved.resolution_note == "Manually confirmed the booking outcome."
    assert dispute_exception.exception_type == PaymentException.ExceptionType.PROVIDER_DISPUTE
    assert dispute_exception.status == PaymentException.Status.OPEN
    assert dispute_exception.amount_inr == 4000
    assert dispute_exception.details == {"provider_reason": "chargeback_opened"}
    assert duplicate_dispute.id == dispute_exception.id
    assert not RefundRecord.objects.filter(booking=booking).exists()
    assert PaymentException.objects.filter(provider_payment=provider_payment).count() == 2
    assert ActivityLog.objects.filter(
        booking=booking,
        action=ActivityLog.Action.PAYMENT_EXCEPTION_RESOLVED,
        actor=operator,
        metadata__payment_exception_id=resolved.id,
    ).exists()


@pytest.mark.django_db
def test_public_qr_manual_payment_submission_api_stays_compatible():
    trip, package = create_manual_qr_trip()
    payment_proof = SimpleUploadedFile(
        "payment-proof.png",
        b"\x89PNG\r\n\x1a\nproof",
        content_type="image/png",
    )

    response = APIClient().post(
        f"/api/public/trips/{trip.organizer.slug}/{trip.slug}/manual-payments/",
        data={
            "booking_contact_name": "Asha Nair",
            "booking_contact_phone": "+919876543210",
            "booking_contact_email": "asha@example.com",
            "traveler_count": 2,
            "package": package.id,
            "payment_reference": "upi-trip-payments-001",
            "note": "Paid by UPI.",
            "payment_proof": payment_proof,
        },
        format="multipart",
    )

    assert response.status_code == 201
    manual_payment = ManualPayment.objects.get()
    assert manual_payment.source == ManualPayment.Source.TRAVELER_SUBMITTED
    assert manual_payment.status == ManualPayment.Status.SUBMITTED
    assert manual_payment.amount_inr == 7000
    assert manual_payment.payment_reference == "upi-trip-payments-001"
    assert manual_payment.booking.booking_state == Booking.BookingState.DRAFT
    assert not LedgerEntry.objects.filter(manual_payment=manual_payment).exists()


@pytest.mark.django_db
def test_trip_payments_derives_payment_state_from_ledger_facts():
    booking = create_reserved_booking()

    assert derived_payment_state(booking) == "unpaid"

    OpeningPaymentRecord.objects.create(booking=booking, amount_inr=8000)
    assert derived_payment_state(booking) == "reservation_paid"

    OpeningPaymentRecord.objects.create(booking=booking, amount_inr=5000)
    assert derived_payment_state(booking) == "partially_paid"

    OpeningPaymentRecord.objects.create(booking=booking, amount_inr=19000)
    assert derived_payment_state(booking) == "fully_paid"
    assert FinancialLedger.for_booking(booking).reconciliation().due_inr == 0


@pytest.mark.django_db
def test_trip_payments_derives_overdue_refund_due_and_refunded_states(monkeypatch):
    monkeypatch.setattr(
        "trip_payments.financial_ledger.timezone.localdate",
        lambda: date(2026, 5, 29),
    )
    booking = create_reserved_booking(start_date=date(2026, 5, 20))

    OpeningPaymentRecord.objects.create(booking=booking, amount_inr=8000)
    overdue_reconciliation = booking_reconciliation(booking)

    assert overdue_reconciliation.due_inr == 24000
    assert overdue_reconciliation.overdue_inr == 24000
    assert derived_payment_state(booking) == "overdue"

    BookingAdjustment.objects.create(
        booking=booking,
        amount_inr=-26000,
        adjustment_reason="Commercial correction.",
    )
    refund_due_reconciliation = booking_reconciliation(booking)

    assert effective_booking_total_inr(booking) == 6000
    assert refund_due_reconciliation.refund_due_inr == 2000
    assert derived_payment_state(booking) == "refund_due"

    RefundRecord.objects.create(
        booking=booking,
        amount_inr=2000,
        refund_reason="Returned over-collected balance.",
    )
    assert booking_reconciliation(booking).refund_due_inr == 0
    assert derived_payment_state(booking) == "fully_paid"

    refunded_booking = create_reserved_booking(title="Refunded state")
    OpeningPaymentRecord.objects.create(booking=refunded_booking, amount_inr=8000)
    RefundRecord.objects.create(
        booking=refunded_booking,
        amount_inr=8000,
        refund_reason="Reservation refunded.",
    )

    assert derived_payment_state(refunded_booking) == "refunded"


@pytest.mark.django_db
def test_trip_payments_records_package_change_ledger_for_nonzero_deltas_only():
    booking = create_reserved_booking()

    positive_entry = FinancialLedger.record_package_change(
        booking=booking,
        amount_inr=10000,
        description="Traveler Package changed from Base to Plus.",
    )
    zero_entry = FinancialLedger.record_package_change(
        booking=booking,
        amount_inr=0,
        description="No commercial package change.",
    )
    negative_entry = FinancialLedger.record_package_change(
        booking=booking,
        amount_inr=-3000,
        description="Traveler Package changed from Plus to Base.",
    )

    assert positive_entry is not None
    assert zero_entry is None
    assert negative_entry is not None
    assert list(
        booking.ledger_entries.filter(entry_type=LedgerEntry.EntryType.PACKAGE_CHANGE)
        .order_by("id")
        .values_list("amount_inr", flat=True)
    ) == [10000, -3000]


@pytest.mark.django_db
def test_legacy_payment_summary_and_reconciliation_flag_shims_stay_compatible(monkeypatch):
    monkeypatch.setattr(
        "organizers.signals.send_manual_payment_acknowledgement",
        lambda manual_payment: [],
    )
    booking = create_reserved_booking()
    provider_attempt = PaymentAttempt.objects.create(
        booking=booking,
        amount_inr=8000,
        status=PaymentAttempt.Status.CONFIRMED,
        provider_attempt_reference="order_summary_provider_001",
    )
    ProviderPayment.objects.create(
        booking=booking,
        payment_attempt=provider_attempt,
        amount_inr=8000,
        provider_fee_amount_inr=240,
        provider_net_settlement_amount_inr=7760,
        provider_payment_reference="pay_summary_provider_001",
    )
    PaymentAttempt.objects.create(
        booking=booking,
        purpose=PaymentAttempt.Purpose.BALANCE,
        amount_inr=24000,
        status=PaymentAttempt.Status.PENDING,
        provider_attempt_reference="order_summary_pending_001",
    )
    PaymentAttempt.objects.create(
        booking=booking,
        purpose=PaymentAttempt.Purpose.RESERVATION,
        amount_inr=8000,
        status=PaymentAttempt.Status.FAILED,
        provider_attempt_reference="order_summary_failed_001",
    )
    ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=2000,
        payment_reference="upi-summary-submitted-001",
    )
    booking_import = BookingImport.objects.create(
        trip=booking.trip,
        status=BookingImport.Status.COMPLETED_WITH_CONFLICTS,
        conflict_count=1,
    )
    BookingImportRow.objects.create(
        booking_import=booking_import,
        booking=booking,
        row_number=1,
        status=BookingImportRow.Status.CONFLICT,
        conflict_code="validation_conflict",
    )

    summary = payment_summary_payload([booking])
    flags = reconciliation_flags_for_booking(booking)
    payload = reconciliation_payload(booking)

    assert summary["collected_inr"] == 8000
    assert summary["due_inr"] == 24000
    assert summary["platform_fee_inr"] == 160
    assert summary["gross_provider_payment_amount_inr"] == 8000
    assert summary["provider_fee_amount_inr"] == 240
    assert summary["provider_net_settlement_amount_inr"] == 7760
    assert summary["pending_manual_payments"] == 1
    assert payload["collected_inr"] == 8000
    assert payload["due_inr"] == 24000
    assert flags == [
        "pending_payment_attempt",
        "failed_payment_attempt",
        "submitted_manual_payment",
        "booking_import_conflict",
    ]


@pytest.mark.django_db
def test_trip_payments_approves_manual_payment_and_records_ledger_effects(monkeypatch):
    mute_payment_notifications(monkeypatch)
    actor = create_user("manual-review-operator@example.com")
    booking = create_reserved_booking(title="Manual Review Approval")
    booking.booking_state = Booking.BookingState.DRAFT
    booking.save(update_fields=["booking_state", "updated_at"])
    manual_payment = ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=booking.booking_reservation_amount_inr,
        payment_reference="upi-review-approval-001",
        payment_proof=SimpleUploadedFile(
            "proof.png",
            b"\x89PNG\r\n\x1a\n",
            content_type="image/png",
        ),
    )

    approved = approve_manual_payment(manual_payment=manual_payment, actor=actor)

    booking.refresh_from_db()
    ledger_entry = LedgerEntry.objects.get(manual_payment=approved)
    assert approved.status == ManualPayment.Status.APPROVED
    assert approved.approved_by == actor
    assert booking.booking_state == Booking.BookingState.RESERVED
    assert ledger_entry.entry_type == LedgerEntry.EntryType.APPROVED_MANUAL_PAYMENT
    assert ledger_entry.amount_inr == booking.booking_reservation_amount_inr
    assert booking_reconciliation(booking).collected_inr == booking.booking_reservation_amount_inr
    assert derived_payment_state(booking) == "reservation_paid"
    assert active_reserved_traveler_count(booking.trip) == 1
    assert available_seats(booking.trip) == booking.trip.capacity - 1


@pytest.mark.django_db
def test_trip_payments_records_sensitive_manual_payment_activity():
    actor = create_user("manual-payment-download@example.com")
    booking = create_reserved_booking(title="Sensitive Manual Payment Activity")
    proof = b"\x89PNG\r\n\x1a\nproof"
    manual_payment = ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=8000,
        payment_reference="upi-sensitive-download-001",
        payment_proof=SimpleUploadedFile(
            "payment-proof.png",
            proof,
            content_type="image/png",
        ),
        original_filename="payment-proof.png",
        content_type="image/png",
        file_size=len(proof),
    )

    record_sensitive_payment_information_download(manual_payment, actor=actor)

    assert ActivityLog.objects.filter(
        booking=booking,
        action=ActivityLog.Action.SENSITIVE_PAYMENT_INFORMATION_DOWNLOAD,
        actor=actor,
        metadata__manual_payment=manual_payment.id,
        metadata__is_sensitive_payment_information=True,
    ).exists()


@pytest.mark.django_db
def test_trip_payments_rejects_manual_payment_without_ledger_effects():
    actor = create_user("manual-review-rejector@example.com")
    booking = create_reserved_booking(title="Manual Review Rejection")
    manual_payment = ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=2000,
        payment_reference="upi-review-reject-001",
        note="Traveler uploaded the wrong payment proof.",
    )

    rejected = reject_manual_payment(
        manual_payment=manual_payment,
        actor=actor,
        rejection_reason="Amount does not match the booking.",
    )

    assert rejected.status == ManualPayment.Status.REJECTED
    assert rejected.approved_by == actor
    assert "Rejection Reason: Amount does not match the booking." in rejected.note
    assert LedgerEntry.objects.filter(manual_payment=rejected).count() == 0
    assert booking_reconciliation(booking).collected_inr == 0


@pytest.mark.django_db
def test_trip_payments_records_adjustments_refunds_and_activity(monkeypatch):
    monkeypatch.setattr(
        "organizers.services.send_refund_acknowledgement",
        lambda **kwargs: [],
    )
    operator = create_user("payment-correction-operator@example.com")
    owner = create_user("payment-correction-owner@example.com")
    booking = create_reserved_booking(title="Payment Corrections")
    OpeningPaymentRecord.objects.create(booking=booking, amount_inr=10000)

    adjustment = create_booking_adjustment(
        booking=booking,
        amount_inr=-25000,
        adjustment_reason="Cancelled add-on removed from booking total.",
        actor=operator,
    )

    adjustment_ledger_entry = LedgerEntry.objects.get(booking_adjustment=adjustment)
    assert adjustment.recorded_by == operator
    assert adjustment_ledger_entry.entry_type == LedgerEntry.EntryType.BOOKING_ADJUSTMENT
    assert adjustment_ledger_entry.amount_inr == -25000
    assert booking_reconciliation(booking).refund_due_inr == 3000
    assert ActivityLog.objects.filter(
        booking=booking,
        action=ActivityLog.Action.BOOKING_ADJUSTMENT_RECORDED,
        actor=operator,
        metadata__booking_adjustment_id=adjustment.id,
    ).exists()

    with pytest.raises(ValidationError, match="Only Owners can create Refund Records"):
        create_refund_record(
            booking=booking,
            amount_inr=3000,
            refund_reason="Returned over-collected amount.",
            actor=operator,
        )

    OrganizerMembership.objects.create(
        user=owner,
        organizer=booking.trip.organizer,
        role=OrganizerMembership.Role.OWNER,
    )
    refund_record = create_refund_record(
        booking=booking,
        amount_inr=3000,
        refund_reason="Returned over-collected amount.",
        refund_reference="upi-refund-correction-001",
        actor=owner,
    )

    refund_ledger_entry = LedgerEntry.objects.get(refund_record=refund_record)
    reconciliation = booking_reconciliation(booking)
    assert refund_record.recorded_by == owner
    assert refund_ledger_entry.entry_type == LedgerEntry.EntryType.REFUND_RECORD
    assert refund_ledger_entry.amount_inr == 3000
    assert reconciliation.refunded_inr == 3000
    assert reconciliation.refund_due_inr == 0
    assert reconciliation.due_inr == 0
    assert derived_payment_state(booking) == "fully_paid"
    assert ActivityLog.objects.filter(
        booking=booking,
        action=ActivityLog.Action.REFUND_RECORD_RECORDED,
        actor=owner,
        metadata__refund_record_id=refund_record.id,
    ).exists()


@pytest.mark.django_db
def test_legacy_manual_payment_api_classes_reexport_trip_payments_implementations():
    from organizers.serializers import (
        BookingAdjustmentSerializer as LegacyBookingAdjustmentSerializer,
    )
    from organizers.serializers import (
        OperationsManualPaymentSerializer as LegacyManualPaymentSerializer,
    )
    from organizers.serializers import RefundRecordSerializer as LegacyRefundRecordSerializer
    from organizers.views import (
        OperationsBookingAdjustmentCreateView as LegacyAdjustmentView,
    )
    from organizers.views import OperationsManualPaymentApproveView as LegacyApprovalView
    from organizers.views import OperationsRefundRecordCreateView as LegacyRefundView
    from trip_payments.serializers import (
        BookingAdjustmentSerializer as PaymentBookingAdjustmentSerializer,
    )
    from trip_payments.serializers import (
        OperationsManualPaymentSerializer as PaymentManualPaymentSerializer,
    )
    from trip_payments.serializers import RefundRecordSerializer as PaymentRefundRecordSerializer
    from trip_payments.views import (
        OperationsBookingAdjustmentCreateView as PaymentAdjustmentView,
    )
    from trip_payments.views import OperationsManualPaymentApproveView as PaymentApprovalView
    from trip_payments.views import OperationsRefundRecordCreateView as PaymentRefundView

    assert LegacyManualPaymentSerializer is PaymentManualPaymentSerializer
    assert LegacyBookingAdjustmentSerializer is PaymentBookingAdjustmentSerializer
    assert LegacyRefundRecordSerializer is PaymentRefundRecordSerializer
    assert LegacyApprovalView is PaymentApprovalView
    assert LegacyAdjustmentView is PaymentAdjustmentView
    assert LegacyRefundView is PaymentRefundView


@pytest.mark.django_db
def test_legacy_platform_fee_and_exception_api_classes_reexport_trip_payments_owners():
    from organizers.serializers import (
        InternalAdminPlatformFeeStatementManageSerializer as LegacyStatementManageSerializer,
    )
    from organizers.serializers import (
        InternalAdminPlatformFeeStatementSerializer as LegacyStatementSerializer,
    )
    from organizers.serializers import (
        PaymentExceptionResolutionSerializer as LegacyExceptionResolutionSerializer,
    )
    from organizers.serializers import PaymentExceptionSerializer as LegacyExceptionSerializer
    from organizers.views import (
        InternalAdminPlatformFeeStatementDetailView as LegacyStatementDetailView,
    )
    from organizers.views import (
        InternalAdminPlatformFeeStatementListCreateView as LegacyStatementListView,
    )
    from organizers.views import (
        OperationsPaymentExceptionResolveView as LegacyExceptionResolveView,
    )
    from trip_payments.serializers import (
        InternalAdminPlatformFeeStatementManageSerializer as PaymentStatementManageSerializer,
    )
    from trip_payments.serializers import (
        InternalAdminPlatformFeeStatementSerializer as PaymentStatementSerializer,
    )
    from trip_payments.serializers import (
        PaymentExceptionResolutionSerializer as PaymentExceptionResolutionSerializer,
    )
    from trip_payments.serializers import PaymentExceptionSerializer as PaymentExceptionSerializer
    from trip_payments.views import (
        InternalAdminPlatformFeeStatementDetailView as PaymentStatementDetailView,
    )
    from trip_payments.views import (
        InternalAdminPlatformFeeStatementListCreateView as PaymentStatementListView,
    )
    from trip_payments.views import (
        OperationsPaymentExceptionResolveView as PaymentExceptionResolveView,
    )

    legacy_root_platform_fees = import_module("organizers.platform_fees")
    legacy_payment_platform_fees = import_module("organizers.payments.platform_fees")
    trip_payment_platform_fees = import_module("trip_payments.platform_fees")

    assert LegacyStatementSerializer is PaymentStatementSerializer
    assert LegacyStatementManageSerializer is PaymentStatementManageSerializer
    assert LegacyExceptionSerializer is PaymentExceptionSerializer
    assert LegacyExceptionResolutionSerializer is PaymentExceptionResolutionSerializer
    assert LegacyStatementListView is PaymentStatementListView
    assert LegacyStatementDetailView is PaymentStatementDetailView
    assert LegacyExceptionResolveView is PaymentExceptionResolveView
    assert (
        legacy_root_platform_fees.generate_platform_fee_statement
        is trip_payment_platform_fees.generate_platform_fee_statement
    )
    assert (
        legacy_payment_platform_fees.refresh_platform_fee_statement
        is trip_payment_platform_fees.refresh_platform_fee_statement
    )


@pytest.mark.django_db
def test_legacy_seat_hold_imports_reexport_trip_payments_owner():
    legacy_root = import_module("organizers.seat_holds")
    legacy_payments = import_module("organizers.payments.seat_holds")
    trip_payment_holds = import_module("trip_payments.seat_holds")

    assert (
        legacy_root.create_seat_hold_for_payment_attempt
        is trip_payment_holds.create_seat_hold_for_payment_attempt
    )
    assert legacy_payments.bookable_seats is trip_payment_holds.bookable_seats
    assert legacy_payments.active_seat_hold_count is trip_payment_holds.active_seat_hold_count


def mute_payment_notifications(monkeypatch):
    monkeypatch.setattr(
        "organizers.signals.send_manual_payment_acknowledgement",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        "organizers.services.send_manual_payment_acknowledgement",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        "organizers.services.send_reservation_acknowledgement",
        lambda *args, **kwargs: [],
    )


def create_user(email: str):
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        password="password",
    )


def create_reserved_booking(
    *,
    title: str = "Spiti Summer",
    start_date: date = date(2026, 7, 10),
) -> Booking:
    organizer = Organizer.objects.create(name=f"{title} Collective")
    trip = Trip.objects.create(
        organizer=organizer,
        title=title,
        start_date=start_date,
        end_date=date(start_date.year, start_date.month, start_date.day + 5),
        capacity=12,
    )
    TripPaymentSchedule.objects.create(trip=trip, balance_due_days_before_start=3)
    package = TripPackage.objects.create(
        trip=trip,
        name="Base",
        price_inr=32000,
        reservation_amount_inr=8000,
        position=1,
    )
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(booking=booking, package=package, position=1)
    return booking


def create_checkout_ready_booking(
    *,
    title: str = "Checkout Ready",
    capacity: int = 8,
    slot_count: int = 1,
) -> Booking:
    organizer = Organizer.objects.create(name=f"{title} Collective")
    mark_online_payment_ready(organizer)
    trip = Trip.objects.create(
        organizer=organizer,
        title=title,
        start_date=date(2026, 7, 10),
        end_date=date(2026, 7, 15),
        capacity=capacity,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
    )
    TripPaymentSchedule.objects.create(trip=trip, balance_due_days_before_start=3)
    package = TripPackage.objects.create(
        trip=trip,
        name="Base",
        price_inr=32000,
        reservation_amount_inr=8000,
        position=1,
    )
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_contact_email="asha@example.com",
        booking_state=Booking.BookingState.DRAFT,
    )
    for position in range(1, slot_count + 1):
        TravelerSlot.objects.create(booking=booking, package=package, position=position)
    return booking


def create_manual_qr_trip() -> tuple[Trip, TripPackage]:
    organizer = Organizer.objects.create(name="Manual QR Collective")
    trip = Trip.objects.create(
        organizer=organizer,
        title="Manual QR Trip",
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 15),
        capacity=8,
        publication_state=Trip.PublicationState.PUBLISHED,
        booking_availability=Trip.BookingAvailability.OPEN,
        manual_payment_availability=Trip.ManualPaymentAvailability.OPEN,
    )
    TripPaymentSchedule.objects.create(trip=trip, balance_due_days_before_start=3)
    package = TripPackage.objects.create(
        trip=trip,
        name="Base",
        price_inr=28000,
        reservation_amount_inr=3500,
        position=1,
    )
    ManualPaymentInstructions.objects.create(
        organizer=organizer,
        payment_qr="manual-payment-qr/payment-qr.png",
        original_filename="payment-qr.png",
        content_type="image/png",
        file_size=128,
        upi_id="trips@example",
        account_name="Manual QR Collective",
    )
    return trip, package


def mark_online_payment_ready(organizer: Organizer) -> None:
    payout_account, _ = PayoutAccount.objects.get_or_create(organizer=organizer)
    payout_account.status = PayoutAccount.Status.ACTIVE
    payout_account.save(update_fields=["status", "updated_at"])

    provider_setup, _ = ProviderPaymentSetup.objects.get_or_create(organizer=organizer)
    provider_setup.status = ProviderPaymentSetup.Status.COMPLETE
    provider_setup.authorization_state = ProviderPaymentSetup.AuthorizationState.AUTHORIZED
    provider_setup.provider_verification_status = (
        ProviderPaymentSetup.ProviderVerificationStatus.VERIFIED
    )
    provider_setup.provider_payment_capability_enabled = True
    provider_setup.provider_connection_state = ProviderPaymentSetup.ProviderConnectionState.HEALTHY
    provider_setup.provider_mode = ProviderPaymentSetup.ProviderMode.LIVE
    provider_setup.provider_merchant_reference = f"acct_trip_payments_{organizer.id}"
    provider_setup.save()

    SensitiveProviderCredentialStore().store_oauth_credentials(
        organizer=organizer,
        access_token=f"oauth_access_token_{organizer.id}",
        refresh_token=f"oauth_refresh_token_{organizer.id}",
        provider_account_reference=provider_setup.provider_merchant_reference,
        public_token=f"rzp_public_{organizer.id}",
        provider_mode=ProviderPaymentSetup.ProviderMode.LIVE,
        scopes=["read_write"],
    )


def razorpay_webhook_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def razorpay_payment_webhook_body(
    payment_attempt: PaymentAttempt,
    *,
    event_reference: str,
    provider_payment_reference: str,
    provider_fee_amount_inr: int | None = None,
) -> bytes:
    organizer = payment_attempt.booking.trip.organizer
    payload = {
        "id": event_reference,
        "entity": "event",
        "event": "payment.captured",
        "account_id": organizer.provider_payment_setup.provider_merchant_reference,
        "payload": {
            "payment": {
                "entity": {
                    "id": provider_payment_reference,
                    "entity": "payment",
                    "amount": payment_attempt.amount_inr * 100,
                    "currency": "INR",
                    "status": "captured",
                    "order_id": payment_attempt.provider_attempt_reference,
                    "notes": {
                        "tripos_organizer_id": str(organizer.id),
                        "tripos_booking_id": str(payment_attempt.booking_id),
                        "tripos_payment_attempt_id": str(payment_attempt.id),
                        "tripos_payment_purpose": payment_attempt.purpose,
                        "tripos_provider_account": (
                            organizer.provider_payment_setup.provider_merchant_reference
                        ),
                    },
                }
            }
        },
    }
    if provider_fee_amount_inr is not None:
        payload["payload"]["payment"]["entity"]["fee"] = provider_fee_amount_inr * 100
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
