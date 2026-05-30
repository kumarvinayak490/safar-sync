from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.utils import timezone

from trip_bookings.models import Booking, BookingAccessLink
from trip_travelers.models import TravelerSlot

ACCESS_LINK_TOKEN_BYTES = 32


@dataclass(frozen=True)
class IssuedAccessLink:
    access_link: BookingAccessLink
    token: str


def access_link_token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_booking_access_link(
    booking: Booking,
    *,
    revoke_existing: bool = True,
) -> IssuedAccessLink:
    return issue_access_link(
        booking=booking,
        scope=BookingAccessLink.Scope.BOOKING,
        traveler_slot=None,
        revoke_existing=revoke_existing,
    )


def issue_traveler_access_link(
    traveler_slot: TravelerSlot,
    *,
    revoke_existing: bool = True,
) -> IssuedAccessLink:
    return issue_access_link(
        booking=traveler_slot.booking,
        scope=BookingAccessLink.Scope.TRAVELER,
        traveler_slot=traveler_slot,
        revoke_existing=revoke_existing,
    )


def issue_access_link(
    *,
    booking: Booking,
    scope: str,
    traveler_slot: TravelerSlot | None,
    revoke_existing: bool = True,
) -> IssuedAccessLink:
    validate_access_link_issue_request(
        booking=booking,
        scope=scope,
        traveler_slot=traveler_slot,
    )

    with transaction.atomic():
        if revoke_existing:
            revoke_active_access_links(
                booking=booking,
                scope=scope,
                traveler_slot=traveler_slot,
            )

        token = secrets.token_urlsafe(ACCESS_LINK_TOKEN_BYTES)
        access_link = BookingAccessLink.objects.create(
            booking=booking,
            traveler_slot=traveler_slot,
            scope=scope,
            token_digest=access_link_token_digest(token),
        )
        return IssuedAccessLink(access_link=access_link, token=token)


def validate_access_link_issue_request(
    *,
    booking: Booking,
    scope: str,
    traveler_slot: TravelerSlot | None,
) -> None:
    if scope == BookingAccessLink.Scope.BOOKING and traveler_slot is not None:
        raise ValidationError(
            {"traveler_slot": "Booking-Level Access Links cannot target one Traveler Slot."}
        )
    if scope == BookingAccessLink.Scope.TRAVELER:
        if traveler_slot is None:
            raise ValidationError(
                {"traveler_slot": "Traveler-Level Access Links require a Traveler Slot."}
            )
        if traveler_slot.booking_id != booking.id:
            raise ValidationError(
                {"traveler_slot": "Traveler-Level Access Link must belong to this Booking."}
            )


def revoke_active_access_links(
    *,
    booking: Booking,
    scope: str,
    traveler_slot: TravelerSlot | None = None,
    revoked_at=None,
) -> int:
    queryset = BookingAccessLink.objects.select_for_update().filter(
        booking=booking,
        scope=scope,
        revoked_at__isnull=True,
    )
    if traveler_slot is not None:
        queryset = queryset.filter(traveler_slot=traveler_slot)
    else:
        queryset = queryset.filter(traveler_slot__isnull=True)
    return queryset.update(revoked_at=revoked_at or timezone.now())


def revoke_booking_level_access_links(booking: Booking, *, revoked_at=None) -> int:
    return revoke_active_access_links(
        booking=booking,
        scope=BookingAccessLink.Scope.BOOKING,
        traveler_slot=None,
        revoked_at=revoked_at,
    )


def resolve_active_access_link(token: str) -> BookingAccessLink:
    if not token:
        raise ValidationError("Booking Access Link is required.")

    try:
        access_link = (
            BookingAccessLink.objects.select_related(
                "booking",
                "booking__trip",
                "booking__trip__organizer",
                "booking__trip__payment_schedule",
                "traveler_slot",
                "traveler_slot__package",
            )
            .prefetch_related(
                "booking__traveler_slots__package",
                "booking__traveler_slots__documents",
                "booking__ledger_entries",
            )
            .get(token_digest=access_link_token_digest(token))
        )
    except BookingAccessLink.DoesNotExist as exc:
        raise ValidationError("Booking Access Link is invalid.") from exc

    if access_link.revoked_at is not None:
        raise ValidationError("Booking Access Link has been revoked.")
    if access_link.is_expired:
        raise ValidationError("Booking Access Link has expired.")
    return access_link


def traveler_slots_for_access_link(access_link: BookingAccessLink) -> list[TravelerSlot]:
    if access_link.scope == BookingAccessLink.Scope.TRAVELER:
        return [access_link.traveler_slot]
    return list(access_link.booking.traveler_slots.select_related("package").all())


def traveler_slot_for_access_link(
    access_link: BookingAccessLink,
    traveler_slot_id: int,
) -> TravelerSlot:
    if access_link.scope == BookingAccessLink.Scope.TRAVELER:
        if access_link.traveler_slot_id != traveler_slot_id:
            raise ValidationError("Traveler-Level Access Link can update only one Traveler.")
        return access_link.traveler_slot

    try:
        return (
            TravelerSlot.objects.select_related("booking", "booking__trip", "package")
            .prefetch_related("documents")
            .get(pk=traveler_slot_id, booking=access_link.booking)
        )
    except TravelerSlot.DoesNotExist as exc:
        raise Http404("No TravelerSlot matches the given query.") from exc
