from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Callable

from hatirlatici.data.repositories import ReminderRepository, SettingsRepository, TaskRepository
from hatirlatici.domain.models import Task


class ValidationError(ValueError):
    pass


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    @staticmethod
    def _validate(task: Task) -> None:
        task.title = task.title.strip()
        task.description = task.description.strip()
        if not task.title:
            raise ValidationError("Görev başlığı boş bırakılamaz.")
        if len(task.title) > 200:
            raise ValidationError("Görev başlığı 200 karakterden uzun olamaz.")

    def add(self, task: Task) -> Task:
        self._validate(task)
        return self.repository.add(task)

    def update(self, task: Task) -> None:
        self._validate(task)
        if task.id is None or not self.repository.update(task):
            raise ValidationError("Güncellenecek görev bulunamadı.")

    def delete(self, task_id: int) -> None:
        if not self.repository.delete(task_id):
            raise ValidationError("Silinecek görev bulunamadı.")

    def set_completed(self, task_id: int, completed: bool) -> None:
        if not self.repository.set_completed(task_id, completed):
            raise ValidationError("Güncellenecek görev bulunamadı.")

    def list_for(self, filter_name: str, today: date | None = None) -> list[Task]:
        current = today or date.today()
        if filter_name == "today":
            return self.repository.list_for_date(current)
        if filter_name == "tomorrow":
            return self.repository.list_for_date(current + timedelta(days=1))
        return self.repository.list_all()


class SettingsService:
    KEY = "reminder_time"

    def __init__(self, repository: SettingsRepository) -> None:
        self.repository = repository

    def get_reminder_time(self) -> time:
        value = self.repository.get(self.KEY, "15:00") or "15:00"
        try:
            return time.fromisoformat(value)
        except ValueError:
            return time(15, 0)

    def set_reminder_time(self, value: time) -> None:
        self.repository.set(self.KEY, value.strftime("%H:%M"))


@dataclass(frozen=True, slots=True)
class ReminderDue:
    reminder_date: date
    target_date: date
    tasks: list[Task]


class ReminderService:
    """Saatten bağımsız, enjekte edilebilir zaman kaynağıyla günlük kontrol."""

    def __init__(
        self,
        task_repository: TaskRepository,
        reminder_repository: ReminderRepository,
        settings_service: SettingsService,
        now_provider: Callable[[], datetime] = datetime.now,
    ) -> None:
        self.task_repository = task_repository
        self.reminder_repository = reminder_repository
        self.settings_service = settings_service
        self.now_provider = now_provider

    def check_due(self) -> ReminderDue | None:
        now = self.now_provider()
        scheduled = self.settings_service.get_reminder_time()
        scheduled_at = datetime.combine(now.date(), scheduled)
        if now < scheduled_at:
            return None

        run = self.reminder_repository.get(now.date())
        if run and run.acknowledged:
            return None
        if run and run.snoozed_until and now < run.snoozed_until:
            return None

        target_date = now.date() + timedelta(days=1)
        tasks = self.task_repository.list_open_for_date(target_date)
        if not tasks:
            return None

        self.reminder_repository.record_first_show(now.date(), target_date, now)
        return ReminderDue(now.date(), target_date, tasks)

    def acknowledge(self, reminder_date: date) -> None:
        if not self.reminder_repository.acknowledge(reminder_date, self.now_provider()):
            raise ValidationError("Onaylanacak günlük hatırlatma bulunamadı.")

    def snooze(self, reminder_date: date, minutes: int = 10) -> None:
        if minutes <= 0:
            raise ValidationError("Erteleme süresi geçerli değil.")
        if not self.reminder_repository.snooze(
            reminder_date, self.now_provider() + timedelta(minutes=minutes)
        ):
            raise ValidationError("Ertelenecek günlük hatırlatma bulunamadı.")
