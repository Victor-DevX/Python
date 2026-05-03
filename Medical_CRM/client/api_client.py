import os
import requests
from datetime import datetime, timezone
import mimetypes
from urllib.parse import unquote

# Приведение datetime к UTC и ISO формату (нормализация, единый стандарт для API)
def to_utc_iso(dt: datetime):
    """
    @requires:
        - dt содержит timezone (tzinfo != None)

    @modifies:
        - Ничего

    @effects:
        - Переводит datetime в UTC
        - Обрезает секунды и микросекунды
        - Возвращает ISO строку

    @raises:
        - Exception если dt невалидный

    @returns:
        - str (ISO datetime в UTC)
    """
    return dt.astimezone(timezone.utc).replace(second=0, microsecond=0).isoformat()

# Клиент для взаимодействия с backend API (HTTP-запросы, авторизация, данные)
class APIClient:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")
        self.token = None
        self.role = None

    
# Формирование HTTP заголовков (добавление Bearer токена)
    def _headers(self):
        """
        @requires:
            - self.token может быть None или строкой

        @modifies:
            - Ничего

        @effects:
            - Формирует HTTP заголовки
            - Добавляет Authorization при наличии токена

        @raises:
            - Ничего

        @returns:
            - dict headers
        """
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers


# Универсальный метод HTTP-запроса с обработкой ошибок и ответов
    def _request(self, method, endpoint, **kwargs):
        """
        @requires:
            - method корректный HTTP метод
            - endpoint строка (начинается с /)
            - backend доступен

        @modifies:
            - Ничего (кроме сетевого запроса)

        @effects:
            - Выполняет HTTP запрос
            - Обрабатывает ошибки сервера
            - Парсит JSON или возвращает raw текст

        @raises:
            - Exception при HTTP ошибке (status >= 400)
            - Exception при ошибке сети
            - Exception при некорректном ответе сервера

        @returns:
            - dict (JSON ответ) или {"raw": str}
        """

        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self._headers(),
                timeout=10,
                **kwargs
            )

            if response.status_code >= 400:
                try:
                    data = response.json()

                    #  ловим Pydantic ошибки
                    if "detail" in data:
                        if isinstance(data["detail"], list):
                            # берем первое сообщение
                            msg = data["detail"][0].get("msg") or str(data["detail"][0])
                        else:
                            msg = data["detail"]
                    else:
                        msg = response.text

                except Exception:
                    msg = response.text

                raise Exception(msg)

            # Защита от не Json ответа
            try:
                if not response.content:
                    return {}

                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type.lower():
                    return response.json()

                return {"raw": response.text}
                
            except Exception:
                raise Exception("Ошибка обработки ответа сервера")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка подключения: {e}")

    
# Авторизация пользователя и сохранение JWT токена
    def login(self, username: str, password: str):
        """
        @requires:
            - username и password заданы
            - endpoint /login доступен

        @modifies:
            - self.token
            - self.role

        @effects:
            - Выполняет авторизацию
            - Сохраняет JWT токен и роль

        @raises:
            - Exception если токен не получен
            - Exception при ошибке API

        @returns:
            - dict с данными авторизации
        """

        data = self._request(
            "POST",
            "/login",
            json={"username": username, "password": password}
        )
        self.token = data.get("access_token")
        self.role = data.get("role")
        if not self.token:
            raise Exception("Не удалось получить токен")
        return data


# Регистрация пользователя через API
    def register(self, username, email, password, role, first_name, last_name, specialty_id=None):
            """
            @requires:
                - обязательные поля заполнены
                - role корректен
                - при role=doctor указан specialty_id

            @modifies:
                - Ничего

            @effects:
                - Отправляет запрос на регистрацию пользователя

            @raises:
                - Exception при ошибке API

            @returns:
                - dict ответ сервера
            """

            payload = {
                "username": username,
                "email": email,
                "password": password,
                "role": role,
                "first_name": first_name,
                "last_name": last_name
            }
            if specialty_id is not None:
                payload["specialty_id"] = specialty_id
                
            return self._request(
                "POST",
                "/register",
                json=payload
            )


# Выход пользователя (очистка токена)
    def logout(self):
        """
        @requires:
            - Ничего

        @modifies:
            - self.token
            - self.role

        @effects:
            - Очищает данные авторизации

        @raises:
            - Ничего

        @returns:
            - None
        """
        self.token = None
        self.role = None
    

# Получение списка медицинских специальностей
    def get_specialties(self):
        """
        @requires:
            - backend доступен

        @modifies:
            - Ничего

        @effects:
            - Получает список медицинских специальностей

        @raises:
            - Exception при ошибке API

        @returns:
            - list словарей специальностей
        """
        return self._request("GET", "/specialties")


