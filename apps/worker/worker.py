from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
API_DIR = ROOT_DIR / "apps" / "api"
sys.path.insert(0, str(API_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tripos_api.settings")


def configure_django() -> None:
    from django.apps import apps
    import django

    if not apps.ready:
        django.setup()


def process_due_work() -> dict:
    configure_django()
    from organizers.services import process_automatic_reminders

    run = process_automatic_reminders()
    return {
        "automatic_reminder_notifications": run.total_notifications,
        "draft_recovery_reminders": run.draft_recovery_reminders,
        "balance_due_reminders": run.balance_due_reminders,
        "overdue_balance_reminders": run.overdue_balance_reminders,
        "missing_requirements_reminders": run.missing_requirements_reminders,
    }


def run_once() -> None:
    from django.conf import settings

    result = process_due_work()
    print(
        "TripOS worker ready",
        {
            "redis_url": settings.REDIS_URL,
            "object_storage_bucket": settings.OBJECT_STORAGE["bucket"],
            **result,
        },
    )


def run_forever(poll_interval: float) -> None:
    configure_django()
    print("TripOS worker started")
    while True:
        process_due_work()
        time.sleep(poll_interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="TripOS worker runtime")
    parser.add_argument("--once", action="store_true", help="run startup checks and exit")
    parser.add_argument("--poll-interval", type=float, default=5.0)
    args = parser.parse_args()

    if args.once:
        run_once()
    else:
        run_forever(args.poll_interval)


if __name__ == "__main__":
    main()
