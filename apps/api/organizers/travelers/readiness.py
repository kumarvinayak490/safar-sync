"""Compatibility import path for legacy Traveler Readiness callers.

New code should import Traveler Readiness helpers from ``trip_travelers``.
"""

from trip_travelers.documents import *  # noqa: F403
from trip_travelers.readiness import *  # noqa: F403
