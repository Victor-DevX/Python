from dotenv import load_dotenv
load_dotenv()
import os
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from bson.errors import InvalidId
import gridfs
from urllib.parse import quote
from typing import Optional
from datetime import datetime, timezone, date
import auth
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId
from psycopg2 import IntegrityError
from database import get_db_cursor, fs
from security import (
    create_access_token,
    get_current_patient,
    get_current_doctor,
    get_current_user,
    get_current_admin,
    check_login_allowed,
    register_failed_login,
    reset_login_attempts
)
from logger import log_info, log_error


app = FastAPI(title="Medical CRM Unified API")


# Автоматическое создание администратора при первом запуске
def ensure_admin_exists():
    # Только для первичной инициализации системы
    """
    @requires:
        - Доступ к базе данных через get_db_cursor()
        - Таблицы users и roles существуют
        - Модуль auth корректно хеширует пароль

    @modifies:
        - Таблица roles (может добавить роль "admin")
        - Таблица users (может создать пользователя admin)

    @effects:
        - Гарантирует наличие администратора в системе
        - Выводит информацию в stdout

    @raises:
        - Exception при ошибках работы с БД

    @returns:
        - None
    """
        
    with get_db_cursor() as cur:
        # 1. создаем роль admin если нет
        cur.execute("SELECT id FROM roles WHERE name = %s", ("admin",))
        role = cur.fetchone()

        if not role:
            cur.execute(
                "INSERT INTO roles (name) VALUES (%s) RETURNING id",
                ("admin",)
            )
            role = cur.fetchone()
            print(">>> Роль admin создана")
            log_info("Создана роль admin")


        # 2. проверяем пользователя admin
        cur.execute("SELECT id FROM users WHERE username = %s", ("admin",))
        user = cur.fetchone()

        if user:
            print(">>> ADMIN УЖЕ СУЩЕСТВУЕТ")
            print(">>> login: admin")
            print(">>> password: (пароль скрыт, по умолчанию - root)")
            print(">>> если забыли пароль — удалите пользователя admin из БД и перезапустите сервер")
            return

        # 3. создаем админа
        password_plain = "root"
        password_hash = auth.hash_password(password_plain)

        cur.execute("""
            INSERT INTO users (username, email, password_hash, role_id)
            VALUES (%s, %s, %s, %s)
        """, (
            "admin",
            "admin@admin.com",
            password_hash,
            role["id"]
        ))

        log_info("Создан администратор", username="admin")
        log_error("Создан admin с дефолтным паролем — требуется смена")


# вызываем при старте
@app.on_event("startup")
def startup_event():
    """
    @requires:
        - FastAPI приложение запущено
        - ensure_admin_exists доступна

    @modifies:
        - Может изменить состояние БД (создать admin)

    @effects:
        - Выполняется при старте сервера
        - Гарантирует наличие администратора

    @raises:
        - Exception если ensure_admin_exists падает

    @returns:
        - None
    """
    ensure_admin_exists()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Схема данных для регистрации пользователя (пациент или врач)
class UserRegisterSchema(BaseModel):
    """
    @requires:
        - Входные данные регистрации соответствуют структуре Pydantic
        - role передается как строка
        - email валиден по EmailStr

    @modifies:
        - Ничего

    @effects:
        - Валидирует структуру регистрации пользователя
        - Запрещает лишние поля (extra=forbid)

    @raises:
        - ValidationError при некорректных данных

    @returns:
        - Объект схемы регистрации пользователя
    """
    model_config = {
        "extra": "forbid"
    }

    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: str
    middle_name: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None      # # в соответствии с ISO: YYYY-MM-DD
    city: Optional[str] = None
    specialty_id: Optional[int] = None


# Схема данных для авторизации пользователя (логин + пароль)
class LoginSchema(BaseModel):
    """
    @requires:
        - username и password переданы

    @modifies:
        - Ничего

    @effects:
        - Валидирует структуру запроса авторизации
        - Запрещает лишние поля

    @raises:
        - ValidationError при ошибке структуры

    @returns:
        - Объект схемы логина
    """
    model_config = {"extra": "forbid"}

    username: str
    password: str


# Схема данных для создания записи на прием
class AppointmentSchema(BaseModel):
    """
    @requires:
        - doctor_id валиден
        - datetime передан в ISO формате или datetime
        - note опционален

    @modifies:
        - Ничего

    @effects:
        - Валидирует данные создания записи на прием

    @raises:
        - ValidationError при ошибке структуры

    @returns:
        - Объект схемы записи на прием
    """
    model_config = {"extra": "forbid"}

    doctor_id: int
    datetime: datetime
    note: Optional[str] = None