# Получение списка врачей по специальности
    def get_doctors(self, specialty_id: int):
        """
        @requires:
            - specialty_id валиден

        @modifies:
            - Ничего

        @effects:
            - Получает список врачей по специальности

        @raises:
            - Exception при ошибке API

        @returns:
            - list врачей
        """
        return self._request(
            "GET",
            "/doctors",
            params={"specialty_id": specialty_id}
        )

    
# Создание записи пациента на прием к врачу
    def create_appointment(self, doctor_id: int, dt: str, note: str = None):
        """
        @requires:
            - doctor_id валиден
            - dt в формате ISO (YYYY-MM-DDTHH:MM)

        @modifies:
            - Ничего

        @effects:
            - Конвертирует datetime в UTC
            - Создает запись через API

        @raises:
            - Exception при некорректном dt
            - Exception при ошибке API

        @returns:
            - dict с appointment_id
        """

        try:
            dt = to_utc_iso(datetime.fromisoformat(dt))
        except:
            raise Exception("Некорректный формат datetime (ISO)")

        return self._request(
            "POST",
            "/appointments",
            json={
                "doctor_id": doctor_id,
                "datetime": dt,
                "note": note
            }
        )


# Форматирование даты приема для отображения в UI
    def format_appointment(self, app: dict):
        """
        @requires:
            - app содержит поле appointment_datetime

        @modifies:
            - app (добавляет formatted_dt)

        @effects:
            - Преобразует datetime в локальное время
            - Форматирует строку для UI

        @raises:
            - Ничего (ошибки перехватываются)

        @returns:
            - dict (обновленный app)
        """

        raw_dt = app.get("appointment_datetime")

        if raw_dt:
            if raw_dt.endswith("Z"):
                raw_dt = raw_dt.replace("Z", "+00:00")

            try:
                dt = datetime.fromisoformat(raw_dt).astimezone()
                app["formatted_dt"] = dt.strftime("%d.%m %H:%M")
            except:
                app["formatted_dt"] = "Ошибка даты"
        else:
            app["formatted_dt"] = "-"

        return app


# Подготовка списка специальностей для отображения в интерфейсе
    def get_specialties_for_ui(self):
        """
        @requires:
            - backend доступен

        @modifies:
            - Ничего

        @effects:
            - Преобразует список специальностей в формат для UI
            - (name, id)

        @raises:
            - Exception при ошибке API

        @returns:
            - list кортежей (name, id)
        """
        data = self.get_specialties()
        return [(s["name"], s["id"]) for s in data]
    

# Получение списка записей текущего пациента
    def get_my_appointments(self):
        """
        @requires:
            - пользователь авторизован

        @modifies:
            - Ничего

        @effects:
            - Получает список приемов текущего пациента

        @raises:
            - Exception при ошибке API

        @returns:
            - list приемов
        """
        return self._request("GET", "/patient/appointments")


# Формирование datetime из UI (дата + время → UTC ISO)
    def build_datetime(self, qdate, time_str: str):
        """
        @requires:
            - qdate — объект с методом toString()
            - time_str в формате HH:MM

        @modifies:
            - Ничего

        @effects:
            - Создает datetime из даты и времени
            - Проверяет шаг 30 минут
            - Переводит в UTC ISO

        @raises:
            - Exception при неправильном формате времени
            - Exception при неверном шаге

        @returns:
            - str (ISO datetime в UTC)
        """
        date_str = qdate.toString("yyyy-MM-dd")
        dt = datetime.fromisoformat(f"{date_str}T{time_str}:00")

        # жестко фиксируем шаг 30 минут
        if dt.minute not in (0, 30):
            raise Exception("Допустимы только значения времени с шагом 30 минут (00 или 30)")

        # локальное → UTC
        dt = dt.astimezone(timezone.utc)

        return to_utc_iso(dt)


# Получение и форматирование списка файлов для UI
    def get_files_for_ui(self, appointment_id: int):
        """
        @requires:
            - appointment_id валиден
            - пользователь имеет доступ

        @modifies:
            - Ничего

        @effects:
            - Получает список файлов
            - Преобразует их в формат UI

        @raises:
            - Exception при ошибке API

        @returns:
            - list словарей {id, file_id, name}
        """
        files = self.get_files_by_appointment(appointment_id)

        return [
            {
                "id": f["id"],               # PostgreSQL record id
                "file_id": f["file_id"],     # GridFS id
                "name": f["filename"]
            }
            for f in files
        ]


