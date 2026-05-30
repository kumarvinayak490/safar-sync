from __future__ import annotations

from pathlib import Path

from django.core.exceptions import ValidationError

from organizer_payments.models import ManualPaymentInstructions
from organizers.models import Organizer

ALLOWED_PAYMENT_QR_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
ALLOWED_PAYMENT_QR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_PAYMENT_QR_BYTES = 3 * 1024 * 1024


def manual_payment_instructions_for(
    organizer: Organizer,
) -> ManualPaymentInstructions | None:
    try:
        return organizer.manual_payment_instructions
    except ManualPaymentInstructions.DoesNotExist:
        return None


def has_ready_manual_payment_instructions(organizer: Organizer) -> bool:
    instructions = manual_payment_instructions_for(organizer)
    return bool(instructions and instructions.is_ready)


def manual_payment_instructions_payload(
    organizer: Organizer,
    *,
    request=None,
    can_manage: bool = False,
) -> dict:
    instructions = manual_payment_instructions_for(organizer)
    if instructions is None:
        return {
            "ready": False,
            "status_label": "Missing Payment QR",
            "blocker_code": "payment_qr_missing",
            "blocker_label": "Payment QR missing",
            "message": (
                "Manual Payment Instructions need a Payment QR before Manual Payments "
                "can be offered from Launch."
            ),
            "payment_qr_uploaded": False,
            "payment_qr_url": "",
            "original_filename": "",
            "content_type": "",
            "file_size": 0,
            "upi_id": "",
            "account_name": "",
            "bank_transfer_details": "",
            "can_manage": can_manage,
        }

    payment_qr_url = instructions.payment_qr_url
    if request is not None and payment_qr_url.startswith("/"):
        payment_qr_url = request.build_absolute_uri(payment_qr_url)
    ready = instructions.is_ready
    return {
        "ready": ready,
        "status_label": "Ready" if ready else "Missing Payment QR",
        "blocker_code": "ready" if ready else "payment_qr_missing",
        "blocker_label": "Ready" if ready else "Payment QR missing",
        "message": (
            "Manual Payment Instructions are ready for Trip-level Manual Payment Availability."
            if ready
            else (
                "Manual Payment Instructions need a Payment QR before Manual Payments "
                "can be offered from Launch."
            )
        ),
        "payment_qr_uploaded": bool(instructions.payment_qr),
        "payment_qr_url": payment_qr_url,
        "original_filename": instructions.original_filename,
        "content_type": instructions.content_type,
        "file_size": instructions.file_size,
        "upi_id": instructions.upi_id,
        "account_name": instructions.account_name,
        "bank_transfer_details": instructions.bank_transfer_details,
        "can_manage": can_manage,
    }


def validate_payment_qr_upload(upload) -> None:
    if not upload:
        raise ValidationError("Payment QR image is required.")

    if getattr(upload, "size", 0) > MAX_PAYMENT_QR_BYTES:
        raise ValidationError("Payment QR must be 3 MB or smaller.")

    extension = Path(upload.name).suffix.lower()
    if extension not in ALLOWED_PAYMENT_QR_EXTENSIONS:
        raise ValidationError("Upload a PNG, JPG, or WebP Payment QR.")

    content_type = getattr(upload, "content_type", "")
    if content_type not in ALLOWED_PAYMENT_QR_CONTENT_TYPES:
        raise ValidationError("Upload a PNG, JPG, or WebP Payment QR.")

    if not _has_allowed_image_signature(upload, extension):
        raise ValidationError("Payment QR file content does not match its image type.")


def _has_allowed_image_signature(upload, extension: str) -> bool:
    position = upload.tell() if hasattr(upload, "tell") else None
    header = upload.read(16)
    if hasattr(upload, "seek"):
        upload.seek(position or 0)

    if extension == ".png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {".jpg", ".jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if extension == ".webp":
        return header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    return False
