"""Compatibility imports for legacy Organizer Settings identity callers.

Organizer Profile owns public organizer identity behavior. Keep this module as
a thin re-export while callers move to ``organizer_profile.identity``.
"""

from organizer_profile.identity import *  # noqa: F403
