"""Compatibility import path for legacy Booking lifecycle intake callers.

New code should import Booking intake helpers from ``trip_bookings.intake``.
"""

from trip_bookings.intake import *  # noqa: F403
