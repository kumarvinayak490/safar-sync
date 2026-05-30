from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from trip_bookings.models import Booking
from trip_operations.activity import actor_for_activity, record_activity_log
from trip_operations.models import ActivityLog
from trip_travelers.models import TravelerSlot
from trips.models import Trip, TripPackage

ACTIVE_BOOKING_STATES = {
    Booking.BookingState.RESERVED,
    Booking.BookingState.CONFIRMED,
}

PRE_PAYMENT_TRAVELER_IDENTITY_MESSAGE = (
    "Public booking collects only Booking Contact Details, Traveler count, Package, "
    "and pricing inputs before reservation payment. Traveler Identity Details and "
    "documents are collected after reservation."
)


@dataclass(frozen=True)
class TravelerSlotIntakeInput:
    package_id: int
    traveler_full_name: str = ""
    traveler_phone: str = ""
    traveler_email: str = ""


@dataclass(frozen=True)
class TravelerSlotIntake:
    package: TripPackage
    position: int
    traveler_full_name: str = ""
    traveler_phone: str = ""
    traveler_email: str = ""


def prepare_traveler_slots_intake(
    *,
    trip: Trip,
    traveler_slots: Sequence[TravelerSlotIntakeInput],
    missing_slots_field: str,
    missing_slots_message: str,
    package_ownership_field: str,
    package_ownership_message: str,
    allow_traveler_identity: bool,
) -> tuple[TravelerSlotIntake, ...]:
    if not traveler_slots:
        raise ValidationError({missing_slots_field: missing_slots_message})

    packages = packages_for_trip(trip)
    prepared_slots = []
    for position, slot in enumerate(traveler_slots, start=1):
        package = packages.get(slot.package_id)
        if package is None:
            raise ValidationError({package_ownership_field: package_ownership_message})
        prepared_slots.append(
            TravelerSlotIntake(
                package=package,
                position=position,
                traveler_full_name=(
                    normalize_traveler_slot_text(slot.traveler_full_name)
                    if allow_traveler_identity
                    else ""
                ),
                traveler_phone=(
                    normalize_traveler_slot_text(slot.traveler_phone)
                    if allow_traveler_identity
                    else ""
                ),
                traveler_email=(
                    normalize_traveler_slot_text(slot.traveler_email)
                    if allow_traveler_identity
                    else ""
                ),
            )
        )

    return tuple(prepared_slots)


def create_traveler_slots_for_booking(
    *,
    booking: Booking,
    traveler_slots: Sequence[TravelerSlotIntake],
) -> list[TravelerSlot]:
    return [
        TravelerSlot.objects.create(
            booking=booking,
            package=slot.package,
            position=slot.position,
            traveler_full_name=slot.traveler_full_name,
            traveler_phone=slot.traveler_phone,
            traveler_email=slot.traveler_email,
        )
        for slot in traveler_slots
    ]


def replace_traveler_slots_for_booking(
    *,
    booking: Booking,
    traveler_slots: Sequence[TravelerSlotIntake],
) -> list[TravelerSlot]:
    booking.traveler_slots.all().delete()
    return create_traveler_slots_for_booking(
        booking=booking,
        traveler_slots=traveler_slots,
    )


def reject_pre_payment_traveler_identity_details(initial_data: Mapping | None) -> None:
    if not isinstance(initial_data, Mapping):
        return

    blocked_top_level_fields = {
        "traveler_full_name",
        "traveler_phone",
        "traveler_email",
        "traveler_documents",
        "documents",
    }
    blocked_slot_fields = blocked_top_level_fields | {
        "arrival_details",
        "departure_details",
        "pickup_location",
        "logistics_note",
        "emergency_contact_name",
        "emergency_contact_phone",
        "emergency_contact_relationship",
        "medical_disclosure",
    }
    supplied_top_level = blocked_top_level_fields.intersection(initial_data)
    supplied_slot_fields = {
        field
        for slot in initial_data.get("traveler_slots", [])
        if isinstance(slot, Mapping)
        for field in blocked_slot_fields.intersection(slot)
    }
    if supplied_top_level or supplied_slot_fields:
        raise ValidationError({"traveler_slots": PRE_PAYMENT_TRAVELER_IDENTITY_MESSAGE})


