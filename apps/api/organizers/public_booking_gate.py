"""Compatibility import path for legacy Public Booking Gate callers.

New code should import Public Booking Gate helpers from
``trips.booking_availability``.
"""

from trips.booking_availability import *  # noqa: F403
