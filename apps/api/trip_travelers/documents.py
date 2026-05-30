from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from trip_operations.activity import record_activity_log
from trip_operations.models import ActivityLog
from trip_travelers.models import TravelerDocument, TravelerSlot

DOCUMENT_STATE_RANK = {
    TravelerDocument.DocumentState.REJECTED: 0,
    TravelerDocument.DocumentState.MISSING: 1,
    TravelerDocument.DocumentState.SUBMITTED: 2,
    TravelerDocument.DocumentState.APPROVED: 3,
}

__all__ = (
    "DOCUMENT_STATE_RANK",
    "TravelerDocumentStateSummary",
    "TravelerDocumentWorkflow",
    "has_approved_traveler_document",
    "record_sensitive_traveler_document_download",
    "review_traveler_document",
    "sensitive_traveler_document_filenames",
    "submit_traveler_document",
    "traveler_document_state_summary",
)


@dataclass(frozen=True)
class TravelerDocumentStateSummary:
    document_state: str
    document_states: str


class TravelerDocumentWorkflow:
    def submit_document(
        self,
        *,
        traveler_slot: TravelerSlot,
        document_kind: str,
        label: str,
        uploaded_file,
    ) -> TravelerDocument:
        document_label = self._require_document_label(label)
        with transaction.atomic():
            document, _ = TravelerDocument.objects.get_or_create(
                traveler_slot=traveler_slot,
                document_kind=document_kind,
                label=document_label,
                defaults={"document_state": TravelerDocument.DocumentState.MISSING},
            )
            document.file = uploaded_file
            document.original_filename = uploaded_file.name
            document.content_type = getattr(uploaded_file, "content_type", "") or ""
            document.file_size = uploaded_file.size
            document.document_state = TravelerDocument.DocumentState.SUBMITTED
            document.rejection_reason = ""
            document.reviewed_by = None
            document.reviewed_at = None
            document.submitted_at = timezone.now()
            document.save()
            return document

    def review_document(
        self,
        *,
        document: TravelerDocument,
        document_state: str,
        reviewer,
        rejection_reason: str = "",
    ) -> TravelerDocument:
        if document_state not in {
            TravelerDocument.DocumentState.APPROVED,
            TravelerDocument.DocumentState.REJECTED,
        }:
            raise ValidationError("Traveler Document review state is unsupported.")

        cleaned_rejection_reason = rejection_reason.strip()
        if (
            document_state == TravelerDocument.DocumentState.REJECTED
            and not cleaned_rejection_reason
        ):
            raise ValidationError("Rejected Traveler Documents need a reason.")

        with transaction.atomic():
            document = (
                TravelerDocument.objects.select_for_update()
                .select_related(
                    "traveler_slot",
                    "traveler_slot__booking",
                    "traveler_slot__booking__trip",
                    "traveler_slot__booking__trip__organizer",
                )
                .get(pk=document.pk)
            )
            document.document_state = document_state
            document.rejection_reason = (
                ""
                if document_state == TravelerDocument.DocumentState.APPROVED
                else cleaned_rejection_reason
            )
            document.reviewed_by = reviewer
            document.reviewed_at = timezone.now()
            document.save(
                update_fields=[
                    "document_state",
                    "rejection_reason",
                    "reviewed_by",
                    "reviewed_at",
                    "updated_at",
                ]
            )
            self._record_document_review_activity(document, reviewer)
            return document

    def document_state_summary(
        self,
        traveler_slot: TravelerSlot,
    ) -> TravelerDocumentStateSummary:
        documents = list(traveler_slot.documents.all())
        if not documents:
            return TravelerDocumentStateSummary(
                document_state=TravelerDocument.DocumentState.MISSING,
                document_states="",
            )

        lowest_state = min(
            documents,
            key=lambda document: DOCUMENT_STATE_RANK[document.document_state],
        )
        state_details = [
            f"{document.label}:{document.document_kind}:{document.document_state}"
            for document in documents
        ]
        return TravelerDocumentStateSummary(
            document_state=lowest_state.document_state,
            document_states="; ".join(state_details),
        )

    def sensitive_document_filenames(self, traveler_slot: TravelerSlot) -> list[str]:
        values = []
        for document in traveler_slot.documents.all():
            if document.is_sensitive_traveler_information and document.file:
                values.append(document.original_filename or document.file.name.rsplit("/", 1)[-1])
        return values

    def record_sensitive_document_download(
        self,
        *,
        document: TravelerDocument,
        actor=None,
    ) -> ActivityLog | None:
        if not document.is_sensitive_traveler_information:
            return None
        return record_activity_log(
            action=ActivityLog.Action.SENSITIVE_TRAVELER_INFORMATION_DOWNLOAD,
            booking=document.traveler_slot.booking,
            traveler_slot=document.traveler_slot,
            traveler_document=document,
            actor=actor,
            metadata={
                "document_kind": document.document_kind,
                "document": document.id,
                "exclude_from_default_exports": document.exclude_from_default_exports,
            },
        )

    @staticmethod
    def has_approved_document(traveler_slot: TravelerSlot) -> bool:
        return any(
            document.document_state == TravelerDocument.DocumentState.APPROVED
            for document in traveler_slot.documents.all()
        )

    def _record_document_review_activity(
        self,
        document: TravelerDocument,
        reviewer,
    ) -> ActivityLog:
        action = (
            ActivityLog.Action.TRAVELER_DOCUMENT_APPROVED
            if document.document_state == TravelerDocument.DocumentState.APPROVED
            else ActivityLog.Action.TRAVELER_DOCUMENT_REJECTED
        )
        return record_activity_log(
            action=action,
            booking=document.traveler_slot.booking,
            traveler_slot=document.traveler_slot,
            traveler_document=document,
            actor=reviewer,
            metadata={
                "document_state": document.document_state,
                "is_sensitive_traveler_information": (
                    document.is_sensitive_traveler_information
                ),
            },
        )

    @staticmethod
    def _require_document_label(label: str) -> str:
        document_label = label.strip()
        if not document_label:
            raise ValidationError("Traveler Document label is required.")
        return document_label


def has_approved_traveler_document(traveler_slot: TravelerSlot) -> bool:
    return TravelerDocumentWorkflow().has_approved_document(traveler_slot)


def submit_traveler_document(
    *,
    traveler_slot: TravelerSlot,
    uploaded_file,
    document_kind: str = TravelerDocument.DocumentKind.IDENTITY,
    label: str = "Identity Document",
) -> TravelerDocument:
    return TravelerDocumentWorkflow().submit_document(
        traveler_slot=traveler_slot,
        document_kind=document_kind,
        label=label,
        uploaded_file=uploaded_file,
    )


def review_traveler_document(
    *,
    document: TravelerDocument,
    document_state: str,
    reviewer,
    rejection_reason: str = "",
) -> TravelerDocument:
    return TravelerDocumentWorkflow().review_document(
        document=document,
        document_state=document_state,
        reviewer=reviewer,
        rejection_reason=rejection_reason,
    )


def traveler_document_state_summary(
    traveler_slot: TravelerSlot,
) -> TravelerDocumentStateSummary:
    return TravelerDocumentWorkflow().document_state_summary(traveler_slot)


def sensitive_traveler_document_filenames(traveler_slot: TravelerSlot) -> list[str]:
    return TravelerDocumentWorkflow().sensitive_document_filenames(traveler_slot)


def record_sensitive_traveler_document_download(
    *,
    document: TravelerDocument,
    actor=None,
) -> ActivityLog | None:
    return TravelerDocumentWorkflow().record_sensitive_document_download(
        document=document,
        actor=actor,
    )
