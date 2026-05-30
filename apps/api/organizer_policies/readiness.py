from __future__ import annotations

from dataclasses import dataclass

from organizer_policies.models import OrganizerPolicies
from organizers.models import Organizer

REQUIRED_POLICY_FIELDS = (
    ("privacy_policy", "Organizer Privacy Policy"),
    ("refund_policy", "Organizer Refund Policy"),
    ("cancellation_policy", "Organizer Cancellation Policy"),
)


@dataclass(frozen=True)
class OrganizerPoliciesReadiness:
    privacy_policy_ready: bool
    refund_policy_ready: bool
    cancellation_policy_ready: bool

    @property
    def ready(self) -> bool:
        return (
            self.privacy_policy_ready
            and self.refund_policy_ready
            and self.cancellation_policy_ready
        )

    @property
    def missing_required_policies(self) -> tuple[str, ...]:
        missing = []
        if not self.privacy_policy_ready:
            missing.append("privacy_policy")
        if not self.refund_policy_ready:
            missing.append("refund_policy")
        if not self.cancellation_policy_ready:
            missing.append("cancellation_policy")
        return tuple(missing)

    @property
    def blockers(self) -> tuple[str, ...]:
        labels_by_field = dict(REQUIRED_POLICY_FIELDS)
        return tuple(
            f"Add {labels_by_field[field]}."
            for field in self.missing_required_policies
        )

    def to_payload(self) -> dict:
        return {
            "organizer_policies_ready": self.ready,
            "privacy_policy_ready": self.privacy_policy_ready,
            "refund_policy_ready": self.refund_policy_ready,
            "cancellation_policy_ready": self.cancellation_policy_ready,
            "missing_required_policies": list(self.missing_required_policies),
            "blockers": list(self.blockers),
        }


def organizer_policies_for(
    organizer: Organizer,
    *,
    create: bool = False,
) -> OrganizerPolicies | None:
    try:
        return organizer.organizer_policies
    except OrganizerPolicies.DoesNotExist:
        if create:
            return OrganizerPolicies.objects.create(organizer=organizer)
        return None


def organizer_policies_readiness(
    organizer: Organizer,
    *,
    policies: OrganizerPolicies | None = None,
) -> OrganizerPoliciesReadiness:
    policy_record = policies if policies is not None else organizer_policies_for(organizer)

    return OrganizerPoliciesReadiness(
        privacy_policy_ready=_policy_has_text(policy_record, "privacy_policy"),
        refund_policy_ready=_policy_has_text(policy_record, "refund_policy"),
        cancellation_policy_ready=_policy_has_text(policy_record, "cancellation_policy"),
    )


def required_organizer_profile_policy_readiness(organizer: Organizer) -> OrganizerPoliciesReadiness:
    return organizer_policies_readiness(organizer)


def _policy_has_text(policies: OrganizerPolicies | None, field_name: str) -> bool:
    if policies is None:
        return False
    return bool(getattr(policies, field_name).strip())
