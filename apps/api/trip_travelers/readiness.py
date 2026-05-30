from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.utils import timezone

from trip_bookings.models import Booking
from trip_payments.financial_ledger import FinancialLedger
from trip_travelers.documents import (
    TravelerDocumentStateSummary,
    has_approved_traveler_document,
    review_traveler_document,
    sensitive_traveler_document_filenames,
    submit_traveler_document,
    traveler_document_state_summary,
)
from trip_travelers.models import TravelerDocument, TravelerSlot
from trip_travelers.slots import (
    update_traveler_identity_details as update_slot_identity_details,
)

ACTIVE_REQUIREMENT_TRAVELER_STATES = {
    TravelerSlot.TravelerState.ACTIVE,
    TravelerSlot.TravelerState.PENDING_ADDITION,
}

__all__ = (
    "ACTIVE_REQUIREMENT_TRAVELER_STATES",
    "BookingConfirmationRequirements",
    "TravelerDocumentStateSummary",
    "TravelerReadiness",
    "TravelerReadinessSummary",
    "UnmetConfirmationRequirement",
    "confirmation_requirements_for_booking",
    "has_approved_traveler_document",
    "readiness_summary_for_traveler_slot",
    "review_traveler_document",
    "sensitive_traveler_document_filenames",
    "submit_traveler_document",
    "traveler_document_state_summary",
    "traveler_portal_readiness_payload",
    "update_emergency_contact",
    "update_medical_disclosure",
    "update_travel_logistics",
    "update_traveler_identity_details",
)


@dataclass(frozen=True)
class UnmetConfirmationRequirement:
    code: str
    label: str
    scope: str = "booking"
    traveler_slot_id: int | None = None
    traveler_slot_position: int | None = None


@dataclass(frozen=True)
class BookingConfirmationRequirements:
    booking: Booking
    ready: bool
    unmet_requirements: list[UnmetConfirmationRequirement]


@dataclass(frozen=True)
class TravelerReadinessSummary:
    traveler_slot: TravelerSlot
    identity_details_ready: bool
    documents_ready: bool
    travel_logistics_ready: bool
    emergency_contact_ready: bool
    medical_disclosure_ready: bool

    @property
    def ready(self) -> bool:
        return all(
            [
                self.identity_details_ready,
                self.documents_ready,
                self.travel_logistics_ready,
                self.emergency_contact_ready,
                self.medical_disclosure_ready,
            ]
        )

    def portal_payload(self) -> dict[str, bool]:
        return {
            "documents_ready": self.documents_ready,
            "travel_logistics_ready": self.travel_logistics_ready,
            "emergency_contact_ready": self.emergency_contact_ready,
            "medical_disclosure_ready": self.medical_disclosure_ready,
            "ready": all(
                [
                    self.documents_ready,
                    self.travel_logistics_ready,
                    self.emergency_contact_ready,
                    self.medical_disclosure_ready,
                ]
            ),
        }


