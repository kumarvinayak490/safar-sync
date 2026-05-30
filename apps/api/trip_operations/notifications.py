from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from organizer_payments.online_payment_readiness import online_payment_readiness_for_organizer
from organizer_profile.identity import organizer_profile_identity_payload
from trip_bookings import access_links as booking_access_links
from trip_bookings import notification_targets as booking_targets
from trip_bookings.models import Booking, BookingAccessLink
from trip_operations.activity import record_activity_log
from trip_operations.models import ActivityLog, Notification
from trip_payments.models import ManualPayment, ProviderPayment
from trip_payments.notification_state import (
    booking_reconciliation_for_notification,
    current_balance_due_for_notification_inr,
    manual_payment_for_notification,
    provider_payment_for_notification,
    should_send_manual_payment_acknowledgement,
)
from trip_travelers import notification_targets as traveler_targets
from trip_travelers.models import TravelerSlot
from trip_travelers.readiness import (
    BookingConfirmationRequirements,
    confirmation_requirements_for_booking,
)
from trips.models import Trip

AUTOMATIC_REMINDER_BOOKING_STATES = booking_targets.AUTOMATIC_REMINDER_BOOKING_STATES
MANUAL_PAYMENT_REMINDER_BOOKING_STATES = booking_targets.MANUAL_PAYMENT_REMINDER_BOOKING_STATES
MANUAL_REQUIREMENTS_REMINDER_BOOKING_STATES = (
    booking_targets.MANUAL_REQUIREMENTS_REMINDER_BOOKING_STATES
)


@dataclass(frozen=True)
class BalancePaymentLink:
    access_link: BookingAccessLink
    token: str
    amount_inr: int

    @property
    def path(self) -> str:
        return f"/portal/{self.token}/"


@dataclass(frozen=True)
class BalancePaymentLinkDelivery:
    balance_payment_link: BalancePaymentLink
    notifications: list[Notification]


@dataclass(frozen=True)
class NotificationRecipient:
    recipient_type: str
    name: str
    phone: str = ""
    email: str = ""
    traveler_slot: TravelerSlot | None = None


@dataclass(frozen=True)
class AutomaticReminderRun:
    draft_recovery_reminders: int = 0
    balance_due_reminders: int = 0
    overdue_balance_reminders: int = 0
    missing_requirements_reminders: int = 0

    @property
    def total_notifications(self) -> int:
        return (
            self.draft_recovery_reminders
            + self.balance_due_reminders
            + self.overdue_balance_reminders
            + self.missing_requirements_reminders
        )


def issue_balance_payment_link(booking: Booking) -> BalancePaymentLink:
    booking = booking_targets.booking_for_reminder(booking)
    amount_inr = current_balance_due_for_notification_inr(booking)
    _validate_balance_payment_link_available(booking, amount_inr=amount_inr)
    issued_access_link = booking_access_links.issue_access_link(
        booking=booking,
        scope=BookingAccessLink.Scope.BOOKING,
        traveler_slot=None,
        revoke_existing=False,
    )
    return BalancePaymentLink(
        access_link=issued_access_link.access_link,
        token=issued_access_link.token,
        amount_inr=amount_inr,
    )


def send_reservation_acknowledgement(
    booking: Booking,
    *,
    provider_payment: ProviderPayment | None = None,
) -> list[Notification]:
    booking = booking_targets.booking_for_notification(booking)
    existing_notifications = list(
        Notification.objects.filter(
            booking=booking,
            notification_type=Notification.NotificationType.RESERVATION_ACKNOWLEDGEMENT,
        )
    )
    if existing_notifications:
        return existing_notifications

    issued_access_link = booking_access_links.issue_booking_access_link(booking)
    reconciliation = booking_reconciliation_for_notification(booking)
    amount_inr = (
        provider_payment.amount_inr
        if provider_payment is not None
        else reconciliation.collected_inr
    )
    metadata = {
        "booking_state": booking.booking_state,
        "amount_inr": amount_inr,
        "balance_due_inr": reconciliation.due_inr,
        "booking_access_link_id": issued_access_link.access_link.id,
        "booking_access_path": f"/portal/{issued_access_link.token}/",
    }
    if provider_payment is not None:
        metadata.update(
            {
                "provider_payment_id": provider_payment.id,
                "provider_payment_reference": provider_payment.provider_payment_reference,
                "provider": provider_payment.provider,
            }
        )
    return _send_booking_state_notifications(
        booking=booking,
        notification_type=Notification.NotificationType.RESERVATION_ACKNOWLEDGEMENT,
        event_key=f"booking:{booking.id}:reserved",
        provider_payment=provider_payment,
        metadata=metadata,
    )


