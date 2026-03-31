# -*- coding: utf-8 -*-
"""
Модуль авторизации и регистрации пользователей
"""
import os
import bcrypt
from logger import logger
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import closing

DB_CONFIG = 

def get_db_connection():
    """
    @requires: Параметры подключения к БД заданы в DB_CONFIG
    @modifies: Ничего
    @effects: Создаёт и возвращает соединение с PostgreSQL
    @raises: psycopg2.OperationalError при невозможности подключения
    @returns: psycopg2.connection — объект соединения с БД
    """
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


DEFAULT_ADMIN = {"username": "admin", "password": "root", "role": "admin"}


def hash_password(password: str) -> str:
    """
    @requires: password — строка, не пустая
    @modifies: Ничего
    @effects: Генерирует соль и создает безопасный хеш пароля с использованием bcrypt
    @raises: Ничего
    @returns: str — хеш пароля в формате UTF-8
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """
    @requires: password — строка, hashed — строка хеша пароля
    @modifies: Ничего
    @effects: Проверяет соответствие введенного пароля и хеша
    @raises: Ничего
    @returns: bool — True если пароль совпадает с хешем, иначе False
    """
    try:
        # Пароль, и хеш — это bytes перед проверкой
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        print(f"Ошибка при верификации: {e}")
        return False


def load_users() -> dict:
    """
    @requires: Доступна функция get_db_connection(); таблица users существует в БД.
    @modifies: None
    @effects: Выполняет SELECT * FROM users, формирует словарь пользователей,
              где ключ — username в нижнем регистре, значение — словарь данных пользователя.
              В случае ошибки возвращает пустой словарь и логирует проблему.
    @raises: None (исключения перехватываются и логируются).
    @returns: dict — {username.lower(): user_dict}
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {u["username"].lower(): u for u in rows}
    except Exception as e:
        logger.error(f"Ошибка загрузки пользователей из БД: {e}")
        return {}

def ensure_admin_in_db():
    """
    @requires: Таблица users существует; доступна функция get_db_connection().
    @modifies: Таблица users в БД.
    @effects: Проверяет наличие пользователя с username='admin'.
              Если отсутствует — создает его с паролем 'root' (в виде хеша) и ролью 'admin'.
              Логирует результат операции.
    @raises: None (исключения перехватываются и логируются).
    @returns: None
    """
    try:
        # Используем closing для авто-закрытия коннекта
        with closing(get_db_connection()) as conn:
            with conn.cursor() as cur:
                # Проверяем существование admin
                cur.execute("SELECT 1 FROM users WHERE username=%s;", ("admin",))
                exists = cur.fetchone()

                if not exists:
                    hashed_password = hash_password("root")
                    cur.execute("""
                        INSERT INTO users (username, password, first_name, last_name, middle_name, role)
                        VALUES (%s, %s, '', '', '', 'admin');
                    """, ("admin", hashed_password))
                    # В psycopg2 'with conn' сделает commit автоматически при выходе из блока
                    conn.commit()
                    print("[+] Администратор 'admin' создан.")
                else:
                    print("[*] Проверка админа выполнена: пользователь 'admin' уже существует.")
    except Exception as e:
        # Здесь мы видим вашу ошибку "Connection refused"
        logger.error(f"Ошибка инициализации админа: {e}")
        print(f"Ошибка инициализации админа: {e}")


def login_user(username: str, password: str):
    """
    @requires: username и password — строки; таблица users доступна.
    @modifies: None
    @effects: Ищет пользователя по username в БД.
              Если пользователь найден — проверяет пароль через verify_password.
              Возвращает (True, {username, role}) при успехе,
              иначе (False, сообщение об ошибке).
    @raises: None (исключения перехватываются и логируются).
    @returns: tuple(bool, dict|str)
    """
    try:
        # closing() принудительно вызовет conn.close() при выходе из блока
        with closing(get_db_connection()) as conn:
            # Курсор закроется сам благодаря своему контекстному менеджеру
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE username=%s", (username,))
                user = cur.fetchone()
        
        # Проверку пароля делаем после закрытия соединения
        if not user:
            return False, "Пользователь не найден"

        if verify_password(password, user["password"]):
            return True, {
                "username": user["username"],
                "role": user.get("role", "user")
            }
        return False, "Неверный пароль"

    except Exception as e:
        logger.error(f"Ошибка входа: {e}")
        return False, "Ошибка базы данных"


def register_user(username, password, first_name, last_name, middle_name=""):
    """
    @requires: username — уникальный логин; password — строка (рекомендуется ≥4 символов);
               доступна таблица users.
    @modifies: Таблица users в БД.
    @effects: Хеширует пароль и создает нового пользователя с ролью 'user'.
              При успешной записи возвращает данные пользователя.
              При дублировании username возвращает ошибку.
    @raises: None (исключения перехватываются; UniqueViolation обрабатывается отдельно).
    @returns: tuple(bool, dict|str)
    """
    try:
            hashed = hash_password(password)
            # psycopg2 поддерживает контекстные менеджеры для соединений и курсоров
            with closing(get_db_connection()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO users (username, password, first_name, last_name, middle_name, role)
                        VALUES (%s,%s,%s,%s,%s,'user');
                        """,
                        (username, hashed, first_name, last_name, middle_name)
                    )
                # conn.commit() вызывается автоматически при успешном выходе из блока with conn
                
            logger.info(f"Новый пользователь '{username}' зарегистрирован")
            return True, {"username": username, "role": "user"}

    except psycopg2.errors.UniqueViolation:
        return False, "Пользователь с таким логином уже существует"

    except Exception as e:
            logger.error(f"Ошибка регистрации пользователя '{username}': {e}")
            return False, str(e)
    
    

if __name__ == "__main__":
    conn = get_db_connection()
    if conn:
        print("PostgreSQL подключение успешно")
        conn.close()
