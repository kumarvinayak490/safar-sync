"""Compatibility import path for legacy Sensitive Provider Credential callers.

New code should import Sensitive Provider Credential helpers from
``organizer_payments.provider_credentials``.
"""

from organizer_payments.provider_credentials import *  # noqa: F403
