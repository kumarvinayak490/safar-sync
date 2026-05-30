from __future__ import annotations

from rest_framework import serializers

from organizer_policies.models import OrganizerPolicies
from organizer_policies.readiness import organizer_policies_readiness


class OrganizerPoliciesSerializer(serializers.ModelSerializer):
    readiness = serializers.SerializerMethodField()

    class Meta:
        model = OrganizerPolicies
        fields = [
            "privacy_policy",
            "refund_policy",
            "cancellation_policy",
            "readiness",
        ]

    def validate_privacy_policy(self, value: str) -> str:
        return value.strip()

    def validate_refund_policy(self, value: str) -> str:
        return value.strip()

    def validate_cancellation_policy(self, value: str) -> str:
        return value.strip()

    def get_readiness(self, policies: OrganizerPolicies) -> dict:
        return organizer_policies_readiness(
            policies.organizer,
            policies=policies,
        ).to_payload()