class TravelerReadiness:
    def confirmation_requirements_for_booking(
        self,
        booking: Booking,
    ) -> BookingConfirmationRequirements:
        unmet_requirements: list[UnmetConfirmationRequirement] = []
        trip = booking.trip

        if trip.requires_full_payment_before_confirmation:
            reconciliation = FinancialLedger.for_booking(booking).reconciliation()
            if reconciliation.due_inr > 0:
                unmet_requirements.append(
                    UnmetConfirmationRequirement(
                        code="full_payment",
                        label="Full payment",
                    )
                )

        for traveler_slot in self._requirement_traveler_slots(booking):
            unmet_requirements.extend(self.unmet_requirements_for_traveler_slot(traveler_slot))

        return BookingConfirmationRequirements(
            booking=booking,
            ready=len(unmet_requirements) == 0,
            unmet_requirements=unmet_requirements,
        )

    def readiness_summary_for_traveler_slot(
        self,
        traveler_slot: TravelerSlot,
    ) -> TravelerReadinessSummary:
        trip = traveler_slot.booking.trip
        return TravelerReadinessSummary(
            traveler_slot=traveler_slot,
            identity_details_ready=(
                not trip.requires_traveler_identity_details
                or self.has_identity_details(traveler_slot)
            ),
            documents_ready=(
                not trip.requires_traveler_documents
                or has_approved_traveler_document(traveler_slot)
            ),
            travel_logistics_ready=(
                not trip.requires_travel_logistics or self.has_travel_logistics(traveler_slot)
            ),
            emergency_contact_ready=(
                not trip.requires_emergency_contact or self.has_emergency_contact(traveler_slot)
            ),
            medical_disclosure_ready=(
                not trip.requires_medical_disclosure or self.has_medical_disclosure(traveler_slot)
            ),
        )

    def unmet_requirements_for_traveler_slot(
        self,
        traveler_slot: TravelerSlot,
    ) -> list[UnmetConfirmationRequirement]:
        trip = traveler_slot.booking.trip
        unmet_requirements: list[UnmetConfirmationRequirement] = []

        def add(code: str, label: str) -> None:
            unmet_requirements.append(
                UnmetConfirmationRequirement(
                    code=code,
                    label=label,
                    scope="traveler_slot",
                    traveler_slot_id=traveler_slot.id,
                    traveler_slot_position=traveler_slot.position,
                )
            )

        if trip.requires_traveler_identity_details and not self.has_identity_details(traveler_slot):
            add("traveler_identity_details", "Traveler Identity Details")

        if trip.requires_traveler_documents and not has_approved_traveler_document(
            traveler_slot
        ):
            add("traveler_documents", "Traveler Documents")

        if trip.requires_travel_logistics and not self.has_travel_logistics(traveler_slot):
            add("travel_logistics", "Travel Logistics")

        if trip.requires_emergency_contact and not self.has_emergency_contact(traveler_slot):
            add("emergency_contact", "Emergency Contact")

        if trip.requires_medical_disclosure and not self.has_medical_disclosure(traveler_slot):
            add("medical_disclosure", "Medical Disclosure")

        return unmet_requirements

    @staticmethod
    def has_identity_details(traveler_slot: TravelerSlot) -> bool:
        return bool(
            traveler_slot.traveler_full_name.strip() and traveler_slot.traveler_phone.strip()
        )

    @staticmethod
    def has_approved_traveler_document(traveler_slot: TravelerSlot) -> bool:
        return has_approved_traveler_document(traveler_slot)

    @staticmethod
    def has_travel_logistics(traveler_slot: TravelerSlot) -> bool:
        return any(
            [
                traveler_slot.arrival_details.strip(),
                traveler_slot.departure_details.strip(),
                traveler_slot.pickup_location.strip(),
                traveler_slot.logistics_note.strip(),
            ]
        )

    @staticmethod
    def has_emergency_contact(traveler_slot: TravelerSlot) -> bool:
        return bool(
            traveler_slot.emergency_contact_name.strip()
            and traveler_slot.emergency_contact_phone.strip()
            and traveler_slot.emergency_contact_relationship.strip()
        )

    @staticmethod
    def has_medical_disclosure(traveler_slot: TravelerSlot) -> bool:
        return bool(traveler_slot.medical_disclosure.strip())

    def submit_document(
        self,
        *,
        traveler_slot: TravelerSlot,
        document_kind: str,
        label: str,
        uploaded_file,
    ) -> TravelerDocument:
        return submit_traveler_document(
            traveler_slot=traveler_slot,
            document_kind=document_kind,
            label=label,
            uploaded_file=uploaded_file,
        )

    def review_document(
        self,
        *,
        document: TravelerDocument,
        document_state: str,
        reviewer,
        rejection_reason: str = "",
    ) -> TravelerDocument:
        return review_traveler_document(
            document=document,
            document_state=document_state,
            reviewer=reviewer,
            rejection_reason=rejection_reason,
        )

    def update_identity_details(
        self,
        traveler_slot: TravelerSlot,
        *,
        traveler_full_name: str,
        traveler_phone: str,
        traveler_email: str = "",
    ) -> TravelerSlot:
        return update_slot_identity_details(
            traveler_slot,
            traveler_full_name=traveler_full_name,
            traveler_phone=traveler_phone,
            traveler_email=traveler_email,
        )

    def update_travel_logistics(
        self,
        traveler_slot: TravelerSlot,
        *,
        arrival_details: str,
        departure_details: str,
        pickup_location: str,
        logistics_note: str,
    ) -> TravelerSlot:
        traveler_slot.arrival_details = arrival_details
        traveler_slot.departure_details = departure_details
        traveler_slot.pickup_location = pickup_location
        traveler_slot.logistics_note = logistics_note
        traveler_slot.save(
            update_fields=[
                "arrival_details",
                "departure_details",
                "pickup_location",
                "logistics_note",
                "updated_at",
            ]
        )
        return traveler_slot

    def update_emergency_contact(
        self,
        traveler_slot: TravelerSlot,
        *,
        emergency_contact_name: str,
        emergency_contact_phone: str,
        emergency_contact_relationship: str,
    ) -> TravelerSlot:
        if (
            not emergency_contact_name.strip()
            or not emergency_contact_phone.strip()
            or not emergency_contact_relationship.strip()
        ):
            raise ValidationError("Emergency Contact requires name, phone, and relationship.")

        traveler_slot.emergency_contact_name = emergency_contact_name
        traveler_slot.emergency_contact_phone = emergency_contact_phone
        traveler_slot.emergency_contact_relationship = emergency_contact_relationship
        traveler_slot.save(
            update_fields=[
                "emergency_contact_name",
                "emergency_contact_phone",
                "emergency_contact_relationship",
                "updated_at",
            ]
        )
        return traveler_slot

    def update_medical_disclosure(
        self,
        traveler_slot: TravelerSlot,
        *,
        medical_disclosure: str,
    ) -> TravelerSlot:
        if not medical_disclosure.strip():
            raise ValidationError("Medical Disclosure cannot be blank.")

        traveler_slot.medical_disclosure = medical_disclosure
        traveler_slot.medical_disclosure_submitted_at = timezone.now()
        traveler_slot.save(
            update_fields=[
                "medical_disclosure",
                "medical_disclosure_submitted_at",
                "updated_at",
            ]
        )
        return traveler_slot

    def document_state_summary(
        self,
        traveler_slot: TravelerSlot,
    ) -> TravelerDocumentStateSummary:
        return traveler_document_state_summary(traveler_slot)

    def sensitive_document_filenames(self, traveler_slot: TravelerSlot) -> list[str]:
        return sensitive_traveler_document_filenames(traveler_slot)

    def _requirement_traveler_slots(self, booking: Booking) -> list[TravelerSlot]:
        return [
            slot
            for slot in booking.traveler_slots.all()
            if slot.traveler_state in ACTIVE_REQUIREMENT_TRAVELER_STATES
        ]


