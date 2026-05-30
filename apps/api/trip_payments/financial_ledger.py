from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.db import models, transaction
from django.utils import timezone

from trip_bookings.models import Booking, BookingImportRow
from trip_payments.models import (
    BookingAdjustment,
    LedgerEntry,
    ManualPayment,
    OpeningPaymentRecord,
    PaymentAttempt,
    ProviderPayment,
    RefundRecord,
)

PLATFORM_FEE_BASIS_POINTS = 200

FinancialLedgerEvent = (
    ProviderPayment | ManualPayment | OpeningPaymentRecord | BookingAdjustment | RefundRecord
)


class PaymentState:
    REFUND_DUE = "refund_due"
    REFUNDED = "refunded"
    OVERDUE = "overdue"
    UNPAID = "unpaid"
    FULLY_PAID = "fully_paid"
    RESERVATION_PAID = "reservation_paid"
    PARTIALLY_PAID = "partially_paid"


COLLECTED_LEDGER_ENTRY_TYPES = (
    LedgerEntry.EntryType.PROVIDER_PAYMENT,
    LedgerEntry.EntryType.APPROVED_MANUAL_PAYMENT,
    LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
)


@dataclass(frozen=True)
class BookingReconciliation:
    booking: Booking
    booking_total_inr: int
    effective_booking_total_inr: int
    collected_inr: int
    due_inr: int
    adjusted_inr: int
    refunded_inr: int
    refund_due_inr: int
    overdue_inr: int
    platform_fee_inr: int


@dataclass(frozen=True)
class _LedgerEntryWrite:
    booking: Booking
    entry_type: str
    amount_inr: int
    description: str
    occurred_at: datetime | None = None
    provider_payment: ProviderPayment | None = None
    manual_payment: ManualPayment | None = None
    opening_payment_record: OpeningPaymentRecord | None = None
    booking_adjustment: BookingAdjustment | None = None
    refund_record: RefundRecord | None = None

    def identity_kwargs(self) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "booking": self.booking,
            "entry_type": self.entry_type,
        }
        for field_name in (
            "provider_payment",
            "manual_payment",
            "opening_payment_record",
            "booking_adjustment",
            "refund_record",
        ):
            value = getattr(self, field_name)
            if value is not None:
                kwargs[field_name] = value
        return kwargs

    def defaults(self) -> dict[str, object]:
        defaults: dict[str, object] = {
            "amount_inr": self.amount_inr,
            "description": self.description,
        }
        if self.occurred_at is not None:
            defaults["occurred_at"] = self.occurred_at
        return defaults

    def create_kwargs(self) -> dict[str, object]:
        return {**self.identity_kwargs(), **self.defaults()}


