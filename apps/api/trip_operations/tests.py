from __future__ import annotations

import csv
from datetime import date, timedelta
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from organizer_payments.models import PayoutAccount, ProviderPaymentSetup
from organizer_payments.provider_credentials import SensitiveProviderCredentialStore
from organizers.models import Organizer
from team_access.models import OrganizerMembership
from trip_bookings.models import Booking
from trip_operations.activity import record_activity_log
from trip_operations.dashboard import build_operations_dashboard_payload
from trip_operations.exports import generate_operational_export_csv
from trip_operations.models import ActivityLog, Notification
from trip_operations.notifications import send_announcement, send_manual_reminder
from trip_operations.serializers import (
    ActivityLogSerializer,
    NotificationSerializer,
    OperationalExportOptionsSerializer,
    OperationsBookingListItemSerializer,
)
from trip_operations.timeline import activity_log_timeline_for_trip, recent_activity_payload
from trip_operations.trip_overview import build_trip_overview_payload
from trip_payments.models import LedgerEntry, ManualPayment, PaymentAttempt, ProviderPayment
from trip_travelers.models import TravelerDocument, TravelerSlot
from trips.models import Trip, TripPackage


@pytest.mark.django_db
def test_trip_operations_records_activity_scope_and_legacy_service_shim():
    from organizers.services import record_activity_log as legacy_record_activity_log

    booking = create_reserved_booking()
    traveler_slot = booking.traveler_slots.get()
    document = TravelerDocument.objects.create(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        label="Passport",
    )
    actor = create_user("activity-operator@example.com")

    activity = legacy_record_activity_log(
        action=ActivityLog.Action.TRAVELER_DOCUMENT_APPROVED,
        traveler_document=document,
        actor=actor,
        metadata={"document_state": TravelerDocument.DocumentState.APPROVED},
    )

    assert legacy_record_activity_log is record_activity_log
    assert activity.organizer == booking.trip.organizer
    assert activity.trip == booking.trip
    assert activity.booking == booking
    assert activity.traveler_slot == traveler_slot
    assert activity.traveler_document == document
    assert activity.actor == actor
    assert activity.metadata == {"document_state": TravelerDocument.DocumentState.APPROVED}

    with pytest.raises(ValidationError, match="requires a Booking or Trip"):
        record_activity_log(action=ActivityLog.Action.TRIP_COMPLETED)


@pytest.mark.django_db
def test_trip_operations_timeline_orders_and_limits_recent_activity_payload():
    booking = create_reserved_booking()
    actor = create_user("timeline-operator@example.com")
    older = record_activity_log(
        action=ActivityLog.Action.TRAVELER_CANCELLED,
        booking=booking,
        metadata={"sequence": "older"},
    )
    newer = record_activity_log(
        action=ActivityLog.Action.BOOKING_CANCELLED,
        booking=booking,
        actor=actor,
        metadata={"sequence": "newer"},
    )
    older_time = timezone.now() - timedelta(hours=2)
    newer_time = timezone.now() - timedelta(hours=1)
    ActivityLog.objects.filter(pk=older.pk).update(occurred_at=older_time)
    ActivityLog.objects.filter(pk=newer.pk).update(occurred_at=newer_time)

    timeline_ids = list(activity_log_timeline_for_trip(booking.trip).values_list("id", flat=True))
    payload = recent_activity_payload(booking.trip, limit=1)

    assert timeline_ids[:2] == [newer.id, older.id]
    assert payload == [
        {
            "id": newer.id,
            "action": ActivityLog.Action.BOOKING_CANCELLED,
            "action_label": "Booking Cancelled",
            "booking_id": booking.id,
            "traveler_slot_id": None,
            "actor_email": "timeline-operator@example.com",
            "occurred_at": newer_time,
            "metadata": {"sequence": "newer"},
        }
    ]


@pytest.mark.django_db
def test_activity_log_serializer_stays_available_from_legacy_api_path():
    from organizers.serializers import ActivityLogSerializer as LegacyActivityLogSerializer

    booking = create_reserved_booking()
    actor = create_user("serializer-operator@example.com")
    activity = record_activity_log(
        action=ActivityLog.Action.TRIP_COMPLETED,
        trip=booking.trip,
        actor=actor,
        metadata={"completion_reason": "Trip finished."},
    )

    payload = LegacyActivityLogSerializer(activity).data

    assert LegacyActivityLogSerializer is ActivityLogSerializer
    assert payload["id"] == activity.id
    assert payload["organizer"] == booking.trip.organizer_id
    assert payload["trip"] == booking.trip_id
    assert payload["booking"] is None
    assert payload["actor"] == actor.id
    assert payload["actor_email"] == "serializer-operator@example.com"
    assert payload["action"] == ActivityLog.Action.TRIP_COMPLETED
    assert payload["action_label"] == "Trip Completed"
    assert payload["metadata"] == {"completion_reason": "Trip finished."}


