# -*- coding: utf-8 -*-
import socket
import json
import struct

HOST = '127.0.0.1'
PORT = 13101

def _send_request(action, **kwargs):
    """
    @requires: action — строка, определяющая тип запроса к серверу.
               kwargs — именованные параметры запроса (сериализуемые в JSON).
               Сервер доступен по HOST и PORT.
               Доступны модули socket, json и struct.

    @modifies: Сетевые ресурсы (создаёт и использует сокет).

    @effects: Устанавливает TCP-соединение с сервером.
              Формирует JSON-запрос с полями "action" и "kwargs",
              отправляет его с префиксом длины (4 байта).
              Получает ответ от сервера:
              - сначала читает длину,
              - затем читает тело сообщения.
              Возвращает ответ в виде словаря.
              В случае ошибки возвращает словарь с ключом "status": "error".

    @raises: Исключения не пробрасываются наружу.
             ConnectionRefusedError и другие ошибки перехватываются
             и преобразуются в словарь ошибки.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            
            # Формируем и отправляем пакет
            req = {"action": action, "kwargs": kwargs}
            req_data = json.dumps(req).encode('utf-8')
            s.sendall(struct.pack('>I', len(req_data)) + req_data)
            
            # Чтение длины ответа
            raw_msglen = s.recv(4)
            if not raw_msglen:
                return {"status": "error", "message": "Сервер разорвал соединение"}
            msglen = struct.unpack('>I', raw_msglen)[0]
            
            # Читаем данные в ответе
            data = bytearray()
            while len(data) < msglen:
                packet = s.recv(msglen - len(data))
                if not packet:
                    break
                data.extend(packet)
                
            return json.loads(data.decode('utf-8'))
            
    except ConnectionRefusedError:
        print("[-] Ошибка: Сервер недоступен!")
        return {"status": "error", "message": "Сервер недоступен"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# === ЗАГЛУШКИ ФУНКЦИЙ ДЛЯ GUI ===

def login_user(username, password):
    """
    @requires: username и password — строки;
               сервер доступен и поддерживает действие "login_user".
    @modifies: Сетевые ресурсы (через _send_request).
    @effects: Отправляет запрос на сервер для аутентификации пользователя.
              Обрабатывает различные форматы ответа сервера:
              - {"status": "success", "ok": bool, "data": dict}
              - {"status": "success", "data": [bool, dict]}
              Возвращает кортеж (ok, data):
              - ok — результат авторизации,
              - data — данные пользователя или сообщение об ошибке.
              В случае ошибки возвращает (False, message).
    @raises: None (исключения перехватываются внутри _send_request).
    @returns: tuple(bool, dict|str)
    """
    res = _send_request("login_user", username=username, password=password)
        
        # ОТЛАДКА: реальный ответ сервера
    print(f"DEBUG FROM SERVER: {res}") 

    if res.get("status") == "success":
            # Если сервер присылает { "status": "success", "ok": True, "data": {...} }
        if "ok" in res:
            return res["ok"], res["data"]
            
        # Если сервер присылает { "status": "success", "data": [True, {...}] }
        # (частая ошибка при возврате кортежа в JSON)
        if isinstance(res.get("data"), list) and len(res["data"]) == 2:
            return res["data"][0], res["data"][1]

    return False, res.get("message", "Ошибка сети")

def register_user(username, password, first_name, last_name, middle_name=""):
    """
    @requires: username, password, first_name, last_name — строки;
               middle_name — строка (опционально);
               сервер доступен и поддерживает действие "register_user".
    @modifies: Сетевые ресурсы.
    @effects: Отправляет запрос на сервер для регистрации пользователя.
              Возвращает кортеж (ok, data):
              - ok — успешность регистрации,
              - data — данные пользователя или сообщение об ошибке.
              В случае ошибки возвращает (False, message).
    @raises: None (исключения перехватываются).
    @returns: tuple(bool, dict|str)
    """

    res = _send_request("register_user", username=username, password=password, 
                        first_name=first_name, last_name=last_name, middle_name=middle_name)
    if res.get("status") == "success":
        return res["ok"], res["data"]
    return False, res.get("message", "Ошибка сети")

def load_markets():
    """
    @requires: Сервер доступен и поддерживает действие "load_markets".
    @modifies: Сетевые ресурсы.
    @effects: Запрашивает у сервера список рынков.
              Возвращает список словарей с данными рынков.
              В случае ошибки возвращает пустой список.
    @raises: None
    @returns: list
    """
    res = _send_request("load_markets")
    return res.get("data", [])

def search_markets(markets, query):
    """
    @requires: query — строка;
               параметр markets передаётся для совместимости с GUI;
               сервер поддерживает действие "search_markets".
    @modifies: Сетевые ресурсы.
    @effects: Отправляет запрос на сервер для поиска рынков по query.
              Возвращает список найденных рынков.
              В случае ошибки возвращает пустой список.
    @raises: None
    @returns: list
    """
    # ВАЖНО: Параметр markets оставляем для совместимости с GUI, но на сервер шлем только query
    res = _send_request("search_markets", query=query)
    return res.get("data", [])

def find_markets_by_distance(markets, lat, lon):
    """
    @requires: lat и lon — числовые значения (float);
               параметр markets используется только для совместимости;
               сервер поддерживает действие "find_markets_by_distance".
    @modifies: Сетевые ресурсы.
    @effects: Отправляет запрос на сервер для поиска ближайших рынков.
              Если ответ успешен — возвращает список рынков.
              При ошибке выводит сообщение в консоль и возвращает пустой список.
    @raises: None
    @returns: list
    """
    res = _send_request("find_markets_by_distance", lat=lat, lon=lon)
    if res.get("status") == "success":
        return res.get("data", [])
    else:
        # Теперь, если сервер вернет ошибку, мы увидим её в терминале клиента
        print(f"[-] Ошибка от сервера при поиске по координатам: {res.get('message')}")
        return []

    '''
    # На сервере есть закэшированный список рынков
    res = _send_request("find_markets_by_distance", lat=lat, lon=lon)
    return res.get("data", [])
    '''



def add_review(fmid, username, rating, text):
    """
    @requires: fmid — идентификатор рынка;
               username — строка;
               rating — число (обычно 1–5);
               text — строка;
               сервер поддерживает действие "add_review".
    @modifies: Состояние данных на сервере (через API).
    @effects: Отправляет запрос на сервер для добавления отзыва.
              Явного результата не возвращает.
              При ошибке информация доступна через лог или ответ сервера.
    @raises: None
    @returns: None
    """

    _send_request("add_review", fmid=fmid, username=username, rating=rating, text=text)

def delete_market(fmid):
    """
    @requires: fmid — идентификатор рынка;
               сервер поддерживает действие "delete_market".
    @modifies: Состояние данных на сервере.
    @effects: Отправляет запрос на сервер для удаления рынка.
              Возвращает результат операции:
              - True — если рынок успешно удалён,
              - False — если операция не удалась.
    @raises: None
    @returns: bool
    """
    res = _send_request("delete_market", fmid=fmid)
    return res.get("data", False)

def get_market_details(market):
    """
    @requires: market — словарь с данными рынка или его идентификатор;
               сервер поддерживает действие "get_market_details".
    @modifies: Сетевые ресурсы.
    @effects: Отправляет запрос на сервер для получения полной информации о рынке.
              Возвращает словарь с деталями:
              (адрес, координаты, продукты, отзывы и т.д.).
              В случае ошибки возвращает пустой словарь.
    @raises: None
    @returns: dict
    """
    res = _send_request("get_market_details", market=market)
    return res.get("data", {})