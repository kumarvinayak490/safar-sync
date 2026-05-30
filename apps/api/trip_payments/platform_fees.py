from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from django.db import models, transaction
from django.utils import timezone

from organizers.models import Organizer
from trip_payments.models import LedgerEntry, PlatformFeeStatement, first_day_of_next_month


@dataclass(frozen=True)
class PlatformFeeStatementAggregation:
    organizer: Organizer
    period_start: date
    period_end: date
    provider_payment_count: int
    gross_provider_payment_amount_inr: int
    platform_fee_amount_inr: int


def month_period_start(value: date | datetime) -> date:
    if isinstance(value, datetime):
        value = timezone.localtime(value).date() if timezone.is_aware(value) else value.date()
    return date(value.year, value.month, 1)


def period_bounds(period_start: date) -> tuple[datetime, datetime]:
    start = month_period_start(period_start)
    end = first_day_of_next_month(start)
    current_timezone = timezone.get_current_timezone()
    return (
        timezone.make_aware(datetime.combine(start, time.min), current_timezone),
        timezone.make_aware(datetime.combine(end, time.min), current_timezone),
    )


def aggregate_platform_fees_for_statement(
    organizer: Organizer,
    period_start: date,
) -> PlatformFeeStatementAggregation:
    period_start = month_period_start(period_start)
    period_end = first_day_of_next_month(period_start)
    start_at, end_at = period_bounds(period_start)
    totals = LedgerEntry.objects.filter(
        booking__trip__organizer=organizer,
        entry_type=LedgerEntry.EntryType.PLATFORM_FEE,
        occurred_at__gte=start_at,
        occurred_at__lt=end_at,
    ).aggregate(
        provider_payment_count=models.Count("provider_payment", distinct=True),
        gross_provider_payment_amount_inr=models.Sum("provider_payment__amount_inr"),
        platform_fee_amount_inr=models.Sum("amount_inr"),
    )
    return PlatformFeeStatementAggregation(
        organizer=organizer,
        period_start=period_start,
        period_end=period_end,
        provider_payment_count=totals["provider_payment_count"] or 0,
        gross_provider_payment_amount_inr=totals["gross_provider_payment_amount_inr"] or 0,
        platform_fee_amount_inr=totals["platform_fee_amount_inr"] or 0,
    )


def apply_platform_fee_statement_aggregation(
    statement: PlatformFeeStatement,
    *,
    generated_at=None,
) -> PlatformFeeStatement:
    aggregation = aggregate_platform_fees_for_statement(
        statement.organizer,
        statement.period_start,
    )
    statement.provider_payment_count = aggregation.provider_payment_count
    statement.gross_provider_payment_amount_inr = aggregation.gross_provider_payment_amount_inr
    statement.platform_fee_amount_inr = aggregation.platform_fee_amount_inr
    statement.generated_at = generated_at or timezone.now()
    return statement


def refresh_platform_fee_statement(
    statement: PlatformFeeStatement,
) -> PlatformFeeStatement:
    apply_platform_fee_statement_aggregation(statement)
    save_fields = [
        "provider_payment_count",
        "gross_provider_payment_amount_inr",
        "platform_fee_amount_inr",
        "generated_at",
        "updated_at",
    ]
    if statement.pk:
        statement.save(update_fields=save_fields)
    else:
        statement.save()
    return statement


def generate_platform_fee_statement(
    organizer: Organizer,
    period_start: date,
    *,
    status: str | None = None,
    notes: str | None = None,
) -> PlatformFeeStatement:
    period_start = month_period_start(period_start)
    with transaction.atomic():
        statement, created = PlatformFeeStatement.objects.select_for_update().get_or_create(
            organizer=organizer,
            period_start=period_start,
            defaults={"status": status or PlatformFeeStatement.Status.DRAFT},
        )
        apply_platform_fee_statement_aggregation(statement)
        update_fields = [
            "provider_payment_count",
            "gross_provider_payment_amount_inr",
            "platform_fee_amount_inr",
            "generated_at",
            "updated_at",
        ]
        if status is not None and statement.status != status:
            statement.status = status
            update_fields.append("status")
        if notes is not None and statement.notes != notes:
            statement.notes = notes
            update_fields.append("notes")

        if created:
            statement.save()
        else:
            statement.save(update_fields=update_fields)
        return statement
