"""Compatibility import path for legacy Provider Webhook callers.

New code should import Provider Webhook helpers from ``trip_payments.provider_webhooks``.
"""

from trip_payments.provider_webhooks import *  # noqa: F403
