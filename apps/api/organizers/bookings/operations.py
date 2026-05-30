"""Compatibility import path for legacy Booking operations callers.

New code should import booking workflow helpers from ``trip_bookings.operations``.
"""

from trip_bookings.operations import *  # noqa: F403