def send_confirmation_notice(booking: Booking) -> list[Notification]:
    booking = booking_targets.booking_for_notification(booking)
    return _send_booking_state_notifications(
        booking=booking,
        notification_type=Notification.NotificationType.CONFIRMATION_NOTICE,
        event_key=f"booking:{booking.id}:confirmed",
    )


def send_provider_payment_acknowledgement(
    provider_payment: ProviderPayment,
) -> list[Notification]:
    provider_payment = provider_payment_for_notification(provider_payment)
    booking = booking_targets.booking_for_notification(provider_payment.booking)
    return _send_payment_acknowledgement(
        booking=booking,
        amount_inr=provider_payment.amount_inr,
        event_key=f"provider-payment:{provider_payment.id}",
        provider_payment=provider_payment,
        metadata={
            "provider_payment_id": provider_payment.id,
            "provider_payment_reference": provider_payment.provider_payment_reference,
            "provider": provider_payment.provider,
            "amount_inr": provider_payment.amount_inr,
        },
    )


def send_manual_payment_acknowledgement(
    manual_payment: ManualPayment,
    *,
    send: bool | None = None,
) -> list[Notification]:
    manual_payment = manual_payment_for_notification(manual_payment)
    if not should_send_manual_payment_acknowledgement(manual_payment, send=send):
        return []

    booking = booking_targets.booking_for_notification(manual_payment.booking)
    return _send_payment_acknowledgement(
        booking=booking,
        amount_inr=manual_payment.amount_inr,
        event_key=f"manual-payment:{manual_payment.id}",
        manual_payment=manual_payment,
        metadata={
            "manual_payment_id": manual_payment.id,
            "manual_payment_source": manual_payment.source,
            "payment_reference": manual_payment.payment_reference,
            "amount_inr": manual_payment.amount_inr,
        },
    )


def send_refund_acknowledgement(
    *,
    booking: Booking,
    amount_inr: int,
    refund_reference: str,
    refund_reason: str = "",
    send: bool = False,
) -> list[Notification]:
    if not send:
        return []
    if amount_inr <= 0:
        raise ValidationError("Refund Acknowledgement amount must be positive.")
    if not refund_reference.strip():
        raise ValidationError("Refund Acknowledgement needs a refund reference.")

    booking = booking_targets.booking_for_notification(booking)
    return _send_notification_batch(
        booking=booking,
        notification_type=Notification.NotificationType.REFUND_ACKNOWLEDGEMENT,
        recipients=_booking_contact_recipients(booking),
        event_key=f"refund:{refund_reference.strip()}",
        metadata={
            "amount_inr": amount_inr,
            "refund_reference": refund_reference.strip(),
            "refund_reason": refund_reason,
        },
    )


def send_date_change_notice(
    booking: Booking,
    *,
    old_start_date: date,
    old_end_date: date,
    new_start_date: date,
    new_end_date: date,
) -> list[Notification]:
    booking = booking_targets.booking_for_notification(booking)
    return _send_notification_batch(
        booking=booking,
        notification_type=Notification.NotificationType.DATE_CHANGE_NOTICE,
        recipients=_booking_contact_recipients(booking) + _active_traveler_recipients(booking),
        event_key=(
            f"trip:{booking.trip_id}:date-change:"
            f"{old_start_date}:{old_end_date}:{new_start_date}:{new_end_date}"
        ),
        metadata={
            "old_start_date": old_start_date.isoformat(),
            "old_end_date": old_end_date.isoformat(),
            "new_start_date": new_start_date.isoformat(),
            "new_end_date": new_end_date.isoformat(),
        },
    )


def send_cancellation_notice(
    booking: Booking,
    *,
    cancellation_reason: str,
) -> list[Notification]:
    booking = booking_targets.booking_for_notification(booking)
    return _send_notification_batch(
        booking=booking,
        notification_type=Notification.NotificationType.CANCELLATION_NOTICE,
        recipients=_booking_contact_recipients(booking) + _active_traveler_recipients(booking),
        event_key=f"trip:{booking.trip_id}:cancellation:{booking.id}",
        metadata={
            "booking_state": booking.booking_state,
            "cancellation_reason": cancellation_reason,
        },
    )


