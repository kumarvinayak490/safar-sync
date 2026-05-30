from __future__ import annotations

from pathlib import Path

from django.core.exceptions import ValidationError

ALLOWED_TRIP_MEDIA_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
ALLOWED_TRIP_MEDIA_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_TRIP_MEDIA_BYTES = 8 * 1024 * 1024


def validate_trip_media_upload(upload) -> None:
    if not upload:
        raise ValidationError("Trip Media Item image is required.")

    if getattr(upload, "size", 0) > MAX_TRIP_MEDIA_BYTES:
        raise ValidationError("Trip Media Item images must be 8 MB or smaller.")

    extension = Path(upload.name).suffix.lower()
    if extension not in ALLOWED_TRIP_MEDIA_EXTENSIONS:
        raise ValidationError("Upload PNG, JPG, or WebP Trip Media Item images.")

    content_type = getattr(upload, "content_type", "")
    if content_type not in ALLOWED_TRIP_MEDIA_CONTENT_TYPES:
        raise ValidationError("Upload PNG, JPG, or WebP Trip Media Item images.")

    if not _has_allowed_image_signature(upload, extension):
        raise ValidationError("Trip Media Item file content does not match its image type.")


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
