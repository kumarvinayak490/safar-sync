"""Compatibility import path for legacy Trip Profile lock callers.

New code should import Trip Profile lock helpers from ``trips.locks``.
"""

from trips.locks import *  # noqa: F403
