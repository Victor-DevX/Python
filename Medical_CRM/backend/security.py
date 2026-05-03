import os
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from database import get_db_cursor
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from logger import log_info, log_error


# Настройка схемы авторизации (Bearer Token через HTTP заголовки)
security = HTTPBearer()
# !!! В production нужно использовать HTTPS/TLS для защиты данных от перехвата !!!

# Секретный ключ для подписи JWT токенов (берется из переменных окружения)
SECRET_KEY = os.getenv("SECRET_KEY")            # потом вынести в .env


# Проверка наличия секретного ключа (без него токены небезопасны)
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is missing")


# Алгоритм подписи JWT токена
ALGORITHM = "HS256"

# Время жизни access-токена (в минутах)
ACCESS_TOKEN_EXPIRE_MINUTES = 720

# Защита от brute-force (in-memory)
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

login_attempts = defaultdict(int)
lockout_until = {}


# Генерация JWT токена с добавлением времени истечения (exp)
def create_access_token(data: dict):
    """
    @requires:
        - data содержит сериализуемые значения (user_id, role и т.д.)
        - SECRET_KEY задан
        - jose.jwt доступен

    @modifies:
        - Ничего

    @effects:
        - Создает JWT токен
        - Добавляет поле exp (время истечения)

    @raises:
        - Exception при ошибке кодирования токена

    @returns:
        - str (JWT токен)
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Декодирование и проверка JWT токена (валидность и структура payload)
def decode_token(token: str):
    """
    @requires:
        - token — валидная строка JWT
        - SECRET_KEY совпадает с ключом подписи

    @modifies:
        - Ничего

    @effects:
        - Декодирует JWT токен
        - Проверяет наличие user_id и role

    @raises:
        - HTTPException(401) если:
            * токен невалидный
            * подпись неверна
            * payload некорректный

    @returns:
        - dict payload токена
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if "user_id" not in payload or "role" not in payload:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return payload
    except JWTError as e:
        log_error("Ошибка JWT", error=e)
        raise HTTPException(status_code=401, detail="Invalid token")

    
def check_login_allowed(identifier: str):
    """
    @requires:
        - identifier передан (username/email)
        - brute-force state доступен (login_attempts, lockout_until)

    @modifies:
        - lockout_until (при истекшей блокировке)
        - login_attempts (сброс после окончания блокировки)

    @effects:
        - Проверяет активна ли временная блокировка
        - Рассчитывает оставшееся время ожидания
        - Блокирует вход при превышении лимита
        - Автоматически снимает истекшую блокировку

    @raises:
        - HTTPException(429) если пользователь временно заблокирован

    @returns:
        - None
    """
    blocked_until = lockout_until.get(identifier)

    if blocked_until:
        if datetime.now(timezone.utc) < blocked_until:
            remaining = int((blocked_until - datetime.now(timezone.utc)).total_seconds() // 60) + 1

            log_error(
                "Попытка входа в заблокированный аккаунт",
                username=identifier,
                blocked_until=blocked_until.isoformat()
            )

            raise HTTPException(
                status_code=429,
                detail=f"Слишком много попыток. Повторите через {remaining} мин."
            )

        # блокировка истекла
        del lockout_until[identifier]
        login_attempts[identifier] = 0


def register_failed_login(identifier: str):
    """
    @requires:
        - identifier передан
        - brute-force state инициализирован

    @modifies:
        - login_attempts
        - lockout_until
        - Логи системы

    @effects:
        - Увеличивает счетчик неудачных попыток
        - Логирует попытку
        - Активирует временную блокировку при достижении лимита

    @raises:
        - Ничего

    @returns:
        - None
    """
    login_attempts[identifier] += 1

    log_info(
        "Неудачная попытка входа",
        username=identifier,
        attempts=login_attempts[identifier]
    )

    if login_attempts[identifier] >= MAX_LOGIN_ATTEMPTS:
        lockout_until[identifier] = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)

        log_error(
            "Аккаунт временно заблокирован из-за обнаружения brute-force",
            username=identifier,
            attempts=login_attempts[identifier],
            lock_minutes=LOCKOUT_MINUTES
        )


