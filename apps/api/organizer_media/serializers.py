from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from rest_framework import serializers

from organizer_media.media import validate_organizer_media_upload
from organizer_media.models import OrganizerMediaItem
from organizer_media.selectors import organizer_media_item_payload


class OrganizerMediaItemSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    is_public = serializers.BooleanField(read_only=True)

    class Meta:
        model = OrganizerMediaItem
        fields = [
            "id",
            "image_url",
            "original_filename",
            "content_type",
            "file_size",
            "position",
            "caption",
            "alt_text",
            "visibility",
            "is_public",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "image_url",
            "original_filename",
            "content_type",
            "file_size",
            "is_public",
            "created_at",
            "updated_at",
        ]

    def get_image_url(self, item: OrganizerMediaItem) -> str:
        return organizer_media_item_payload(
            item,
            request=self.context.get("request"),
        )["image_url"]


class OrganizerMediaLibraryRowSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    position = serializers.IntegerField(required=False, min_value=1)
    caption = serializers.CharField(max_length=220, allow_blank=True, required=False)
    alt_text = serializers.CharField(max_length=220, allow_blank=True, required=False)
    visibility = serializers.ChoiceField(
        choices=OrganizerMediaItem.Visibility.choices,
        required=False,
        default=OrganizerMediaItem.Visibility.PRIVATE,
    )


class OrganizerMediaLibrarySerializer(serializers.Serializer):
    media_items = OrganizerMediaLibraryRowSerializer(many=True, allow_empty=True)
    readiness = serializers.SerializerMethodField()

    def to_representation(self, instance) -> dict[str, object]:
        organizer = self.context.get("organizer", instance)
        items = (
            organizer.organizer_media_items.ordered_for_display()
            if organizer is not None
            else []
        )
        return {
            "media_items": OrganizerMediaItemSerializer(
                items,
                many=True,
                context=self.context,
            ).data,
            "readiness": self.get_readiness(instance),
        }

    def validate_media_items(self, items: list[dict]) -> list[dict]:
        organizer = self.context.get("organizer")
        existing_item_ids = (
            set(organizer.organizer_media_items.values_list("id", flat=True))
            if organizer is not None
            else set()
        )
        submitted_ids: set[int] = set()

        for index, item in enumerate(items, start=1):
            item_id = item.get("id")
            if item_id is None:
                raise serializers.ValidationError("Organizer Media Item id is required.")
            if item_id in submitted_ids:
                raise serializers.ValidationError("Organizer Media Item rows must be unique.")
            if item_id not in existing_item_ids:
                raise serializers.ValidationError(
                    f"Organizer Media Item {item_id} does not belong to this Organizer."
                )
            submitted_ids.add(item_id)
            item["position"] = index
            item["caption"] = item.get("caption", "").strip()
            item["alt_text"] = item.get("alt_text", "").strip()
        return items

    def save(self, **kwargs):
        organizer = self.context["organizer"]
        items = self.validated_data["media_items"]
        with transaction.atomic():
            existing_items = {
                item.id: item
                for item in OrganizerMediaItem.objects.select_for_update().filter(
                    organizer=organizer,
                )
            }
            submitted_ids = {item["id"] for item in items}
            OrganizerMediaItem.objects.filter(organizer=organizer).exclude(
                id__in=submitted_ids,
            ).delete()

            for position, item_data in enumerate(items, start=1):
                item = existing_items[item_data["id"]]
                item.position = position
                item.caption = item_data.get("caption", "")
                item.alt_text = item_data.get("alt_text", "")
                item.visibility = item_data.get(
                    "visibility",
                    OrganizerMediaItem.Visibility.PRIVATE,
                )
                item.save()
        return organizer

    def get_readiness(self, value) -> dict[str, object]:
        organizer = self.context.get("organizer", value)
        public_media_count = (
            organizer.organizer_media_items.public().count() if organizer is not None else 0
        )
        total_media_count = (
            organizer.organizer_media_items.count() if organizer is not None else 0
        )
        return {
            "public_media_count": public_media_count,
            "total_media_count": total_media_count,
            "encouraged": (
                [] if public_media_count else ["Add at least one Public Organizer Media item."]
            ),
            "blockers": [],
        }


class OrganizerMediaUploadSerializer(serializers.Serializer):
    images = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False),
        allow_empty=False,
        max_length=12,
    )

    def validate_images(self, images):
        for image in images:
            try:
                validate_organizer_media_upload(image)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.messages) from exc
        return images

    def save(self, **kwargs):
        organizer = self.context["organizer"]
        actor = self.context.get("actor")
        images = self.validated_data["images"]
        with transaction.atomic():
            next_position = (
                organizer.organizer_media_items.select_for_update()
                .aggregate(max_position=models.Max("position"))
                .get("max_position")
                or 0
            ) + 1
            created_items = []
            for index, image in enumerate(images):
                item = OrganizerMediaItem(
                    organizer=organizer,
                    image=image,
                    original_filename=getattr(image, "name", "")[:240],
                    content_type=getattr(image, "content_type", "")[:120],
                    file_size=getattr(image, "size", 0) or 0,
                    uploaded_by=actor if getattr(actor, "is_authenticated", False) else None,
                    position=next_position + index,
                )
                item.save()
                created_items.append(item)
        return created_items