class FinancialLedger:
    def __init__(self, booking: Booking):
        self.booking = booking

    @classmethod
    def for_booking(cls, booking: Booking) -> FinancialLedger:
        return cls(booking)

    @staticmethod
    def platform_fee_for_provider_payment_inr(provider_payment: ProviderPayment) -> int:
        return provider_payment.amount_inr * PLATFORM_FEE_BASIS_POINTS // 10_000

    @staticmethod
    def record_event(event: FinancialLedgerEvent) -> tuple[LedgerEntry, ...]:
        if isinstance(event, ProviderPayment):
            return FinancialLedger._record_provider_payment_event(event)
        if isinstance(event, ManualPayment):
            return FinancialLedger._record_manual_payment_event(event)
        if isinstance(event, OpeningPaymentRecord):
            return FinancialLedger._record_opening_payment_record_event(event)
        if isinstance(event, BookingAdjustment):
            return FinancialLedger._record_booking_adjustment_event(event)
        if isinstance(event, RefundRecord):
            return FinancialLedger._record_refund_record_event(event)
        raise TypeError(f"Unsupported Financial Ledger event: {type(event).__name__}")

    @staticmethod
    def _record_provider_payment_event(
        provider_payment: ProviderPayment,
    ) -> tuple[LedgerEntry, ...]:
        writes = [
            _LedgerEntryWrite(
                booking=provider_payment.booking,
                provider_payment=provider_payment,
                entry_type=LedgerEntry.EntryType.PROVIDER_PAYMENT,
                amount_inr=provider_payment.amount_inr,
                description="Collected Provider Payment.",
                occurred_at=provider_payment.confirmed_at,
            )
        ]

        platform_fee = FinancialLedger.platform_fee_for_provider_payment_inr(provider_payment)
        if platform_fee > 0:
            writes.append(
                _LedgerEntryWrite(
                    booking=provider_payment.booking,
                    provider_payment=provider_payment,
                    entry_type=LedgerEntry.EntryType.PLATFORM_FEE,
                    amount_inr=platform_fee,
                    description="Organizer-absorbed Platform Fee.",
                    occurred_at=provider_payment.confirmed_at,
                )
            )

        return _record_idempotent_ledger_entries(writes)

    @staticmethod
    def _record_manual_payment_event(manual_payment: ManualPayment) -> tuple[LedgerEntry, ...]:
        if manual_payment.status != ManualPayment.Status.APPROVED:
            return ()

        return _record_idempotent_ledger_entries(
            [
                _LedgerEntryWrite(
                    booking=manual_payment.booking,
                    manual_payment=manual_payment,
                    entry_type=LedgerEntry.EntryType.APPROVED_MANUAL_PAYMENT,
                    amount_inr=manual_payment.amount_inr,
                    description="Approved Manual Payment.",
                    occurred_at=manual_payment.approved_at or manual_payment.submitted_at,
                )
            ]
        )

    @staticmethod
    def _record_opening_payment_record_event(
        opening_payment_record: OpeningPaymentRecord,
    ) -> tuple[LedgerEntry, ...]:
        return _record_idempotent_ledger_entries(
            [
                _LedgerEntryWrite(
                    booking=opening_payment_record.booking,
                    opening_payment_record=opening_payment_record,
                    entry_type=LedgerEntry.EntryType.OPENING_PAYMENT_RECORD,
                    amount_inr=opening_payment_record.amount_inr,
                    description=(
                        opening_payment_record.note.strip()
                        or "Imported historical amount as an Opening Payment Record."
                    ),
                    occurred_at=opening_payment_record.occurred_at,
                )
            ]
        )

    @staticmethod
    def _record_booking_adjustment_event(
        booking_adjustment: BookingAdjustment,
    ) -> tuple[LedgerEntry, ...]:
        return _record_idempotent_ledger_entries(
            [
                _LedgerEntryWrite(
                    booking=booking_adjustment.booking,
                    booking_adjustment=booking_adjustment,
                    entry_type=LedgerEntry.EntryType.BOOKING_ADJUSTMENT,
                    amount_inr=booking_adjustment.amount_inr,
                    description=booking_adjustment.adjustment_reason,
                    occurred_at=booking_adjustment.occurred_at,
                )
            ]
        )

    @staticmethod
    def _record_refund_record_event(refund_record: RefundRecord) -> tuple[LedgerEntry, ...]:
        return _record_idempotent_ledger_entries(
            [
                _LedgerEntryWrite(
                    booking=refund_record.booking,
                    refund_record=refund_record,
                    entry_type=LedgerEntry.EntryType.REFUND_RECORD,
                    amount_inr=refund_record.amount_inr,
                    description=refund_record.refund_reason,
                    occurred_at=refund_record.occurred_at,
                )
            ]
        )

    @staticmethod
    def record_provider_payment(provider_payment: ProviderPayment) -> tuple[LedgerEntry, ...]:
        return FinancialLedger.record_event(provider_payment)

    @staticmethod
    def record_approved_manual_payment(manual_payment: ManualPayment) -> tuple[LedgerEntry, ...]:
        return FinancialLedger.record_event(manual_payment)

    @staticmethod
    def record_opening_payment_record(
        opening_payment_record: OpeningPaymentRecord,
    ) -> tuple[LedgerEntry, ...]:
        return FinancialLedger.record_event(opening_payment_record)

    @staticmethod
    def record_booking_adjustment(
        booking_adjustment: BookingAdjustment,
    ) -> tuple[LedgerEntry, ...]:
        return FinancialLedger.record_event(booking_adjustment)

    @staticmethod
    def record_refund_record(refund_record: RefundRecord) -> tuple[LedgerEntry, ...]:
        return FinancialLedger.record_event(refund_record)

    @staticmethod
    def record_package_change(
        *,
        booking: Booking,
        amount_inr: int,
        description: str,
    ) -> LedgerEntry | None:
        if amount_inr == 0:
            return None
        return _create_ledger_entry(
            _LedgerEntryWrite(
                booking=booking,
                entry_type=LedgerEntry.EntryType.PACKAGE_CHANGE,
                amount_inr=amount_inr,
                description=description,
            )
        )

    def collected_amount_inr(self) -> int:
        return self._sum_entries(COLLECTED_LEDGER_ENTRY_TYPES)

    def adjusted_amount_inr(self) -> int:
        return self._sum_entries((LedgerEntry.EntryType.BOOKING_ADJUSTMENT,))

    def refunded_amount_inr(self) -> int:
        return self._sum_entries((LedgerEntry.EntryType.REFUND_RECORD,))

    def platform_fee_amount_inr(self) -> int:
        return self._sum_entries((LedgerEntry.EntryType.PLATFORM_FEE,))

    def effective_booking_total_inr(self) -> int:
        return max(self.booking.booking_total_inr + self.adjusted_amount_inr(), 0)

    def reconciliation(self) -> BookingReconciliation:
        collected = self.collected_amount_inr()
        adjusted = self.adjusted_amount_inr()
        refunded = self.refunded_amount_inr()
        effective_total = max(self.booking.booking_total_inr + adjusted, 0)
        net_collected = collected - refunded
        due = max(effective_total - net_collected, 0)
        refund_due = max(net_collected - effective_total, 0)
        overdue = due if self._balance_is_overdue() else 0
        return BookingReconciliation(
            booking=self.booking,
            booking_total_inr=self.booking.booking_total_inr,
            effective_booking_total_inr=effective_total,
            collected_inr=collected,
            due_inr=due,
            adjusted_inr=adjusted,
            refunded_inr=refunded,
            refund_due_inr=refund_due,
            overdue_inr=overdue,
            platform_fee_inr=self.platform_fee_amount_inr(),
        )

    def payment_state(self) -> str:
        reconciliation = self.reconciliation()
        if reconciliation.refund_due_inr > 0:
            return PaymentState.REFUND_DUE
        if (
            reconciliation.collected_inr > 0
            and reconciliation.refunded_inr >= reconciliation.collected_inr
        ):
            return PaymentState.REFUNDED
        if reconciliation.overdue_inr > 0:
            return PaymentState.OVERDUE
        if reconciliation.collected_inr <= 0:
            return PaymentState.UNPAID
        if reconciliation.due_inr <= 0:
            return PaymentState.FULLY_PAID
        if reconciliation.collected_inr <= self.booking.booking_reservation_amount_inr:
            return PaymentState.RESERVATION_PAID
        return PaymentState.PARTIALLY_PAID

    def reconciliation_flags(self) -> list[str]:
        return _booking_reconciliation_flags(self.reconciliation())

    def _sum_entries(self, entry_types: tuple[str, ...]) -> int:
        total = self.booking.ledger_entries.filter(entry_type__in=entry_types).aggregate(
            total=models.Sum("amount_inr"),
        )["total"]
        return total or 0

    def _balance_is_overdue(self) -> bool:
        if self.booking.booking_state == Booking.BookingState.DRAFT:
            return False
        schedule = getattr(self.booking.trip, "payment_schedule", None)
        if schedule is None or schedule.balance_due_date is None:
            return False
        return timezone.localdate() > schedule.balance_due_date