def process_automatic_reminders(*, now=None) -> AutomaticReminderRun:
    current_time = now or timezone.now()
    return AutomaticReminderRun(
        draft_recovery_reminders=len(send_due_draft_recovery_reminders(now=current_time)),
        balance_due_reminders=len(send_due_balance_due_reminders(now=current_time)),
        overdue_balance_reminders=len(send_due_overdue_balance_reminders(now=current_time)),
        missing_requirements_reminders=len(
            send_due_missing_requirements_reminders(now=current_time)
        ),
    )


def send_manual_reminder(
    booking: Booking,
    *,
    reminder_kind: str,
    note: str = "",
    actor=None,
) -> list[Notification]:
    booking = booking_targets.booking_for_reminder(booking)
    reminder_kind = reminder_kind.strip()
    event_key = f"booking:{booking.id}:manual-reminder:{timezone.now().isoformat()}"

    if reminder_kind == "payment_balance":
        recipients, metadata = _manual_payment_reminder_payload(booking, note=note)
    elif reminder_kind == "missing_requirements":
        recipients, metadata = _manual_requirements_reminder_payload(booking, note=note)
    else:
        raise ValidationError("Manual Reminder kind is not supported.")

    return _send_notification_batch(
        booking=booking,
        notification_type=Notification.NotificationType.MANUAL_REMINDER,
        recipients=recipients,
        event_key=event_key,
        metadata=metadata,
        actor=actor,
    )


def send_balance_payment_link(
    booking: Booking,
    *,
    note: str = "",
    actor=None,
) -> BalancePaymentLinkDelivery:
    booking = booking_targets.booking_for_reminder(booking)
    balance_payment_link = issue_balance_payment_link(booking)
    recipients = _booking_contact_recipients(booking)
    metadata = _balance_payment_link_metadata(
        balance_payment_link,
        note=note,
        manual_send=True,
    )
    notifications = _send_notification_batch(
        booking=booking,
        notification_type=Notification.NotificationType.MANUAL_REMINDER,
        recipients=recipients,
        event_key=f"booking:{booking.id}:balance-payment-link:{timezone.now().isoformat()}",
        metadata=metadata,
        actor=actor,
    )
    return BalancePaymentLinkDelivery(
        balance_payment_link=balance_payment_link,
        notifications=notifications,
    )


def send_announcement(
    trip: Trip,
    *,
    subject: str,
    body: str,
    actor=None,
) -> list[Notification]:
    subject = subject.strip()
    body = body.strip()
    if not subject:
        raise ValidationError("Announcement Subject is required.")
    if not body:
        raise ValidationError("Announcement Body is required.")

    sent: list[Notification] = []
    event_key = f"trip:{trip.id}:announcement:{timezone.now().isoformat()}"
    for booking in booking_targets.announcement_bookings_for_trip(trip):
        sent.extend(
            _send_notification_batch(
                booking=booking,
                notification_type=Notification.NotificationType.ANNOUNCEMENT,
                recipients=_booking_contact_recipients(booking)
                + _active_traveler_recipients(booking),
                event_key=f"{event_key}:booking:{booking.id}",
                metadata={
                    "announcement": True,
                    "announcement_subject": subject,
                    "announcement_body": body,
                },
                actor=actor,
            )
        )
    return sent


def send_due_draft_recovery_reminders(*, now=None) -> list[Notification]:
    current_time = now or timezone.now()
    sent: list[Notification] = []
    for booking in booking_targets.draft_recovery_reminder_candidates(now=current_time):
        recipients = _booking_contact_recipients(booking)
        if not _recipients_have_channels(recipients):
            continue
        sent.extend(
            _send_notification_batch(
                booking=booking,
                notification_type=Notification.NotificationType.DRAFT_RECOVERY_REMINDER,
                recipients=recipients,
                event_key=f"booking:{booking.id}:draft-recovery",
                skip_existing=True,
                metadata={
                    "automatic_reminder": True,
                    "draft_created_at": booking.created_at.isoformat(),
                    "draft_expires_at": booking.draft_expires_at.isoformat(),
                },
            )
        )
    return sent