# Схема медицинской записи врача (результаты приема и планирование следующего визита)
class RecordSchema(BaseModel):
    """
    @requires:
        - appointment_id существует
        - visit_datetime валиден
        - next_visit опционален

    @modifies:
        - Ничего

    @effects:
        - Валидирует структуру медицинской записи

    @raises:
        - ValidationError при ошибке структуры

    @returns:
        - Объект схемы медицинской записи
    """

    model_config = {"extra": "forbid"}

    appointment_id: int
    visit_datetime: datetime
    next_visit: Optional[datetime] = None
    diagnosis: Optional[str] = None
    medication: Optional[str] = None
    recommendations: Optional[str] = None


# Аутентификация
# Регистрация нового пользователя (пациент/врач)
@app.post("/register")
def register(data: UserRegisterSchema):
    """
    @requires:
        - data валидирован Pydantic схемой
        - auth.register_user доступен и работает
        - БД доступна

    @modifies:
        - Таблица users
        - Таблица patients или employees (в зависимости от роли)

    @effects:
        - Создает нового пользователя

    @raises:
        - HTTPException(400) при ошибке регистрации
        - HTTPException(400) при внутренних ошибках

    @returns:
        - dict с user_id и статусом
    """

    try:
        if data.role not in ["patient", "doctor"]:
            raise HTTPException(status_code=400, detail="Недопустимая роль")

        ok, result = auth.register_user(
                username=data.username,
                email=data.email,
                password=data.password,
                role_name=data.role,
                first_name=data.first_name,
                last_name=data.last_name,
                middle_name=data.middle_name,
                phone=data.phone,
                birth_date=data.birth_date,
                city=data.city,
                specialty_id=data.specialty_id
            )
        
#        if data.role not in ["patient", "doctor"]:
#           raise HTTPException(status_code=400, detail="Недопустимая роль")

    except Exception as e:
        log_error("Ошибка регистрации (endpoint)", error=e)
        raise HTTPException(400, "Ошибка обработки запроса")

    if not ok:
        raise HTTPException(status_code=400, detail=result)

    log_info("Регистрация через API", user_id=result["user_id"])

    return {
        "status": "success",
        "user_id": result["user_id"]
    }


# Авторизация пользователя и выдача JWT токена
@app.post("/login")
def login(data: LoginSchema):
    """
    @requires:
        - data содержит корректные username и password
        - auth.login_user доступен
        - create_access_token работает

    @modifies:
        - Не изменяет состояние БД

    @effects:
        - Проверяет учетные данные
        - Генерирует JWT токен

    @raises:
        - HTTPException(401) при неверных данных

    @returns:
        - dict с access_token, token_type, role
    """
    
    identifier = data.username.strip().lower()
    check_login_allowed(identifier)


    ok, user = auth.login_user(identifier, data.password)

    if not ok:
        if user != "RESET_REQUIRED":
            register_failed_login(identifier)

        if user == "RESET_REQUIRED":
            raise HTTPException(
                status_code=403,
                detail="RESET_REQUIRED"
            )

        raise HTTPException(status_code=401, detail=user)

    reset_login_attempts(identifier)

    token = create_access_token({
        "user_id": user["user_id"],
        "role": user["role"],
        "username": user["username"]
    })

    log_info("Выдан JWT", user_id=user["user_id"], role=user["role"])
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"]
    }


# Сброс пароля для пользователей из панели администратора
@app.post("/admin/reset-password/{user_id}")
def admin_reset_password(user_id: int, admin=Depends(get_current_admin)):
    """
    @requires:
        - Пользователь авторизован как admin
        - user_id существует в системе

    @modifies:
        - Таблица users (password_hash = NULL)

    @effects:
        - Делает пароль пользователя недействительным
        - Требует установки нового пароля

    @raises:
        - HTTPException(404) если пользователь не найден
        - HTTPException(403) если нет прав администратора

    @returns:
        - dict со статусом reset_required
    """


    with get_db_cursor() as cur:
        cur.execute("""
            UPDATE users
            SET password_hash = NULL
            WHERE id = %s
            RETURNING id
        """, (user_id,))

        if not cur.fetchone():
            raise HTTPException(404, "Пользователь не найден")

    return {"status": "reset_required"}


class PasswordSchema(BaseModel):
    """
    @requires:
        - new_password передан

    @modifies:
        - Ничего

    @effects:
        - Валидирует структуру установки нового пароля

    @raises:
        - ValidationError при ошибке структуры

    @returns:
        - Объект схемы нового пароля
    """
    model_config = {"extra": "forbid"}

    new_password: str

