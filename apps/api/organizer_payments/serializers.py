from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from organizer_payments.manual_payment_instructions import (
    manual_payment_instructions_payload,
    validate_payment_qr_upload,
)
from organizer_payments.models import ManualPaymentInstructions


class ManualPaymentInstructionsSerializer(serializers.ModelSerializer):
    payment_qr = serializers.FileField(required=False, write_only=True)
    remove_payment_qr = serializers.BooleanField(default=False, required=False, write_only=True)
    ready = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    blocker_code = serializers.SerializerMethodField()
    blocker_label = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    payment_qr_url = serializers.SerializerMethodField()
    payment_qr_uploaded = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = ManualPaymentInstructions
        fields = [
            "ready",
            "status_label",
            "blocker_code",
            "blocker_label",
            "message",
            "payment_qr",
            "remove_payment_qr",
            "payment_qr_url",
            "payment_qr_uploaded",
            "original_filename",
            "content_type",
            "file_size",
            "upi_id",
            "account_name",
            "bank_transfer_details",
            "can_manage",
            "updated_at",
        ]
        read_only_fields = [
            "ready",
            "status_label",
            "blocker_code",
            "blocker_label",
            "message",
            "payment_qr_url",
            "payment_qr_uploaded",
            "original_filename",
            "content_type",
            "file_size",
            "can_manage",
            "updated_at",
        ]

    def validate_payment_qr(self, value):
        try:
            validate_payment_qr_upload(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    def validate_upi_id(self, value: str) -> str:
        return value.strip()

    def validate_account_name(self, value: str) -> str:
        return value.strip()

    def validate_bank_transfer_details(self, value: str) -> str:
        bank_transfer_details = value.strip()
        if len(bank_transfer_details) > 600:
            raise serializers.ValidationError(
                "Keep bank transfer details to 600 characters or fewer."
            )
        return bank_transfer_details

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.get("payment_qr") and attrs.get("remove_payment_qr"):
            raise serializers.ValidationError(
                {"payment_qr": "Upload or remove the Payment QR, not both."}
            )
        return attrs

    def update(
        self,
        instance: ManualPaymentInstructions,
        validated_data,
    ) -> ManualPaymentInstructions:
        payment_qr = validated_data.pop("payment_qr", None)
        remove_payment_qr = validated_data.pop("remove_payment_qr", False)
        old_payment_qr_name = instance.payment_qr.name if instance.payment_qr else ""

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if remove_payment_qr:
            instance.payment_qr = ""
            instance.original_filename = ""
            instance.content_type = ""
            instance.file_size = 0
        elif payment_qr is not None:
            instance.payment_qr = payment_qr
            instance.original_filename = payment_qr.name[:240]
            instance.content_type = getattr(payment_qr, "content_type", "")[:120]
            instance.file_size = getattr(payment_qr, "size", 0) or 0

        instance.save()

        if old_payment_qr_name and (remove_payment_qr or payment_qr is not None):
            if old_payment_qr_name != (
                instance.payment_qr.name if instance.payment_qr else ""
            ):
                instance.payment_qr.storage.delete(old_payment_qr_name)

        return instance

    def get_ready(self, instructions: ManualPaymentInstructions) -> bool:
        return instructions.is_ready

    def get_status_label(self, instructions: ManualPaymentInstructions) -> str:
        return "Ready" if instructions.is_ready else "Missing Payment QR"

    def get_blocker_code(self, instructions: ManualPaymentInstructions) -> str:
        return "ready" if instructions.is_ready else "payment_qr_missing"

    def get_blocker_label(self, instructions: ManualPaymentInstructions) -> str:
        return "Ready" if instructions.is_ready else "Payment QR missing"

    def get_message(self, instructions: ManualPaymentInstructions) -> str:
        return manual_payment_instructions_payload(
            instructions.organizer,
            request=self.context.get("request"),
        )["message"]

    def get_payment_qr_url(self, instructions: ManualPaymentInstructions) -> str:
        return manual_payment_instructions_payload(
            instructions.organizer,
            request=self.context.get("request"),
        )["payment_qr_url"]

    def get_payment_qr_uploaded(self, instructions: ManualPaymentInstructions) -> bool:
        return bool(instructions.payment_qr)

    def get_can_manage(self, instructions: ManualPaymentInstructions) -> bool:
        return bool(self.context.get("can_manage", False))
