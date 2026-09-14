from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SHORTCUT_NAME = "Hatirlatici.lnk"


class StartupError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StartupLaunch:
    executable: Path
    arguments: str
    working_directory: Path


def startup_launch(
    app_script: Path,
    *,
    frozen: bool | None = None,
    executable: Path | None = None,
) -> StartupLaunch:
    """Kaynak kod ve paketlenmiş EXE için güvenli başlangıç komutunu üretir."""
    app_script = app_script.resolve()
    runtime = (executable or Path(sys.executable)).resolve()
    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    if is_frozen:
        return StartupLaunch(runtime, "--startup", runtime.parent)

    pythonw = runtime.with_name("pythonw.exe")
    interpreter = pythonw if pythonw.exists() else runtime
    return StartupLaunch(interpreter, f'"{app_script}" --startup', app_script.parent)


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
        launch = startup_launch(self.app_script)
        command = (
            "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:HATIRLATICI_SHORTCUT);"
            "$s.TargetPath=$env:HATIRLATICI_TARGET;"
            "$s.Arguments=$env:HATIRLATICI_ARGUMENTS;"
            "$s.WorkingDirectory=$env:HATIRLATICI_WORKING;"
            "$s.Description='Hatırlatıcı';$s.Save()"
        )
        process_environment = os.environ.copy()
        process_environment.update(
            {
                "HATIRLATICI_SHORTCUT": str(shortcut),
                "HATIRLATICI_TARGET": str(launch.executable),
                "HATIRLATICI_ARGUMENTS": launch.arguments,
                "HATIRLATICI_WORKING": str(launch.working_directory),
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
