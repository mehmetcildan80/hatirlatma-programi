from __future__ import annotations

import sqlite3
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QTimer, QTime, Qt
from PySide6.QtGui import QAction, QColor, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QHBoxLayout, QLabel, QListWidget,
    QMainWindow, QMenu, QMessageBox, QPushButton, QStackedWidget, QStyle,
    QSystemTrayIcon, QTableWidget,
    QTableWidgetItem, QTimeEdit, QVBoxLayout, QWidget, QHeaderView,
)

from hatirlatici.config import database_path
from hatirlatici.data.database import Database
from hatirlatici.data.repositories import ReminderRepository, SettingsRepository, TaskRepository
from hatirlatici.domain.models import Task
from hatirlatici.domain.services import ReminderService, SettingsService, TaskService, ValidationError
from hatirlatici.platform.startup import StartupError, StartupManager
from hatirlatici.ui.reminder_dialog import ReminderDialog
from hatirlatici.ui.styles import APP_STYLE
from hatirlatici.ui.task_dialog import TaskDialog


class MainWindow(QMainWindow):
    def __init__(
        self,
        task_service: TaskService,
        settings_service: SettingsService,
        reminder_service: ReminderService,
        startup_manager: StartupManager,
    ) -> None:
        super().__init__()
        self.task_service = task_service
        self.settings_service = settings_service
        self.reminder_service = reminder_service
        self.startup_manager = startup_manager
        self.current_filter = "today"
        self.tasks: list[Task] = []
        self.reminder_dialog: ReminderDialog | None = None
        self._really_quit = False
        self.setWindowTitle("Hatırlatıcı")
        self.resize(980, 620)
        self.setMinimumSize(820, 520)
        self.setStyleSheet(APP_STYLE)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame(objectName="sidebar")
        sidebar.setFixedWidth(205)
        side_layout = QVBoxLayout(sidebar)
        brand = QLabel("HATIRLATICI", objectName="brand")
        brand_caption = QLabel("Görev ve hatırlatma", objectName="brandCaption")
        self.navigation = QListWidget(objectName="navigation")
        for label in ("Bugün", "Yarın", "Tüm Görevler", "Yeni Görev", "Ayarlar"):
            self.navigation.addItem(label)
        side_layout.addWidget(brand)
        side_layout.addWidget(brand_caption)
        side_layout.addWidget(self.navigation)

        self.stack = QStackedWidget()
        self.tasks_page = self._create_tasks_page()
        self.settings_page = self._create_settings_page()
        self.stack.addWidget(self.tasks_page)
        self.stack.addWidget(self.settings_page)
        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self.navigation.currentRowChanged.connect(self._navigate)
        self.navigation.setCurrentRow(0)
        self._create_tray_icon()
        self.reminder_timer = QTimer(self)
        self.reminder_timer.setInterval(30_000)
        self.reminder_timer.timeout.connect(self.check_reminder)
        self.reminder_timer.start()

    def _create_tray_icon(self) -> None:
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView)
        self.setWindowIcon(icon)
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Hatırlatıcı")
        menu = QMenu(self)
        open_action = QAction("Uygulamayı Aç", self)
        tomorrow_action = QAction("Yarınki Görevleri Göster", self)
        exit_action = QAction("Çıkış", self)
        open_action.triggered.connect(self.show_main_window)
        tomorrow_action.triggered.connect(self.show_tomorrow)
        exit_action.triggered.connect(self.quit_application)
        menu.addAction(open_action)
        menu.addAction(tomorrow_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()

    def _create_tasks_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(14)
        page_header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(2)
        self.page_title = QLabel("Bugün", objectName="pageTitle")
        self.page_caption = QLabel("Görevlerinizi düzenleyin ve durumlarını takip edin.", objectName="pageCaption")
        heading.addWidget(self.page_title)
        heading.addWidget(self.page_caption)
        page_header.addLayout(heading, 1)
        header_add_button = QPushButton("+  Yeni Görev")
        header_add_button.clicked.connect(self.add_task)
        page_header.addWidget(header_add_button, 0, Qt.AlignmentFlag.AlignVCenter)
        self.empty_label = QLabel()
        self.empty_label.setObjectName("muted")
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Durum", "Başlık", "Tarih", "Saat", "Açıklama"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(46)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self.edit_selected)

        button_row = QHBoxLayout()
        edit_button = QPushButton("Düzenle", objectName="secondary")
        complete_button = QPushButton("Tamamlandı / Açık", objectName="secondary")
        delete_button = QPushButton("Sil", objectName="danger")
        edit_button.clicked.connect(self.edit_selected)
        complete_button.clicked.connect(self.toggle_selected)
        delete_button.clicked.connect(self.delete_selected)
        for button in (edit_button, complete_button, delete_button):
            button_row.addWidget(button)
        button_row.addStretch()

        layout.addLayout(page_header)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.table, 1)
        layout.addLayout(button_row)
        return page

    def _create_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(14)
        layout.addWidget(QLabel("Ayarlar", objectName="pageTitle"))
        layout.addWidget(QLabel("Hatırlatma ve Windows başlangıç tercihlerinizi yönetin.", objectName="pageCaption"))
        card = QFrame(objectName="settingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 20)
        card_layout.setSpacing(12)
        reminder_title = QLabel("Genel hatırlatma saati")
        reminder_title.setStyleSheet("font-weight:700; font-size:15px;")
        card_layout.addWidget(reminder_title)
        card_layout.addWidget(QLabel("Her gün bu saatte ertesi günün açık görevleri kontrol edilir.", objectName="muted"))
        self.reminder_time = QTimeEdit()
        self.reminder_time.setDisplayFormat("HH:mm")
        self.reminder_time.setMaximumWidth(140)
        self.start_with_windows = QCheckBox("Windows ile birlikte başlat")
        save_button = QPushButton("Ayarı Kaydet")
        save_button.setMaximumWidth(160)
        save_button.clicked.connect(self.save_settings)
        card_layout.addWidget(self.reminder_time)
        card_layout.addSpacing(6)
        card_layout.addWidget(self.start_with_windows)
        card_layout.addWidget(QLabel("Uygulama oturum açıldığında ana pencereyi göstermeden sistem tepsisinde başlar.", objectName="muted"))
        card_layout.addSpacing(6)
        card_layout.addWidget(save_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _navigate(self, row: int) -> None:
        if row in (0, 1, 2):
            self.current_filter = ("today", "tomorrow", "all")[row]
            self.page_title.setText(("Bugün", "Yarın", "Tüm Görevler")[row])
            self.stack.setCurrentWidget(self.tasks_page)
            self.refresh_tasks()
        elif row == 3:
            self.add_task()
            self.navigation.setCurrentRow(("today", "tomorrow", "all").index(self.current_filter))
        elif row == 4:
            value = self.settings_service.get_reminder_time()
            self.reminder_time.setTime(QTime(value.hour, value.minute))
            self.start_with_windows.setChecked(self.startup_manager.is_enabled())
            self.stack.setCurrentWidget(self.settings_page)

    def _selected_task(self) -> Task | None:
        row = self.table.currentRow()
        return self.tasks[row] if 0 <= row < len(self.tasks) else None

    def refresh_tasks(self) -> None:
        try:
            self.tasks = self.task_service.list_for(self.current_filter)
            self.table.setRowCount(len(self.tasks))
            for row, task in enumerate(self.tasks):
                values = [
                    "Tamamlandı" if task.completed else "Açık",
                    task.title,
                    task.due_date.strftime("%d.%m.%Y"),
                    task.due_time.strftime("%H:%M") if task.due_time else "—",
                    task.description,
                ]
                for column, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if task.completed:
                        item.setForeground(QColor("#718096"))
                        item.setBackground(QColor("#edf8f1"))
                    item.setToolTip(value)
                    self.table.setItem(row, column, item)
            self.empty_label.setText("Bu bölümde görev bulunmuyor." if not self.tasks else f"{len(self.tasks)} görev")
        except (sqlite3.Error, OSError, ValueError) as error:
            self._show_error("Görevler yüklenemedi.", error)

    def add_task(self) -> None:
        dialog = TaskDialog(self)
        if dialog.exec() == TaskDialog.DialogCode.Accepted:
            try:
                self.task_service.add(dialog.task_value())
                self.refresh_tasks()
            except (ValidationError, sqlite3.Error, OSError) as error:
                self._show_error("Görev kaydedilemedi.", error)

    def edit_selected(self) -> None:
        task = self._selected_task()
        if not task:
            QMessageBox.information(self, "Görev Seçin", "Düzenlemek için bir görev seçin.")
            return
        dialog = TaskDialog(self, task)
        if dialog.exec() == TaskDialog.DialogCode.Accepted:
            try:
                self.task_service.update(dialog.task_value())
                self.refresh_tasks()
            except (ValidationError, sqlite3.Error, OSError) as error:
                self._show_error("Görev güncellenemedi.", error)

    def toggle_selected(self) -> None:
        task = self._selected_task()
        if not task:
            QMessageBox.information(self, "Görev Seçin", "Durumunu değiştirmek için bir görev seçin.")
            return
        try:
            self.task_service.set_completed(task.id, not task.completed)  # type: ignore[arg-type]
            self.refresh_tasks()
        except (ValidationError, sqlite3.Error, OSError) as error:
            self._show_error("Görev durumu güncellenemedi.", error)

    def delete_selected(self) -> None:
        task = self._selected_task()
        if not task:
            QMessageBox.information(self, "Görev Seçin", "Silmek için bir görev seçin.")
            return
        answer = QMessageBox.question(
            self, "Görevi Sil", f"“{task.title}” görevini silmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            try:
                self.task_service.delete(task.id)  # type: ignore[arg-type]
                self.refresh_tasks()
            except (ValidationError, sqlite3.Error, OSError) as error:
                self._show_error("Görev silinemedi.", error)

    def save_settings(self) -> None:
        selected = self.reminder_time.time()
        try:
            from datetime import time
            self.settings_service.set_reminder_time(time(selected.hour(), selected.minute()))
            self.startup_manager.set_enabled(self.start_with_windows.isChecked())
            QMessageBox.information(self, "Ayarlar", "Genel hatırlatma saati kaydedildi.")
            self.check_reminder()
        except (sqlite3.Error, OSError, ValueError, StartupError) as error:
            self._show_error("Ayar kaydedilemedi.", error)

    def check_reminder(self) -> None:
        if self.reminder_dialog and self.reminder_dialog.isVisible():
            return
        try:
            due = self.reminder_service.check_due()
            if not due:
                return
            dialog = ReminderDialog(due, self)
            dialog.acknowledged.connect(self._acknowledge_reminder)
            dialog.snoozed.connect(self._snooze_reminder)
            self.reminder_dialog = dialog
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
        except (ValidationError, sqlite3.Error, OSError, ValueError) as error:
            self._show_error("Hatırlatma kontrol edilemedi.", error)

    def _acknowledge_reminder(self) -> None:
        if not self.reminder_dialog:
            return
        try:
            self.reminder_service.acknowledge(self.reminder_dialog.due.reminder_date)
            self.reminder_dialog.close()
        except (ValidationError, sqlite3.Error, OSError) as error:
            self._show_error("Hatırlatma onaylanamadı.", error)

    def _snooze_reminder(self) -> None:
        if not self.reminder_dialog:
            return
        try:
            self.reminder_service.snooze(self.reminder_dialog.due.reminder_date, 10)
            self.reminder_dialog.close()
        except (ValidationError, sqlite3.Error, OSError) as error:
            self._show_error("Hatırlatma ertelenemedi.", error)

    def show_main_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def show_tomorrow(self) -> None:
        self.show_main_window()
        self.navigation.setCurrentRow(1)

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_main_window()

    def quit_application(self) -> None:
        self._really_quit = True
        self.tray_icon.hide()
        QApplication.instance().quit()  # type: ignore[union-attr]

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._really_quit:
            event.accept()
        else:
            event.ignore()
            self.hide()

    def _show_error(self, message: str, error: Exception) -> None:
        QMessageBox.critical(self, "Hata", f"{message}\n\nAyrıntı: {error}")


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Hatırlatıcı")
    app.setQuitOnLastWindowClosed(False)
    try:
        database = Database(database_path())
        database.initialize()
        task_repository = TaskRepository(database)
        settings_service = SettingsService(SettingsRepository(database))
        window = MainWindow(
            TaskService(task_repository),
            settings_service,
            ReminderService(task_repository, ReminderRepository(database), settings_service),
            StartupManager(Path(__file__).resolve().parents[2] / "app.py"),
        )
        started_by_windows = "--startup" in sys.argv[1:]
        if not started_by_windows:
            window.show()
        QTimer.singleShot(0, window.check_reminder)
        return app.exec()
    except (sqlite3.Error, OSError) as error:
        QMessageBox.critical(None, "Başlatma Hatası", f"Uygulama başlatılamadı.\n\nAyrıntı: {error}")
        return 1
