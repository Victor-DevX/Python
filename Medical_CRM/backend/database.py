# backend/database.py
import os
from dotenv import load_dotenv
load_dotenv() 
from pymongo import MongoClient
import gridfs
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from logger import log_info, log_error


# Конфигурация подключения к PostgreSQL (из переменных окружения)
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

"""
@requires:
    - Переменные окружения DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT заданы

@modifies:
    - Ничего

@effects:
    - Формирует конфигурацию подключения PostgreSQL

@raises:
    - RuntimeError позже, если конфигурация неполная

@returns:
    - dict параметров подключения PostgreSQL
"""

# Проверка наличия всех параметров подключения к БД
if not all(DB_CONFIG.values()):
    raise RuntimeError(f"DB_CONFIG is incomplete: {DB_CONFIG}")


# Подключение к MongoDB (используется для хранения файлов)
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

client = MongoClient(MONGO_URL)
"""
@requires:
    - MONGO_URL валиден
    - MongoDB доступен

@modifies:
    - Создает MongoDB client connection

@effects:
    - Инициализирует подключение к MongoDB

@raises:
    - Exception при ошибке подключения

@returns:
    - MongoClient instance
"""


db = client["medical_crm"]
"""
@requires:
    - MongoClient инициализирован

@modifies:
    - Ничего

@effects:
    - Предоставляет доступ к MongoDB database medical_crm

@raises:
    - Exception при ошибке доступа

@returns:
    - MongoDB database object
"""


fs = gridfs.GridFS(db)
"""
@requires:
    - MongoDB database доступна

@modifies:
    - Ничего

@effects:
    - Инициализирует GridFS для хранения файлов

@raises:
    - Exception при ошибке GridFS

@returns:
    - GridFS instance
"""


# Пул соединений PostgreSQL (оптимизация производительности и повторное использование соединений)
# Создаем пул соединений (мин 1, макс 10)
# ThreadedConnectionPool важен для FastAPI, так как он работает в многопоточном режиме
pool = ThreadedConnectionPool(1, 10, **DB_CONFIG)
"""
@requires:
    - DB_CONFIG полный
    - PostgreSQL доступен

@modifies:
    - Создает пул соединений PostgreSQL

@effects:
    - Управляет многопоточными подключениями
    - Оптимизирует повторное использование соединений

@raises:
    - Exception при ошибке подключения к PostgreSQL

@returns:
    - ThreadedConnectionPool instance
"""


@contextmanager
def get_db_cursor():
    """
    @requires:
        - pool инициализирован
        - PostgreSQL доступен
        - Соединение может быть получено из пула

    @modifies:
        - Выделяет и возвращает соединение из пула
        - Выполняет commit/rollback
        - Логи системы

    @effects:
        - Предоставляет RealDictCursor
        - Автоматически:
            * commit при успехе
            * rollback при ошибке
            * возврат соединения в пул

    @raises:
        - Exception при SQL ошибках
        - Exception при ошибках соединения
        - RuntimeError при неработающем пуле

    @returns:
        - RealDictCursor через yield
    """
    
    conn = pool.getconn()
    try:
        # cursor_factory=RealDictCursor превращает кортежи в словари
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception as e:
        conn.rollback()
        log_error("Ошибка БД", error=e)
        raise
    finally:
        pool.putconn(conn)
