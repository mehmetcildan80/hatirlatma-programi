from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from hatirlatici.data.database import Database
from hatirlatici.domain.models import Task


class TaskRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _from_row(row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            due_date=date.fromisoformat(row["due_date"]),
            due_time=time.fromisoformat(row["due_time"]) if row["due_time"] else None,
            completed=bool(row["completed"]),
        )

    def add(self, task: Task) -> Task:
        with self.database.session() as connection:
            cursor = connection.execute(
                """INSERT INTO tasks(title, description, due_date, due_time, completed)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    task.title,
                    task.description,
                    task.due_date.isoformat(),
                    task.due_time.strftime("%H:%M") if task.due_time else None,
                    int(task.completed),
                ),
            )
            task.id = cursor.lastrowid
        return task

    def add_many(self, tasks: list[Task]) -> list[Task]:
        """Tüm görevleri tek SQLite transaction içinde kaydeder."""
        with self.database.session() as connection:
            for task in tasks:
                cursor = connection.execute(
                    """INSERT INTO tasks(title, description, due_date, due_time, completed)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        task.title,
                        task.description,
                        task.due_date.isoformat(),
                        task.due_time.strftime("%H:%M") if task.due_time else None,
                        int(task.completed),
                    ),
                )
                task.id = cursor.lastrowid
        return tasks

    def get(self, task_id: int) -> Task | None:
        with self.database.session() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[Task]:
        with self.database.session() as connection:
            rows = connection.execute(
                "SELECT * FROM tasks ORDER BY due_date, COALESCE(due_time, '23:59'), id"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def list_for_date(self, due_date: date) -> list[Task]:
        with self.database.session() as connection:
            rows = connection.execute(
                """SELECT * FROM tasks WHERE due_date = ?
                   ORDER BY COALESCE(due_time, '23:59'), id""",
                (due_date.isoformat(),),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def list_open_for_date(self, due_date: date) -> list[Task]:
        with self.database.session() as connection:
            rows = connection.execute(
                """SELECT * FROM tasks WHERE due_date = ? AND completed = 0
                   ORDER BY COALESCE(due_time, '23:59'), id""",
                (due_date.isoformat(),),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def update(self, task: Task) -> bool:
        if task.id is None:
            return False
        with self.database.session() as connection:
            cursor = connection.execute(
                """UPDATE tasks SET title = ?, description = ?, due_date = ?,
                   due_time = ?, completed = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (
                    task.title,
                    task.description,
                    task.due_date.isoformat(),
                    task.due_time.strftime("%H:%M") if task.due_time else None,
                    int(task.completed),
                    task.id,
                ),
            )
        return cursor.rowcount == 1

    def delete(self, task_id: int) -> bool:
        with self.database.session() as connection:
            cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cursor.rowcount == 1

    def set_completed(self, task_id: int, completed: bool) -> bool:
        with self.database.session() as connection:
            cursor = connection.execute(
                """UPDATE tasks SET completed = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (int(completed), task_id),
            )
        return cursor.rowcount == 1


class SettingsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get(self, key: str, default: str | None = None) -> str | None:
        with self.database.session() as connection:
            row = connection.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        with self.database.session() as connection:
            connection.execute(
                """INSERT INTO settings(key, value) VALUES (?, ?)
                   ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
                (key, value),
            )


@dataclass(frozen=True, slots=True)
class ReminderRun:
    reminder_date: date
    target_date: date
    first_shown_at: datetime
    acknowledged: bool
    acknowledged_at: datetime | None
    snoozed_until: datetime | None


class ReminderRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _from_row(row) -> ReminderRun:
        return ReminderRun(
            reminder_date=date.fromisoformat(row["reminder_date"]),
            target_date=date.fromisoformat(row["target_date"]),
            first_shown_at=datetime.fromisoformat(row["first_shown_at"]),
            acknowledged=bool(row["acknowledged"]),
            acknowledged_at=(
                datetime.fromisoformat(row["acknowledged_at"])
                if row["acknowledged_at"] else None
            ),
            snoozed_until=(
                datetime.fromisoformat(row["snoozed_until"])
                if row["snoozed_until"] else None
            ),
        )

    def get(self, reminder_date: date) -> ReminderRun | None:
        with self.database.session() as connection:
            row = connection.execute(
                "SELECT * FROM reminder_runs WHERE reminder_date = ?",
                (reminder_date.isoformat(),),
            ).fetchone()
        return self._from_row(row) if row else None

    def record_first_show(self, reminder_date: date, target_date: date, shown_at: datetime) -> None:
        with self.database.session() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO reminder_runs(
                       reminder_date, target_date, first_shown_at, acknowledged
                   ) VALUES (?, ?, ?, 0)""",
                (reminder_date.isoformat(), target_date.isoformat(), shown_at.isoformat()),
            )

    def acknowledge(self, reminder_date: date, acknowledged_at: datetime) -> bool:
        with self.database.session() as connection:
            cursor = connection.execute(
                """UPDATE reminder_runs
                   SET acknowledged = 1, acknowledged_at = ?, snoozed_until = NULL
                   WHERE reminder_date = ? AND acknowledged = 0""",
                (acknowledged_at.isoformat(), reminder_date.isoformat()),
            )
        return cursor.rowcount == 1

    def snooze(self, reminder_date: date, until: datetime) -> bool:
        with self.database.session() as connection:
            cursor = connection.execute(
                """UPDATE reminder_runs SET snoozed_until = ?
                   WHERE reminder_date = ? AND acknowledged = 0""",
                (until.isoformat(), reminder_date.isoformat()),
            )
        return cursor.rowcount == 1
