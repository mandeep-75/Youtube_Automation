import os
import sys
import logging

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

os.makedirs(LOGS_DIR, exist_ok=True)


def get_logger(name: str, log_file: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        "%(asctime)s │ %(levelname)-8s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_youtube_logger() -> logging.Logger:
    return get_logger("youtube", os.path.join(LOGS_DIR, "youtube_upload.log"))


def get_instagram_logger() -> logging.Logger:
    return get_logger("instagram", os.path.join(LOGS_DIR, "instagram_upload.log"))


def get_auto_upload_logger() -> logging.Logger:
    return get_logger("auto_upload", os.path.join(LOGS_DIR, "auto_upload.log"))
