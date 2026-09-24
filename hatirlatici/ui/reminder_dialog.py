from __future__ import annotations

from datetime import date, time

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from hatirlatici.domain.models import Task
from hatirlatici.domain.services import ReminderDue
from hatirlatici.ui.styles import APP_STYLE


MONTHS = (
    "", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
)
DAYS = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")


def turkish_date(value: date) -> str:
    return f"{value.day} {MONTHS[value.month]} {value.year} {DAYS[value.weekday()]}"


def sorted_reminder_tasks(tasks: list[Task]) -> list[Task]:
    return sorted(
        tasks,
        key=lambda task: (task.due_time is None, task.due_time or time.max, task.title.casefold()),
    )


class TaskCard(QFrame):
    def __init__(self, task: Task, parent=None) -> None:
        super().__init__(parent, objectName="taskCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(4)

        top = QHBoxLayout()
        hour = QLabel(task.due_time.strftime("%H:%M") if task.due_time else "SAAT YOK")
        hour.setStyleSheet("color:#2f78b7; font-weight:700; font-size:12px;")
        title = QLabel(task.title)
        title.setWordWrap(True)
        title.setStyleSheet("font-weight:650; font-size:14px; color:#1f2f43;")
        top.addWidget(hour, 0, Qt.AlignmentFlag.AlignTop)
        top.addSpacing(10)
        top.addWidget(title, 1)
        layout.addLayout(top)

        if task.description:
            description = QLabel(task.description)
            description.setWordWrap(True)
            description.setMaximumHeight(48)
            description.setToolTip(task.description)
            description.setStyleSheet("color:#66758a; font-size:12px;")
            layout.addWidget(description)


class ReminderDialog(QDialog):
    acknowledged = Signal()
    snoozed = Signal()

    BASE_HEIGHT = 218
    CARD_HEIGHT = 78
    MAX_HEIGHT = 640

    def __init__(self, due: ReminderDue, parent=None) -> None:
        super().__init__(parent)
        self.due = due
        self.setWindowTitle("Hatırlatıcı — Yarınki Görevler")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setModal(False)
        self.setMinimumWidth(520)
        self.setMaximumWidth(680)
        self.resize(600, self.preferred_height(len(due.tasks)))
        self.setStyleSheet(APP_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(14)

        header = QHBoxLayout()
        icon = QLabel("●")
        icon.setFixedSize(30, 30)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("background:#e5f1fb; color:#2f78b7; border-radius:15px; font-size:15px;")
        heading = QVBoxLayout()
        heading.setSpacing(2)
        count = len(due.tasks)
        title = QLabel(f"Yarın yapılacak {count} iş var")
        title.setStyleSheet("font-size:21px; font-weight:700; color:#17283f;")
        target_date = QLabel(turkish_date(due.target_date), objectName="muted")
        heading.addWidget(title)
        heading.addWidget(target_date)
        header.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        header.addSpacing(8)
        header.addLayout(heading, 1)
        layout.addLayout(header)

        body = QWidget()
        body.setStyleSheet("background:transparent;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(8)
        for task in sorted_reminder_tasks(due.tasks):
            body_layout.addWidget(TaskCard(task))
        body_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        snooze = QPushButton("10 dakika sonra tekrar hatırlat", objectName="secondary")
        confirm = QPushButton("Gördüm / Onayla")
        snooze.setMinimumWidth(230)
        confirm.setMinimumWidth(150)
        snooze.clicked.connect(self._snooze)
        confirm.clicked.connect(self._acknowledge)
        buttons.addWidget(snooze, 1)
        buttons.addWidget(confirm)
        layout.addLayout(buttons)

    @classmethod
    def preferred_height(cls, task_count: int, available_height: int | None = None) -> int:
        if available_height is None:
            screen = QApplication.primaryScreen()
            available_height = screen.availableGeometry().height() if screen else cls.MAX_HEIGHT
        screen_limit = max(360, available_height - 80)
        return min(
            cls.BASE_HEIGHT + max(1, task_count) * cls.CARD_HEIGHT,
            cls.MAX_HEIGHT,
            screen_limit,
        )

    def showEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        screen = self.screen() or QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            width = min(max(520, self.width()), max(420, area.width() - 48))
            self.resize(width, self.preferred_height(len(self.due.tasks), area.height()))
        super().showEvent(event)

    def _acknowledge(self) -> None:
        self.acknowledged.emit()

    def _snooze(self) -> None:
        self.snoozed.emit()
