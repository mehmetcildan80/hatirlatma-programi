from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from hatirlatici.config import log_dir


LOGGER_NAME = "hatirlatici"
LOG_FILE_NAME = "hatirlatici.log"
MAX_LOG_BYTES = 512 * 1024
BACKUP_COUNT = 3
_SAFE_FIELDS = {"reason", "count", "status", "error_type", "version"}


def configure_logging(directory: Path | None = None) -> logging.Logger:
    """Kişisel görev içeriği almayan, dönen uygulama günlüğünü hazırlar."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if any(getattr(handler, "_hatirlatici_handler", False) for handler in logger.handlers):
        return logger
    try:
        target_dir = Path(directory) if directory is not None else log_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            target_dir / LOG_FILE_NAME,
            maxBytes=MAX_LOG_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        handler._hatirlatici_handler = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    except OSError:
        if not logger.handlers:
            logger.addHandler(logging.NullHandler())
    return logger


def log_event(event: str, **fields: object) -> None:
    """Yalnızca önceden tanımlı teknik alanları yazar; görev içeriği kabul etmez."""
    safe = [f"event={event}"]
    safe.extend(f"{key}={fields[key]}" for key in sorted(fields) if key in _SAFE_FIELDS)
    configure_logging().info(" ".join(safe))


def reset_logging_for_tests() -> None:
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
