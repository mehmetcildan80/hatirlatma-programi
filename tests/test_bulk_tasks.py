from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit, QMessageBox, QPushButton

from hatirlatici.data.database import Database
from hatirlatici.data.repositories import ReminderRepository, SettingsRepository, TaskRepository
from hatirlatici.domain.models import BulkTaskDraft
from hatirlatici.domain.services import ReminderService, SettingsService, TaskService, ValidationError
from hatirlatici.platform.startup import StartupManager
from hatirlatici.ui.bulk_task_dialog import BulkTaskDialog
from hatirlatici.ui.main_window import MainWindow


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


class BulkTaskServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "bulk.db")
        self.database.initialize()
        self.repository = TaskRepository(self.database)
        self.service = TaskService(self.repository)
        self.target = date(2026, 9, 27)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_adds_three_tasks_for_same_date(self) -> None:
        count = self.service.add_bulk(
            [BulkTaskDraft("Bir"), BulkTaskDraft("İki"), BulkTaskDraft("Üç")], self.target
        )
        self.assertEqual(count, 3)
        self.assertEqual({task.due_date for task in self.repository.list_all()}, {self.target})

    def test_adds_many_tasks(self) -> None:
        drafts = [BulkTaskDraft(f"Görev {index}") for index in range(30)]
        self.assertEqual(self.service.add_bulk(drafts, self.target), 30)
        self.assertEqual(len(self.repository.list_all()), 30)

    def test_adds_timed_and_untimed_tasks(self) -> None:
        self.service.add_bulk(
            [BulkTaskDraft("Saatli", "09:30"), BulkTaskDraft("Saatsiz")], self.target
        )
        tasks = self.repository.list_for_date(self.target)
        self.assertEqual(tasks[0].due_time, time(9, 30))
        self.assertIsNone(tasks[1].due_time)

    def test_skips_completely_empty_rows(self) -> None:
        count = self.service.add_bulk(
            [BulkTaskDraft(), BulkTaskDraft("Gerçek görev"), BulkTaskDraft(" ", " ", " ")],
            self.target,
        )
        self.assertEqual(count, 1)

    def test_rejects_description_without_title(self) -> None:
        with self.assertRaisesRegex(ValidationError, "1. satır"):
            self.service.add_bulk([BulkTaskDraft("", "", "Açıklama var")], self.target)

    def test_rejects_invalid_time(self) -> None:
        with self.assertRaisesRegex(ValidationError, "HH:MM"):
            self.service.add_bulk([BulkTaskDraft("Görev", "25:70")], self.target)
        with self.assertRaisesRegex(ValidationError, "HH:MM"):
            self.service.add_bulk([BulkTaskDraft("Görev", "9:30")], self.target)

    def test_validation_error_saves_nothing(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.add_bulk(
                [BulkTaskDraft("Geçerli"), BulkTaskDraft("", "10:00", "Başlık yok")],
                self.target,
            )
        self.assertEqual(self.repository.list_all(), [])

    def test_database_error_rolls_back_transaction(self) -> None:
        with self.database.session() as connection:
            connection.execute(
                """CREATE TRIGGER fail_bulk BEFORE INSERT ON tasks
                   WHEN NEW.title = 'Hata' BEGIN SELECT RAISE(ABORT, 'zorunlu test hatası'); END"""
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.service.add_bulk(
                [BulkTaskDraft("İlk"), BulkTaskDraft("Hata"), BulkTaskDraft("Son")],
                self.target,
            )
        self.assertEqual(self.repository.list_all(), [])

    def test_returns_saved_task_count(self) -> None:
        count = self.service.add_bulk(
            [BulkTaskDraft("Bir"), BulkTaskDraft(), BulkTaskDraft("İki")], self.target
        )
        self.assertEqual(count, 2)

    def test_bulk_tasks_appear_in_date_filter(self) -> None:
        self.service.add_bulk([BulkTaskDraft("Filtre görevi")], self.target)
        self.assertEqual(
            [task.title for task in self.service.list_for("tomorrow", self.target - timedelta(days=1))],
            ["Filtre görevi"],
        )

    def test_bulk_tomorrow_tasks_are_detected_by_reminder(self) -> None:
        now = datetime(2026, 9, 26, 15, 1)
        tomorrow = now.date() + timedelta(days=1)
        self.service.add_bulk([BulkTaskDraft("Bir"), BulkTaskDraft("İki")], tomorrow)
        settings = SettingsService(SettingsRepository(self.database))
        reminder = ReminderService(
            self.repository, ReminderRepository(self.database), settings, lambda: now
        )
        due = reminder.check_due()
        self.assertIsNotNone(due)
        self.assertEqual(len(due.tasks), 2)  # type: ignore[union-attr]
        run = ReminderRepository(self.database).get(now.date())
        self.assertFalse(run.acknowledged)  # type: ignore[union-attr]


class BulkTaskDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "ui.db")
        self.database.initialize()
        self.repository = TaskRepository(self.database)
        self.service = TaskService(self.repository)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @staticmethod
    def editors(dialog: BulkTaskDialog, row: int) -> tuple[QLineEdit, QLineEdit, QLineEdit]:
        return tuple(dialog.table.cellWidget(row, column) for column in range(3))  # type: ignore[return-value]

    def test_dialog_starts_with_three_rows(self) -> None:
        dialog = BulkTaskDialog(self.service)
        self.assertEqual(dialog.table.rowCount(), 3)

    def test_common_date_change_preserves_row_values(self) -> None:
        dialog = BulkTaskDialog(self.service)
        title, hour, description = self.editors(dialog, 0)
        title.setText("Korunacak")
        hour.setText("11:20")
        description.setText("Açıklama")
        dialog.date_edit.setDate(QDate(2026, 10, 2))
        self.assertEqual(dialog.drafts()[0], BulkTaskDraft("Korunacak", "11:20", "Açıklama"))

    def test_removing_row_preserves_other_rows(self) -> None:
        dialog = BulkTaskDialog(self.service)
        self.editors(dialog, 0)[0].setText("Bir")
        self.editors(dialog, 1)[0].setText("İki")
        self.editors(dialog, 2)[0].setText("Üç")
        remove = dialog.table.cellWidget(1, 3)
        self.assertIsInstance(remove, QPushButton)
        remove.click()  # type: ignore[union-attr]
        self.assertEqual([draft.title for draft in dialog.drafts()], ["Bir", "Üç"])

    def test_repeated_save_does_not_duplicate_tasks(self) -> None:
        dialog = BulkTaskDialog(self.service)
        self.editors(dialog, 0)[0].setText("Tek kayıt")
        with patch.object(QMessageBox, "information", return_value=QMessageBox.StandardButton.Ok):
            dialog.save_all()
            dialog.save_all()
        self.assertEqual(len(self.repository.list_all()), 1)

    def test_invalid_row_keeps_input_and_is_marked(self) -> None:
        dialog = BulkTaskDialog(self.service)
        _title, hour, description = self.editors(dialog, 0)
        hour.setText("99:99")
        description.setText("Kaybolmamalı")
        dialog.save_all()
        self.assertEqual(dialog.drafts()[0].description, "Kaybolmamalı")
        self.assertIn("1. satır", dialog.error_label.text())
        self.assertTrue(dialog.save_button.isEnabled())

    def test_successful_dialog_save_returns_correct_count(self) -> None:
        dialog = BulkTaskDialog(self.service)
        self.editors(dialog, 0)[0].setText("Bir")
        self.editors(dialog, 1)[0].setText("İki")
        with patch.object(QMessageBox, "information") as information:
            dialog.save_all()
        information.assert_called_once()
        self.assertIn("2 görev", information.call_args.args[2])
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)

    def test_main_window_refreshes_after_bulk_dialog_accepts(self) -> None:
        settings = SettingsService(SettingsRepository(self.database))
        reminder = ReminderService(
            self.repository, ReminderRepository(self.database), settings
        )
        window = MainWindow(
            self.service,
            settings,
            reminder,
            StartupManager(Path(self.temp_dir.name) / "app.py"),
        )
        self.service.add_bulk([BulkTaskDraft("Bugünkü görev")], date.today())
        with patch("hatirlatici.ui.main_window.BulkTaskDialog") as dialog_class:
            dialog_class.DialogCode.Accepted = QDialog.DialogCode.Accepted
            dialog_class.return_value.exec.return_value = QDialog.DialogCode.Accepted
            window.add_bulk_tasks()
        self.assertEqual(window.table.rowCount(), 1)
        dispose_window(window)

    def test_hidden_main_window_shows_bulk_task_reminder_unacknowledged(self) -> None:
        now = datetime(2026, 9, 26, 15, 1)
        tomorrow = now.date() + timedelta(days=1)
        self.service.add_bulk(
            [BulkTaskDraft("Toplu bir"), BulkTaskDraft("Toplu iki")], tomorrow
        )
        settings = SettingsService(SettingsRepository(self.database))
        reminder_repository = ReminderRepository(self.database)
        reminder = ReminderService(
            self.repository, reminder_repository, settings, lambda: now
        )
        window = MainWindow(
            self.service,
            settings,
            reminder,
            StartupManager(Path(self.temp_dir.name) / "app.py"),
        )
        window.hide()
        window.check_reminder()
        self.app.processEvents()
        self.assertIsNotNone(window.reminder_dialog)
        self.assertIsNone(window.reminder_dialog.parent())  # type: ignore[union-attr]
        self.assertTrue(window.reminder_dialog.isVisible())  # type: ignore[union-attr]
        self.assertEqual(len(window.reminder_dialog.due.tasks), 2)  # type: ignore[union-attr]
        run = reminder_repository.get(now.date())
        self.assertFalse(run.acknowledged)  # type: ignore[union-attr]
        window.reminder_dialog.close()  # type: ignore[union-attr]
        dispose_window(window)


if __name__ == "__main__":
    unittest.main()
