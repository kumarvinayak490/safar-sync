from __future__ import annotations

from organizer_media.models import OrganizerMediaItem


def public_organizer_media_queryset(organizer):
    return (
        OrganizerMediaItem.objects.filter(organizer=organizer)
        .public()
        .ordered_for_display()
    )


def organizer_media_item_payload(item: OrganizerMediaItem, request=None) -> dict:
    image_url = item.image_url
    if request is not None and image_url.startswith("/"):
        image_url = request.build_absolute_uri(image_url)

    return {
        "id": item.id,
        "image_url": image_url,
        "original_filename": item.original_filename,
        "content_type": item.content_type,
        "file_size": item.file_size,
        "position": item.position,
        "caption": item.caption,
        "alt_text": item.alt_text,
        "visibility": item.visibility,
        "is_public": item.is_public,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def public_organizer_media_payload(organizer, request=None) -> list[dict]:
    return [
        organizer_media_item_payload(item, request=request)
        for item in public_organizer_media_queryset(organizer)
    ]
