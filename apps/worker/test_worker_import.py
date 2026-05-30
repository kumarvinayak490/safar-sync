import pytest

from worker import ROOT_DIR, process_due_work

pytestmark = pytest.mark.django_db


def test_worker_finds_repo_root():
    assert (ROOT_DIR / "apps" / "api" / "manage.py").exists()


def test_worker_processes_due_work_without_pending_reminders():
    result = process_due_work()

    assert result["automatic_reminder_notifications"] == 0
    assert result["draft_recovery_reminders"] == 0
