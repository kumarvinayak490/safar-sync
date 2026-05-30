from __future__ import annotations

from rest_framework import serializers

from creative_setup.models import CreativeSetup


class CreativeSetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreativeSetup
        fields = [
            "model_choice",
            "brand_tone",
            "default_style",
            "logo_usage",
            "poster_defaults",
        ]

    def validate_brand_tone(self, value: str) -> str:
        return value.strip()

    def validate_default_style(self, value: str) -> str:
        return value.strip()

    def validate_poster_defaults(self, value: dict) -> dict:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Poster defaults must be an object.")
        return value
