"""Compatibility import path for legacy Connected Provider Account readiness callers.

New code should import readiness mutation helpers from
``organizer_payments.provider_account_readiness``.
"""

from organizer_payments.provider_account_readiness import *  # noqa: F403
