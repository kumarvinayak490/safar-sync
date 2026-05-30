"""Compatibility import path for legacy Booking lifecycle callers.

New code should import booking workflow helpers from ``trip_bookings.operations``.
"""

from trip_bookings.operations import *  # noqa: F403
from trip_bookings.operations import (  # noqa: F401
    BookingOperationsWorkflow,
)
