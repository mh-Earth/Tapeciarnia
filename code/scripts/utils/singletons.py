
# ============================================================
#  SINGLE INSTANCE (QLockFile + QLocalServer FOR IPC)
# ============================================================


from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Signal, QLockFile, QDir
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from models.config import Config
import logging
import os


class SingleApplication(QApplication):
    message_received = Signal(str)

    SERVER_NAME = "Tapeciarnia_IPC"
    LOCKFILE_NAME = "Tapeciarnia.lock"

    def __init__(self, argv):
        super().__init__(argv)

        # -----------------------------
        # 1. TRUE SINGLE INSTANCE LOCK
        # -----------------------------
        lock_dir = QDir.tempPath()
        self.lockfile_path = os.path.join(lock_dir, self.LOCKFILE_NAME)

        self.lockfile = QLockFile(self.lockfile_path)
        self.lockfile.setStaleLockTime(0)

        # Attempt to lock
        if not self.lockfile.tryLock(100):
            # Another instance already running → send args then exit
            self._send_message_to_primary(argv)
            self.is_primary_instance = False
            return

        # This is the primary instance
        self.is_primary_instance = True

        # -----------------------------
        # 2. IPC SERVER FOR MESSAGE PASSING
        # -----------------------------
        self.server = QLocalServer(self)

        # In case of stale pipe (after crash)
        QLocalServer.removeServer(self.SERVER_NAME)

        if self.server.listen(self.SERVER_NAME):
            self.server.newConnection.connect(self._on_new_connection)
            logging.info("Primary instance started (lock + IPC OK)")
        else:
            logging.error(f"IPC failed: {self.server.errorString()}")

    # Primary receives connection from secondary instance
    def _on_new_connection(self):
        socket = self.server.nextPendingConnection()
        if not socket:
            return

        if socket.waitForReadyRead(2000):
            message = bytes(socket.readAll()).decode("utf-8")
            logging.info(f"Primary received: {message}")
            self.message_received.emit(message)

        socket.disconnectFromServer()
        socket.deleteLater()

    # Secondary → send args to primary then quit
    def _send_message_to_primary(self, argv):
        message = " ".join(argv[1:]) if len(argv) > 1 else ""

        socket = QLocalSocket()
        socket.connectToServer(self.SERVER_NAME)

        if socket.waitForConnected(1000):
            socket.write(message.encode("utf-8"))
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
            logging.info("Secondary instance passed message to primary.")
        else:
            logging.error("Could not connect to primary. (Failsafe: multiple instances allowed)")



_config_instance: Config | None = None

def get_config() -> Config:
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