# Эндпоинт восстановления пароля
@app.post("/auth/set-password")
def set_password(
    data: PasswordSchema,
    user=Depends(get_current_user)
):
    """
    @requires:
        - Пользователь авторизован
        - Пароль ранее был сброшен администратором
        - data.new_password передан

    @modifies:
        - Таблица users (обновляет password_hash)

    @effects:
        - Устанавливает новый пароль

    @raises:
        - HTTPException(404) если пользователь не найден
        - HTTPException(400) если пароль не был сброшен

    @returns:
        - dict со статусом password_set
    """

    with get_db_cursor() as cur:
        cur.execute("""
            SELECT id, password_hash
            FROM users
            WHERE id = %s
        """, (user["user_id"],))

        db_user = cur.fetchone()

        if not db_user:
            raise HTTPException(404, "Пользователь не найден")

        # доступ только если пароль сброшен
        if db_user["password_hash"] is not None:
            raise HTTPException(400, "Сброс пароля не запрошен администратором")

        cur.execute("""
            UPDATE users
            SET password_hash = %s
            WHERE id = %s
        """, (
            auth.hash_password(data.new_password),
            db_user["id"]
        ))

    log_info("Пользователь установил новый пароль", user_id=user["user_id"])

    return {"status": "password_set"}


class ResetPasswordSchema(BaseModel):
    """
    @requires:
        - username существует
        - new_password передан

    @modifies:
        - Ничего

    @effects:
        - Валидирует frontend reset password запрос

    @raises:
        - ValidationError при ошибке структуры

    @returns:
        - Объект схемы frontend reset
    """
    model_config = {"extra": "forbid"}
    
    username: str
    new_password: str


# Эндпоинт восстановления пароля из front
@app.post("/auth/reset-password")
def frontend_reset_password(data: ResetPasswordSchema):
    """
    @requires:
        - username/email существует
        - Пароль пользователя ранее сброшен администратором
        - new_password >= 4 символов

    @modifies:
        - Таблица users (обновляет password_hash)

    @effects:
        - Проверяет право на восстановление
        - Устанавливает новый пароль через frontend flow

    @raises:
        - HTTPException(400) если пароль короткий
        - HTTPException(404) если пользователь не найден
        - HTTPException(400) если reset не был инициирован

    @returns:
        - dict со статусом password_set
    """

    if not data.new_password or len(data.new_password) < 4:
        raise HTTPException(
            400,
            "Пароль должен содержать минимум 4 символов"
        )

    with get_db_cursor() as cur:
        cur.execute("""
            SELECT id, password_hash
            FROM users
            WHERE username = %s OR email = %s
        """, (data.username, data.username))

        db_user = cur.fetchone()

        if not db_user:
            raise HTTPException(404, "Пользователь не найден")

        # ключевая защита
        if db_user["password_hash"] is not None:
            raise HTTPException(400, "Сброс пароля не запрошен")

        cur.execute("""
            UPDATE users
            SET password_hash = %s
            WHERE id = %s
        """, (
            auth.hash_password(data.new_password),
            db_user["id"]
        ))

        log_info("Пароль восстановлен через frontend", user_id=db_user["id"])

    return {"status": "password_set"}


# СПРАВОЧНИК
# Получение списка медицинских специальностей
@app.get("/specialties")
def get_specialties():
    """
    @requires:
        - Таблица specialties существует

    @modifies:
        - Ничего

    @effects:
        - Получает список медицинских специальностей

    @raises:
        - Exception при ошибке БД

    @returns:
        - list словарей {id, name}
    """

    with get_db_cursor() as cur:
        cur.execute("SELECT id, name FROM specialties LIMIT 100")
        return cur.fetchall()


# Получение данных текущего пользователя (врач/пациент)
@app.get("/me")
def get_me(user=Depends(get_current_user)):

    """
    @requires:
        - Пользователь авторизован
        - role корректна (doctor/patient/admin)

    @modifies:
        - Ничего

    @effects:
        - Возвращает базовый профиль текущего пользователя

    @raises:
        - HTTPException(403) при неверной роли
        - HTTPException(404) если профиль не найден

    @returns:
        - dict с first_name / last_name
    """

    with get_db_cursor() as cur:

        if user["role"] == "doctor":
            cur.execute("""
                SELECT first_name, last_name
                FROM employees
                WHERE user_id = %s
            """, (user["user_id"],))

        elif user["role"] == "patient":
            cur.execute("""
                SELECT first_name, last_name
                FROM patients
                WHERE user_id = %s
            """, (user["user_id"],))

        elif user["role"] == "admin":
            return {
                "first_name": "Администратор",
                "last_name": user["username"]
            }

        else:
            raise HTTPException(403, "Недопустимая роль")

        user_data = cur.fetchone()

        if not user_data:
            raise HTTPException(404, "Пользователь не найден")

        return user_data


