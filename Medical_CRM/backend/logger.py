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
    @requires:
        - message передан
        - logger инициализирован

    @modifies:
        - Лог-файл
        - Консольный вывод

    @effects:
        - Записывает информационное сообщение уровня INFO
        - Добавляет context при наличии
        - Используется для бизнес-событий и обычных операций

    @raises:
        - Exception при ошибке logging subsystem

    @returns:
        - None
    """
    
    if context:
        message = f"{message} | {context}"
    logger.info(message)


def log_error(message: str, error: Exception = None, **context):
    """
    @requires:
        - message передан
        - logger инициализирован

    @modifies:
        - Лог-файл
        - Консольный вывод

    @effects:
        - Записывает сообщение уровня ERROR
        - Добавляет текст ошибки (error)
        - Добавляет дополнительный context
        - Используется для ошибок API, БД, JWT и системных сбоев

    @raises:
        - Exception при ошибке logging subsystem

    @returns:
        - None
    """

    if error:
        message = f"{message} | error={str(error)}"
    if context:
        message = f"{message} | {context}"
    logger.error(message)


def log_debug(message: str, **context):
    """
    @requires:
        - message передан
        - logger инициализирован

    @modifies:
        - Лог-файл (если DEBUG включен)
        - Консольный вывод

    @effects:
        - Записывает debug-сообщение
        - Добавляет context
        - Используется для диагностики и разработки

    @raises:
        - Exception при ошибке logging subsystem

    @returns:
        - None
    """
    if context:
        message = f"{message} | {context}"
    logger.debug(message)
