# backend/auth.py

import bcrypt
from database import get_db_cursor
from logger import log_info, log_error


# Хеширование пароля пользователя (bcrypt)
# bcrypt автоматически использует соль и защищает от brute-force атак
def hash_password(password: str) -> str:
    """
    @requires:
        - password — непустая строка
        - bcrypt установлен и работает

    @modifies:
        - Ничего

    @effects:
        - Генерирует хеш пароля с солью (bcrypt)
        - Повышает безопасность хранения паролей

    @raises:
        - Exception при ошибке bcrypt

    @returns:
        - str (хеш пароля)
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# Проверка пароля пользователя (сравнение с хешем)
def verify_password(password: str, hashed: str) -> bool:
    """
    @requires:
        - password — строка
        - hashed — валидный bcrypt-хеш

    @modifies:
        - Ничего

    @effects:
        - Сравнивает пароль с хешем

    @raises:
        - Exception если hashed поврежден или некорректен

    @returns:
        - bool (True если пароль совпадает)
    """
    return bcrypt.checkpw(password.encode(), hashed.encode())


# Регистрация пользователя с созданием профиля (пациент или врач) и проверками
def register_user(
    username, email, password, role_name, 
    first_name, last_name, middle_name=None,
    phone=None, birth_date=None, city=None,
    specialty_id=None
):
    """
    @requires:
        - username, email, password не пустые
        - role_name существует в таблице roles
        - при role_name="doctor" указан specialty_id
        - БД доступна

    @modifies:
        - Таблица users (создание пользователя)
        - Таблица employees или patients (создание профиля)

    @effects:
        - Проверяет уникальность пользователя
        - Создает пользователя и профиль (врач или пациент)
        - Хеширует пароль

    @raises:
        - Exception при ошибках БД (оборачивается в "Ошибка регистрации")

    @returns:
        - (True, {"user_id": int}) при успехе
        - (False, str) при бизнес-ошибке (валидация, дубликаты и т.д.)
    """

    # 1. Нормализация роли
    role_name_clean = role_name.strip().lower()

    # 2. Валидация ДО БД
    if not username.strip() or not email.strip() or not password.strip():
        log_info("Попытка регистрации с пустыми данными", username=username, email=email)
        return False, "Обязательные поля не заполнены"
    
    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    username = username.strip()
    email = email.strip().lower() if email else None
    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    
    if email and "@" not in email:
        return False, "Некорректный email"


    # Базовая проверка username
    if len(username.strip()) < 2:
        return False, "Логин должен содержать минимум 2 символа"

    # Минимальный пароль
    if len(password) < 4:
        return False, "Пароль должен содержать минимум 4 символа"

    if role_name_clean == "doctor" and not specialty_id:
        return False, "Для регистрации врача необходим specialty_id"

    with get_db_cursor() as cur:
        try:
            # Проверка уникальности
            cur.execute(
                "SELECT id FROM users WHERE username = %s OR email = %s",
                (username, email)
            )
            if cur.fetchone():
                return False, "Пользователь уже существует"

            # Получение роли
            cur.execute("SELECT id FROM roles WHERE name = %s", (role_name_clean,))
            role = cur.fetchone()
            if not role:
                return False, "Роль не найдена"

            # Хеширование пароля
            pwd_hash = hash_password(password)

            cur.execute("""
                INSERT INTO users (username, email, password_hash, role_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (username, email, pwd_hash, role["id"]))

            user_id = cur.fetchone()["id"]


            # Создание профиля
            if role_name_clean == "doctor":
                cur.execute("""
                    INSERT INTO employees 
                    (user_id, first_name, last_name, middle_name, specialty_id, phone)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, first_name, last_name, middle_name, specialty_id, phone))
            else:
                cur.execute("""
                    INSERT INTO patients 
                    (user_id, first_name, last_name, middle_name, phone, birth_date, city)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (user_id, first_name, last_name, middle_name, phone, birth_date, city))

            log_info("Пользователь зарегистрирован", user_id=user_id, role=role_name_clean)
            return True, {"user_id": user_id}

        except Exception as e:
            log_error("Ошибка регистрации", error=e, username=username)
            raise Exception(f"Ошибка регистрации: {e}")


# Авторизация пользователя с проверкой пароля и возвратом данных для JWT
def login_user(username, password):
    """
    @requires:
        - username и password переданы
        - БД доступна
        - Таблицы users и roles существуют

    @modifies:
        - Ничего

    @effects:
        - Ищет пользователя по username или email
        - Проверяет пароль
        - Проверяет необходимость сброса пароля

    @raises:
        - Exception при ошибках БД

    @returns:
        - (True, dict) при успешной авторизации:
            {
                user_id: int,
                role: str,
                username: str
            }
        - (False, str) при ошибке:
            * неверный логин/пароль
            * требуется сброс пароля
    """
    with get_db_cursor() as cur:
        # Добавлен u.username в SELECT
        cur.execute("""
            SELECT u.id, u.username, u.password_hash, r.name as role
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.username = %s OR u.email = %s
        """, (username, username))

        user = cur.fetchone()

        if not user:
            return False, "Неверный логин или пароль"

        if user["password_hash"] is None:
            return False, "RESET_REQUIRED"

        if not verify_password(password, user["password_hash"]):
            log_info("Неудачная попытка входа", username=username)
            return False, "Неверный логин или пароль"

        log_info("Успешный вход", user_id=user["id"], role=user["role"])
        



        return True, {
            "user_id": user["id"],
            "role": user["role"],
            "username": user["username"] # берется из базы
        }