def send_due_balance_due_reminders(*, now=None) -> list[Notification]:
    current_time = now or timezone.now()
    current_date = timezone.localdate(current_time)
    bookings = (
        booking_targets.automatic_reminder_booking_queryset()
        .filter(trip__payment_schedule__balance_due_days_before_start__isnull=False)
        .order_by("id")
    )
    sent: list[Notification] = []
    for booking in bookings:
        schedule = booking.trip.payment_schedule
        balance_due_date = schedule.balance_due_date
        if balance_due_date is None:
            continue
        reminder_date = balance_due_date - timedelta(days=schedule.balance_reminder_lead_days)
        if not (reminder_date <= current_date <= balance_due_date):
            continue
        reconciliation = booking_reconciliation_for_notification(booking)
        if reconciliation.due_inr <= 0:
            continue
        if Notification.objects.filter(
            booking=booking,
            notification_type=Notification.NotificationType.BALANCE_DUE_REMINDER,
            metadata__balance_due_date=balance_due_date.isoformat(),
        ).exists():
            continue
        recipients = _booking_contact_recipients(booking)
        if not _recipients_have_channels(recipients):
            continue
        balance_payment_link = issue_balance_payment_link(booking)
        sent.extend(
            _send_notification_batch(
                booking=booking,
                notification_type=Notification.NotificationType.BALANCE_DUE_REMINDER,
                recipients=recipients,
                event_key=f"booking:{booking.id}:balance-due:{balance_due_date.isoformat()}",
                skip_existing=True,
                metadata={
                    "automatic_reminder": True,
                    "balance_due_date": balance_due_date.isoformat(),
                    "balance_reminder_lead_days": schedule.balance_reminder_lead_days,
                    "amount_inr": reconciliation.due_inr,
                    "due_inr": reconciliation.due_inr,
                    **_balance_payment_link_metadata(balance_payment_link),
                },
            )
        )
    return sent


def send_due_overdue_balance_reminders(*, now=None) -> list[Notification]:
    current_time = now or timezone.now()
    current_date = timezone.localdate(current_time)
    bookings = (
        booking_targets.automatic_reminder_booking_queryset()
        .filter(trip__payment_schedule__balance_due_days_before_start__isnull=False)
        .order_by("id")
    )
    sent: list[Notification] = []
    for booking in bookings:
        balance_due_date = booking.trip.payment_schedule.balance_due_date
        if balance_due_date is None or current_date < balance_due_date + timedelta(days=1):
            continue
        reconciliation = booking_reconciliation_for_notification(booking)
        if reconciliation.due_inr <= 0:
            continue
        if Notification.objects.filter(
            booking=booking,
            notification_type=Notification.NotificationType.OVERDUE_BALANCE_REMINDER,
            metadata__balance_due_date=balance_due_date.isoformat(),
        ).exists():
            continue
        recipients = _booking_contact_recipients(booking)
        if not _recipients_have_channels(recipients):
            continue
        balance_payment_link = issue_balance_payment_link(booking)
        sent.extend(
            _send_notification_batch(
                booking=booking,
                notification_type=Notification.NotificationType.OVERDUE_BALANCE_REMINDER,
                recipients=recipients,
                event_key=f"booking:{booking.id}:overdue-balance:{balance_due_date.isoformat()}",
                skip_existing=True,
                metadata={
                    "automatic_reminder": True,
                    "balance_due_date": balance_due_date.isoformat(),
                    "amount_inr": reconciliation.due_inr,
                    "due_inr": reconciliation.due_inr,
                    **_balance_payment_link_metadata(balance_payment_link),
                },
            )
        )
    return sent


