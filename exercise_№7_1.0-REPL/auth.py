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
    @requires: password — строка
    @modifies: Ничего
    @effects: Создает безопасный хеш пароля с использованием bcrypt
    @raises: Ничего
    @returns: str — хеш пароля
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """
    @requires: password — строка, hashed — хешированная строка пароля
    @modifies: Ничего
    @effects: Проверяет соответствие пароля и хеша
    @raises: Ничего
    @returns: bool — True если пароль совпадает, иначе False
    """

    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def load_users():
    """
    @requires: users.json может существовать или нет
    @modifies: Ничего
    @effects: Загружает пользователей из JSON файла
    @raises: Ничего
    @returns: dict — словарь пользователей
    """
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
#        logger.error(f"Ошибка чтения users.json: {e}")
        return {}
    

def save_users(users: dict):
    """
    @requires: users — словарь пользователей
    @modifies: users.json
    @effects: Сохраняет пользователей в файл JSON
    @raises: IOError если запись невозможна
    @returns: None
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
    @effects: Создает файл users.json с пустым словарем, если его нет
    @raises: IOError если создать файл невозможно
    @returns: None
    """
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
        logger.info("Файл users.json создан")

def ensure_admin():
    """
    @requires: users.json может существовать
    @modifies: users.json
    @effects: Создает администратора admin/root, если его нет
    @raises: IOError если запись невозможна
    @returns: None
    """
    users = load_users()
    if "admin" not in users:
        users["admin"] = {
            "password": hash_password(DEFAULT_ADMIN["password"]),  # root
            "role": "admin"
        }
        save_users(users)
        logger.info("Автоматически создан админ с паролем root")



def login_user(username, password):
    """
    @requires: username, password — строки
    @modifies: Ничего
    @effects: Проверяет данные пользователя, возвращает результат аутентификации
    @raises: Ничего
    @returns: tuple (bool, str) — (True, роль) если успешно, иначе (False, сообщение)
    """

    users = load_users()
    # Создание администратора по умолчанию, если файла еще нет или нет admin
    if "admin" not in users:
        users["admin"] = {
            "password": hash_password(DEFAULT_ADMIN["password"]),  # root
            "role": "admin"
        }
        save_users(users)
        logger.info("Автоматически создан админ с паролем root")

    user = users.get(username)
    if not user:
        return False, "Пользователь не найден"

    if verify_password(password, user["password"]):
        return True, user["role"]
    else:
        return False, "Неверный пароль"


def register_user(username: str, password: str):
    """
    @requires: username, password — строки
    @modifies: users.json
    @effects: Регистрирует нового пользователя с ролью user
    @raises: Ничего
    @returns: tuple (bool, str) — (True, сообщение) если успешно, иначе (False, сообщение)
    """
    users = load_users()
    if username in users:
        return False, "Пользователь уже существует"
    users[username] = {
        "password": hash_password(password),
        "role": "user"
    }
    save_users(users)
#    logger.info(f"Новый пользователь '{username}' зарегистрирован")
    return True, "Пользователь успешно зарегистрирован"