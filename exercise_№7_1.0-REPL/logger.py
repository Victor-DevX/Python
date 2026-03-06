import logging
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "logs.txt")

logger = logging.getLogger("farm_market_app")
logger.setLevel(logging.INFO)

# Удаляем все обработчики
if logger.hasHandlers():
    logger.handlers.clear()

# Добавляем только файловый обработчик
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)