def confirmation_requirements_for_booking(booking: Booking) -> BookingConfirmationRequirements:
    return TravelerReadiness().confirmation_requirements_for_booking(booking)


def readiness_summary_for_traveler_slot(
    traveler_slot: TravelerSlot,
) -> TravelerReadinessSummary:
    return TravelerReadiness().readiness_summary_for_traveler_slot(traveler_slot)


def traveler_portal_readiness_payload(traveler_slot: TravelerSlot) -> dict[str, bool]:
    return readiness_summary_for_traveler_slot(traveler_slot).portal_payload()


def update_traveler_identity_details(
    traveler_slot: TravelerSlot,
    *,
    traveler_full_name: str,
    traveler_phone: str,
    traveler_email: str = "",
) -> TravelerSlot:
    return TravelerReadiness().update_identity_details(
        traveler_slot,
        traveler_full_name=traveler_full_name,
        traveler_phone=traveler_phone,
        traveler_email=traveler_email,
    )


def update_travel_logistics(
    traveler_slot: TravelerSlot,
    *,
    arrival_details: str,
    departure_details: str,
    pickup_location: str,
    logistics_note: str,
) -> TravelerSlot:
    return TravelerReadiness().update_travel_logistics(
        traveler_slot,
        arrival_details=arrival_details,
        departure_details=departure_details,
        pickup_location=pickup_location,
        logistics_note=logistics_note,
    )


def update_emergency_contact(
    traveler_slot: TravelerSlot,
    *,
    emergency_contact_name: str,
    emergency_contact_phone: str,
    emergency_contact_relationship: str,
) -> TravelerSlot:
    return TravelerReadiness().update_emergency_contact(
        traveler_slot,
        emergency_contact_name=emergency_contact_name,
        emergency_contact_phone=emergency_contact_phone,
        emergency_contact_relationship=emergency_contact_relationship,
    )


def update_medical_disclosure(
    traveler_slot: TravelerSlot,
    *,
    medical_disclosure: str,
) -> TravelerSlot:
    return TravelerReadiness().update_medical_disclosure(
        traveler_slot,
        medical_disclosure=medical_disclosure,
    )
