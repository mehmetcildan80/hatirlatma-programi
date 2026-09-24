from __future__ import annotations

from datetime import date, time

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QCheckBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QLineEdit, QPlainTextEdit, QTimeEdit, QVBoxLayout,
)

from hatirlatici.domain.models import Task
from hatirlatici.ui.styles import APP_STYLE


class TaskDialog(QDialog):
    def __init__(self, parent=None, task: Task | None = None) -> None:
        super().__init__(parent)
        self.task = task
        self.setWindowTitle("Görevi Düzenle" if task else "Yeni Görev")
        self.setMinimumWidth(500)
        self.setStyleSheet(APP_STYLE)

        heading = QLabel("Görevi düzenleyin" if task else "Yeni görev oluşturun")
        heading.setStyleSheet("font-size:21px; font-weight:700; color:#17283f;")
        caption = QLabel("Başlık ve tarih zorunludur. Saat bilgisi isteğe bağlıdır.", objectName="muted")

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Örn. Aylık raporu gönder")
        self.title_edit.setMaxLength(200)
        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText("Görevle ilgili kısa notlar")
        self.description_edit.setMaximumHeight(112)
        self.date_edit = QDateEdit(calendarPopup=True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setMinimumDate(QDate(2000, 1, 1))
        self.time_enabled = QCheckBox("Görev saati belirt")
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setEnabled(False)
        self.completed_edit = QCheckBox("Görev tamamlandı")
        self.time_enabled.toggled.connect(self.time_edit.setEnabled)

        form = QFormLayout()
        form.setContentsMargins(0, 8, 0, 8)
        form.setHorizontalSpacing(22)
        form.setVerticalSpacing(13)
        form.addRow("Başlık *", self.title_edit)
        form.addRow("Açıklama", self.description_edit)
        form.addRow("Yapılacağı tarih *", self.date_edit)
        form.addRow("", self.time_enabled)
        form.addRow("Görev saati", self.time_edit)
        form.addRow("", self.completed_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Kaydet")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("İptal")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setObjectName("secondary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(8)
        layout.addWidget(heading)
        layout.addWidget(caption)
        layout.addLayout(form)
        layout.addWidget(buttons)

        if task:
            self.title_edit.setText(task.title)
            self.description_edit.setPlainText(task.description)
            self.date_edit.setDate(QDate(task.due_date.year, task.due_date.month, task.due_date.day))
            self.completed_edit.setChecked(task.completed)
            if task.due_time:
                self.time_enabled.setChecked(True)
                self.time_edit.setTime(QTime(task.due_time.hour, task.due_time.minute))
        else:
            current = date.today()
            self.date_edit.setDate(QDate(current.year, current.month, current.day))

    def task_value(self) -> Task:
        selected_date = self.date_edit.date()
        selected_time = self.time_edit.time()
        return Task(
            id=self.task.id if self.task else None,
            title=self.title_edit.text(),
            description=self.description_edit.toPlainText(),
            due_date=date(selected_date.year(), selected_date.month(), selected_date.day()),
            due_time=time(selected_time.hour(), selected_time.minute()) if self.time_enabled.isChecked() else None,
            completed=self.completed_edit.isChecked(),
        )