@pytest.mark.django_db
def test_operations_dashboard_summary_values_are_owned_by_trip_operations():
    booking = create_reserved_booking()
    trip = booking.trip
    organizer = trip.organizer
    owner = create_user("dashboard-owner@example.com")
    create_membership(organizer, owner)
    trip.requires_emergency_contact = True
    trip.save(update_fields=["requires_emergency_contact", "updated_at"])
    ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=5000,
        payment_reference="upi-dashboard-pending",
    )

    payload = build_operations_dashboard_payload(owner, organizer.id)
    summary = payload["trips"]["latest"]
    metrics = summary["operational_metrics"]

    assert summary["id"] == trip.id
    assert summary["capacity"] == 12
    assert summary["available_seats"] == 11
    assert summary["core_operational_booking_count"] == 1
    assert metrics["unpaid_bookings"] == 1
    assert metrics["pending_manual_payments"] == 1
    assert metrics["missing_requirements"] == 1
    assert metrics["reserved_travelers"] == 1
    assert metrics["booking_state_counts"][Booking.BookingState.RESERVED] == 1
    assert payload["trips"]["attention_items"][0]["kind"] == "payment_approvals"


@pytest.mark.django_db
def test_trip_overview_composes_sibling_domain_data_and_recent_activity():
    booking = create_reserved_booking()
    trip = booking.trip
    organizer = trip.organizer
    owner = create_user("overview-owner@example.com")
    create_membership(organizer, owner)
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.APPROVED_MANUAL_PAYMENT,
        amount_inr=10000,
        description="Reservation collected.",
    )
    activity = record_activity_log(
        action=ActivityLog.Action.BOOKING_COMPLETED,
        booking=booking,
        actor=owner,
        metadata={"source": "overview-test"},
    )

    payload = build_trip_overview_payload(owner, organizer.id, trip.id)

    assert payload["trip"]["id"] == trip.id
    assert payload["capacity"] == {
        "total_seats": 12,
        "available_seats": 11,
        "reserved_travelers": 1,
        "core_operational_booking_count": 1,
    }
    assert payload["packages"][0]["name"] == "Base"
    assert payload["booking_progress"]["booking_state_counts"][Booking.BookingState.RESERVED] == 1
    assert payload["booking_progress"]["bookings"][0]["id"] == booking.id
    assert payload["payment_readiness"]["collected_inr"] == 10000
    assert payload["recent_activity"][0]["id"] == activity.id
    assert payload["recent_activity"][0]["metadata"] == {"source": "overview-test"}


@pytest.mark.django_db
def test_operational_export_output_shape_and_activity_log():
    booking = create_reserved_booking()
    trip = booking.trip
    traveler_slot = booking.traveler_slots.get()
    create_booking_for_trip(
        trip,
        state=Booking.BookingState.DRAFT,
        contact_name="Draft Contact",
        contact_phone="+919876543212",
    )
    TravelerDocument.objects.create(
        traveler_slot=traveler_slot,
        document_kind=TravelerDocument.DocumentKind.IDENTITY,
        label="Passport",
        document_state=TravelerDocument.DocumentState.SUBMITTED,
        file="traveler-documents/passport.pdf",
        original_filename="passport.pdf",
    )
    payment_attempt = PaymentAttempt.objects.create(
        booking=booking,
        purpose=PaymentAttempt.Purpose.RESERVATION,
        amount_inr=10000,
        provider_attempt_reference="order_export_001",
    )
    ProviderPayment.objects.create(
        booking=booking,
        payment_attempt=payment_attempt,
        amount_inr=10000,
        provider_payment_reference="pay_export_001",
    )
    ManualPayment.objects.create(
        booking=booking,
        source=ManualPayment.Source.TRAVELER_SUBMITTED,
        status=ManualPayment.Status.SUBMITTED,
        amount_inr=5000,
        payment_reference="upi-export-001",
        payment_proof="manual-payment-proofs/payment-proof.txt",
        original_filename="payment-proof.txt",
    )

    default_export = generate_operational_export_csv(trip)
    default_rows = csv_rows(default_export.csv_content)
    sensitive_export = generate_operational_export_csv(
        trip,
        include_sensitive_traveler_information=True,
        include_sensitive_payment_information=True,
    )
    sensitive_rows = csv_rows(sensitive_export.csv_content)

    assert default_export.row_count == 1
    assert default_export.excluded_draft_booking_count == 1
    assert default_rows[0]["booking_id"] == str(booking.id)
    assert default_rows[0]["traveler_name"] == "Asha Nair"
    assert "sensitive_medical_disclosure" not in default_rows[0]
    assert "sensitive_provider_payment_references" not in default_rows[0]
    assert sensitive_rows[0]["sensitive_traveler_document_files"] == "passport.pdf"
    assert sensitive_rows[0]["sensitive_provider_payment_references"] == "pay_export_001"
    assert sensitive_rows[0]["sensitive_manual_payment_references"] == "upi-export-001"
    assert sensitive_rows[0]["sensitive_payment_proof_files"] == "payment-proof.txt"

    activity = ActivityLog.objects.filter(
        action=ActivityLog.Action.OPERATIONAL_EXPORT_GENERATED
    ).latest("id")
    assert activity.trip == trip
    assert activity.metadata["row_count"] == 1
    assert activity.metadata["excluded_draft_booking_count"] == 1
    assert activity.metadata["include_sensitive_traveler_information"] is True
    assert activity.metadata["include_sensitive_payment_information"] is True


