from __future__ import annotations

import sqlite3
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.session() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL CHECK(length(trim(title)) > 0),
                    description TEXT NOT NULL DEFAULT '',
                    due_date TEXT NOT NULL,
                    due_time TEXT,
                    completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_due_date
                    ON tasks(due_date);

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reminder_runs (
                    reminder_date TEXT PRIMARY KEY,
                    target_date TEXT NOT NULL,
                    first_shown_at TEXT NOT NULL,
                    acknowledged INTEGER NOT NULL DEFAULT 0
                        CHECK(acknowledged IN (0, 1)),
                    acknowledged_at TEXT,
                    snoozed_until TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_reminder_runs_target_date
                    ON reminder_runs(target_date);

                INSERT OR IGNORE INTO settings(key, value)
                    VALUES ('reminder_time', '15:00');
                """
            )

    def create_backup(self, directory: Path, now: datetime | None = None) -> Path:
        """SQLite'ın tutarlı çevrimiçi yedekleme API'siyle güvenli kopya üretir."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S-%f")
        destination = directory / f"hatirlatici-{stamp}.db"
        temporary = destination.with_suffix(".db.tmp")
        source: sqlite3.Connection | None = None
        target: sqlite3.Connection | None = None
        try:
            source = self.connect()
            target = sqlite3.connect(temporary)
            source.backup(target)
            target.commit()
            target.close()
            target = None
            temporary.replace(destination)
            return destination
        except Exception:
            if target is not None:
                target.close()
            temporary.unlink(missing_ok=True)
            raise
        finally:
            if source is not None:
                source.close()
