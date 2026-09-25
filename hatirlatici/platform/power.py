from __future__ import annotations

import sys
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal


WM_POWERBROADCAST = 0x0218
PBT_APMRESUMESUSPEND = 0x0007
PBT_APMRESUMEAUTOMATIC = 0x0012


class PowerResumeWatcher(QObject, QAbstractNativeEventFilter):
    """Windows uyku dönüşünü Qt olay döngüsüne güvenli bir sinyal olarak taşır."""

    resumed = Signal()

    def nativeEventFilter(self, event_type, message):  # type: ignore[no-untyped-def]
        if sys.platform == "win32" and event_type in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            try:
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_POWERBROADCAST and msg.wParam in (
                    PBT_APMRESUMESUSPEND,
                    PBT_APMRESUMEAUTOMATIC,
                ):
                    self.resumed.emit()
            except (TypeError, ValueError, OSError):
                # Geçersiz yerel ileti uygulamanın olay döngüsünü bozmamalıdır.
                pass
        return False, 0
