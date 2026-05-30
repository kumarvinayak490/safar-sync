from __future__ import annotations

from creative_setup.models import CreativeSetup
from organizers.models import Organizer


def creative_setup_for(organizer: Organizer, *, create: bool = False) -> CreativeSetup | None:
    if create:
        setup, _created = CreativeSetup.objects.get_or_create(organizer=organizer)
        return setup
    return CreativeSetup.objects.filter(organizer=organizer).first()
