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


# Проверка наличия всех параметров подключения к БД
if not all(DB_CONFIG.values()):
    raise RuntimeError(f"DB_CONFIG is incomplete: {DB_CONFIG}")


# Подключение к MongoDB (используется для хранения файлов)
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

client = MongoClient(MONGO_URL)
db = client["medical_crm"]
fs = gridfs.GridFS(db)


# Пул соединений PostgreSQL (оптимизация производительности и повторное использование соединений)
# Создаем пул соединений (мин 1, макс 10)
# ThreadedConnectionPool важен для FastAPI, так как он работает в многопоточном режиме
pool = ThreadedConnectionPool(1, 10, **DB_CONFIG)

@contextmanager
def get_db_cursor():
    """
    @requires:
        - Пул соединений pool инициализирован
        - PostgreSQL доступен
        - DB_CONFIG корректно задан
        - psycopg2 подключен

    @modifies:
        - Использует соединение из пула (временно)
        - Может изменять состояние БД (в зависимости от выполняемых запросов)
        - Выполняет commit или rollback транзакции

    @effects:
        - Предоставляет курсор с RealDictCursor (результаты в виде dict)
        - Автоматически управляет транзакцией:
            * commit при успехе
            * rollback при ошибке
        - Возвращает соединение обратно в пул

    @raises:
        - Exception при ошибках SQL-запросов
        - Exception при проблемах с соединением
        - RuntimeError если пул соединений не работает

    @returns:
        - cursor (RealDictCursor) через yield
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