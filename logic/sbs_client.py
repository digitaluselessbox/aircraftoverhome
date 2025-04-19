# sbs_client.py

import socket
import select
import time

class SBSClient:
    def __init__(self, host: str, port: int, logger=None):
        self.host = host
        self.port = port
        self.sock = None
        self.buffer = ""
        self.logger = logger

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        self.sock.setblocking(False)
        self.sock.connect_ex((self.host, self.port))

        ready_to_read, ready_to_write, in_error = select.select([], [self.sock], [], 5)
        if not ready_to_write:
            raise ConnectionError("Verbindung zum dump1090-Server fehlgeschlagen.")
        if self.logger:
            self.logger.info("Verbindung zu Dump1090 hergestellt.")

    def read_lines(self):
        try:
            data = self.sock.recv(8192).decode("utf-8")
            if not data:
                if self.logger:
                    self.logger.warning("Keine Daten vom Socket erhalten.")
                return []

            self.buffer += data
            lines = self.buffer.splitlines()
            self.buffer = lines[-1] if lines else ""
            return lines[:-1]
        except BlockingIOError:
            return []
        except Exception as e:
            if self.logger:
                self.logger.error(f"Fehler beim Lesen vom Socket: {e}")
            return []

    def close(self):
        if self.sock:
            self.sock.close()
            if self.logger:
                self.logger.info("Socket-Verbindung geschlossen.")
