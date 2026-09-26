from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from hatirlatici.domain.models import Task
from hatirlatici.domain.services import ReminderDue
from hatirlatici.data.database import Database
from hatirlatici.data.repositories import ReminderRepository, SettingsRepository, TaskRepository
from hatirlatici.domain.services import ReminderService, SettingsService, TaskService
from hatirlatici.platform.startup import StartupManager
from hatirlatici.ui.main_window import MainWindow
from hatirlatici.ui.reminder_dialog import ReminderDialog, sorted_reminder_tasks, turkish_date


class FakeReminderService:
    def __init__(self, due: ReminderDue | None = None) -> None:
        self.due = due
        self.check_count = 0

    def check_due(self) -> ReminderDue | None:
        self.check_count += 1
        return self.due

    def acknowledge(self, reminder_date: date) -> None:
        pass

    def snooze(self, reminder_date: date, minutes: int = 10) -> None:
        pass


def dispose_window(window: MainWindow) -> None:
    app = QApplication.instance()
    window.reminder_timer.stop()
    if window.reminder_dialog:
        window.reminder_dialog.close()
    window.tray_icon.hide()
    if app:
        app.removeNativeEventFilter(window.power_resume_watcher)
        try:
            app.applicationStateChanged.disconnect(window._handle_application_state)
        except (RuntimeError, TypeError):
            pass
    window._really_quit = True
    window.close()
    window.deleteLater()
    if app:
        app.processEvents()


class ReminderDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def due(self, count: int) -> ReminderDue:
        tasks = [
            Task(
                title=f"Görev {index}",
                due_date=date(2026, 9, 25),
                description="Uzun açıklama " * 12,
                due_time=time(9 + index % 8, index % 60) if index % 2 else None,
            )
            for index in range(count)
        ]
        return ReminderDue(date(2026, 9, 24), date(2026, 9, 25), tasks)

    def test_single_task_is_compact_and_many_tasks_are_capped(self) -> None:
        single = ReminderDialog.preferred_height(1, 900)
        many = ReminderDialog.preferred_height(20, 900)
        self.assertLess(single, 400)
        self.assertGreater(many, single)
        self.assertLessEqual(many, ReminderDialog.MAX_HEIGHT)

    def test_small_screen_height_is_respected(self) -> None:
        self.assertLessEqual(ReminderDialog.preferred_height(20, 480), 400)

    def test_tasks_are_sorted_by_time_with_unscheduled_last(self) -> None:
        tasks = [
            Task("Saati yok", date(2026, 9, 25)),
            Task("Geç", date(2026, 9, 25), due_time=time(16, 0)),
            Task("Erken", date(2026, 9, 25), due_time=time(9, 0)),
        ]
        self.assertEqual([task.title for task in sorted_reminder_tasks(tasks)], ["Erken", "Geç", "Saati yok"])

    def test_turkish_date_and_complete_button_labels(self) -> None:
        dialog = ReminderDialog(self.due(1))
        labels = [label.text() for label in dialog.findChildren(QLabel)]
        buttons = [button.text() for button in dialog.findChildren(QPushButton)]
        self.assertIn("25 Eylül 2026 Cuma", labels)
        self.assertIn("10 dakika sonra tekrar hatırlat", buttons)
        self.assertIn("Gördüm / Onayla", buttons)

    def test_closing_does_not_acknowledge(self) -> None:
        dialog = ReminderDialog(self.due(1))
        acknowledged = QSignalSpy(dialog.acknowledged)
        dialog.show()
        self.app.processEvents()
        dialog.close()
        self.app.processEvents()
        self.assertEqual(acknowledged.count(), 0)

    def test_snooze_does_not_emit_acknowledgement(self) -> None:
        dialog = ReminderDialog(self.due(1))
        acknowledged = QSignalSpy(dialog.acknowledged)
        snoozed = QSignalSpy(dialog.snoozed)
        snooze = next(
            button for button in dialog.findChildren(QPushButton)
            if button.text() == "10 dakika sonra tekrar hatırlat"
        )
        snooze.click()
        self.assertEqual(acknowledged.count(), 0)
        self.assertEqual(snoozed.count(), 1)

    def test_only_confirm_button_emits_acknowledgement(self) -> None:
        dialog = ReminderDialog(self.due(1))
        acknowledged = QSignalSpy(dialog.acknowledged)
        confirm = next(
            button for button in dialog.findChildren(QPushButton)
            if button.text() == "Gördüm / Onayla"
        )
        confirm.click()
        self.assertEqual(acknowledged.count(), 1)

    def test_main_window_can_be_constructed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "ui.db")
            database.initialize()
            tasks = TaskRepository(database)
            settings = SettingsService(SettingsRepository(database))
            window = MainWindow(
                TaskService(tasks),
                settings,
                ReminderService(tasks, ReminderRepository(database), settings),
                StartupManager(Path(directory) / "app.py"),
            )
            self.assertEqual(window.windowTitle(), "Hatırlatıcı")
            dispose_window(window)

    def test_power_resume_schedules_reminder_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "ui.db")
            database.initialize()
            tasks = TaskRepository(database)
            settings = SettingsService(SettingsRepository(database))
            reminder = FakeReminderService()
            window = MainWindow(
                TaskService(tasks), settings, reminder, StartupManager(Path(directory) / "app.py")
            )
            before = reminder.check_count
            window._handle_power_resume()
            self.app.processEvents()
            self.assertGreater(reminder.check_count, before)
            dispose_window(window)

    def test_hidden_tray_window_does_not_block_reminder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "ui.db")
            database.initialize()
            tasks = TaskRepository(database)
            settings = SettingsService(SettingsRepository(database))
            reminder = FakeReminderService(self.due(1))
            window = MainWindow(
                TaskService(tasks), settings, reminder, StartupManager(Path(directory) / "app.py")
            )
            window.hide()
            window.check_reminder()
            self.app.processEvents()
            self.assertIsNotNone(window.reminder_dialog)
            self.assertTrue(window.reminder_dialog.isVisible())  # type: ignore[union-attr]
            window.reminder_dialog.close()  # type: ignore[union-attr]
            dispose_window(window)


if __name__ == "__main__":
    unittest.main()