def send_due_missing_requirements_reminders(*, now=None) -> list[Notification]:
    current_time = now or timezone.now()
    current_date = timezone.localdate(current_time)
    bookings = booking_targets.automatic_reminder_booking_queryset().order_by("id")
    sent: list[Notification] = []
    for booking in bookings:
        scheduled_date = booking.trip.start_date - timedelta(days=3)
        if current_date >= booking.trip.start_date:
            continue
        reminder_timing = _missing_requirements_reminder_timing(
            booking=booking,
            current_date=current_date,
            scheduled_date=scheduled_date,
        )
        if reminder_timing is None:
            continue

        requirements = confirmation_requirements_for_booking(booking)
        if requirements.ready:
            continue
        recipients = _missing_requirements_recipients(booking, requirements)
        if not _recipients_have_channels(recipients):
            continue
        sent.extend(
            _send_notification_batch(
                booking=booking,
                notification_type=Notification.NotificationType.MISSING_REQUIREMENTS_REMINDER,
                recipients=recipients,
                event_key=(
                    f"booking:{booking.id}:missing-requirements:"
                    f"{reminder_timing}:{scheduled_date.isoformat()}"
                ),
                skip_existing=True,
                metadata={
                    "automatic_reminder": True,
                    "reminder_timing": reminder_timing,
                    "scheduled_date": scheduled_date.isoformat(),
                    "trip_start_date": booking.trip.start_date.isoformat(),
                    "unmet_requirements": [
                        {
                            "code": requirement.code,
                            "label": requirement.label,
                            "scope": requirement.scope,
                            "traveler_slot_id": requirement.traveler_slot_id,
                            "traveler_slot_position": requirement.traveler_slot_position,
                        }
                        for requirement in requirements.unmet_requirements
                    ],
                },
            )
        )
    return sent


def _send_booking_state_notifications(
    *,
    booking: Booking,
    notification_type: str,
    event_key: str,
    metadata: dict | None = None,
    provider_payment: ProviderPayment | None = None,
) -> list[Notification]:
    recipients = _booking_contact_recipients(booking)
    recipients.extend(_active_traveler_recipients(booking))
    notification_metadata = {"booking_state": booking.booking_state}
    notification_metadata.update(metadata or {})
    return _send_notification_batch(
        booking=booking,
        notification_type=notification_type,
        recipients=recipients,
        event_key=event_key,
        provider_payment=provider_payment,
        metadata=notification_metadata,
    )


def _send_payment_acknowledgement(
    *,
    booking: Booking,
    amount_inr: int,
    event_key: str,
    metadata: dict,
    provider_payment: ProviderPayment | None = None,
    manual_payment: ManualPayment | None = None,
) -> list[Notification]:
    return _send_notification_batch(
        booking=booking,
        notification_type=Notification.NotificationType.PAYMENT_ACKNOWLEDGEMENT,
        recipients=_booking_contact_recipients(booking),
        event_key=event_key,
        provider_payment=provider_payment,
        manual_payment=manual_payment,
        metadata={"amount_inr": amount_inr, **metadata},
    )


def _send_notification_batch(
    *,
    booking: Booking,
    notification_type: str,
    recipients: list[NotificationRecipient],
    event_key: str,
    metadata: dict,
    provider_payment: ProviderPayment | None = None,
    manual_payment: ManualPayment | None = None,
    skip_existing: bool = False,
    actor=None,
) -> list[Notification]:
    notifications: list[Notification] = []
    for recipient in recipients:
        for channel in _channels_for_recipient(recipient):
            if skip_existing and _notification_exists(
                event_key=event_key,
                notification_type=notification_type,
                recipient=recipient,
                channel=channel,
            ):
                continue
            notification = _get_or_create_sent_notification(
                booking=booking,
                notification_type=notification_type,
                recipient=recipient,
                channel=channel,
                event_key=event_key,
                provider_payment=provider_payment,
                manual_payment=manual_payment,
                metadata=metadata,
                actor=actor,
            )
            notifications.append(notification)
    return notifications


def _notification_exists(
    *,
    event_key: str,
    notification_type: str,
    recipient: NotificationRecipient,
    channel: str,
) -> bool:
    return Notification.objects.filter(
        idempotency_key=_notification_idempotency_key(
            event_key=event_key,
            notification_type=notification_type,
            recipient=recipient,
            channel=channel,
        )
    ).exists()


