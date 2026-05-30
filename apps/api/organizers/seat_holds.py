"""Compatibility import path for legacy Seat Hold callers.

New code should import Seat Hold helpers from ``trip_payments.seat_holds``.
"""

from organizers.payments.seat_holds import *  # noqa: F403
