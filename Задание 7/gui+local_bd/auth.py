# -*- coding: utf-8 -*-
"""
Модуль авторизации и регистрации пользователей
"""

import bcrypt
from logger import logger
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "dbname": "farmers_markets",
    "user": "postgres",
    "password": "ваш_пароль",
    "host": "localhost",
    "port": 5432
}

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
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def load_users() -> dict:
    """
    @requires: 
    @modifies: Ничего
    @effects: Загружает пользователей из ..., преобразует в словарь с ключами username.lower()
    @raises: Ничего, ошибки чтения логируются
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
    @requires: Таблица users существует в PostgreSQL
    @modifies: Таблица users
    @effects: Проверяет наличие пользователя 'admin', если отсутствует — создаёт с паролем
    @raises: Исключения при подключении или записи логируются
    @returns: None
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Проверяем существует ли admin
        cur.execute("SELECT 1 FROM users WHERE username=%s;", ("admin",))
        exists = cur.fetchone()

        if not exists:
            hashed_password = hash_password("root")
            cur.execute("""
                INSERT INTO users (username, password, first_name, last_name, middle_name, role)
                VALUES (%s, %s, '', '', '', 'admin');
            """, ("admin", hashed_password))
            conn.commit()
            print("Администратор 'admin' создан.")
        else:
            print("Проверка админа выполнена: пользователь 'admin' уже существует.")

        cur.close()
        conn.close()

    except Exception as e:
        logger.error(f"Ошибка инициализации админа: {e}")
        print(f"Ошибка инициализации админа: {e}")


def login_user(username: str, password: str):
    """
    @requires: Пользователь с указанным username должен существовать в таблице users
    @modifies: Ничего
    @effects: Проверяет пароль и возвращает данные пользователя
    @raises: Ничего, ошибки логируются
    @returns: tuple(bool, dict|str) — (успешно, user_dict) или (False, сообщение об ошибке)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if not user:
            return False, "Пользователь не найден"

        if verify_password(password, user["password"]):
            return True, {
                "username": user["username"],
                "role": user.get("role", "user")
            }

        return False, "Неверный пароль"

    except Exception as e:
        logger.error(f"Ошибка входа пользователя '{username}': {e}")
        return False, str(e)


def register_user(username, password, first_name, last_name, middle_name=""):
    """
    @requires: username уникален (ограничение UNIQUE в БД), password строка ≥4 символов
    @modifies: Таблица users в PostgreSQL
    @effects: Создаёт нового пользователя с ролью 'user'
    @raises: Исключения при записи в БД логируются
    @returns: tuple(bool, str|dict) — True и словарь с username/role при успешной регистрации,
             False и сообщение об ошибке при неудаче
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        hashed = hash_password(password)

        cur.execute(
            """
            INSERT INTO users (username, password, first_name, last_name, middle_name, role)
            VALUES (%s,%s,%s,%s,%s,'user');
            """,
            (username, hashed, first_name, last_name, middle_name)
        )

        conn.commit()

        cur.close()
        conn.close()

        logger.info(f"Новый пользователь '{username}' зарегистрирован")
        return True, {"username": username, "role": "user"}

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        cur.close()
        conn.close()
        return False, "Пользователь с таким логином уже существует"

    except Exception as e:
        logger.error(f"Ошибка регистрации пользователя '{username}': {e}")
        try:
            conn.rollback()
            cur.close()
            conn.close()
        except:
            pass
        return False, str(e)
    
    

if __name__ == "__main__":
    conn = get_db_connection()
    if conn:
        print("PostgreSQL подключение успешно")
        conn.close()