# Получение списка врачей по специальности
@app.get("/doctors")
def get_doctors(specialty_id: int):
    """
    @requires:
        - specialty_id существует
        - Таблицы employees и specialties доступны

    @modifies:
        - Ничего

    @effects:
        - Возвращает список врачей по специальности

    @raises:
        - Exception при ошибке БД

    @returns:
        - list словарей с врачами
    """
    with get_db_cursor() as cur:
        cur.execute("""
        SELECT e.id, e.first_name, e.last_name, s.name as specialty
        FROM employees e
        JOIN specialties s ON e.specialty_id = s.id
        WHERE e.specialty_id = %s
        """, (specialty_id,))
        return cur.fetchall()


# Получение списка записей пациента к врачам
@app.get("/patient/appointments")
def get_patient_appointments(
    limit: int = 50,
    offset: int = 0,
    patient_id: int = Depends(get_current_patient)
):
    """
    @requires:
        - Пользователь авторизован как пациент
        - patient_id получен через Depends

    @modifies:
        - Ничего

    @effects:
        - Получает список записей пациента

    @raises:
        - HTTPException при проблемах авторизации
        - Exception при ошибке БД

    @returns:
        - list записей
    """
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT 
                a.id,
                a.appointment_datetime,
                a.note,
                e.first_name,
                e.last_name
            FROM appointments a
            JOIN employees e ON a.doctor_id = e.id
            WHERE a.patient_id = %s
            ORDER BY a.appointment_datetime
            LIMIT %s OFFSET %s
        """, (patient_id, limit, offset))
        return cur.fetchall()


# Получение списка записей врача с фильтрами (дата, поиск, статус)
@app.get("/doctor/appointments")
def get_doctor_appointments(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    doctor_id: int = Depends(get_current_doctor)
):    
    """
    @requires:
        - Пользователь авторизован как врач
        - doctor_id валиден
        - date/search/status опционально корректны

    @modifies:
        - Ничего

    @effects:
        - Возвращает список приемов врача
        - Поддерживает фильтрацию:
            * диапазон дат
            * поиск пациента
            * done/pending
        - Добавляет has_record и patient_name

    @raises:
        - HTTPException(403) при отсутствии роли врача
        - Exception при ошибке БД

    @returns:
        - list словарей приемов
    """
    
    
    query = """
        SELECT 
            a.id,
            a.appointment_datetime,
            a.note,
            p.first_name,
            p.last_name,
            m.id as record_id,
            (
                SELECT COUNT(*) 
                FROM appointment_files f 
                WHERE f.appointment_id = a.id
            ) as files_count
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        LEFT JOIN medical_records m ON m.appointment_id = a.id
        WHERE a.doctor_id = %s
    """

    params = [doctor_id]

    # фильтр по датам
    if date_from:
        query += " AND a.appointment_datetime >= %s"
        params.append(date_from)

    if date_to:
        query += " AND a.appointment_datetime <= %s"
        params.append(date_to)

    #  поиск пациента
    if search:
        query += """
        AND (LOWER(p.first_name) LIKE %s 
             OR LOWER(p.last_name) LIKE %s)
        """
        search_term = f"%{search.lower()}%"
        params.extend([search_term, search_term])

    # статус
    if status == "done":
        query += " AND m.id IS NOT NULL"
    elif status == "pending":
        query += " AND m.id IS NULL"

    query += " ORDER BY a.appointment_datetime LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with get_db_cursor() as cur:
        cur.execute(query, tuple(params))
        rows = cur.fetchall()

    for r in rows:
        r["patient_name"] = f"{r['last_name']} {r['first_name']}"
        r["has_record"] = r["record_id"] is not None

    return rows


# Поиск по ФИО для панели админа
@app.get("/admin/search")
def admin_search(q: str, admin_id: int = Depends(get_current_admin)):
    """
    @requires:
        - Пользователь авторизован как admin
        - q >= 2 символов

    @modifies:
        - Ничего

    @effects:
        - Выполняет поиск пользователей по:
            * username
            * имени
            * фамилии

    @raises:
        - HTTPException(400) если запрос слишком короткий
        - HTTPException(403) если нет прав

    @returns:
        - list найденных пользователей
    """

    q = q.strip()

    if len(q) < 2:
        raise HTTPException(400, "Введите минимум 2 символа")
    
    q = f"%{q.lower()}%"

    with get_db_cursor() as cur:
        cur.execute("""
            SELECT u.id, u.username, r.name as role,
                   COALESCE(p.first_name, e.first_name) as first_name,
                   COALESCE(p.last_name, e.last_name) as last_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            LEFT JOIN patients p ON p.user_id = u.id
            LEFT JOIN employees e ON e.user_id = u.id
            WHERE LOWER(u.username) LIKE %s
               OR LOWER(p.first_name) LIKE %s
               OR LOWER(p.last_name) LIKE %s
               OR LOWER(e.first_name) LIKE %s
               OR LOWER(e.last_name) LIKE %s
        """, (q, q, q, q, q))

        return cur.fetchall()


# Базовая функция создания записи на прием (проверки и вставка в БД)
def core_create_appointment(cur, doctor_id: int, patient_id: int, dt: datetime, note: str = None):
    """
    @requires:
        - dt содержит timezone (tzinfo != None)
        - doctor_id и patient_id валидны
        - cur — активный DB cursor

    @modifies:
        - Таблица appointments

    @effects:
        - Проверяет:
            * время не в прошлом
            * шаг 30 минут
            * занятость врача
        - Создает запись

    @raises:
        - HTTPException(400) если:
            * время в прошлом
            * неправильный шаг
            * слот занят
            * нет timezone

    @returns:
        - int id созданной записи
    """

    if dt.tzinfo is None:
    # если отсутствует, то пришло локальное время - делаем UTC
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    dt = dt.astimezone(timezone.utc)

    # 1. Запрет на прошлое время
    now = datetime.now(timezone.utc)
    if dt <= now:
        raise HTTPException(400, "Нельзя записаться на прошедшее время")

    # 2. Нормализация (обрезаем секунды)
    dt = dt.replace(second=0, microsecond=0)
    if dt.minute not in (0, 30):
        raise HTTPException(400, "Время должно быть кратно 30 минутам (00 или 30)")

    # 3. Проверка занятости
    cur.execute("""
        SELECT 1 FROM appointments
        WHERE doctor_id = %s
        AND appointment_datetime = %s
    """, (doctor_id, dt))

    if cur.fetchone():
        raise HTTPException(400, "Это время уже занято другим пациентом")

    # 4. Создание
    try:
        cur.execute("""
            INSERT INTO appointments
            (patient_id, doctor_id, appointment_datetime, note)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            patient_id,
            doctor_id,
            dt,
            note
        ))

    except IntegrityError:
        raise HTTPException(
            400,
            "Это время уже занято, выберите другой слот"
        )

    return cur.fetchone()["id"]