def _get_or_create_sent_notification(
    *,
    booking: Booking,
    notification_type: str,
    recipient: NotificationRecipient,
    channel: str,
    event_key: str,
    metadata: dict,
    provider_payment: ProviderPayment | None = None,
    manual_payment: ManualPayment | None = None,
    actor=None,
) -> Notification:
    idempotency_key = _notification_idempotency_key(
        event_key=event_key,
        notification_type=notification_type,
        recipient=recipient,
        channel=channel,
    )
    subject, body = _notification_content(
        booking=booking,
        notification_type=notification_type,
        metadata=metadata,
    )
    notification, created = Notification.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "organizer": booking.trip.organizer,
            "trip": booking.trip,
            "booking": booking,
            "traveler_slot": recipient.traveler_slot,
            "provider_payment": provider_payment,
            "manual_payment": manual_payment,
            "notification_type": notification_type,
            "channel": channel,
            "recipient_type": recipient.recipient_type,
            "recipient_name": recipient.name,
            "recipient_phone": recipient.phone,
            "recipient_email": recipient.email,
            "organizer_identity_name": booking.trip.organizer.display_identity_name,
            "organizer_identity_logo_url": organizer_profile_identity_payload(
                booking.trip.organizer
            )["logo_url"],
            "subject": subject,
            "body": body,
            "metadata": metadata,
            "status": Notification.Status.SENT,
        },
    )
    if created:
        record_activity_log(
            action=ActivityLog.Action.NOTIFICATION_SENT,
            booking=booking,
            traveler_slot=recipient.traveler_slot,
            actor=actor,
            metadata={
                "notification_id": notification.id,
                "notification_type": notification.notification_type,
                "channel": notification.channel,
                "recipient_type": notification.recipient_type,
                "idempotency_key": notification.idempotency_key,
            },
        )
    return notification


def _manual_payment_reminder_payload(
    booking: Booking,
    *,
    note: str,
) -> tuple[list[NotificationRecipient], dict]:
    if booking_targets.is_cancelled_booking(booking):
        raise ValidationError("Cancelled Bookings do not receive payment Reminders.")
    if not booking_targets.can_receive_manual_payment_reminder(booking):
        raise ValidationError(
            "Payment Manual Reminders require a Reserved, Confirmed, or Completed Booking."
        )

    reconciliation = booking_reconciliation_for_notification(booking)
    if reconciliation.due_inr <= 0:
        raise ValidationError("Payment Manual Reminder requires due balance.")

    return _booking_contact_recipients(booking), {
        "manual_reminder": True,
        "reminder_kind": "payment_balance",
        "obligation": "balance_due",
        "amount_inr": reconciliation.due_inr,
        "due_inr": reconciliation.due_inr,
        "note": note.strip(),
        **_balance_payment_link_metadata(issue_balance_payment_link(booking)),
    }


def _balance_payment_link_metadata(
    balance_payment_link: BalancePaymentLink,
    *,
    note: str = "",
    manual_send: bool = False,
) -> dict:
    return {
        "balance_payment_link": True,
        "balance_payment_link_manual_send": manual_send,
        "balance_payment_link_id": balance_payment_link.access_link.id,
        "balance_payment_link_path": balance_payment_link.path,
        "balance_payment_amount_inr": balance_payment_link.amount_inr,
        "balance_payment_link_expires_at": balance_payment_link.access_link.expires_at.isoformat(),
        "amount_inr": balance_payment_link.amount_inr,
        "due_inr": balance_payment_link.amount_inr,
        "note": note.strip(),
    }


