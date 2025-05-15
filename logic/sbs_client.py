import socket
import time
import logging


class SBSClient:
    def __init__(self, config, logger=None):
        self.config = config
        self.sock = None
        self.buffer = ""
        self.logger = logger or logging.getLogger(__name__)
        self.last_data_time = time.time()

    def connect(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.config.HOST, self.config.PORT))
                self.logger.info(f"Verbindung zu Dump1090 hergestellt: {self.config.HOST}:{self.config.PORT}")
                self.buffer = ""
                self.last_data_time = time.time()
                break
            except Exception as e:
                self.logger.warning(f"Verbindung fehlgeschlagen, neuer Versuch in 5s: {e}")
                time.sleep(5)

    def reconnect(self):
        try:
            self.close()
        except:
            pass
        self.logger.info("Verbindung wird neu aufgebaut...")
        self.connect()

    def read_lines(self, timeout=60):
        try:
            data = self.sock.recv(8192).decode("utf-8")
            if not data:
                if time.time() - self.last_data_time > timeout:
                    self.logger.warning("Verbindung scheint tot zu sein – Reconnect wird durchgeführt.")
                    self.reconnect()
                return []

            self.last_data_time = time.time()
            self.buffer += data
            lines = self.buffer.splitlines()
            self.buffer = lines[-1] if lines else ""
            return lines[:-1]
        except socket.timeout:
            return []
        except socket.error as e:
            self.logger.error(f"Socket-Fehler beim Lesen: {e}")
            self.reconnect()
            return []
        except Exception as e:
            self.logger.error(f"Allgemeiner Fehler beim Lesen: {e}")
            self.reconnect()
            return []

    def close(self):
        if self.sock:
            try:
                self.sock.close()
                self.logger.info("Verbindung zu Dump1090 geschlossen.")
            except Exception as e:
                self.logger.error(f"Fehler beim Schließen des Sockets: {e}")
