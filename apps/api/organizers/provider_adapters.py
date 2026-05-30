"""Compatibility import path for legacy Provider adapter callers.

New code should import checkout/webhook adapter helpers from
``trip_payments.provider_adapters`` and OAuth adapter helpers from
``organizer_payments.provider_adapters``.
"""

from organizer_payments.provider_adapters import *  # noqa: F403
from trip_payments.provider_adapters import *  # noqa: F403