def _record_idempotent_ledger_entries(
    writes: list[_LedgerEntryWrite],
) -> tuple[LedgerEntry, ...]:
    with transaction.atomic():
        return tuple(_get_or_create_ledger_entry(write) for write in writes)


def _get_or_create_ledger_entry(write: _LedgerEntryWrite) -> LedgerEntry:
    ledger_entry, _created = LedgerEntry.objects.get_or_create(
        **write.identity_kwargs(),
        defaults=write.defaults(),
    )
    return ledger_entry


def _create_ledger_entry(write: _LedgerEntryWrite) -> LedgerEntry:
    return LedgerEntry.objects.create(**write.create_kwargs())


def platform_fee_for_provider_payment_inr(provider_payment: ProviderPayment) -> int:
    return FinancialLedger.platform_fee_for_provider_payment_inr(provider_payment)


def record_financial_ledger_event(event: FinancialLedgerEvent) -> tuple[LedgerEntry, ...]:
    return FinancialLedger.record_event(event)


def collected_ledger_amount_inr(booking: Booking) -> int:
    return FinancialLedger.for_booking(booking).collected_amount_inr()


def collected_provider_payment_amount_inr(booking: Booking) -> int:
    total = booking.ledger_entries.filter(
        entry_type=LedgerEntry.EntryType.PROVIDER_PAYMENT,
    ).aggregate(total=models.Sum("amount_inr"))["total"]
    return total or 0


def platform_fee_for_provider_payment_ledger_amount_inr(
    provider_payment: ProviderPayment,
) -> int:
    total = provider_payment.ledger_entries.filter(
        entry_type=LedgerEntry.EntryType.PLATFORM_FEE,
    ).aggregate(total=models.Sum("amount_inr"))["total"]
    return total or 0