# Эндпоинт для пациента
@app.post("/appointments")
def create_appointment(data: AppointmentSchema, patient_id: int = Depends(get_current_patient)):
    """
    @requires:
        - Пользователь авторизован как пациент
        - doctor_id валиден
        - datetime валиден

    @modifies:
        - Таблица appointments

    @effects:
        - Создает запись пациента на прием

    @raises:
        - HTTPException(400) при ошибке времени/слота
        - HTTPException(403) при отсутствии доступа

    @returns:
        - dict с appointment_id
    """

    with get_db_cursor() as cur:
        new_id = core_create_appointment(
            cur, data.doctor_id, patient_id, data.datetime, data.note
        )

        log_info("Создана запись", doctor_id=data.doctor_id, patient_id=patient_id)

        return {"appointment_id": new_id}



# Эндпоинт для врача
@app.post("/medical-record")
def create_record(data: RecordSchema, doctor_id: int = Depends(get_current_doctor)):
    """
    @requires:
        - Пользователь авторизован как врач
        - appointment_id принадлежит врачу
        - Данные записи валидны

    @modifies:
        - Таблица medical_records
        - Таблица appointments (если создается next_visit)

    @effects:
        - Создает медицинскую запись
        - Может создать повторный прием
        - Блокирует повторную запись на тот же прием

    @raises:
        - HTTPException(404) если прием не найден
        - HTTPException(400) если запись уже существует
        - HTTPException(400) при ошибке next_visit

    @returns:
        - dict со статусом success и состоянием next_visit
    """

    with get_db_cursor() as cur:
        # Получаем данные пациента из текущего приема
        cur.execute(
            "SELECT patient_id FROM appointments WHERE id = %s AND doctor_id = %s",
            (data.appointment_id, doctor_id)
        )
        
        log_info("Создание мед записи", appointment_id=data.appointment_id)

        app_res = cur.fetchone()
        if not app_res:
            raise HTTPException(404, "Текущий прием не найден")

        patient_id = app_res['patient_id']

        # Проверяем, не был ли этот прием уже создан при предыдущем сохранении карточки
        next_visit_status = None

        if data.next_visit:
            cur.execute("""
                SELECT 1 FROM appointments
                WHERE doctor_id = %s AND patient_id = %s AND appointment_datetime = %s
            """, (doctor_id, patient_id, data.next_visit))

            if not cur.fetchone():
                try:
                    core_create_appointment(
                        cur,
                        doctor_id,
                        patient_id,
                        data.next_visit,
                        "Повторный прием (назначен врачом)"
                    )

                    next_visit_status = "created"

                except HTTPException as e:
                    next_visit_status = f"failed: {e.detail}"

            else:
                next_visit_status = "already_exists"


        # Сохраняем мед. карту
        cur.execute("""
            INSERT INTO medical_records 
            (appointment_id, doctor_id, patient_id, visit_datetime, 
             next_visit_datetime, diagnosis, medication, recommendations)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (appointment_id) DO NOTHING
                diagnosis = EXCLUDED.diagnosis,
                medication = EXCLUDED.medication,
                recommendations = EXCLUDED.recommendations,
                next_visit_datetime = EXCLUDED.next_visit_datetime
        """, (
            data.appointment_id, doctor_id, patient_id, 
            data.visit_datetime or datetime.now(timezone.utc),
            data.next_visit, data.diagnosis, data.medication, data.recommendations
        ))

        if cur.rowcount == 0:
            raise HTTPException(
                400,
                "Медицинская запись для этого приема уже существует"
    )

        return {
        "status": "success",
        "next_visit": next_visit_status
    }