@pytest.mark.django_db
def test_trip_operations_legacy_dashboard_overview_export_imports_are_thin_shims():
    from organizers.operations.dashboard import (
        build_operations_dashboard_payload as nested_dashboard_payload,
    )
    from organizers.operations.trip_overview import (
        build_trip_overview_payload as nested_trip_overview_payload,
    )
    from organizers.operations_dashboard import (
        build_operations_dashboard_payload as root_dashboard_payload,
    )
    from organizers.serializers import (
        OperationalExportOptionsSerializer as LegacyOperationalExportOptionsSerializer,
    )
    from organizers.serializers import (
        OperationsBookingListItemSerializer as LegacyOperationsBookingListItemSerializer,
    )
    from organizers.services import generate_operational_export_csv as legacy_export_csv
    from organizers.trip_overview import build_trip_overview_payload as root_trip_overview_payload

    assert nested_dashboard_payload is build_operations_dashboard_payload
    assert root_dashboard_payload is build_operations_dashboard_payload
    assert nested_trip_overview_payload is build_trip_overview_payload
    assert root_trip_overview_payload is build_trip_overview_payload
    assert legacy_export_csv is generate_operational_export_csv
    assert LegacyOperationalExportOptionsSerializer is OperationalExportOptionsSerializer
    assert LegacyOperationsBookingListItemSerializer is OperationsBookingListItemSerializer


@pytest.mark.django_db
def test_trip_operations_manual_balance_reminder_creates_delivery_payload_and_legacy_shim():
    from organizers.services import send_manual_reminder as legacy_send_manual_reminder

    booking = create_reserved_booking()
    mark_online_payment_ready(booking.trip.organizer)
    booking.booking_contact_email = "asha@example.com"
    booking.save(update_fields=["booking_contact_email", "updated_at"])
    LedgerEntry.objects.create(
        booking=booking,
        entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
        amount_inr=booking.booking_reservation_amount_inr,
        description="Reservation amount collected.",
    )
    actor = create_user("manual-reminder@example.com")

    notifications = legacy_send_manual_reminder(
        booking,
        reminder_kind="payment_balance",
        note="Please settle before departure.",
        actor=actor,
    )

    assert legacy_send_manual_reminder is send_manual_reminder
    assert len(notifications) == 2
    assert {notification.channel for notification in notifications} == {
        Notification.Channel.WHATSAPP,
        Notification.Channel.EMAIL,
    }
    assert all(
        notification.notification_type == Notification.NotificationType.MANUAL_REMINDER
        for notification in notifications
    )
    assert all(
        notification.metadata["balance_payment_link"] is True
        for notification in notifications
    )
    assert all(notification.metadata["due_inr"] == 30000 for notification in notifications)
    assert all("/portal/" in notification.body for notification in notifications)
    assert (
        ActivityLog.objects.filter(
            booking=booking,
            actor=actor,
            action=ActivityLog.Action.NOTIFICATION_SENT,
            metadata__notification_type=Notification.NotificationType.MANUAL_REMINDER,
        ).count()
        == 2
    )