# Получение списка приемов врача с фильтрацией
    def get_doctor_appointments(self, date_from=None, date_to=None, search=None, status=None):
        """
        @requires:
            - пользователь авторизован как врач
            - параметры фильтра корректны

        @modifies:
            - Ничего

        @effects:
            - Получает список приемов врача
            - Применяет фильтры
            - Форматирует даты через format_appointment

        @raises:
            - Exception при ошибке API

        @returns:
            - list приемов (с formatted_dt)
        """

        params = {}
        params["limit"] = 50
        params["offset"] = 0
        
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if search:
            params["search"] = search
        if status:
            params["status"] = status

        data = self._request(
            "GET",
            "/doctor/appointments",
            params=params
        )

        # форматирование тут, а не в GUI
        return [self.format_appointment(app) for app in data]

    
# Получение медицинской записи по ID приема
    def get_record(self, appointment_id: int):
        """
        @requires:
            - appointment_id валиден
            - пользователь авторизован

        @modifies:
            - Ничего

        @effects:
            - Получает медицинскую запись по конкретному приему

        @raises:
            - Exception при ошибке API

        @returns:
            - dict с диагнозом, лечением, рекомендациями
        """

        return self._request(
            "GET",
            f"/medical-record/{appointment_id}"
        )


# Создание медицинской записи и (опционально) следующего визита
    def create_record(
        self,
        appointment_id: int,
        diagnosis: str = None,
        medication: str = None,
        recommendations: str = None,
        next_visit: str = None
    ):
        """
        @requires:
            - appointment_id валиден
            - пользователь авторизован как врач
            - next_visit (если есть) в ISO формате

        @modifies:
            - Ничего (кроме отправки запроса)

        @effects:
            - Конвертирует next_visit в UTC
            - Создает медицинскую запись
            - Может инициировать повторный прием

        @raises:
            - Exception при неверном формате next_visit
            - Exception при ошибке API

        @returns:
            - dict результат операции
        """    
    
        if next_visit:
            try:
                next_visit = to_utc_iso(datetime.fromisoformat(next_visit))
            except ValueError:
                raise Exception("Некорректный формат next_visit (YYYY-MM-DDTHH:MM)")

        return self._request(
            "POST",
            "/medical-record",
            json={
                "appointment_id": appointment_id,
                "visit_datetime": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "next_visit": next_visit,
                "diagnosis": diagnosis,
                "medication": medication,
                "recommendations": recommendations
            }
        )


# Получение медицинских записей пациента
    def get_my_records(self):
        """
        @requires:
            - пользователь авторизован

        @modifies:
            - Ничего

        @effects:
            - Получает список медицинских записей пациента

        @raises:
            - Exception при ошибке API

        @returns:
            - list записей
        """

        return self._request("GET", "/patient/records")
    
  
# Проверка файла перед загрузкой (тип, размер, MIME)
    def validate_file(self, file_path: str):
        """
        @requires:
            - file_path существует

        @modifies:
            - Ничего

        @effects:
            - Проверяет расширение файла
            - Проверяет MIME тип
            - Проверяет размер (до 8MB)

        @raises:
            - Exception при несоответствии требованиям

        @returns:
            - None
        """

        if not os.path.isfile(file_path):
            raise Exception("Файл не найден")

        # расширения
        allowed_ext = (".jpg", ".jpeg", ".pdf")
        ext = os.path.splitext(file_path)[-1].lower()


        if ext not in allowed_ext:
            raise Exception("Можно загружать только JPG/JPEG и PDF файлы")

        # MIME
        mime_type, _ = mimetypes.guess_type(file_path)

        allowed_mime = {
            "image/jpeg",
            "application/pdf"
        }

        if mime_type not in allowed_mime:
            raise Exception("Недопустимый тип файла")

        # размер (8MB)
        max_size = 8 * 1024 * 1024
        if os.path.getsize(file_path) > max_size:
            raise Exception("Файл слишком большой (макс 8MB)")
        

# Загрузка файла на сервер (с привязкой к приему)
    def upload_file(self, file_path: str, appointment_id: int):
        """
        @requires:
            - file_path валиден
            - appointment_id существует

        @modifies:
            - Ничего (кроме загрузки на сервер)

        @effects:
            - Валидирует файл
            - Загружает файл через API

        @raises:
            - Exception при ошибке валидации
            - Exception при ошибке загрузки

        @returns:
            - dict с file_id
        """

        # сначала проверка
        self.validate_file(file_path)

        try:
            with open(file_path, "rb") as f:
                files = {
                    "file": (os.path.basename(file_path), f)
                }

                data = {
                    "appointment_id": str(appointment_id)
                }

                return self._request(
                    "POST",
                    "/upload",
                    files=files,
                    data=data
                )
        except Exception as e:
            raise Exception(f"Ошибка загрузки файла: {e}")
    

