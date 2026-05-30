from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from organizer_profile.identity import (
    organizer_profile_fallback,
    organizer_profile_identity_payload,
    public_organizer_name,
    validate_organizer_logo_upload,
)
from organizer_profile.models import OrganizerProfile
from organizer_profile.publication import (
    organizer_profile_for,
    organizer_profile_public_description,
    organizer_profile_publication_readiness,
    organizer_profile_publication_state,
)
from organizers.models import Organizer


class OrganizerProfileIdentitySerializer(serializers.ModelSerializer):
    public_description = serializers.CharField(allow_blank=True, required=False)
    publication_state = serializers.ChoiceField(
        choices=OrganizerProfile.PublicationState.choices,
        required=False,
    )
    publication_state_label = serializers.SerializerMethodField()
    organizer_profile_readiness = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()
    logo_uploaded = serializers.SerializerMethodField()
    media_items = serializers.SerializerMethodField()
    fallback = serializers.SerializerMethodField()
    placeholder = serializers.SerializerMethodField()
    identity_logo = serializers.FileField(required=False, write_only=True)
    remove_identity_logo = serializers.BooleanField(
        default=False,
        required=False,
        write_only=True,
    )

    class Meta:
        model = Organizer
        fields = [
            "identity_name",
            "identity_whatsapp_number",
            "public_description",
            "publication_state",
            "publication_state_label",
            "organizer_profile_readiness",
            "name",
            "logo_url",
            "logo_uploaded",
            "media_items",
            "fallback",
            "placeholder",
            "identity_logo",
            "remove_identity_logo",
        ]
        read_only_fields = [
            "name",
            "logo_url",
            "logo_uploaded",
            "publication_state_label",
            "organizer_profile_readiness",
            "media_items",
            "fallback",
            "placeholder",
        ]

    def validate_identity_name(self, value: str) -> str:
        identity_name = value.strip()
        if not identity_name:
            raise serializers.ValidationError("Enter the traveler-facing Organizer Identity name.")
        return identity_name

    def validate_identity_whatsapp_number(self, value: str) -> str:
        return value.strip()

    def validate_identity_logo(self, value):
        try:
            validate_organizer_logo_upload(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.get("identity_logo") and attrs.get("remove_identity_logo"):
            raise serializers.ValidationError(
                {"identity_logo": "Upload or remove the Organizer Logo, not both."}
            )
        if attrs.get("publication_state") == OrganizerProfile.PublicationState.PUBLISHED:
            role = self.context.get("role")
            if role is not None and not role.can_publish_organizer_profile:
                raise serializers.ValidationError(
                    {"publication_state": "Only Owners can publish Organizer Profile."}
                )

            readiness_profile = self._profile_for_validation(attrs)
            readiness = organizer_profile_publication_readiness(
                self.instance,
                profile=readiness_profile,
            )
            if not readiness.publish_eligible:
                raise serializers.ValidationError(
                    {
                        "publication_state": (
                            "Organizer Profile is not ready to publish."
                        ),
                        "organizer_profile_readiness": readiness.to_payload(),
                    }
                )
        return attrs

    def update(self, instance: Organizer, validated_data):
        identity_logo = validated_data.pop("identity_logo", None)
        remove_identity_logo = validated_data.pop("remove_identity_logo", False)
        public_description = validated_data.pop("public_description", None)
        publication_state = validated_data.pop("publication_state", None)
        old_logo_name = instance.identity_logo.name if instance.identity_logo else ""

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if remove_identity_logo:
            instance.identity_logo = ""
        elif identity_logo is not None:
            instance.identity_logo = identity_logo

        instance.save()
        if public_description is not None or publication_state is not None:
            profile = organizer_profile_for(instance, create=True)
            if public_description is not None:
                profile.public_description = public_description
            if publication_state is not None:
                profile.publication_state = publication_state
            profile.save()

        if old_logo_name and (remove_identity_logo or identity_logo is not None):
            if old_logo_name != (instance.identity_logo.name if instance.identity_logo else ""):
                instance.identity_logo.storage.delete(old_logo_name)

        return instance

    def to_representation(self, instance: Organizer) -> dict:
        data = super().to_representation(instance)
        data["public_description"] = organizer_profile_public_description(instance)
        data["publication_state"] = organizer_profile_publication_state(instance)
        return data

    def get_name(self, organizer: Organizer) -> str:
        return public_organizer_name(organizer)

    def get_publication_state_label(self, organizer: Organizer) -> str:
        state = organizer_profile_publication_state(organizer)
        return OrganizerProfile.PublicationState(state).label

    def get_organizer_profile_readiness(self, organizer: Organizer) -> dict:
        return organizer_profile_publication_readiness(organizer).to_payload()

    def get_logo_url(self, organizer: Organizer) -> str:
        payload = organizer_profile_identity_payload(
            organizer,
            request=self.context.get("request"),
        )
        return payload["logo_url"]

    def get_logo_uploaded(self, organizer: Organizer) -> bool:
        return bool(organizer.identity_logo)

    def get_media_items(self, organizer: Organizer) -> list[dict]:
        from organizer_media.selectors import public_organizer_media_payload

        return public_organizer_media_payload(
            organizer,
            request=self.context.get("request"),
        )

    def get_fallback(self, organizer: Organizer) -> dict[str, str]:
        return organizer_profile_fallback(public_organizer_name(organizer)).to_payload()

    def get_placeholder(self, organizer: Organizer) -> bool:
        return not bool(organizer.identity_name)

    def _profile_for_validation(self, attrs) -> OrganizerProfile:
        profile = organizer_profile_for(self.instance) or OrganizerProfile(
            organizer=self.instance
        )
        if "public_description" in attrs:
            profile.public_description = attrs["public_description"]
        return profile


OrganizerIdentitySerializer = OrganizerProfileIdentitySerializer
