from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from hatirlatici.domain.services import ReminderDue


class ReminderDialog(QDialog):
    acknowledged = Signal()
    snoozed = Signal()

    def __init__(self, due: ReminderDue, parent=None) -> None:
        super().__init__(parent)
        self.due = due
        self.setWindowTitle("Hatırlatıcı — Yarınki Görevler")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumSize(560, 420)
        self.setModal(False)

        layout = QVBoxLayout(self)
        title = QLabel("Yarın yapılacak işler")
        title.setStyleSheet("font-size: 23px; font-weight: 700; color: #17263c;")
        date_label = QLabel(due.target_date.strftime("%d.%m.%Y"))
        date_label.setStyleSheet("color: #526579; font-size: 14px;")
        layout.addWidget(title)
        layout.addWidget(date_label)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        for task in due.tasks:
            hour = task.due_time.strftime("%H:%M") if task.due_time else "Saat belirtilmedi"
            item = QLabel(f"<b>{hour} — {task.title}</b><br>{task.description or 'Açıklama yok'}")
            item.setWordWrap(True)
            item.setStyleSheet("background: #f2f5f8; border-radius: 6px; padding: 12px;")
            body_layout.addWidget(item)
        body_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        snooze = QPushButton("10 dakika sonra tekrar hatırlat")
        confirm = QPushButton("Gördüm / Onayla")
        snooze.clicked.connect(self._snooze)
        confirm.clicked.connect(self._acknowledge)
        buttons.addWidget(snooze)
        buttons.addStretch()
        buttons.addWidget(confirm)
        layout.addLayout(buttons)

    def _acknowledge(self) -> None:
        self.acknowledged.emit()

    def _snooze(self) -> None:
        self.snoozed.emit()
