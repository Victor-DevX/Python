# -*- coding: utf-8 -*-
import logging
import os
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "crm_logs.txt")

logger = logging.getLogger("medical_crm")
logger.setLevel(logging.INFO)

if logger.hasHandlers():
    logger.handlers.clear()

file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=2 * 1024 * 1024,  # 2 MB
    backupCount=3,
    encoding="utf-8"
)
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

def log_info(message: str, **context):
    """
    Логирование информационных событий
    """
    if context:
        message = f"{message} | {context}"
    logger.info(message)


def log_error(message: str, error: Exception = None, **context):
    """
    Логирование ошибок
    """
    if error:
        message = f"{message} | error={str(error)}"
    if context:
        message = f"{message} | {context}"
    logger.error(message)


def log_debug(message: str, **context):
    """
    Логирование отладочной информации
    """
    if context:
        message = f"{message} | {context}"
    logger.debug(message)