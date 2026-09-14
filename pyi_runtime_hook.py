"""PyInstaller altında PySide6 DLL dizinini Windows aramasına kaydeder."""

from __future__ import annotations

import os
import sys
from pathlib import Path


if sys.platform == "win32" and hasattr(sys, "_MEIPASS"):
    qt_dll_dir = Path(sys._MEIPASS) / "PySide6"  # type: ignore[attr-defined]
    if qt_dll_dir.is_dir():
        os.environ["PATH"] = f"{qt_dll_dir}{os.pathsep}{os.environ.get('PATH', '')}"
        if hasattr(os, "add_dll_directory"):
            # Tutamacın ömrü uygulama süresince devam etmelidir.
            sys._hatirlatici_qt_dll_handle = os.add_dll_directory(qt_dll_dir)  # type: ignore[attr-defined]