# Получение медицинских записей пациента
@app.get("/patient/records")
def get_patient_records(patient_id: int = Depends(get_current_patient)):
    """
    @requires:
        - Пользователь авторизован как пациент

    @modifies:
        - Ничего

    @effects:
        - Возвращает историю медицинских записей пациента

    @raises:
        - HTTPException(403) при отсутствии доступа
        - Exception при ошибке БД

    @returns:
        - list медицинских записей
    """

    with get_db_cursor() as cur:
        cur.execute("""
            SELECT 
                m.*,
                e.first_name as doctor_first_name,
                e.last_name as doctor_last_name,
                s.name as specialty
            FROM medical_records m
            JOIN employees e ON m.doctor_id = e.id
            JOIN specialties s ON e.specialty_id = s.id
            WHERE m.patient_id = %s
            ORDER BY m.created_at DESC
        """, (patient_id,))
        return cur.fetchall()


# Проверка прав доступа к приему (пациент или врач)
def check_appointment_access(cur, appointment_id, user):
    """
    @requires:
        - appointment_id существует
        - user содержит user_id и role

    @modifies:
        - Ничего

    @effects:
        - Проверяет доступ пользователя к приему

    @raises:
        - HTTPException(404) если прием не найден
        - HTTPException(403) если нет доступа

    @returns:
        - id пациента или врача (в зависимости от роли)
    """

    cur.execute("""
        SELECT a.patient_id, a.doctor_id,
               p.user_id AS patient_user_id,
               e.user_id AS doctor_user_id
        FROM appointments a
        LEFT JOIN patients p ON a.patient_id = p.id
        LEFT JOIN employees e ON a.doctor_id = e.id
        WHERE a.id = %s
    """, (appointment_id,))

    row = cur.fetchone()

    if not row:
        raise HTTPException(404, "Прием не найден")
    
    if user["role"] == "admin":
            return row["patient_id"]

    if user["role"] == "patient":
        if row["patient_user_id"] != user["user_id"]:
            raise HTTPException(403, "Нет доступа")
        return row["patient_id"]

    elif user["role"] == "doctor":
        if row["doctor_user_id"] != user["user_id"]:
            raise HTTPException(403, "Нет доступа")
        return row["doctor_id"]

    else:
        raise HTTPException(403, "Нет доступа")
    

# Получение медицинской записи по конкретному приему (для врача / админа)
@app.get("/medical-record/{appointment_id}")
def get_medical_record(
    appointment_id: int,
    user=Depends(get_current_user)
):
    """
    @requires:
        - Пользователь авторизован
        - appointment_id существует
        - Есть доступ к приему

    @modifies:
        - Ничего

    @effects:
        - Возвращает медицинскую запись по конкретному приему

    @raises:
        - HTTPException(403) если нет доступа
        - HTTPException(404) если запись не найдена

    @returns:
        - dict медицинской записи
    """

    with get_db_cursor() as cur:

        # Проверка доступа к приему
        check_appointment_access(cur, appointment_id, user)

        cur.execute("""
            SELECT
                appointment_id,
                diagnosis,
                medication,
                recommendations,
                visit_datetime,
                next_visit_datetime
            FROM medical_records
            WHERE appointment_id = %s
        """, (appointment_id,))

        record = cur.fetchone()

        if not record:
            raise HTTPException(404, "Медицинская запись не найдена")

        return record




