"""Compatibility import path for legacy Public Booking payment method callers.

New code should import payment method readiness helpers from
``trips.payment_method_readiness``.
"""

from trips.payment_method_readiness import *  # noqa: F403