def effective_booking_total_inr(booking: Booking) -> int:
    return FinancialLedger.for_booking(booking).effective_booking_total_inr()


def booking_reconciliation_payload(booking: Booking) -> dict[str, int]:
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


def booking_reconciliation(booking: Booking) -> BookingReconciliation:
    return FinancialLedger.for_booking(booking).reconciliation()


def booking_reconciliation_flags_for_booking(booking: Booking) -> list[str]:
    reconciliation = booking_reconciliation(booking)
    flags = []
    if reconciliation.refund_due_inr > 0:
        flags.append("refund_due")
    if reconciliation.overdue_inr > 0:
        flags.append("overdue_balance")
    if booking.payment_attempts.filter(
        status__in=[
            PaymentAttempt.Status.PENDING,
            PaymentAttempt.Status.CONFIRMING,
        ]
    ).exists():
        flags.append("pending_payment_attempt")
    if booking.payment_attempts.filter(status=PaymentAttempt.Status.FAILED).exists():
        flags.append("failed_payment_attempt")
    if booking.manual_payments.filter(status=ManualPayment.Status.SUBMITTED).exists():
        flags.append("submitted_manual_payment")
    if booking.import_rows.filter(status=BookingImportRow.Status.CONFLICT).exists():
        flags.append("booking_import_conflict")
    return flags


def booking_reconciliation_flags(reconciliation: BookingReconciliation) -> list[str]:
    return _booking_reconciliation_flags(reconciliation)


def derived_payment_state(booking: Booking) -> str:
    return FinancialLedger.for_booking(booking).payment_state()


def booking_payment_summary_payload(bookings) -> dict:
    collected_inr = 0
    due_inr = 0
    overdue_inr = 0
    refund_due_inr = 0
    platform_fee_inr = 0
    gross_provider_payment_amount_inr = 0
    provider_fee_amount_inr = 0
    provider_net_settlement_amount_inr = 0
    provider_payment_count = 0
    provider_payments_with_fee_count = 0
    provider_payments_with_net_settlement_count = 0
    pending_manual_payments = 0

    for booking in bookings:
        reconciliation = booking_reconciliation(booking)
        collected_inr += reconciliation.collected_inr
        due_inr += reconciliation.due_inr
        overdue_inr += reconciliation.overdue_inr
        refund_due_inr += reconciliation.refund_due_inr
        platform_fee_inr += reconciliation.platform_fee_inr
        for provider_payment in booking.provider_payments.all():
            provider_payment_count += 1
            gross_provider_payment_amount_inr += provider_payment.amount_inr
            if provider_payment.provider_fee_amount_inr is not None:
                provider_payments_with_fee_count += 1
                provider_fee_amount_inr += provider_payment.provider_fee_amount_inr
            if provider_payment.provider_net_settlement_amount_inr is not None:
                provider_payments_with_net_settlement_count += 1
                provider_net_settlement_amount_inr += (
                    provider_payment.provider_net_settlement_amount_inr
                )
        pending_manual_payments += booking.manual_payments.filter(
            status=ManualPayment.Status.SUBMITTED,
        ).count()

    return {
        "collected_inr": collected_inr,
        "due_inr": due_inr,
        "overdue_inr": overdue_inr,
        "refund_due_inr": refund_due_inr,
        "platform_fee_inr": platform_fee_inr,
        "gross_provider_payment_amount_inr": gross_provider_payment_amount_inr,
        "provider_fee_amount_inr": provider_fee_amount_inr,
        "provider_net_settlement_amount_inr": provider_net_settlement_amount_inr,
        "provider_payment_count": provider_payment_count,
        "provider_payments_with_fee_count": provider_payments_with_fee_count,
        "provider_payments_with_net_settlement_count": (
            provider_payments_with_net_settlement_count
        ),
        "pending_manual_payments": pending_manual_payments,
    }


def _booking_reconciliation_flags(reconciliation: BookingReconciliation) -> list[str]:
    flags = []
    if reconciliation.due_inr > 0:
        flags.append("balance_due")
    if reconciliation.overdue_inr > 0:
        flags.append("overdue")
    if reconciliation.refund_due_inr > 0:
        flags.append("refund_due")
    if reconciliation.adjusted_inr != 0:
        flags.append("adjusted")
    if reconciliation.refunded_inr > 0:
        flags.append("refunded")
    return flags