# Получение списка файлов по ID приема
    def get_files_by_appointment(self, appointment_id: int):
        """
        @requires:
            - appointment_id валиден
            - пользователь имеет доступ

        @modifies:
            - Ничего

        @effects:
            - Получает список файлов по приему

        @raises:
            - Exception при ошибке API

        @returns:
            - list файлов
        """

        return self._request(
            "GET",
            f"/appointment/{appointment_id}/files"
        )

    
# Скачивание файла с сервера с извлечением имени
    def download_file_with_name(self, file_id: str):
        """
        @requires:
            - file_id валиден
            - сервер доступен

        @modifies:
            - Ничего

        @effects:
            - Загружает файл с сервера
            - Извлекает имя файла из заголовков

        @raises:
            - Exception при ошибке загрузки

        @returns:
            - dict {content: bytes, filename: str}
        """

        url = f"{self.base_url}/file/{file_id}"

        try:
            response = requests.get(
                url,
                headers=self._headers(),
                timeout=15
            )

            if response.status_code >= 400:
                try:
                    data = response.json()
                    msg = data.get("detail", response.text)
                except:
                    msg = response.text
                raise Exception(msg)

            # вытаскиваем имя файла
            content_disposition = response.headers.get("Content-Disposition", "")
            filename = "file"

            # Сначала проверяем закодированный вариант с кириллицей (filename*=utf-8'')
            if "filename*=utf-8''" in content_disposition:
                encoded_name = content_disposition.split("filename*=utf-8''")[-1].strip('"')
                filename = unquote(encoded_name)
            # Фолбек для обычных ASCII имен
            elif "filename=" in content_disposition:
                filename = content_disposition.split("filename=")[-1].strip('"')

            return {
                "content": response.content,
                "filename": filename
            }

        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка загрузки файла: {e}")
    

# Получение URL файла для предпросмотра
    def get_file_url(self, file_id: str):
        """
        @requires:
            - file_id валиден

        @modifies:
            - Ничего

        @effects:
            - Формирует URL для доступа к файлу

        @raises:
            - Ничего

        @returns:
            - строка URL файла
        """

        return f"{self.base_url}/file/{file_id}"


# Функционал удаления файла с сервера
    def admin_delete(self, table: str = None, record_id: int = None, *, file_id: str = None, full: bool = False):
        """
        @requires:
            - либо file_id, либо table + record_id

        @modifies:
            - данные на сервере

        @effects:
            - Удаляет файл или запись из БД

        @raises:
            - ValueError если аргументы не заданы
            - Exception при ошибке API

        @returns:
            - dict ответ сервера
        """

        # удаление файла
        if file_id:
            return self._request(
                "DELETE",
                f"/admin/records/appointment_files/{file_id}"
            )

        # удаление записи из БД
        if table and record_id is not None:
            return self._request(
                "DELETE",
                f"/admin/records/{table}/{record_id}",
                params={"full_delete": full}
            )

        raise ValueError("Укажите либо file_id, либо table + record_id")


# Функционал поиска для админа
    def admin_search(self, query: str):
        """
        @requires:
            - query >= 2 символов
            - пользователь admin

        @modifies:
            - Ничего

        @effects:
            - Выполняет поиск пользователей

        @raises:
            - Exception при ошибке API

        @returns:
            - list пользователей
        """

        return self._request("GET", "/admin/search", params={"q": query})


# Сброс пароля для пользователя
    def admin_reset_password(self, user_id: int):
        """
        @requires:
            - user_id валиден
            - пользователь admin

        @modifies:
            - password_hash пользователя (на сервере)

        @effects:
            - Инициирует сброс пароля

        @raises:
            - Exception при ошибке API

        @returns:
            - dict статус операции
        """

        return self._request(
            "POST",
            f"/admin/reset-password/{user_id}"
        )

    
# Получение данных текущего пользователя
    def get_me(self):
        """
        @requires:
            - пользователь авторизован

        @modifies:
            - Ничего

        @effects:
            - Получает данные текущего пользователя

        @raises:
            - Exception при ошибке API

        @returns:
            - dict с данными пользователя
        """

        return self._request("GET", "/me")


# Проверка доступности backend API
    def health(self):
        """
        @requires:
            - backend доступен

        @modifies:
            - Ничего

        @effects:
            - Проверяет доступность API

        @raises:
            - Exception при ошибке подключения

        @returns:
            - dict со статусом
        """

        return self._request("GET", "/health")
