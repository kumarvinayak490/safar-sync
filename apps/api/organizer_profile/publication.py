from __future__ import annotations

from dataclasses import dataclass

from organizer_policies.readiness import (
    OrganizerPoliciesReadiness,
    required_organizer_profile_policy_readiness,
)
from organizer_profile.models import OrganizerProfile
from organizers.models import Organizer


@dataclass(frozen=True)
class OrganizerProfileReadiness:
    public_description_ready: bool
    policy_readiness: OrganizerPoliciesReadiness
    public_media_count: int

    @property
    def publish_eligible(self) -> bool:
        return self.public_description_ready and self.policy_readiness.ready

    @property
    def blockers(self) -> tuple[str, ...]:
        blockers = []
        if not self.public_description_ready:
            blockers.append("Add Public Organizer Description.")
        blockers.extend(self.policy_readiness.blockers)
        return tuple(blockers)

    @property
    def encouraged(self) -> tuple[str, ...]:
        if self.public_media_count > 0:
            return ()
        return ("Add at least one Public Organizer Media item.",)

    def to_payload(self) -> dict:
        return {
            "publish_eligible": self.publish_eligible,
            "public_description_ready": self.public_description_ready,
            "organizer_policies_ready": self.policy_readiness.ready,
            "privacy_policy_ready": self.policy_readiness.privacy_policy_ready,
            "refund_policy_ready": self.policy_readiness.refund_policy_ready,
            "cancellation_policy_ready": self.policy_readiness.cancellation_policy_ready,
            "missing_required_policies": list(
                self.policy_readiness.missing_required_policies
            ),
            "public_media_count": self.public_media_count,
            "blockers": list(self.blockers),
            "encouraged": list(self.encouraged),
        }


def organizer_profile_for(
    organizer: Organizer,
    *,
    create: bool = False,
) -> OrganizerProfile | None:
    try:
        return organizer.organizer_profile
    except OrganizerProfile.DoesNotExist:
        if create:
            return OrganizerProfile.objects.create(organizer=organizer)
        return None


def organizer_profile_publication_state(organizer: Organizer) -> str:
    profile = organizer_profile_for(organizer)
    if profile is None:
        return OrganizerProfile.PublicationState.DRAFT
    return profile.publication_state


def organizer_profile_public_description(organizer: Organizer) -> str:
    profile = organizer_profile_for(organizer)
    if profile is None:
        return ""
    return profile.public_description


def organizer_profile_publication_readiness(
    organizer: Organizer,
    *,
    profile: OrganizerProfile | None = None,
) -> OrganizerProfileReadiness:
    profile_record = profile if profile is not None else organizer_profile_for(organizer)
    return OrganizerProfileReadiness(
        public_description_ready=bool(
            profile_record and profile_record.public_description.strip()
        ),
        policy_readiness=required_organizer_profile_policy_readiness(organizer),
        public_media_count=_public_media_count(organizer),
    )


def _public_media_count(organizer: Organizer) -> int:
    from organizer_media.selectors import public_organizer_media_queryset

    return public_organizer_media_queryset(organizer).count()
