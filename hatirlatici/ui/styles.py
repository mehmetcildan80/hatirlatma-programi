APP_STYLE = """
* { font-family: "Segoe UI"; font-size: 13px; color: #253347; }
QMainWindow, QDialog { background: #f5f7fa; }
QFrame#sidebar { background: #17283f; border: 0; }
QLabel#brand { color: white; font-size: 19px; font-weight: 700; padding: 22px 14px 14px; }
QLabel#brandCaption { color: #9fb1c5; font-size: 11px; padding: 0 14px 18px; }
QListWidget#navigation { background: transparent; color: #dce6f1; border: 0; outline: 0; }
QListWidget#navigation::item { color: #dce6f1; padding: 12px 15px; margin: 2px 9px; border-radius: 7px; }
QListWidget#navigation::item:hover { background: #223b5a; }
QListWidget#navigation::item:selected { background: #286da8; color: white; }
QLabel#pageTitle { color: #17283f; font-size: 25px; font-weight: 700; }
QLabel#pageCaption, QLabel#muted { color: #66758a; }
QFrame#panel, QFrame#settingsCard, QFrame#taskCard { background: white; border: 1px solid #dce3eb; border-radius: 10px; }
QTableWidget { background: white; alternate-background-color: #f8fafc; border: 1px solid #dce3eb; border-radius: 9px; gridline-color: #edf1f5; selection-background-color: #e3f0fb; selection-color: #17283f; }
QHeaderView::section { background: #eef3f7; color: #42536a; padding: 10px 8px; border: 0; border-bottom: 1px solid #dce3eb; font-weight: 600; }
QLineEdit, QPlainTextEdit, QDateEdit, QTimeEdit { background: white; border: 1px solid #cbd5e1; border-radius: 7px; padding: 8px; selection-background-color: #2f78b7; }
QLineEdit:focus, QPlainTextEdit:focus, QDateEdit:focus, QTimeEdit:focus { border: 2px solid #2f78b7; }
QLineEdit, QDateEdit, QTimeEdit { min-height: 22px; }
QPushButton { background: #2f78b7; color: white; border: 0; border-radius: 7px; padding: 9px 16px; min-height: 20px; font-weight: 600; }
QPushButton:hover { background: #25669e; }
QPushButton:pressed { background: #1f5685; }
QPushButton#secondary { background: #e8eef4; color: #30445b; }
QPushButton#secondary:hover { background: #dbe5ee; }
QPushButton#danger { background: #fff0f1; color: #a23440; }
QPushButton#danger:hover { background: #fbdfe2; }
QCheckBox { spacing: 8px; }
QScrollArea { border: 0; background: transparent; }
QToolTip { background: #17283f; color: white; border: 0; padding: 5px; }
"""
