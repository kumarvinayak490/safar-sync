from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.utils import timezone
from rest_framework import serializers

from organizer_payments.manual_payment_instructions import manual_payment_instructions_payload
from organizer_profile.identity import organizer_profile_identity_payload
from trips.booking_availability import public_booking_gate_decision
from trips.locks import is_trip_profile_locked
from trips.media import validate_trip_media_upload
from trips.models import (
    Trip,
    TripItineraryDay,
    TripMediaAsset,
    TripMediaItem,
    TripPackage,
    TripPaymentSchedule,
)
from trips.rich_text import (
    is_trip_rich_text_empty,
    sanitize_trip_rich_text,
    trip_rich_text_plain_text,
)


class TripProfileCoreSerializer(serializers.ModelSerializer):
    description_plain_text = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id",
            "organizer",
            "title",
            "slug",
            "start_date",
            "end_date",
            "capacity",
            "description_rich_text",
            "description_plain_text",
            "publication_state",
            "booking_availability",
            "manual_payment_availability",
            "public_url_path",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organizer",
            "slug",
            "description_plain_text",
            "public_url_path",
            "created_at",
            "updated_at",
        ]

    def validate_description_rich_text(self, value):
        try:
            return sanitize_trip_rich_text(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "Trip end date cannot be before Trip Start Date."}
            )
        return attrs

    def create(self, validated_data):
        return Trip.objects.create(
            organizer=self.context["organizer"],
            **validated_data,
        )

    def get_description_plain_text(self, trip: Trip) -> str:
        return trip_rich_text_plain_text(trip.description_rich_text)


