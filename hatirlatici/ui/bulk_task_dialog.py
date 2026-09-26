from __future__ import annotations

import sqlite3
from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from PySide6.QtWidgets import (
    QDateEdit, QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QVBoxLayout, QWidget,
)

from hatirlatici.domain.models import BulkTaskDraft
from hatirlatici.domain.services import TaskService, ValidationError
from hatirlatici.ui.styles import APP_STYLE


class BulkTaskDialog(QDialog):
    def __init__(self, task_service: TaskService, parent=None) -> None:
        super().__init__(parent)
        self.task_service = task_service
        self._saving = False
        self._saved = False
        self.setWindowTitle("Toplu Görev Ekle")
        self.setMinimumSize(760, 480)
        self.resize(940, 600)
        self.setStyleSheet(APP_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Toplu Görev Ekle", objectName="pageTitle")
        caption = QLabel(
            "Aynı güne ait birden fazla görevi tek seferde kaydedebilirsiniz.",
            objectName="pageCaption",
        )
        layout.addWidget(title)
        layout.addWidget(caption)

        date_row = QHBoxLayout()
        date_label = QLabel("Ortak tarih")
        date_label.setStyleSheet("font-weight:700;")
        self.date_edit = QDateEdit(calendarPopup=True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        current = date.today()
        self.date_edit.setDate(QDate(current.year, current.month, current.day))
        date_row.addWidget(date_label)
        date_row.addWidget(self.date_edit)
        date_row.addStretch()
        layout.addLayout(date_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Görev başlığı *", "Saat", "Açıklama", "Satırı sil"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 100)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 105)
        layout.addWidget(self.table, 1)

        add_row = QHBoxLayout()
        self.add_row_button = QPushButton("+  Satır Ekle", objectName="secondary")
        self.add_row_button.clicked.connect(self.add_row)
        add_row.addWidget(self.add_row_button)
        add_row.addStretch()
        layout.addLayout(add_row)

        footer = QHBoxLayout()
        self.status_label = QLabel(objectName="muted")
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color:#a23440;")
        self.error_label.setWordWrap(True)
        footer_text = QVBoxLayout()
        footer_text.addWidget(self.status_label)
        footer_text.addWidget(self.error_label)
        footer.addLayout(footer_text, 1)
        cancel = QPushButton("İptal", objectName="secondary")
        self.save_button = QPushButton("Tüm Görevleri Kaydet")
        cancel.clicked.connect(self.reject)
        self.save_button.clicked.connect(self.save_all)
        footer.addWidget(cancel)
        footer.addWidget(self.save_button)
        layout.addLayout(footer)

        for _ in range(3):
            self.add_row(focus=False)
        self._update_status()

    def add_row(self, checked: bool = False, *, focus: bool = True) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        title = QLineEdit()
        title.setPlaceholderText("Görev başlığı")
        title.setMaxLength(200)
        time_edit = QLineEdit()
        time_edit.setPlaceholderText("HH:MM")
        time_edit.setMaxLength(5)
        time_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9:]{0,5}"), time_edit))
        description = QLineEdit()
        description.setPlaceholderText("İsteğe bağlı açıklama")
        remove = QPushButton("Sil", objectName="danger")
        remove.clicked.connect(lambda _checked=False, button=remove: self._remove_button_row(button))
        for editor in (title, time_edit, description):
            editor.textChanged.connect(self._on_row_changed)
        self.table.setCellWidget(row, 0, title)
        self.table.setCellWidget(row, 1, time_edit)
        self.table.setCellWidget(row, 2, description)
        self.table.setCellWidget(row, 3, remove)
        self._update_status()
        if focus:
            title.setFocus(Qt.FocusReason.OtherFocusReason)

    def _remove_button_row(self, button: QPushButton) -> None:
        for row in range(self.table.rowCount()):
            if self.table.cellWidget(row, 3) is button:
                self.table.removeRow(row)
                break
        self._update_status()

    def _on_row_changed(self) -> None:
        editor = self.sender()
        if isinstance(editor, QLineEdit):
            editor.setStyleSheet("")
        self.error_label.clear()
        self._update_status()

    def drafts(self) -> list[BulkTaskDraft]:
        result: list[BulkTaskDraft] = []
        for row in range(self.table.rowCount()):
            title = self.table.cellWidget(row, 0)
            time_edit = self.table.cellWidget(row, 1)
            description = self.table.cellWidget(row, 2)
            result.append(
                BulkTaskDraft(
                    title.text() if isinstance(title, QLineEdit) else "",
                    time_edit.text() if isinstance(time_edit, QLineEdit) else "",
                    description.text() if isinstance(description, QLineEdit) else "",
                )
            )
        return result

    def selected_date(self) -> date:
        value = self.date_edit.date()
        return date(value.year(), value.month(), value.day())

    def _update_status(self) -> None:
        ready = sum(1 for draft in self.drafts() if draft.title.strip())
        incomplete = sum(
            1 for draft in self.drafts()
            if not draft.title.strip() and (draft.time_text.strip() or draft.description.strip())
        )
        text = f"Kaydedilmeye hazır: {ready} görev"
        if incomplete:
            text += f"  •  Hatalı: {incomplete} satır"
        self.status_label.setText(text)

    def _mark_error_rows(self, message: str) -> None:
        for line in message.splitlines():
            prefix = line.split(".", 1)[0]
            if not prefix.isdigit():
                continue
            row = int(prefix) - 1
            if 0 <= row < self.table.rowCount():
                for column in range(3):
                    widget = self.table.cellWidget(row, column)
                    if widget:
                        widget.setStyleSheet("border:2px solid #c94b57;")

    def save_all(self) -> None:
        if self._saving or self._saved:
            return
        self._saving = True
        self.save_button.setEnabled(False)
        self.error_label.clear()
        try:
            count = self.task_service.add_bulk(self.drafts(), self.selected_date())
            self._saved = True
            QMessageBox.information(self, "Toplu Görev Ekle", f"{count} görev başarıyla kaydedildi.")
            self.accept()
        except ValidationError as error:
            message = str(error)
            self.error_label.setText(message.replace("\n", "  •  "))
            self._mark_error_rows(message)
        except (sqlite3.Error, OSError) as error:
            self.error_label.setText(f"Görevler kaydedilemedi: {error}")
        finally:
            self._saving = False
            if not self._saved:
                self.save_button.setEnabled(True)
