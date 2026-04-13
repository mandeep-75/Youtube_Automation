# utils/logger.py
# ─────────────────────────────────────────────────────────────────────────────
# Logging utility for YouTube automation pipeline
# Provides consistent logging to both console and file
# ─────────────────────────────────────────────────────────────────────────────

import logging
import os
import sys
from datetime import datetime
from pathlib import Path


def setup_logger(
    name: str = "youtube_automation",
    log_dir: str = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Create and configure a logger for the pipeline.

    Args:
        name: Logger name
        log_dir: Directory for log files (default: PROJECT_ROOT/logs)
        level: Logging level

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Default to logs directory in project root
    if log_dir is None:
        project_root = Path(__file__).parent.parent.parent
        log_dir = project_root / "logs"

    os.makedirs(log_dir, exist_ok=True)

    # Console handler with emoji formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # File handler
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(log_dir, f"pipeline_{timestamp}.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)

    # Console format (with emojis)
    console_format = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_format)

    # File format (with timestamps)
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# Default logger instance
default_logger = setup_logger()


def log_step(step_num: int, step_name: str, logger=None) -> None:
    """
    Log a pipeline step header.

    Args:
        step_num: Step number (1-8)
        step_name: Step description
        logger: Optional logger instance
    """
    if logger is None:
        logger = default_logger

    border = "─" * 64
    logger.info(f"\n{border}")
    logger.info(f"Step {step_num}  {step_name}")
    logger.info(border)


def log_success(message: str, logger=None) -> None:
    """Log a success message with checkmark emoji."""
    if logger is None:
        logger = default_logger
    logger.info(f"✅ {message}")


def log_error(message: str, logger=None) -> None:
    """Log an error message."""
    if logger is None:
        logger = default_logger
    logger.error(f"❌ {message}")


def log_warning(message: str, logger=None) -> None:
    """Log a warning message."""
    if logger is None:
        logger = default_logger
    logger.warning(f"⚠️  {message}")


def log_info(message: str, logger=None) -> None:
    """Log an info message."""
    if logger is None:
        logger = default_logger
    logger.info(f"ℹ️  {message}")


def log_debug(message: str, logger=None) -> None:
    """Log a debug message."""
    if logger is None:
        logger = default_logger
    logger.debug(f"🐛 {message}")