def _manual_requirements_reminder_payload(
    booking: Booking,
    *,
    note: str,
) -> tuple[list[NotificationRecipient], dict]:
    if booking_targets.is_cancelled_booking(booking):
        raise ValidationError("Cancelled Bookings do not receive document Reminders.")
    if not booking_targets.can_receive_manual_requirements_reminder(booking):
        raise ValidationError(
            "Missing Requirements Manual Reminders require a Reserved or Confirmed Booking."
        )

    requirements = confirmation_requirements_for_booking(booking)
    if requirements.ready:
        raise ValidationError(
            "Missing Requirements Manual Reminder requires unmet Confirmation Requirements."
        )

    return _missing_requirements_recipients(booking, requirements), {
        "manual_reminder": True,
        "reminder_kind": "missing_requirements",
        "obligation": "confirmation_requirements",
        "note": note.strip(),
        "unmet_requirements": [
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


def _notification_idempotency_key(
    *,
    event_key: str,
    notification_type: str,
    recipient: NotificationRecipient,
    channel: str,
) -> str:
    traveler_key = recipient.traveler_slot.id if recipient.traveler_slot else "contact"
    raw_key = f"{event_key}:{notification_type}:{recipient.recipient_type}:{traveler_key}:{channel}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _booking_contact_recipients(booking: Booking) -> list[NotificationRecipient]:
    target = booking_targets.booking_contact_notification_target(booking)
    return [
        NotificationRecipient(
            recipient_type=Notification.RecipientType.BOOKING_CONTACT,
            name=target.name,
            phone=target.phone,
            email=target.email,
        )
    ]


def _missing_requirements_reminder_timing(
    *,
    booking: Booking,
    current_date: date,
    scheduled_date: date,
) -> str | None:
    reservation_date = booking_targets.booking_updated_local_date(booking)
    late_addition_dates = traveler_targets.addition_reserved_local_dates(booking)
    if current_date >= scheduled_date:
        if reservation_date >= scheduled_date or any(
            addition_date >= scheduled_date for addition_date in late_addition_dates
        ):
            return "late"
        return "scheduled"
    return None


def _missing_requirements_recipients(
    booking: Booking,
    requirements: BookingConfirmationRequirements,
) -> list[NotificationRecipient]:
    recipients = _booking_contact_recipients(booking)
    recipients.extend(
        NotificationRecipient(
            recipient_type=Notification.RecipientType.TRAVELER,
            name=target.name,
            phone=target.phone,
            email=target.email,
            traveler_slot=target.traveler_slot,
        )
        for target in traveler_targets.missing_requirements_traveler_notification_targets(
            booking,
            requirements,
        )
    )
    return recipients


def _active_traveler_recipients(booking: Booking) -> list[NotificationRecipient]:
    if not booking_targets.can_receive_active_traveler_notifications(booking):
        return []

    return [
        NotificationRecipient(
            recipient_type=Notification.RecipientType.TRAVELER,
            name=target.name,
            phone=target.phone,
            email=target.email,
            traveler_slot=target.traveler_slot,
        )
        for target in traveler_targets.active_traveler_notification_targets(booking)
    ]


def _channels_for_recipient(recipient: NotificationRecipient) -> list[str]:
    channels = []
    if recipient.phone.strip():
        channels.append(Notification.Channel.WHATSAPP)
    if recipient.email.strip():
        channels.append(Notification.Channel.EMAIL)
    return channels


def _recipients_have_channels(recipients: list[NotificationRecipient]) -> bool:
    return any(_channels_for_recipient(recipient) for recipient in recipients)


def _notification_content(
    *,
    booking: Booking,
    notification_type: str,
    metadata: dict,
) -> tuple[str, str]:
    identity_name = booking.trip.organizer.display_identity_name
    trip_title = booking.trip.title
    amount = metadata.get("amount_inr")
    formatted_amount = _format_inr(amount) if amount else ""

    if notification_type == Notification.NotificationType.DRAFT_RECOVERY_REMINDER:
        subject = f"{identity_name}: Complete your Booking for {trip_title}"
        body = (
            f"{identity_name} is holding your Draft Booking #{booking.id} for "
            f"{trip_title}. Complete it before the draft expires."
        )
    elif notification_type == Notification.NotificationType.BALANCE_DUE_REMINDER:
        subject = f"{identity_name}: Balance Due Reminder for {trip_title}"
        body = (
            f"{identity_name} reminds you that {formatted_amount} remains due for "
            f"Booking #{booking.id} on {trip_title}. The balance milestone is "
            f"{metadata.get('balance_due_date')}."
        )
        if metadata.get("balance_payment_link_path"):
            body = f"{body} Balance Payment Link: {metadata['balance_payment_link_path']}"
    elif notification_type == Notification.NotificationType.OVERDUE_BALANCE_REMINDER:
        subject = f"{identity_name}: Overdue Balance Reminder for {trip_title}"
        body = (
            f"{identity_name} reminds you that {formatted_amount} is overdue for "
            f"Booking #{booking.id} on {trip_title}. The balance milestone was "
            f"{metadata.get('balance_due_date')}."
        )
        if metadata.get("balance_payment_link_path"):
            body = f"{body} Balance Payment Link: {metadata['balance_payment_link_path']}"
    elif notification_type == Notification.NotificationType.MISSING_REQUIREMENTS_REMINDER:
        subject = f"{identity_name}: Missing Requirements Reminder for {trip_title}"
        body = (
            f"{identity_name} reminds you that Booking #{booking.id} for {trip_title} "
            "still has unmet Confirmation Requirements before the trip starts."
        )
    elif notification_type == Notification.NotificationType.MANUAL_REMINDER:
        subject = f"{identity_name}: Manual Reminder for {trip_title}"
        if metadata.get("reminder_kind") == "payment_balance":
            body = (
                f"{identity_name} reminds you that {formatted_amount} remains due for "
                f"Booking #{booking.id} on {trip_title}."
            )
            if metadata.get("balance_payment_link_path"):
                body = f"{body} Balance Payment Link: {metadata['balance_payment_link_path']}"
        else:
            body = (
                f"{identity_name} reminds you that Booking #{booking.id} for "
                f"{trip_title} still has unmet Confirmation Requirements."
            )
        if metadata.get("note"):
            body = f"{body} Note from the organizer: {metadata['note']}"
    elif notification_type == Notification.NotificationType.ANNOUNCEMENT:
        subject = f"{identity_name}: {metadata.get('announcement_subject')}"
        body = f"{identity_name} announcement for {trip_title}: {metadata.get('announcement_body')}"
    elif notification_type == Notification.NotificationType.RESERVATION_ACKNOWLEDGEMENT:
        subject = f"{identity_name}: Reservation Acknowledgement for {trip_title}"
        balance_due = metadata.get("balance_due_inr")
        access_path = metadata.get("booking_access_path")
        body = (
            f"{identity_name} has reserved your Booking for {trip_title}. "
            f"Your seats are held under Booking #{booking.id}."
        )
        if formatted_amount:
            body = f"{body} Payment received: {formatted_amount}."
        if balance_due is not None:
            balance_text = (
                f"Balance due: {_format_inr(balance_due)}."
                if balance_due > 0
                else "No balance is currently due."
            )
            body = f"{body} {balance_text}"
        if access_path:
            body = f"{body} Booking-Level Access Link: {access_path}"
    elif notification_type == Notification.NotificationType.CONFIRMATION_NOTICE:
        subject = f"{identity_name}: Confirmation Notice for {trip_title}"
        body = (
            f"{identity_name} has confirmed your Booking for {trip_title}. "
            "Your readiness has been accepted by the organizer team."
        )
    elif notification_type == Notification.NotificationType.PAYMENT_ACKNOWLEDGEMENT:
        subject = f"{identity_name}: Payment Acknowledgement for {trip_title}"
        body = (
            f"{identity_name} has acknowledged payment of {formatted_amount} "
            f"for Booking #{booking.id} on {trip_title}."
        )
    elif notification_type == Notification.NotificationType.REFUND_ACKNOWLEDGEMENT:
        subject = f"{identity_name}: Refund Acknowledgement for {trip_title}"
        body = (
            f"{identity_name} has acknowledged a refund of {formatted_amount} "
            f"for Booking #{booking.id} on {trip_title}."
        )
    elif notification_type == Notification.NotificationType.DATE_CHANGE_NOTICE:
        subject = f"{identity_name}: Date Change Notice for {trip_title}"
        body = (
            f"{identity_name} has changed the trip dates for {trip_title} "
            f"from {metadata.get('old_start_date')} to {metadata.get('new_start_date')}. "
            f"Booking #{booking.id} remains an operational record."
        )
    else:
        subject = f"{identity_name}: Cancellation Notice for {trip_title}"
        body = (
            f"{identity_name} has cancelled {trip_title} for Booking #{booking.id}. "
            "Refunds or balance corrections will be handled separately by the organizer."
        )

    return subject[:180], body


def _validate_balance_payment_link_available(
    booking: Booking,
    *,
    amount_inr: int,
) -> None:
    if booking.booking_state == Booking.BookingState.DRAFT:
        raise ValidationError("Balance Payment Links are available after reservation.")
    if booking_targets.is_cancelled_booking(booking):
        raise ValidationError("Cancelled Bookings cannot start Balance Payment Attempts.")
    if amount_inr <= 0:
        raise ValidationError("No balance is currently due.")

    readiness = online_payment_readiness_for_organizer(booking.trip.organizer)
    if not readiness.ready:
        raise ValidationError(f"Online Payment Readiness is blocked: {readiness.message}")


def _format_inr(amount_inr: int) -> str:
    return f"INR {amount_inr:,}"
