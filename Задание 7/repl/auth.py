# -*- coding: utf-8 -*-
"""
Модуль авторизации и регистрации пользователей
"""

import os
import json
import bcrypt
from logger import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")

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
    @requires: users.json может существовать или нет
    @modifies: Ничего
    @effects: Загружает пользователей из JSON файла, преобразует в словарь с ключами username.lower()
    @raises: Ничего, ошибки чтения логируются
    @returns: dict — {username.lower(): user_dict}
    """
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        data = json.load(open(USERS_FILE, "r", encoding="utf-8"))
        # если файл был списком, преобразуем в словарь
        if isinstance(data, list):
            users = {}
            for u in data:
                if "username" in u:
                    users[u["username"].lower()] = u
            return users
        elif isinstance(data, dict):
            return {k.lower(): v for k, v in data.items()}
        else:
            return {}
    except Exception as e:
        logger.error(f"Ошибка чтения users.json: {e}")
        return {}


def save_users(users: dict):
    """
    @requires: users.json может существовать или нет
    @modifies: Ничего
    @effects: Загружает пользователей из JSON файла, преобразует в словарь с ключами username.lower()
    @raises: Ничего, ошибки чтения логируются
    @returns: dict — {username.lower(): user_dict}
    """
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Ошибка записи users.json: {e}")

def ensure_users_file():
    """
    @requires: Ничего
    @modifies: users.json (если отсутствует)
    @effects: Создает файл users.json с пустым словарем, если файла нет
    @raises: IOError если создать файл невозможно, ошибки логируются
    @returns: None
    """
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
        logger.info("Файл users.json создан")

def ensure_admin():
    """
    @requires: Ничего
    @modifies: users.json
    @effects: Проверяет наличие пользователя 'admin' и создает его с паролем 'root', если нет
    @raises: IOError если запись невозможна, ошибки логируются
    @returns: None
    """
    users = load_users()
    if "admin" not in users:
        users["admin"] = {
            "username": "admin",
            "password": hash_password(DEFAULT_ADMIN["password"]),
            "first_name": "",
            "last_name": "",
            "middle_name": "",
            "role": "admin"
        }
        save_users(users)
        logger.info("Автоматически создан админ с паролем root")


def login_user(username: str, password: str) -> tuple[bool, dict | str]:
    """
    @requires: username, password — строки, не пустые
    @modifies: Ничего
    @effects: Проверяет, существует ли пользователь и совпадает ли пароль
    @raises: Ничего, ошибки логируются
    @returns: tuple[bool, dict|str] — (True, user_dict) если успешно, (False, сообщение) если ошибка
    """
    users = load_users()
    if not users:
        ensure_admin()
        users = load_users()

    user = users.get(username.lower())
    if not user:
        return False, "Пользователь не найден"

    if verify_password(password, user["password"]):
        return True, user
    else:
        return False, "Неверный пароль"


def register_user(username, password, first_name, last_name, middle_name="") -> tuple[bool, dict | str]:
    """
    @requires: username, password — строки, не пустые
    @modifies: Ничего
    @effects: Проверяет, существует ли пользователь и совпадает ли пароль
    @raises: Ничего, ошибки логируются
    @returns: tuple[bool, dict|str] — (True, user_dict) если успешно, (False, сообщение) если ошибка
    """
    users = load_users()
    key = username.lower()
    if key in users:
        return False, "Пользователь уже существует"

    user = {
        "username": username,
        "password": hash_password(password),
        "first_name": first_name,
        "last_name": last_name,
        "middle_name": middle_name,
        "role": "user"
    }
    users[key] = user
    save_users(users)
    logger.info(f"Новый пользователь '{username}' зарегистрирован")
    return True, user