def active_reserved_traveler_count(trip: Trip) -> int:
    return TravelerSlot.objects.filter(
        booking__trip=trip,
        booking__booking_state__in=ACTIVE_BOOKING_STATES,
        traveler_state=TravelerSlot.TravelerState.ACTIVE,
    ).count()


def available_seats(trip: Trip) -> int:
    return max(trip.capacity - active_reserved_traveler_count(trip), 0)


def booking_reservation_amount_inr(booking: Booking) -> int:
    return sum(
        slot.booked_reservation_amount_inr
        for slot in booking.traveler_slots.select_related("package")
        if slot.traveler_state != TravelerSlot.TravelerState.REPLACED
    )


def booking_total_inr(booking: Booking) -> int:
    return sum(
        slot.booked_package_price_inr
        for slot in booking.traveler_slots.select_related("package")
        if slot.traveler_state != TravelerSlot.TravelerState.REPLACED
    )


def traveler_slot_count_for_booking(booking: Booking) -> int:
    return booking.traveler_slots.exclude(
        traveler_state=TravelerSlot.TravelerState.REPLACED
    ).count()


def update_traveler_identity_details(
    traveler_slot: TravelerSlot,
    *,
    traveler_full_name: str,
    traveler_phone: str,
    traveler_email: str = "",
) -> TravelerSlot:
    if not traveler_full_name.strip():
        raise ValidationError("Traveler Identity Details require full name.")
    if not traveler_phone.strip():
        raise ValidationError("Traveler Identity Details require phone number.")

    traveler_slot.traveler_full_name = traveler_full_name
    traveler_slot.traveler_phone = traveler_phone
    traveler_slot.traveler_email = traveler_email
    traveler_slot.save(
        update_fields=[
            "traveler_full_name",
            "traveler_phone",
            "traveler_email",
            "updated_at",
        ]
    )
    return traveler_slot


def validate_package_for_booking(
    *,
    package: TripPackage,
    booking: Booking,
    message: str,
) -> None:
    if package.trip_id != booking.trip_id:
        raise ValidationError(message)


def packages_for_trip(trip: Trip) -> dict[int, TripPackage]:
    return {package.id: package for package in trip.packages.active()}


def normalize_traveler_slot_text(value: str | None) -> str:
    return (value or "").strip()