# Загрузка файла (анализы, документы) к приему
@app.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    appointment_id: int = Form(...),
    user=Depends(get_current_user)
):
    """
    @requires:
        - Пользователь авторизован
        - appointment_id валиден
        - file передан

    @modifies:
        - GridFS (сохраняет файл)
        - Таблица appointment_files

    @effects:
        - Проверяет тип, размер и расширение файла
        - Сохраняет файл и метаданные

    @raises:
        - HTTPException(400) при неверном формате
        - HTTPException(403) при отсутствии доступа
        - HTTPException(500) при ошибке сохранения

    @returns:
        - dict с file_id
    """

    # 1. Проверка типа файла (MIME)
    allowed_types = {"image/jpeg", "image/jpg", "application/pdf"}
    if file.content_type not in allowed_types:
        raise HTTPException(400, "Разрешены только JPG/JPEG и PDF файлы")

    # 2. Проверка расширения
    filename = (file.filename or "").lower()
    if not filename.endswith((".jpg", ".jpeg", ".pdf")):
        raise HTTPException(400, "Недопустимое расширение файла")

    # 3. Читаем синхронно через встроенный SpooledTemporaryFile
    MAX_SIZE = 8 * 1024 * 1024  # 8MB
    content = file.file.read(MAX_SIZE + 1)

    if len(content) > MAX_SIZE:
        raise HTTPException(400, "Файл слишком большой (макс 8MB)")

    # 4. Проверка пустого файла
    if not content:
        raise HTTPException(400, "Пустой файл")
    
    # 5 Проверка сигнатуры файла (magic bytes)
    if filename.endswith(".pdf") and not content.startswith(b"%PDF"):
        raise HTTPException(400, "Файл поврежден или не является PDF")

    if filename.endswith((".jpg", ".jpeg")) and not content.startswith(b"\xff\xd8"):
        raise HTTPException(400, "Файл поврежден или не является JPEG")

    # 6. Мини-очистка имени файла
    safe_filename = os.path.basename(filename).replace("/", "_").replace("\\", "_")

    # 7. Разделяем транзакции для безопасной обработки ошибок
    with get_db_cursor() as cur:
        uploader_id = check_appointment_access(cur, appointment_id, user)

        file_id = fs.put(
            content,
            filename=safe_filename,
            content_type=file.content_type,
            metadata={
                "appointment_id": appointment_id,
                "uploaded_by": user["role"],
                "uploader_id": uploader_id
            }
        )

        log_info("Файл загружен", appointment_id=appointment_id, user_role=user["role"])

        try:
            cur.execute("""
                INSERT INTO appointment_files 
                (appointment_id, file_id, filename, uploaded_by, uploader_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (appointment_id, str(file_id), safe_filename, user["role"], uploader_id))

        except Exception as e:
            fs.delete(file_id)
            log_error("Ошибка загрузки файла", error=e)
            raise HTTPException(500, "Ошибка при сохранении файла")

    return {
        "status": "uploaded",
        "file_id": str(file_id)
    }




# Получение файла по ID с проверкой прав доступа к приему
@app.get("/file/{file_id}")
def get_file(
    file_id: str,
    user=Depends(get_current_user)
):
    """
    @requires:
        - file_id валиден
        - пользователь авторизован

    @modifies:
        - Ничего

    @effects:
        - Проверяет доступ
        - Возвращает файл как StreamingResponse

    @raises:
        - HTTPException(404) если файл не найден
        - HTTPException(403) если нет доступа
        - HTTPException(500) при ошибке

    @returns:
        - StreamingResponse
    """

    try:
        file = fs.get(ObjectId(file_id))

        metadata = file.metadata or {}
        appointment_id = metadata.get("appointment_id")
        if not appointment_id:
            raise HTTPException(400, "Файл без привязки к приему")

        # Получаем данные о приеме, к которому прикреплен файл
        with get_db_cursor() as cur:              
            check_appointment_access(cur, appointment_id, user)

            encoded_filename = quote(file.filename)

            return StreamingResponse(
                file,
                media_type=file.content_type or "application/octet-stream",
                headers={
                    # Используем стандарт filename*=utf-8''
                    "Content-Disposition": f"inline; filename*=utf-8''{encoded_filename}"
                }
            )

    except (InvalidId, gridfs.errors.NoFile):
        raise HTTPException(status_code=404, detail="Файл не найден")

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка сервера при получении файла")
    

# Получение списка файлов, прикрепленных к приему
@app.get("/appointment/{appointment_id}/files")
def get_files_by_appointment(
    appointment_id: int,
    user=Depends(get_current_user)
):
    """
    @requires:
        - Пользователь авторизован
        - appointment_id существует

    @modifies:
        - Ничего

    @effects:
        - Проверяет доступ
        - Возвращает список файлов приема

    @raises:
        - HTTPException(404) если прием не найден
        - HTTPException(403) если нет доступа

    @returns:
        - list файлов
    """

    with get_db_cursor() as cur:
        cur.execute("""
            SELECT patient_id, doctor_id FROM appointments
            WHERE id = %s
        """, (appointment_id,))
        appointment = cur.fetchone()

    if not appointment:
        raise HTTPException(404, "Прием не найден")

    # Проверяем права на просмотр файлов этого приема
    with get_db_cursor() as cur:
        check_appointment_access(cur, appointment_id, user)

        # Получаем список файлов
        cur.execute("""
            SELECT id, file_id, filename
            FROM appointment_files
            WHERE appointment_id = %s
        """, (appointment_id,))
        return cur.fetchall()
    

# Удаление записей из БД администратором
@app.delete("/admin/records/{table}/{record_id}")
def admin_delete_record(
    table: str,
    record_id: int,
    full_delete: bool = False,
    admin_id: int = Depends(get_current_admin)
):
    """
    @requires:
        - Пользователь авторизован как admin
        - table входит в whitelist
        - record_id > 0

    @modifies:
        - PostgreSQL записи
        - GridFS файлы (при необходимости)

    @effects:
        - Удаляет запись
        - Может выполнять каскадное удаление связанных файлов

    @raises:
        - HTTPException(400) при неверной таблице/ID
        - HTTPException(403) при отсутствии прав

    @returns:
        - dict со статусом deleted
    """

    # whitelist таблиц — ВСЕГДА проверяется
    allowed_tables = {
        "users", "patients", "employees",
        "appointments", "medical_records",
        "specialties", "appointment_files"
    }

    if table not in allowed_tables:
        raise HTTPException(400, "Недопустимая таблица")

    if record_id <= 0:
        raise HTTPException(400, "Некорректный ID")

    with get_db_cursor() as cur:

        gridfs_file_ids = []

        # Удаление одного файла
        if table == "appointment_files":
            cur.execute(
                "SELECT file_id FROM appointment_files WHERE id = %s",
                (record_id,)
            )

            gridfs_file_ids = [
                row["file_id"] for row in cur.fetchall()
            ]

        # Полное удаление пользователя
        elif full_delete and table == "users":
            cur.execute("""
                SELECT af.file_id
                FROM appointment_files af
                JOIN appointments a ON af.appointment_id = a.id
                LEFT JOIN patients p ON a.patient_id = p.id
                LEFT JOIN employees e ON a.doctor_id = e.id
                WHERE p.user_id = %s OR e.user_id = %s
            """, (record_id, record_id))

            gridfs_file_ids = [
                row["file_id"] for row in cur.fetchall()
            ]

            # удаляем профили
            cur.execute(
                "DELETE FROM patients WHERE user_id = %s",
                (record_id,)
            )

            cur.execute(
                "DELETE FROM employees WHERE user_id = %s",
                (record_id,)
            )

        # Полное удаление приема
        elif full_delete and table == "appointments":
            cur.execute(
                "SELECT file_id FROM appointment_files WHERE appointment_id = %s",
                (record_id,)
            )

            gridfs_file_ids = [
                row["file_id"] for row in cur.fetchall()
            ]

        # Удаляем GridFS ДО SQL DELETE
        for fid in gridfs_file_ids:
            try:
                fs.delete(ObjectId(fid))

            except gridfs.errors.NoFile:
                pass

            except Exception as e:
                log_error(
                    "Ошибка удаления GridFS файла",
                    error=e,
                    file_id=fid
                )

        # PostgreSQL CASCADE дополнительно очистит связанные записи
        query = f'DELETE FROM "{table}" WHERE id = %s'
        cur.execute(query, (record_id,))

    return {"status": "deleted"}


# Проверка работоспособности API
@app.get("/health")
def health_check():
    """
    @requires:
        - Сервер запущен

    @modifies:
        - Логи системы

    @effects:
        - Проверяет доступность API

    @raises:
        - Ничего

    @returns:
        - dict со статусом online
    """

    log_info("Health check")
    return {"status": "online"}


# Точка входа для запуска сервера
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
