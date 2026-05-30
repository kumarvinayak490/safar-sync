from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from trip_bookings.imports import (
    BookingImportRowInput,
    BookingImportTravelerSlotInput,
    create_booking_import,
    prepare_booking_import_intake,
)
from trip_bookings.models import BookingImport, BookingImportRow
from trip_payments.models import OpeningPaymentRecord
from trip_travelers.slots import TravelerSlotIntakeInput
from trips.models import TripPackage


def _error_detail_from_django(exc: DjangoValidationError):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return exc.messages


class OperationsBookingImportTravelerSlotSerializer(serializers.Serializer):
    package = serializers.PrimaryKeyRelatedField(queryset=TripPackage.objects.all())
    traveler_full_name = serializers.CharField(required=False, allow_blank=True, default="")
    traveler_phone = serializers.CharField(required=False, allow_blank=True, default="")
    traveler_email = serializers.EmailField(required=False, allow_blank=True, default="")


class OperationsBookingImportSubmitSerializer(serializers.Serializer):
    rows = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    source_filename = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_rows(self, rows: list[dict]) -> list[dict]:
        validated_rows = []
        trip = self.context["trip"]
        for index, row in enumerate(rows, start=1):
            row_serializer = _BookingImportRowSubmitSerializer(
                data=row,
                context={"trip": trip, "row_number": index},
            )
            row_serializer.is_valid(raise_exception=True)
            validated_rows.append(row_serializer.validated_data)
        return validated_rows

    def create(self, validated_data):
        return create_booking_import(
            trip=self.context["trip"],
            rows=[
                BookingImportRowInput(
                    booking_id=row.get("booking_id"),
                    booking_contact_name=row["_booking_intake"].contact.name,
                    booking_contact_phone=row["_booking_intake"].contact.phone,
                    booking_contact_email=row["_booking_intake"].contact.email,
                    traveler_slots=[
                        BookingImportTravelerSlotInput(
                            package_id=slot.package.id,
                            traveler_full_name=slot.traveler_full_name,
                            traveler_phone=slot.traveler_phone,
                            traveler_email=slot.traveler_email,
                        )
                        for slot in row["_booking_intake"].traveler_slots
                    ],
                    opening_payment_amount_inr=row.get("opening_payment_amount_inr", 0),
                    opening_payment_reference=row.get("opening_payment_reference", ""),
                    opening_payment_note=row.get("opening_payment_note", ""),
                )
                for row in validated_data["rows"]
            ],
            actor=self.context.get("actor"),
            source_filename=validated_data.get("source_filename", ""),
        )


class _BookingImportRowSubmitSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField(required=False, min_value=1)
    booking_contact_name = serializers.CharField(allow_blank=False)
    booking_contact_phone = serializers.CharField(allow_blank=False)
    booking_contact_email = serializers.EmailField(required=False, allow_blank=True, default="")
    traveler_slots = OperationsBookingImportTravelerSlotSerializer(many=True, allow_empty=False)
    opening_payment_amount_inr = serializers.IntegerField(required=False, min_value=0, default=0)
    opening_payment_reference = serializers.CharField(required=False, allow_blank=True, default="")
    opening_payment_note = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        trip = self.context["trip"]
        try:
            attrs["_booking_intake"] = prepare_booking_import_intake(
                trip=trip,
                booking_contact_name=attrs.get("booking_contact_name", ""),
                booking_contact_phone=attrs.get("booking_contact_phone", ""),
                booking_contact_email=attrs.get("booking_contact_email", ""),
                traveler_slots=[
                    TravelerSlotIntakeInput(
                        package_id=slot["package"].id,
                        traveler_full_name=slot.get("traveler_full_name", ""),
                        traveler_phone=slot.get("traveler_phone", ""),
                        traveler_email=slot.get("traveler_email", ""),
                    )
                    for slot in attrs.get("traveler_slots", [])
                ],
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(_error_detail_from_django(exc)) from exc
        return attrs


class OpeningPaymentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpeningPaymentRecord
        fields = [
            "id",
            "booking",
            "booking_import",
            "amount_inr",
            "payment_reference",
            "note",
            "recorded_by",
            "occurred_at",
            "created_at",
        ]
        read_only_fields = fields


class BookingImportRowSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = BookingImportRow
        fields = [
            "id",
            "row_number",
            "booking",
            "status",
            "status_label",
            "conflict_code",
            "message",
            "payload",
            "created_at",
        ]
        read_only_fields = fields


class OperationsBookingImportResultSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    rows = BookingImportRowSerializer(many=True, read_only=True)
    opening_payment_records = OpeningPaymentRecordSerializer(many=True, read_only=True)

    class Meta:
        model = BookingImport
        fields = [
            "id",
            "trip",
            "status",
            "status_label",
            "source_filename",
            "created_count",
            "updated_count",
            "skipped_count",
            "conflict_count",
            "rows",
            "opening_payment_records",
            "submitted_by",
            "created_at",
        ]
        read_only_fields = fields