class TravelerSlotWorkflow:
    def __init__(
        self,
        *,
        required_amount_to_reserve: Callable[[Booking], int] | None = None,
        collected_amount: Callable[[Booking], int] | None = None,
    ):
        self.required_amount_to_reserve = required_amount_to_reserve
        self.collected_amount = collected_amount

    def cancel_traveler(
        self,
        traveler_slot: TravelerSlot,
        *,
        cancellation_reason: str,
        actor=None,
    ) -> TravelerSlot:
        cancellation_reason = self._require_reason(
            cancellation_reason,
            "Traveler Cancellation requires Cancellation Reason.",
        )

        with transaction.atomic():
            traveler_slot = self._lock_traveler_slot(traveler_slot)
            booking = traveler_slot.booking
            self._require_active_booking(
                booking,
                "Traveler Cancellation is available only for Reserved or Confirmed Bookings.",
            )
            self._require_traveler_state(
                traveler_slot,
                {TravelerSlot.TravelerState.ACTIVE},
                "Only Active Travelers can be cancelled.",
            )

            traveler_slot.traveler_state = TravelerSlot.TravelerState.CANCELLED
            traveler_slot.cancellation_reason = cancellation_reason
            traveler_slot.cancelled_at = timezone.now()
            traveler_slot.cancelled_by = actor_for_activity(actor)
            traveler_slot.save(
                update_fields=[
                    "traveler_state",
                    "cancellation_reason",
                    "cancelled_at",
                    "cancelled_by",
                    "updated_at",
                ]
            )
            self._record_transition_activity(
                action=ActivityLog.Action.TRAVELER_CANCELLED,
                booking=booking,
                traveler_slot=traveler_slot,
                actor=actor,
                metadata={"cancellation_reason": cancellation_reason},
            )
            return traveler_slot

    def replace_traveler(
        self,
        traveler_slot: TravelerSlot,
        *,
        traveler_full_name: str,
        traveler_phone: str,
        traveler_email: str = "",
        actor=None,
    ) -> TravelerSlot:
        if not traveler_full_name.strip() or not traveler_phone.strip():
            raise ValidationError("Traveler Replacement requires Traveler Identity Details.")

        with transaction.atomic():
            traveler_slot = self._lock_traveler_slot(traveler_slot)
            booking = traveler_slot.booking
            self._require_active_booking(
                booking,
                "Traveler Replacement is available only for Reserved or Confirmed Bookings.",
            )
            self._require_traveler_state(
                traveler_slot,
                {TravelerSlot.TravelerState.ACTIVE},
                "Only Active Travelers can be replaced.",
            )

            replacement = TravelerSlot.objects.create(
                booking=booking,
                package=traveler_slot.package,
                position=self._next_traveler_position(booking),
                traveler_state=TravelerSlot.TravelerState.ACTIVE,
                booked_package_price_inr=traveler_slot.booked_package_price_inr,
                booked_reservation_amount_inr=traveler_slot.booked_reservation_amount_inr,
                traveler_full_name=traveler_full_name,
                traveler_phone=traveler_phone,
                traveler_email=traveler_email,
            )
            traveler_slot.traveler_state = TravelerSlot.TravelerState.REPLACED
            traveler_slot.replaced_by_slot = replacement
            traveler_slot.save(update_fields=["traveler_state", "replaced_by_slot", "updated_at"])
            self._record_transition_activity(
                action=ActivityLog.Action.TRAVELER_REPLACED,
                booking=booking,
                traveler_slot=traveler_slot,
                actor=actor,
                metadata={
                    "replacement_traveler_slot_id": replacement.id,
                    "inherited_package_id": replacement.package_id,
                    "booked_package_price_inr": replacement.booked_package_price_inr,
                    "booked_reservation_amount_inr": replacement.booked_reservation_amount_inr,
                },
            )
            return replacement

    def add_traveler_to_booking(
        self,
        booking: Booking,
        *,
        package: TripPackage,
        traveler_full_name: str = "",
        traveler_phone: str = "",
        traveler_email: str = "",
        actor=None,
    ) -> TravelerSlot:
        with transaction.atomic():
            booking = self._lock_booking(booking, prefetch_travelers=True, prefetch_ledger=True)
            package = TripPackage.objects.select_for_update().get(pk=package.pk)
            validate_package_for_booking(
                package=package,
                booking=booking,
                message="Traveler Addition Package must belong to the Booking Trip.",
            )
            self._require_active_booking(
                booking,
                "Traveler Addition is available only for Reserved or Confirmed Bookings.",
            )
            if available_seats(booking.trip) < 1:
                raise ValidationError("Traveler Addition requires enough Available Seats.")

            traveler_slot = TravelerSlot.objects.create(
                booking=booking,
                package=package,
                position=self._next_traveler_position(booking),
                traveler_state=TravelerSlot.TravelerState.PENDING_ADDITION,
                traveler_full_name=traveler_full_name,
                traveler_phone=traveler_phone,
                traveler_email=traveler_email,
            )
            self._record_transition_activity(
                action=ActivityLog.Action.TRAVELER_ADDITION_CREATED,
                booking=booking,
                traveler_slot=traveler_slot,
                actor=actor,
                metadata={
                    "package_id": package.id,
                    "booked_package_price_inr": traveler_slot.booked_package_price_inr,
                    "booked_reservation_amount_inr": traveler_slot.booked_reservation_amount_inr,
                },
            )
            self.reserve_pending_traveler_additions_if_ready(booking, actor=actor)
            return traveler_slot

    def reserve_pending_traveler_additions_if_ready(
        self,
        booking: Booking,
        *,
        actor=None,
    ) -> list[TravelerSlot]:
        if booking.booking_state not in ACTIVE_BOOKING_STATES:
            return []

        booking = self._load_booking_for_addition_reservation(booking)
        pending_slots = [
            slot
            for slot in booking.traveler_slots.all()
            if slot.traveler_state == TravelerSlot.TravelerState.PENDING_ADDITION
        ]
        if not pending_slots:
            return []
        required_amount = self._required_amount_to_reserve_inr(booking)
        if self._collected_amount_inr(booking) < required_amount:
            return []
        if available_seats(booking.trip) < len(pending_slots):
            raise ValidationError("Available Seats are no longer sufficient for Traveler Addition.")

        reserved_at = timezone.now()
        reserved_slots = []
        for slot in pending_slots:
            slot.traveler_state = TravelerSlot.TravelerState.ACTIVE
            slot.addition_reserved_at = reserved_at
            slot.save(update_fields=["traveler_state", "addition_reserved_at", "updated_at"])
            self._record_transition_activity(
                action=ActivityLog.Action.TRAVELER_ADDITION_RESERVED,
                booking=booking,
                traveler_slot=slot,
                actor=actor,
                metadata={
                    "booked_reservation_amount_inr": slot.booked_reservation_amount_inr,
                    "required_amount_to_reserve_inr": required_amount,
                },
            )
            reserved_slots.append(slot)
        return reserved_slots

    def change_traveler_package(
        self,
        traveler_slot: TravelerSlot,
        *,
        package: TripPackage,
        actor=None,
    ) -> TravelerSlot:
        with transaction.atomic():
            traveler_slot = self._lock_traveler_slot(traveler_slot)
            package = TripPackage.objects.select_for_update().get(pk=package.pk)
            booking = traveler_slot.booking
            validate_package_for_booking(
                package=package,
                booking=booking,
                message="Package must belong to the Booking Trip.",
            )
            self._require_active_booking(
                booking,
                "Post-reservation package changes are available only for Reserved or Confirmed "
                "Bookings.",
            )
            if traveler_slot.traveler_state == TravelerSlot.TravelerState.REPLACED:
                raise ValidationError("Replaced Travelers cannot have package changes.")

            old_package_id = traveler_slot.package_id
            old_price = traveler_slot.booked_package_price_inr
            old_reservation = traveler_slot.booked_reservation_amount_inr
            traveler_slot.package = package
            traveler_slot.booked_package_price_inr = package.price_inr
            traveler_slot.booked_reservation_amount_inr = package.reservation_amount_inr
            traveler_slot.save(
                update_fields=[
                    "package",
                    "booked_package_price_inr",
                    "booked_reservation_amount_inr",
                    "updated_at",
                ]
            )
            amount_delta = traveler_slot.booked_package_price_inr - old_price
            ledger_entry = self._record_package_change(
                booking=booking,
                amount_inr=amount_delta,
                description=f"Traveler Package changed from {old_package_id} to {package.id}.",
            )
            self._record_transition_activity(
                action=ActivityLog.Action.TRAVELER_PACKAGE_CHANGED,
                booking=booking,
                traveler_slot=traveler_slot,
                actor=actor,
                metadata={
                    "old_package_id": old_package_id,
                    "new_package_id": package.id,
                    "old_booked_package_price_inr": old_price,
                    "new_booked_package_price_inr": traveler_slot.booked_package_price_inr,
                    "old_booked_reservation_amount_inr": old_reservation,
                    "new_booked_reservation_amount_inr": (
                        traveler_slot.booked_reservation_amount_inr
                    ),
                    "ledger_entry_id": ledger_entry.id if ledger_entry else None,
                },
            )
            self.reserve_pending_traveler_additions_if_ready(booking, actor=actor)
            return traveler_slot

    def _load_booking_for_addition_reservation(self, booking: Booking) -> Booking:
        return (
            Booking.objects.select_related("trip", "trip__payment_schedule")
            .prefetch_related("traveler_slots__package", "ledger_entries")
            .get(pk=booking.pk)
        )

    def _lock_booking(
        self,
        booking: Booking,
        *,
        prefetch_travelers: bool = False,
        prefetch_ledger: bool = False,
    ) -> Booking:
        queryset = Booking.objects.select_for_update().select_related(
            "trip",
            "trip__organizer",
            "trip__payment_schedule",
        )
        prefetches = []
        if prefetch_travelers:
            prefetches.append("traveler_slots__package")
        if prefetch_ledger:
            prefetches.append("ledger_entries")
        if prefetches:
            queryset = queryset.prefetch_related(*prefetches)
        return queryset.get(pk=booking.pk)

    def _lock_traveler_slot(self, traveler_slot: TravelerSlot) -> TravelerSlot:
        return (
            TravelerSlot.objects.select_for_update()
            .select_related("booking", "booking__trip", "booking__trip__organizer", "package")
            .get(pk=traveler_slot.pk)
        )

    def _require_active_booking(self, booking: Booking, message: str) -> None:
        if booking.booking_state not in ACTIVE_BOOKING_STATES:
            raise ValidationError(message)

    def _require_traveler_state(
        self,
        traveler_slot: TravelerSlot,
        allowed_states: set[str],
        message: str,
    ) -> None:
        if traveler_slot.traveler_state not in allowed_states:
            raise ValidationError(message)

    def _require_reason(self, reason: str, message: str) -> str:
        if not reason.strip():
            raise ValidationError(message)
        return reason

    def _next_traveler_position(self, booking: Booking) -> int:
        return (
            booking.traveler_slots.aggregate(max_position=models.Max("position"))["max_position"]
            or 0
        ) + 1

    def _record_transition_activity(
        self,
        *,
        action: str,
        booking: Booking,
        traveler_slot: TravelerSlot | None = None,
        actor=None,
        metadata: dict | None = None,
    ) -> ActivityLog:
        return record_activity_log(
            action=action,
            booking=booking,
            traveler_slot=traveler_slot,
            actor=actor,
            metadata=metadata or {},
        )

    def _required_amount_to_reserve_inr(self, booking: Booking) -> int:
        if self.required_amount_to_reserve is not None:
            return self.required_amount_to_reserve(booking)

        from trip_bookings.lifecycle import required_amount_to_reserve_inr

        return required_amount_to_reserve_inr(booking)

    def _collected_amount_inr(self, booking: Booking) -> int:
        if self.collected_amount is not None:
            return self.collected_amount(booking)

        from trip_payments.financial_ledger import FinancialLedger

        return FinancialLedger.for_booking(booking).collected_amount_inr()

    def _record_package_change(self, *, booking: Booking, amount_inr: int, description: str):
        from trip_payments.financial_ledger import FinancialLedger

        return FinancialLedger.record_package_change(
            booking=booking,
            amount_inr=amount_inr,
            description=description,
        )


def cancel_traveler(
    traveler_slot: TravelerSlot,
    *,
    cancellation_reason: str,
    actor=None,
) -> TravelerSlot:
    return TravelerSlotWorkflow().cancel_traveler(
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
    return TravelerSlotWorkflow().replace_traveler(
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
    return TravelerSlotWorkflow().add_traveler_to_booking(
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
    return TravelerSlotWorkflow().reserve_pending_traveler_additions_if_ready(
        booking,
        actor=actor,
    )


def change_traveler_package(
    traveler_slot: TravelerSlot,
    *,
    package: TripPackage,
    actor=None,
) -> TravelerSlot:
    return TravelerSlotWorkflow().change_traveler_package(
        traveler_slot,
        package=package,
        actor=actor,
    )
