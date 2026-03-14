import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

CONSOLE_FORMAT = "[%(levelname)s] %(message)s"


def setup_logger(
    name: str,
    log_file: str = None,
    level: int = logging.INFO,
    console: bool = True
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()

    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    if log_file:
        file_path = os.path.join(LOG_DIR, log_file)
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


pipeline_logger = setup_logger("pipeline", "pipeline.log")
yt_logger = setup_logger("yt_upload", "yt_upload.log")
ig_logger = setup_logger("ig_upload", "ig_upload.log")
error_logger = setup_logger("error", "error.log", level=logging.ERROR)


class PipelineLogger:
    def __init__(self, step_name: str):
        self.logger = logging.getLogger(f"pipeline.{step_name}")
        self.step_name = step_name
    
    def setLevel(self, level: int):
        """Set the logging level."""
        self.logger.setLevel(level)
    
    def info(self, message: str):
        self.logger.info(f"[{self.step_name}] {message}")

    def error(self, message: str):
        self.logger.error(f"[{self.step_name}] {message}")
        error_logger.error(f"[{self.step_name}] {message}")

    def warning(self, message: str):
        self.logger.warning(f"[{self.step_name}] {message}")

    def debug(self, message: str):
        self.logger.debug(f"[{self.step_name}] {message}")
