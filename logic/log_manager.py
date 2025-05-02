import os
import logging
from logging.handlers import RotatingFileHandler

class LogManager:
    def __init__(self, config):
        self.config = config
        self._loggers = {}  # interne Registry
        self._setup_logs()

    def _setup_logs(self):
        log_dir = self.config.LOG_DIRECTORY
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(f"{log_dir}/lines", exist_ok=True)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        self._register_logger(
            name="main",
            path=f"{log_dir}/adsb_over_home.log",
            level=logging.INFO,
            formatter=formatter,
            max_bytes=512_000,
            backup_count=10,
        )

        self._register_logger(
            name="debug",
            path=f"{log_dir}/adsb_over_home_debug.log",
            level=logging.DEBUG,
            formatter=formatter,
            max_bytes=512_000,
            backup_count=100,
        )

        self._register_logger(
            name="lines",
            path=f"{log_dir}/lines/adsb_over_home_lines.log",
            level=logging.DEBUG,
            formatter=formatter,
            max_bytes=1_024_000,
            backup_count=100,
        )

    def _register_logger(self, name, path, level, formatter, max_bytes, backup_count):
        logger = logging.getLogger(name)
        handler = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count)
        handler.setFormatter(formatter)
        logger.setLevel(level)
        logger.addHandler(handler)
        logger.propagate = False  # verhindert doppelte Ausgaben auf root logger
        self._loggers[name] = logger

    def get_logger(self, name):
        return self._loggers.get(name, logging.getLogger("default"))

    def set_level(self, name, level):
        logger = self._loggers.get(name)
        if logger:
            logger.setLevel(level)
