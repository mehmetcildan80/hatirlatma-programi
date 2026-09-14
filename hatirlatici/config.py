from __future__ import annotations

import os
from pathlib import Path


APP_FOLDER_NAME = "Hatirlatici"
DATABASE_FILE_NAME = "hatirlatici.db"


def application_data_dir() -> Path:
    """Kullanıcının yazabildiği yerel uygulama veri klasörünü döndürür."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_FOLDER_NAME
    # Windows dışındaki geliştirme/test ortamlarında güvenli geri dönüş.
    return Path.home() / ".local" / "share" / APP_FOLDER_NAME


def database_path() -> Path:
    return application_data_dir() / DATABASE_FILE_NAME

