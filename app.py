from __future__ import annotations

from hatirlatici.platform.logging_setup import configure_logging, log_event


def main() -> int:
    configure_logging()
    try:
        from hatirlatici.ui.main_window import run

        return run()
    except Exception as error:
        log_event("unexpected_crash", error_type=type(error).__name__)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
