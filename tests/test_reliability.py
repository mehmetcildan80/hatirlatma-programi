from __future__ import annotations

import logging
import sqlite3
import tempfile
import unittest
import uuid
from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication

from hatirlatici.data.database import Database
from hatirlatici.platform.logging_setup import (
    BACKUP_COUNT,
    LOG_FILE_NAME,
    configure_logging,
    log_event,
    reset_logging_for_tests,
)
from hatirlatici.platform.single_instance import SingleInstanceGuard


class BackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.database = Database(self.root / "original.db")
        self.database.initialize()
        with self.database.session() as connection:
            connection.execute(
                "INSERT INTO tasks(title, due_date) VALUES (?, ?)",
                ("Yedeklenecek görev", date(2026, 9, 27).isoformat()),
            )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_sqlite_backup_is_readable_and_complete(self) -> None:
        backup = self.database.create_backup(
            self.root / "backups", datetime(2026, 9, 26, 16, 30)
        )
        connection = sqlite3.connect(backup)
        try:
            count = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(count, 1)
        self.assertEqual(integrity, "ok")

    def test_failed_backup_leaves_original_intact_and_no_partial_file(self) -> None:
        before = self.database.path.read_bytes()
        broken_source = Mock()
        broken_source.backup.side_effect = sqlite3.OperationalError("simulated")
        with patch.object(self.database, "connect", return_value=broken_source):
            with self.assertRaises(sqlite3.OperationalError):
                self.database.create_backup(self.root / "failed")
        self.assertEqual(self.database.path.read_bytes(), before)
        self.assertEqual(list((self.root / "failed").glob("*")), [])
        broken_source.close.assert_called_once()


class LoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_logging_for_tests()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        reset_logging_for_tests()
        self.temp_dir.cleanup()

    def test_log_file_is_created_and_excludes_task_content(self) -> None:
        configure_logging(self.log_root)
        secret = "Çok gizli müşteri görevi"
        log_event("task_saved", title=secret, description=secret, count=1)
        reset_logging_for_tests()
        content = (self.log_root / LOG_FILE_NAME).read_text(encoding="utf-8")
        self.assertIn("event=task_saved", content)
        self.assertIn("count=1", content)
        self.assertNotIn(secret, content)

    def test_log_files_rotate_and_are_bounded(self) -> None:
        logger = configure_logging(self.log_root)
        handler = next(handler for handler in logger.handlers if hasattr(handler, "maxBytes"))
        handler.maxBytes = 256  # type: ignore[attr-defined]
        for index in range(100):
            logger.info("event=rotation_test count=%s", index)
        reset_logging_for_tests()
        files = list(self.log_root.glob(f"{LOG_FILE_NAME}*"))
        self.assertLessEqual(len(files), BACKUP_COUNT + 1)
        self.assertTrue(all(path.stat().st_size <= 512 for path in files))


class SingleInstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_second_instance_requests_existing_window(self) -> None:
        name = f"Hatirlatici-Test-{uuid.uuid4().hex}"
        primary = SingleInstanceGuard(name)
        secondary = SingleInstanceGuard(name)
        self.assertTrue(primary.acquire())
        spy = QSignalSpy(primary.show_requested)
        self.assertFalse(secondary.acquire())
        QTest.qWait(300)
        self.app.processEvents()
        self.assertEqual(spy.count(), 1)
        primary.close()


if __name__ == "__main__":
    unittest.main()