class TripDescriptionSerializer(serializers.ModelSerializer):
    description_plain_text = serializers.SerializerMethodField()
    trip_profile_locked = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id",
            "description_rich_text",
            "description_plain_text",
            "trip_profile_locked",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "description_plain_text",
            "trip_profile_locked",
            "updated_at",
        ]

    def validate_description_rich_text(self, value):
        try:
            return sanitize_trip_rich_text(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def get_description_plain_text(self, trip: Trip) -> str:
        return trip_rich_text_plain_text(trip.description_rich_text)

    def get_trip_profile_locked(self, trip: Trip) -> bool:
        return is_trip_profile_locked(trip)


class TripPackageSerializer(serializers.ModelSerializer):
    lifecycle_state_label = serializers.CharField(
        source="get_lifecycle_state_display",
        read_only=True,
    )
    is_withdrawn = serializers.BooleanField(read_only=True)

    class Meta:
        model = TripPackage
        fields = [
            "id",
            "name",
            "description",
            "price_inr",
            "reservation_amount_inr",
            "position",
            "lifecycle_state",
            "lifecycle_state_label",
            "is_withdrawn",
        ]
        read_only_fields = [
            "id",
            "lifecycle_state",
            "lifecycle_state_label",
            "is_withdrawn",
        ]

    def validate(self, attrs):
        price = attrs.get("price_inr", getattr(self.instance, "price_inr", None))
        reservation_amount = attrs.get(
            "reservation_amount_inr",
            getattr(self.instance, "reservation_amount_inr", None),
        )
        if price is not None and reservation_amount is not None and reservation_amount > price:
            raise serializers.ValidationError(
                {"reservation_amount_inr": "Reservation Amount cannot exceed Package price."}
            )
        return attrs


class TripPackageSectionRowSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(max_length=140, allow_blank=True)
    description = serializers.CharField(allow_blank=True, required=False)
    price_inr = serializers.IntegerField(min_value=1)
    reservation_amount_inr = serializers.IntegerField(min_value=1)
    position = serializers.IntegerField(required=False, min_value=1)

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Package name is required.")
        return name

    def validate_description(self, value: str) -> str:
        return value.strip()

    def validate(self, attrs):
        price = attrs.get("price_inr")
        reservation_amount = attrs.get("reservation_amount_inr")
        if (
            price is not None
            and reservation_amount is not None
            and reservation_amount > price
        ):
            raise serializers.ValidationError(
                {"reservation_amount_inr": "Reservation Amount cannot exceed Package price."}
            )
        return attrs


class TripPackageSectionSerializer(serializers.Serializer):
    packages = TripPackageSectionRowSerializer(many=True, allow_empty=True)
    trip_profile_locked = serializers.SerializerMethodField()
    readiness = serializers.SerializerMethodField()

    def to_representation(self, instance) -> dict[str, object]:
        trip = self.context.get("trip", instance if isinstance(instance, Trip) else None)
        packages = (
            trip.packages.active().order_by("position", "id")
            if trip is not None
            else []
        )
        return {
            "packages": TripPackageSectionRowSerializer(packages, many=True).data,
            "trip_profile_locked": self.get_trip_profile_locked(instance),
            "readiness": self.get_readiness(instance),
        }

    def validate_packages(self, packages: list[dict]) -> list[dict]:
        if not packages:
            raise serializers.ValidationError("Every Trip needs at least one Package.")

        trip: Trip | None = self.context.get("trip")
        existing_package_ids = (
            set(trip.packages.active().values_list("id", flat=True))
            if trip is not None
            else set()
        )
        submitted_ids: set[int] = set()
        for package in packages:
            package_id = package.get("id")
            if package_id is None:
                continue
            if package_id in submitted_ids:
                raise serializers.ValidationError("Package rows must be unique.")
            if package_id not in existing_package_ids:
                raise serializers.ValidationError(
                    f"Package {package_id} does not belong to this Trip."
                )
            submitted_ids.add(package_id)

        return packages

    def save(self, **kwargs):
        trip: Trip = self.context["trip"]
        submitted_packages = self.validated_data["packages"]

        with transaction.atomic():
            existing_packages = {
                package.id: package
                for package in TripPackage.objects.select_for_update()
                .active()
                .filter(trip=trip)
            }
            submitted_package_ids = {
                package["id"] for package in submitted_packages if package.get("id") is not None
            }
            package_ids_to_remove = set(existing_packages) - submitted_package_ids
            package_ids_to_withdraw = set(
                TripPackage.objects.filter(
                    id__in=package_ids_to_remove,
                    traveler_slots__isnull=False,
                    lifecycle_state=TripPackage.LifecycleState.ACTIVE,
                )
                .distinct()
                .values_list("id", flat=True)
            )
            package_ids_to_delete = package_ids_to_remove - package_ids_to_withdraw

            if package_ids_to_withdraw:
                TripPackage.objects.filter(id__in=package_ids_to_withdraw).update(
                    lifecycle_state=TripPackage.LifecycleState.WITHDRAWN,
                    updated_at=timezone.now(),
                )

            if package_ids_to_delete:
                TripPackage.objects.filter(id__in=package_ids_to_delete).delete()

            for position, package_data in enumerate(submitted_packages, start=1):
                package_id = package_data.get("id")
                defaults = {
                    "name": package_data["name"],
                    "description": package_data.get("description", ""),
                    "price_inr": package_data["price_inr"],
                    "reservation_amount_inr": package_data["reservation_amount_inr"],
                    "position": position,
                }
                if package_id is None:
                    package = TripPackage(trip=trip, **defaults)
                else:
                    package = existing_packages[package_id]
                    for field, value in defaults.items():
                        setattr(package, field, value)
                package.save()

        return trip

    def get_trip_profile_locked(self, value) -> bool:
        trip = self.context.get("trip", value if isinstance(value, Trip) else None)
        return bool(trip and is_trip_profile_locked(trip))

    def get_readiness(self, value) -> dict[str, object]:
        trip = self.context.get("trip", value if isinstance(value, Trip) else None)
        package_count = trip.packages.active().count() if trip is not None else 0
        return {
            "package_ready": package_count > 0,
            "active_package_count": package_count,
            "blockers": [] if package_count else ["At least one active Package is required."],
        }


class TripPaymentScheduleSerializer(serializers.ModelSerializer):
    reservation_milestone = serializers.SerializerMethodField()
    has_balance_milestone = serializers.BooleanField(read_only=True)
    balance_due_date = serializers.DateField(read_only=True)
    reviewed = serializers.BooleanField(source="is_reviewed", read_only=True)

    class Meta:
        model = TripPaymentSchedule
        fields = [
            "reservation_milestone",
            "balance_due_days_before_start",
            "balance_due_date",
            "balance_reminder_lead_days",
            "has_balance_milestone",
            "reviewed",
            "reviewed_at",
        ]
        read_only_fields = ["reviewed", "reviewed_at"]

    def get_reservation_milestone(self, schedule: TripPaymentSchedule) -> dict[str, str]:
        return {
            "type": "reservation",
            "due": "immediate",
            "amount_source": "package_reservation_amounts",
        }


class TripPaymentScheduleSectionSerializer(serializers.ModelSerializer):
    reservation_milestone = serializers.SerializerMethodField()
    has_balance_milestone = serializers.BooleanField(required=False)
    balance_due_date = serializers.DateField(read_only=True)
    reviewed = serializers.BooleanField(source="is_reviewed", read_only=True)
    trip_profile_locked = serializers.SerializerMethodField()
    readiness = serializers.SerializerMethodField()

    class Meta:
        model = TripPaymentSchedule
        fields = [
            "reservation_milestone",
            "has_balance_milestone",
            "balance_due_days_before_start",
            "balance_due_date",
            "balance_reminder_lead_days",
            "reviewed",
            "reviewed_at",
            "trip_profile_locked",
            "readiness",
        ]
        read_only_fields = [
            "reservation_milestone",
            "balance_due_date",
            "reviewed",
            "reviewed_at",
            "trip_profile_locked",
            "readiness",
        ]
        extra_kwargs = {
            "balance_due_days_before_start": {"required": False, "allow_null": True},
            "balance_reminder_lead_days": {"required": False, "min_value": 0},
        }

    def get_reservation_milestone(self, schedule: TripPaymentSchedule) -> dict[str, str]:
        return {
            "type": "reservation",
            "due": "immediate",
            "amount_source": "package_reservation_amounts",
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.instance
        has_balance_milestone = attrs.pop(
            "has_balance_milestone",
            instance.has_balance_milestone if instance is not None else True,
        )
        balance_due_days = attrs.get(
            "balance_due_days_before_start",
            getattr(instance, "balance_due_days_before_start", None),
        )
        reminder_lead_days = attrs.get(
            "balance_reminder_lead_days",
            getattr(instance, "balance_reminder_lead_days", 3),
        )

        if not has_balance_milestone:
            attrs["balance_due_days_before_start"] = None
            return attrs

        if balance_due_days is None:
            raise serializers.ValidationError(
                {
                    "balance_due_days_before_start": (
                        "Enter when the final balance is due, or disable it."
                    )
                }
            )
        if balance_due_days < 1:
            raise serializers.ValidationError(
                {
                    "balance_due_days_before_start": (
                        "Final balance due days must be greater than 0."
                    )
                }
            )
        if reminder_lead_days is not None and reminder_lead_days > balance_due_days:
            raise serializers.ValidationError(
                {
                    "balance_reminder_lead_days": (
                        "Reminder lead time cannot exceed final balance due days."
                    )
                }
            )
        return attrs

    def update(self, instance: TripPaymentSchedule, validated_data):
        actor = self.context.get("actor")
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.reviewed_at = timezone.now()
        if actor is not None and getattr(actor, "is_authenticated", False):
            instance.reviewed_by = actor
        instance.save()
        return instance

    def get_trip_profile_locked(self, schedule: TripPaymentSchedule) -> bool:
        return is_trip_profile_locked(schedule.trip)

    def get_readiness(self, schedule: TripPaymentSchedule) -> dict[str, object]:
        return {
            "payment_schedule_reviewed": schedule.is_reviewed,
            "blockers": (
                []
                if schedule.is_reviewed
                else ["Owner review of balance payment schedule is required."]
            ),
        }


class TripConfirmationRequirementsSectionSerializer(serializers.ModelSerializer):
    reviewed = serializers.BooleanField(
        source="confirmation_requirements_reviewed",
        read_only=True,
    )
    reviewed_at = serializers.DateTimeField(
        source="confirmation_requirements_reviewed_at",
        read_only=True,
    )
    trip_profile_locked = serializers.SerializerMethodField()
    readiness = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "confirmation_requirements_note",
            "requires_traveler_documents",
            "requires_traveler_identity_details",
            "requires_travel_logistics",
            "requires_emergency_contact",
            "requires_medical_disclosure",
            "requires_full_payment_before_confirmation",
            "reviewed",
            "reviewed_at",
            "trip_profile_locked",
            "readiness",
        ]
        read_only_fields = [
            "reviewed",
            "reviewed_at",
            "trip_profile_locked",
            "readiness",
        ]
        extra_kwargs = {
            "confirmation_requirements_note": {
                "required": False,
                "allow_blank": True,
            },
            "requires_traveler_documents": {"required": False},
            "requires_traveler_identity_details": {"required": False},
            "requires_travel_logistics": {"required": False},
            "requires_emergency_contact": {"required": False},
            "requires_medical_disclosure": {"required": False},
            "requires_full_payment_before_confirmation": {"required": False},
        }

    def validate_confirmation_requirements_note(self, value: str) -> str:
        return value.strip()

    def update(self, instance: Trip, validated_data):
        actor = self.context.get("actor")
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.confirmation_requirements_reviewed_at = timezone.now()
        if actor is not None and getattr(actor, "is_authenticated", False):
            instance.confirmation_requirements_reviewed_by = actor
        instance.save()
        return instance

    def get_trip_profile_locked(self, trip: Trip) -> bool:
        return is_trip_profile_locked(trip)

    def get_readiness(self, trip: Trip) -> dict[str, object]:
        active_requirements = [
            code
            for code, enabled in [
                ("traveler_documents", trip.requires_traveler_documents),
                ("traveler_identity_details", trip.requires_traveler_identity_details),
                ("travel_logistics", trip.requires_travel_logistics),
                ("emergency_contact", trip.requires_emergency_contact),
                ("medical_disclosure", trip.requires_medical_disclosure),
                ("full_payment", trip.requires_full_payment_before_confirmation),
            ]
            if enabled
        ]
        return {
            "confirmation_requirements_reviewed": (
                trip.confirmation_requirements_reviewed
            ),
            "active_requirements": active_requirements,
            "blockers": (
                []
                if trip.confirmation_requirements_reviewed
                else ["Review Confirmation Requirements before publication."]
            ),
        }


class TripItineraryDaySerializer(serializers.ModelSerializer):
    description_plain_text = serializers.SerializerMethodField()
    title = serializers.CharField(max_length=140, allow_blank=True)

    class Meta:
        model = TripItineraryDay
        fields = [
            "id",
            "sequence",
            "title",
            "date_label",
            "description_rich_text",
            "description_plain_text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "description_plain_text", "created_at", "updated_at"]

    def validate_title(self, value: str) -> str:
        title = value.strip()
        if not title:
            raise serializers.ValidationError("Itinerary Day title is required.")
        return title

    def validate_date_label(self, value: str) -> str:
        return value.strip()

    def validate_description_rich_text(self, value):
        try:
            sanitized = sanitize_trip_rich_text(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        if is_trip_rich_text_empty(sanitized):
            raise serializers.ValidationError("Itinerary Day description is required.")
        return sanitized

    def get_description_plain_text(self, day: TripItineraryDay) -> str:
        return trip_rich_text_plain_text(day.description_rich_text)


class TripItinerarySectionSerializer(serializers.Serializer):
    itinerary_days = TripItineraryDaySerializer(many=True, allow_empty=True)
    trip_profile_locked = serializers.SerializerMethodField()

    def validate_itinerary_days(self, days: list[dict]) -> list[dict]:
        sequences = [day["sequence"] for day in days]
        if len(sequences) != len(set(sequences)):
            raise serializers.ValidationError("Itinerary Day sequences must be unique.")
        return sorted(days, key=lambda day: day["sequence"])

    def save(self, **kwargs):
        trip: Trip = self.context["trip"]
        days = self.validated_data["itinerary_days"]
        with transaction.atomic():
            trip.itinerary_days.all().delete()
            created_days = [
                TripItineraryDay(
                    trip=trip,
                    sequence=day["sequence"],
                    title=day["title"],
                    date_label=day.get("date_label", ""),
                    description_rich_text=day["description_rich_text"],
                )
                for day in days
            ]
            for day in created_days:
                day.save()
        return trip

    def get_trip_profile_locked(self, value) -> bool:
        trip = self.context.get("trip", value if isinstance(value, Trip) else None)
        return bool(trip and is_trip_profile_locked(trip))


class TripMediaItemSerializer(serializers.ModelSerializer):
    asset_id = serializers.IntegerField(source="asset.id", read_only=True)
    image_url = serializers.SerializerMethodField()
    original_filename = serializers.CharField(source="asset.original_filename", read_only=True)
    content_type = serializers.CharField(source="asset.content_type", read_only=True)
    file_size = serializers.IntegerField(source="asset.file_size", read_only=True)

    class Meta:
        model = TripMediaItem
        fields = [
            "id",
            "asset_id",
            "image_url",
            "original_filename",
            "content_type",
            "file_size",
            "position",
            "caption",
            "alt_text",
            "is_public",
            "is_cover",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "asset_id",
            "image_url",
            "original_filename",
            "content_type",
            "file_size",
            "created_at",
            "updated_at",
        ]

    def get_image_url(self, item: TripMediaItem) -> str:
        image_url = item.asset.image_url
        request = self.context.get("request")
        if request is not None and image_url.startswith("/"):
            return request.build_absolute_uri(image_url)
        return image_url


class TripMediaGalleryRowSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    position = serializers.IntegerField(required=False, min_value=1)
    caption = serializers.CharField(max_length=220, allow_blank=True, required=False)
    alt_text = serializers.CharField(max_length=220, allow_blank=True, required=False)
    is_public = serializers.BooleanField(required=False, default=False)
    is_cover = serializers.BooleanField(required=False, default=False)


class TripMediaGallerySerializer(serializers.Serializer):
    media_items = TripMediaGalleryRowSerializer(many=True, allow_empty=True)
    trip_profile_locked = serializers.SerializerMethodField()
    readiness = serializers.SerializerMethodField()

    def to_representation(self, instance) -> dict[str, object]:
        trip = self.context.get("trip", instance if isinstance(instance, Trip) else None)
        items = (
            trip.media_items.select_related("asset").order_by("position", "id")
            if trip is not None
            else []
        )
        return {
            "media_items": TripMediaItemSerializer(
                items,
                many=True,
                context=self.context,
            ).data,
            "trip_profile_locked": self.get_trip_profile_locked(instance),
            "readiness": self.get_readiness(instance),
        }

    def validate_media_items(self, items: list[dict]) -> list[dict]:
        trip: Trip | None = self.context.get("trip")
        existing_item_ids = (
            set(trip.media_items.values_list("id", flat=True)) if trip is not None else set()
        )
        submitted_ids: set[int] = set()
        cover_count = 0

        for index, item in enumerate(items, start=1):
            item_id = item.get("id")
            if item_id is None:
                raise serializers.ValidationError("Trip Media Item id is required.")
            if item_id in submitted_ids:
                raise serializers.ValidationError("Trip Media Item rows must be unique.")
            if item_id not in existing_item_ids:
                raise serializers.ValidationError(
                    f"Trip Media Item {item_id} does not belong to this Trip."
                )
            submitted_ids.add(item_id)
            item["position"] = index
            item["caption"] = item.get("caption", "").strip()
            item["alt_text"] = item.get("alt_text", "").strip()
            if item.get("is_cover"):
                cover_count += 1

        if cover_count > 1:
            raise serializers.ValidationError("A Trip can have only one cover image.")
        if items and cover_count == 0:
            raise serializers.ValidationError("Select one Trip Media cover image.")
        return items

    def save(self, **kwargs):
        trip: Trip = self.context["trip"]
        items = self.validated_data["media_items"]
        with transaction.atomic():
            existing_items = {
                item.id: item
                for item in TripMediaItem.objects.select_for_update()
                .filter(trip=trip)
                .select_related("asset")
            }
            cover_item_id = next(
                (item["id"] for item in items if item.get("is_cover")),
                None,
            )
            if cover_item_id is not None:
                TripMediaItem.objects.filter(trip=trip, is_cover=True).exclude(
                    id=cover_item_id
                ).update(is_cover=False, updated_at=timezone.now())

            submitted_ids = {item["id"] for item in items}
            TripMediaItem.objects.filter(trip=trip).exclude(id__in=submitted_ids).delete()

            for position, item_data in enumerate(items, start=1):
                item = existing_items[item_data["id"]]
                item.position = position
                item.caption = item_data.get("caption", "")
                item.alt_text = item_data.get("alt_text", "")
                item.is_public = item_data.get("is_public", False)
                item.is_cover = item_data.get("is_cover", False)
                item.save()
        return trip

    def get_trip_profile_locked(self, value) -> bool:
        trip = self.context.get("trip", value if isinstance(value, Trip) else None)
        return bool(trip and is_trip_profile_locked(trip))

    def get_readiness(self, value) -> dict[str, object]:
        trip = self.context.get("trip", value if isinstance(value, Trip) else None)
        public_media_count = (
            trip.media_items.filter(is_public=True).count() if trip is not None else 0
        )
        total_media_count = trip.media_items.count() if trip is not None else 0
        return {
            "public_media_count": public_media_count,
            "total_media_count": total_media_count,
            "encouraged": (
                [] if public_media_count else ["Add at least one public Trip Media Item."]
            ),
            "blockers": [],
        }


class TripMediaUploadSerializer(serializers.Serializer):
    images = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False),
        allow_empty=False,
        max_length=12,
    )

    def validate_images(self, images):
        for image in images:
            try:
                validate_trip_media_upload(image)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.messages) from exc
        return images

    def save(self, **kwargs):
        trip: Trip = self.context["trip"]
        actor = self.context.get("actor")
        images = self.validated_data["images"]
        with transaction.atomic():
            next_position = (
                trip.media_items.select_for_update()
                .aggregate(max_position=models.Max("position"))
                .get("max_position")
                or 0
            ) + 1
            has_cover = trip.media_items.filter(is_cover=True).exists()
            created_items = []
            for index, image in enumerate(images):
                asset = TripMediaAsset.objects.create(
                    organizer=trip.organizer,
                    uploaded_for_trip=trip,
                    image=image,
                    original_filename=getattr(image, "name", "")[:240],
                    content_type=getattr(image, "content_type", "")[:120],
                    file_size=getattr(image, "size", 0) or 0,
                    uploaded_by=actor if getattr(actor, "is_authenticated", False) else None,
                )
                item = TripMediaItem(
                    trip=trip,
                    asset=asset,
                    position=next_position + index,
                    is_public=True,
                    is_cover=(not has_cover and index == 0),
                )
                item.save()
                created_items.append(item)
        return created_items


