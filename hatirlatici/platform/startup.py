from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


SHORTCUT_NAME = "Hatirlatici.lnk"


class StartupError(RuntimeError):
    pass


class StartupManager:
    def __init__(self, app_script: Path) -> None:
        self.app_script = app_script.resolve()

    @staticmethod
    def startup_dir() -> Path:
        app_data = os.environ.get("APPDATA")
        if not app_data:
            raise StartupError("Windows kullanıcı Startup klasörü bulunamadı.")
        return Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

    def shortcut_path(self) -> Path:
        return self.startup_dir() / SHORTCUT_NAME

    def is_enabled(self) -> bool:
        try:
            return self.shortcut_path().is_file()
        except StartupError:
            return False

    def set_enabled(self, enabled: bool) -> None:
        shortcut = self.shortcut_path()
        if not enabled:
            if shortcut.exists():
                shortcut.unlink()
            return

        shortcut.parent.mkdir(parents=True, exist_ok=True)
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        executable = pythonw if pythonw.exists() else Path(sys.executable)
        command = (
            "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:HATIRLATICI_SHORTCUT);"
            "$s.TargetPath=$env:HATIRLATICI_TARGET;"
            "$s.Arguments='\"'+$env:HATIRLATICI_SCRIPT+'\" --startup';"
            "$s.WorkingDirectory=$env:HATIRLATICI_WORKING;"
            "$s.Description='Hatırlatıcı';$s.Save()"
        )
        process_environment = os.environ.copy()
        process_environment.update(
            {
                "HATIRLATICI_SHORTCUT": str(shortcut),
                "HATIRLATICI_TARGET": str(executable),
                "HATIRLATICI_SCRIPT": str(self.app_script),
                "HATIRLATICI_WORKING": str(self.app_script.parent),
            }
        )
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=process_environment,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0 or not shortcut.is_file():
            detail = result.stderr.strip() or "Kısayol oluşturulamadı."
            raise StartupError(detail)