def reset_login_attempts(identifier: str):
    """
    @requires:
        - identifier передан

    @modifies:
        - login_attempts
        - lockout_until
        - Логи системы

    @effects:
        - Сбрасывает счетчик неудачных попыток
        - Удаляет временную блокировку
        - Используется после успешного входа

    @raises:
        - Ничего

    @returns:
        - None
    """
    login_attempts[identifier] = 0

    if identifier in lockout_until:
        del lockout_until[identifier]

    log_info(
        "Счетчик попыток входа сброшен",
        username=identifier
    )



# Получение текущего пользователя из JWT токена (через Authorization header)
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    @requires:
        - Authorization header содержит Bearer token
        - credentials корректно извлечены FastAPI
        - token валиден

    @modifies:
        - Ничего

    @effects:
        - Извлекает JWT токен
        - Декодирует payload
        - Возвращает данные текущего пользователя

    @raises:
        - HTTPException(401) при невалидном/отсутствующем токене

    @returns:
        - dict:
            {
                user_id: int,
                role: str,
                username: str (если есть)
            }
    """
    token = credentials.credentials
    payload = decode_token(token)

    return payload


# Проверка роли пользователя (ограничение доступа к эндпоинтам)
def require_role(required_role: str):
    """
    @requires:
        - required_role является валидной ролью
        - JWT dependency доступен

    @modifies:
        - Логи системы

    @effects:
        - Создает dependency wrapper
        - Проверяет соответствие роли
        - Ограничивает доступ к endpoint

    @raises:
        - HTTPException(403) при недостатке прав

    @returns:
        - function role_checker
    """

    def role_checker(user=Depends(get_current_user)):
        
        if user["role"] != required_role:
            log_error(
                "Недостаточно прав",
                user_id=user["user_id"],
                role=user["role"],
                required=required_role
            )
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return user
    return role_checker


# Получение текущего ID пациента с проверкой роли
def get_current_patient(user=Depends(require_role("patient"))):
    """
    @requires:
        - пользователь авторизован как patient
        - Таблица patients доступна

    @modifies:
        - Ничего

    @effects:
        - Находит patient_id по user_id
        - Проверяет существование профиля пациента

    @raises:
        - HTTPException(403) если роль неверна
        - HTTPException(404) если пациент не найден
        - Exception при ошибке БД

    @returns:
        - int patient_id
    """

    with get_db_cursor() as cur:
        cur.execute(
            "SELECT id FROM patients WHERE user_id = %s",
            (user["user_id"],)
        )
        patient = cur.fetchone()

        if not patient:
            raise HTTPException(status_code=404, detail="Пациент не найден")

        return patient["id"]


# Получение текущего ID врача с проверкой роли
def get_current_doctor(user=Depends(require_role("doctor"))):
    """
    @requires:
        - пользователь авторизован как doctor
        - Таблица employees доступна

    @modifies:
        - Ничего

    @effects:
        - Находит doctor_id по user_id
        - Проверяет существование профиля врача

    @raises:
        - HTTPException(403) если роль неверна
        - HTTPException(404) если врач не найден
        - Exception при ошибке БД

    @returns:
        - int doctor_id
    """

    with get_db_cursor() as cur:
        cur.execute(
            "SELECT id FROM employees WHERE user_id = %s",
            (user["user_id"],)
        )
        doctor = cur.fetchone()

        if not doctor:
            raise HTTPException(status_code=404, detail="Врач не найден")

        return doctor["id"]
    
# Получение текущего ID администратора с проверкой роли
def get_current_admin(user=Depends(require_role("admin"))):
    """
    @requires:
        - пользователь авторизован как admin

    @modifies:
        - Ничего

    @effects:
        - Проверяет admin role
        - Возвращает user_id администратора

    @raises:
        - HTTPException(403) если роль неверна

    @returns:
        - int admin user_id
    """
    
    return user["user_id"]
