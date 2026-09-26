from __future__ import annotations

import getpass
import hashlib

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


def user_server_name() -> str:
    identity = getpass.getuser().encode("utf-8", errors="replace")
    return f"Hatirlatici-{hashlib.sha256(identity).hexdigest()[:16]}"


class SingleInstanceGuard(QObject):
    show_requested = Signal()

    def __init__(self, name: str | None = None) -> None:
        super().__init__()
        self.name = name or user_server_name()
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._receive)
        self.is_primary = False

    def acquire(self) -> bool:
        probe = QLocalSocket()
        probe.connectToServer(self.name)
        if probe.waitForConnected(250):
            probe.write(b"SHOW")
            probe.flush()
            probe.waitForBytesWritten(250)
            probe.disconnectFromServer()
            return False

        # Yalnızca bağlantı kurulamadığında önceki çökmeye ait sahipsiz uç temizlenir.
        QLocalServer.removeServer(self.name)
        self.is_primary = self.server.listen(self.name)
        return self.is_primary

    def _receive(self) -> None:
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            # Bu kullanıcıya özel yerel uca bağlanabilen ikincil örneğin tek
            # anlamlı isteği çalışan pencereyi öne getirmektir. Bağlantı olayı
            # yeterlidir; istemci hızlı kapanırsa veri paketine bağımlı kalmayız.
            self.show_requested.emit()
            socket.readAll()
            socket.disconnectFromServer()
            socket.deleteLater()

    def close(self) -> None:
        if self.server.isListening():
            self.server.close()
            QLocalServer.removeServer(self.name)
        self.is_primary = False
