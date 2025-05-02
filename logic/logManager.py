# logManager.py

import os
import logging
from logging.handlers import RotatingFileHandler

class LogManager:
    def __init__(self, config):
        self.config = config
        
        self.main_logger = None
        self.debug_logger = None
        self.lines_logger = None

        self._setup_logging()
    
    def _setup_logging(self):
        log_dir = self.config.LOG_DIRECTORY
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(f"{log_dir}/lines", exist_ok=True)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        # Main Logger
        self.main = logging.getLogger("main_logger")
        main_handler = RotatingFileHandler(f"{log_dir}/adsb_over_home.log", maxBytes=512000, backupCount=10)
        main_handler.setFormatter(formatter)
        self.main.setLevel(logging.INFO)
        self.main.addHandler(main_handler)

        
        # Debug Logger
        self.debug = logging.getLogger("debug_logger")
        debug_handler = RotatingFileHandler(f"{log_dir}/adsb_over_home_debug.log", maxBytes=512000, backupCount=100)
        debug_handler.setFormatter(formatter)
        self.debug.setLevel(logging.DEBUG)
        self.debug.addHandler(debug_handler)


        # Lines Logger
        self.lines = logging.getLogger("lines_logger")
        lines_handler = RotatingFileHandler(f"{log_dir}/lines/adsb_over_home_lines.log", maxBytes=1024000, backupCount=100)
        lines_handler.setFormatter(formatter)
        self.lines.setLevel(logging.DEBUG)
        self.lines.addHandler(lines_handler)
