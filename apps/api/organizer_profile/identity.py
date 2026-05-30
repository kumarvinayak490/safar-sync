from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django.core.exceptions import ValidationError

ALLOWED_LOGO_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
ALLOWED_LOGO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_LOGO_BYTES = 2 * 1024 * 1024

FALLBACK_COLORS = [
    ("oklch(0.96 0.024 78)", "oklch(0.36 0.08 62)"),
    ("oklch(0.96 0.024 150)", "oklch(0.34 0.078 150)"),
    ("oklch(0.96 0.022 238)", "oklch(0.34 0.07 238)"),
    ("oklch(0.965 0.024 42)", "oklch(0.38 0.085 42)"),
]


@dataclass(frozen=True)
class OrganizerProfileFallback:
    initials: str
    label: str
    background: str
    foreground: str

    def to_payload(self) -> dict[str, str]:
        return {
            "initials": self.initials,
            "label": self.label,
            "background": self.background,
            "foreground": self.foreground,
        }


def public_organizer_name(organizer) -> str:
    return organizer.identity_name or organizer.name


def public_organizer_logo_url(organizer) -> str:
    if not organizer.identity_logo:
        return ""
    try:
        return organizer.identity_logo.url
    except ValueError:
        return ""


def organizer_profile_identity_payload(organizer, request=None) -> dict:
    logo_url = public_organizer_logo_url(organizer)
    if request is not None and logo_url.startswith("/"):
        logo_url = request.build_absolute_uri(logo_url)

    name = public_organizer_name(organizer)
    return {
        "name": name,
        "identity_name": organizer.identity_name,
        "identity_whatsapp_number": organizer.identity_whatsapp_number.strip(),
        "logo_url": logo_url,
        "logo_uploaded": bool(organizer.identity_logo),
        "fallback": organizer_profile_fallback(name).to_payload(),
        "placeholder": not bool(organizer.identity_name),
    }


def organizer_profile_fallback(name: str) -> OrganizerProfileFallback:
    label = name.strip() or "Organizer"
    words = [word for word in label.replace("&", " ").split() if word]
    initials = "".join(word[0].upper() for word in words[:2] if word[0].isalnum())
    if not initials:
        initials = "TO"

    background, foreground = FALLBACK_COLORS[_stable_color_index(label)]
    return OrganizerProfileFallback(
        initials=initials[:2],
        label=label,
        background=background,
        foreground=foreground,
    )


def validate_organizer_logo_upload(upload) -> None:
    if not upload:
        return

    if getattr(upload, "size", 0) > MAX_LOGO_BYTES:
        raise ValidationError("Organizer Logo must be 2 MB or smaller.")

    extension = Path(upload.name).suffix.lower()
    if extension not in ALLOWED_LOGO_EXTENSIONS:
        raise ValidationError("Upload a PNG, JPG, or WebP Organizer Logo.")

    content_type = getattr(upload, "content_type", "")
    if content_type not in ALLOWED_LOGO_CONTENT_TYPES:
        raise ValidationError("Upload a PNG, JPG, or WebP Organizer Logo.")

    if not _has_allowed_image_signature(upload, extension):
        raise ValidationError("Organizer Logo file content does not match its image type.")


def _stable_color_index(label: str) -> int:
    return sum(ord(character) for character in label.lower()) % len(FALLBACK_COLORS)


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


OrganizerIdentityFallback = OrganizerProfileFallback
organizer_identity_fallback = organizer_profile_fallback
organizer_identity_payload = organizer_profile_identity_payload
