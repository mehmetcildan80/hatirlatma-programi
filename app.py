from __future__ import annotations

import os
import traceback
from pathlib import Path


def _write_crash_log() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Hatirlatici"
    base.mkdir(parents=True, exist_ok=True)
    log_path = base / "hatirlatici.log"
    log_path.write_text(traceback.format_exc(), encoding="utf-8")
    return log_path


def main() -> int:
    try:
        from hatirlatici.ui.main_window import run

        return run()
    except Exception:
        try:
            _write_crash_log()
        except OSError:
            pass
        raise


if __name__ == "__main__":
    raise SystemExit(main())