@pytest.mark.django_db
def test_trip_operations_announcement_targets_visible_active_recipients_only():
    booking = create_reserved_booking()
    trip = booking.trip
    booking.booking_contact_email = "reserved@example.com"
    booking.save(update_fields=["booking_contact_email", "updated_at"])
    reserved_slot = booking.traveler_slots.get()
    reserved_slot.traveler_email = ""
    reserved_slot.save(update_fields=["traveler_email", "updated_at"])
    confirmed = create_booking_for_trip(
        trip,
        state=Booking.BookingState.CONFIRMED,
        contact_name="Confirmed Contact",
        contact_phone="+919876543211",
    )
    confirmed_slot = confirmed.traveler_slots.get()
    confirmed_slot.traveler_state = TravelerSlot.TravelerState.CANCELLED
    confirmed_slot.save(update_fields=["traveler_state", "updated_at"])
    draft = create_booking_for_trip(
        trip,
        state=Booking.BookingState.DRAFT,
        contact_name="Draft Contact",
        contact_phone="+919876543212",
    )
    cancelled = create_booking_for_trip(
        trip,
        state=Booking.BookingState.CANCELLED,
        contact_name="Cancelled Contact",
        contact_phone="+919876543213",
    )
    actor = create_user("announcement@example.com")

    notifications = send_announcement(
        trip,
        subject="Pickup point changed",
        body="Boarding now starts at Gate 2.",
        actor=actor,
    )

    assert len(notifications) == 4
    assert {notification.booking_id for notification in notifications} == {
        booking.id,
        confirmed.id,
    }
    assert Notification.objects.filter(booking=draft).count() == 0
    assert Notification.objects.filter(booking=cancelled).count() == 0
    assert Notification.objects.filter(traveler_slot=confirmed_slot).count() == 0
    assert Notification.objects.filter(
        booking=booking,
        recipient_type=Notification.RecipientType.BOOKING_CONTACT,
    ).count() == 2
    assert Notification.objects.filter(
        booking=booking,
        traveler_slot=reserved_slot,
        recipient_type=Notification.RecipientType.TRAVELER,
    ).count() == 1
    assert (
        ActivityLog.objects.filter(
            trip=trip,
            actor=actor,
            action=ActivityLog.Action.NOTIFICATION_SENT,
            metadata__notification_type=Notification.NotificationType.ANNOUNCEMENT,
        ).count()
        == 4
    )


@pytest.mark.django_db
def test_notification_serializer_stays_available_from_legacy_api_path():
    from organizers.serializers import NotificationSerializer as LegacyNotificationSerializer

    booking = create_reserved_booking()
    notification = send_announcement(
        booking.trip,
        subject="Gate update",
        body="Use the north entrance.",
    )[0]

    payload = LegacyNotificationSerializer(notification).data

    assert LegacyNotificationSerializer is NotificationSerializer
    assert payload["id"] == notification.id
    assert payload["notification_type"] == Notification.NotificationType.ANNOUNCEMENT
    assert payload["notification_type_label"] == "Announcement"
    assert payload["recipient_type"] == Notification.RecipientType.BOOKING_CONTACT
    assert payload["metadata"]["announcement_subject"] == "Gate update"


def create_user(email: str):
    return get_user_model().objects.create_user(username=email, email=email, password="password")


def create_membership(organizer: Organizer, user, role=OrganizerMembership.Role.OWNER):
    return OrganizerMembership.objects.create(organizer=organizer, user=user, role=role)


def create_reserved_booking() -> Booking:
    organizer = Organizer.objects.create(name="Trip Operations Collective")
    trip = Trip.objects.create(
        organizer=organizer,
        title="Spiti Operations Run",
        start_date=date(2026, 7, 10),
        end_date=date(2026, 7, 16),
        capacity=12,
    )
    package = TripPackage.objects.create(
        trip=trip,
        name="Base",
        price_inr=40000,
        reservation_amount_inr=10000,
        position=1,
    )
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name="Asha Nair",
        booking_contact_phone="+919876543210",
        booking_state=Booking.BookingState.RESERVED,
    )
    TravelerSlot.objects.create(
        booking=booking,
        package=package,
        position=1,
        traveler_full_name="Asha Nair",
        traveler_phone="+919876543210",
    )
    return booking


def csv_rows(csv_content: str) -> list[dict[str, str]]:
    return list(csv.DictReader(StringIO(csv_content)))


def create_booking_for_trip(
    trip: Trip,
    *,
    state: str,
    contact_name: str,
    contact_phone: str,
) -> Booking:
    booking = Booking.objects.create(
        trip=trip,
        booking_contact_name=contact_name,
        booking_contact_phone=contact_phone,
        booking_state=state,
    )
    TravelerSlot.objects.create(
        booking=booking,
        package=trip.packages.get(),
        position=1,
        traveler_full_name=f"{contact_name} Traveler",
        traveler_phone=contact_phone,
    )
    return booking


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
    provider_setup.provider_merchant_reference = f"acct_trip_operations_{organizer.id}"
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
