from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path

from hatirlatici.data.database import Database
from hatirlatici.data.repositories import ReminderRepository, SettingsRepository, TaskRepository
from hatirlatici.domain.models import Task
from hatirlatici.domain.services import ReminderService, SettingsService, TaskService, ValidationError


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()
        self.task_repository = TaskRepository(self.database)
        self.task_service = TaskService(self.task_repository)
        self.settings_service = SettingsService(SettingsRepository(self.database))
        self.reminder_repository = ReminderRepository(self.database)
        self.now = datetime(2026, 9, 14, 14, 0)
        self.reminder_service = ReminderService(
            self.task_repository,
            self.reminder_repository,
            self.settings_service,
            lambda: self.now,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_add_and_read_task(self) -> None:
        task = self.task_service.add(Task("  Raporu hazırla  ", date(2026, 9, 15), "Taslak", time(10, 30)))
        self.assertIsNotNone(task.id)
        loaded = self.task_service.list_for("all")
        self.assertEqual(loaded[0].title, "Raporu hazırla")
        self.assertEqual(loaded[0].due_time, time(10, 30))

    def test_update_task(self) -> None:
        task = self.task_service.add(Task("Eski", date(2026, 9, 15)))
        task.title = "Yeni"
        task.completed = True
        self.task_service.update(task)
        updated = self.task_service.list_for("all")[0]
        self.assertEqual(updated.title, "Yeni")
        self.assertTrue(updated.completed)

    def test_delete_task(self) -> None:
        task = self.task_service.add(Task("Silinecek", date(2026, 9, 15)))
        self.task_service.delete(task.id)  # type: ignore[arg-type]
        self.assertEqual(self.task_service.list_for("all"), [])

    def test_mark_task_completed(self) -> None:
        task = self.task_service.add(Task("Tamamlanacak", date(2026, 9, 15)))
        self.task_service.set_completed(task.id, True)  # type: ignore[arg-type]
        self.assertTrue(self.task_service.list_for("all")[0].completed)

    def test_date_filters(self) -> None:
        today = date(2026, 9, 14)
        self.task_service.add(Task("Bugün", today))
        self.task_service.add(Task("Yarın", today + timedelta(days=1)))
        self.task_service.add(Task("Sonra", today + timedelta(days=2)))
        self.assertEqual([x.title for x in self.task_service.list_for("today", today)], ["Bugün"])
        self.assertEqual([x.title for x in self.task_service.list_for("tomorrow", today)], ["Yarın"])
        self.assertEqual(len(self.task_service.list_for("all", today)), 3)

    def test_settings_default_and_save(self) -> None:
        self.assertEqual(self.settings_service.get_reminder_time(), time(15, 0))
        self.settings_service.set_reminder_time(time(17, 45))
        self.assertEqual(self.settings_service.get_reminder_time(), time(17, 45))

    def test_empty_title_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.task_service.add(Task("   ", date.today()))

    def add_tomorrow_task(self, completed: bool = False) -> Task:
        return self.task_service.add(
            Task("Yarınki iş", self.now.date() + timedelta(days=1), completed=completed)
        )

    def test_no_reminder_before_scheduled_time(self) -> None:
        self.add_tomorrow_task()
        self.assertIsNone(self.reminder_service.check_due())

    def test_reminder_after_scheduled_time(self) -> None:
        self.add_tomorrow_task()
        self.now = datetime(2026, 9, 14, 15, 1)
        due = self.reminder_service.check_due()
        self.assertIsNotNone(due)
        self.assertEqual(due.tasks[0].title, "Yarınki iş")  # type: ignore[union-attr]

    def test_no_reminder_without_tomorrow_tasks(self) -> None:
        self.now = datetime(2026, 9, 14, 16, 0)
        self.assertIsNone(self.reminder_service.check_due())

    def test_completed_tasks_are_excluded_from_reminder(self) -> None:
        self.add_tomorrow_task(completed=True)
        self.now = datetime(2026, 9, 14, 16, 0)
        self.assertIsNone(self.reminder_service.check_due())

    def test_acknowledged_daily_reminder_does_not_repeat(self) -> None:
        self.add_tomorrow_task()
        self.now = datetime(2026, 9, 14, 16, 0)
        due = self.reminder_service.check_due()
        self.reminder_service.acknowledge(due.reminder_date)  # type: ignore[union-attr]
        self.now += timedelta(minutes=1)
        self.assertIsNone(self.reminder_service.check_due())

    def test_unacknowledged_reminder_can_be_shown_again(self) -> None:
        self.add_tomorrow_task()
        self.now = datetime(2026, 9, 14, 16, 0)
        self.assertIsNotNone(self.reminder_service.check_due())
        self.now += timedelta(minutes=1)
        self.assertIsNotNone(self.reminder_service.check_due())

    def test_missed_reminder_is_detected_after_restart(self) -> None:
        self.add_tomorrow_task()
        self.now = datetime(2026, 9, 14, 16, 30)
        restarted_service = ReminderService(
            self.task_repository,
            self.reminder_repository,
            self.settings_service,
            lambda: self.now,
        )
        self.assertIsNotNone(restarted_service.check_due())

    def test_snooze_does_not_acknowledge_and_persists(self) -> None:
        self.add_tomorrow_task()
        self.now = datetime(2026, 9, 14, 16, 0)
        due = self.reminder_service.check_due()
        self.reminder_service.snooze(due.reminder_date)  # type: ignore[union-attr]
        run = self.reminder_repository.get(self.now.date())
        self.assertFalse(run.acknowledged)  # type: ignore[union-attr]
        self.now += timedelta(minutes=9)
        self.assertIsNone(self.reminder_service.check_due())
        self.now += timedelta(minutes=1)
        self.assertIsNotNone(self.reminder_service.check_due())

    def test_acknowledgement_time_is_saved(self) -> None:
        self.add_tomorrow_task()
        self.now = datetime(2026, 9, 14, 16, 0)
        due = self.reminder_service.check_due()
        self.now = datetime(2026, 9, 14, 16, 5)
        self.reminder_service.acknowledge(due.reminder_date)  # type: ignore[union-attr]
        run = self.reminder_repository.get(date(2026, 9, 14))
        self.assertEqual(run.acknowledged_at, self.now)  # type: ignore[union-attr]

    def test_changed_general_time_is_applied(self) -> None:
        self.add_tomorrow_task()
        self.settings_service.set_reminder_time(time(17, 0))
        self.now = datetime(2026, 9, 14, 16, 59)
        self.assertIsNone(self.reminder_service.check_due())
        self.now = datetime(2026, 9, 14, 17, 0)
        self.assertIsNotNone(self.reminder_service.check_due())


if __name__ == "__main__":
    unittest.main()