class PublicBookingGateSerializerMixin:
    def public_booking_gate_decision(self, trip: Trip):
        cache = getattr(self, "_public_booking_gate_cache", None)
        if cache is None:
            cache = {}
            self._public_booking_gate_cache = cache
        if trip.pk not in cache:
            cache[trip.pk] = public_booking_gate_decision(trip)
        return cache[trip.pk]


class PublicTripSerializer(PublicBookingGateSerializerMixin, serializers.ModelSerializer):
    organizer_identity = serializers.SerializerMethodField()
    itinerary_days = TripItineraryDaySerializer(many=True, read_only=True)
    media_items = serializers.SerializerMethodField()
    packages = serializers.SerializerMethodField()
    payment_schedule = TripPaymentScheduleSerializer(read_only=True)
    publication_state_label = serializers.CharField(
        source="get_publication_state_display",
        read_only=True,
    )
    booking_availability_label = serializers.CharField(
        source="get_booking_availability_display",
        read_only=True,
    )
    effective_booking_availability = serializers.SerializerMethodField()
    availability_band = serializers.SerializerMethodField()
    availability_band_label = serializers.SerializerMethodField()
    public_booking_gate = serializers.SerializerMethodField()
    manual_payment_instructions = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id",
            "title",
            "slug",
            "start_date",
            "end_date",
            "confirmation_requirements_note",
            "requires_traveler_documents",
            "requires_traveler_identity_details",
            "requires_travel_logistics",
            "requires_emergency_contact",
            "requires_medical_disclosure",
            "requires_full_payment_before_confirmation",
            "description_rich_text",
            "itinerary",
            "itinerary_days",
            "media_items",
            "publication_state",
            "publication_state_label",
            "booking_availability",
            "booking_availability_label",
            "effective_booking_availability",
            "public_url_path",
            "organizer_identity",
            "packages",
            "payment_schedule",
            "availability_band",
            "availability_band_label",
            "public_booking_gate",
            "manual_payment_instructions",
            "updated_at",
        ]

    def get_organizer_identity(self, trip: Trip) -> dict:
        return organizer_profile_identity_payload(
            trip.organizer,
            request=self.context.get("request"),
        )

    def get_packages(self, trip: Trip) -> list[dict]:
        return TripPackageSerializer(
            trip.packages.active().order_by("position", "id"),
            many=True,
        ).data

    def get_media_items(self, trip: Trip) -> list[dict]:
        return TripMediaItemSerializer(
            trip.media_items.filter(is_public=True).select_related("asset").order_by(
                "position", "id"
            ),
            many=True,
            context=self.context,
        ).data

    def get_effective_booking_availability(self, trip: Trip) -> str:
        return self.public_booking_gate_decision(trip).effective_booking_availability

    def get_availability_band(self, trip: Trip) -> str:
        return self.public_booking_gate_decision(trip).availability_band

    def get_availability_band_label(self, trip: Trip) -> str:
        return self.public_booking_gate_decision(trip).availability_band_label

    def get_public_booking_gate(self, trip: Trip) -> dict[str, bool | int | str]:
        return self.public_booking_gate_decision(trip).to_payload()

    def get_manual_payment_instructions(
        self,
        trip: Trip,
    ) -> dict[str, bool | int | str] | None:
        gate = self.public_booking_gate_decision(trip)
        if not gate.ready or not gate.payment_method_readiness.manual_method.ready:
            return None

        instructions = manual_payment_instructions_payload(
            trip.organizer,
            request=self.context.get("request"),
            can_manage=False,
        )
        if not instructions["ready"]:
            return None

        return {
            "ready": True,
            "message": (
                "Scan the Payment QR and submit Payment Proof for Organizer review."
            ),
            "payment_qr_url": instructions["payment_qr_url"],
            "upi_id": instructions["upi_id"],
            "account_name": instructions["account_name"],
            "bank_transfer_details": instructions["bank_transfer_details"],
        }
