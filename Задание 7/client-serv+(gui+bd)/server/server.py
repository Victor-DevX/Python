# -*- coding: utf-8 -*-
import socket
import json
import struct
import threading
from decimal import Decimal
from auth import register_user, login_user, ensure_admin_in_db, get_db_connection
import kernel
from logger import logger

HOST = '127.0.0.1'
PORT = 13101

# Специальный энкодер, чтобы JSON мог переваривать тип Decimal из PostgreSQL (координаты)
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        """
        @requires: obj — произвольный Python-объект.
        @modifies: None
        @effects: Преобразует объект типа Decimal в float для корректной сериализации в JSON.
                Для остальных типов делегирует обработку родительскому JSONEncoder.
        @raises: TypeError если объект не может быть сериализован базовым энкодером.
        """
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def recvall(sock, n):
    """
    @requires: sock — открытый сокет с методом recv().
               n — положительное целое число (количество байт для чтения).
    @modifies: None
    @effects: Считывает ровно n байт из сокета, получая данные частями.
              Возвращает bytearray длиной n при успехе.
              Если соединение закрыто до получения всех данных — возвращает None.
    @raises: socket.error при ошибках работы с сокетом.
    """
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def handle_client(conn, addr):
    """
    @requires: conn — активное TCP-соединение с клиентом.
               addr — адрес клиента (tuple).
               Определены функции recvall() и process_request().
    @modifies: conn (чтение/запись), логирование через logger.
    @effects: В цикле принимает сообщения клиента:
              - читает длину (4 байта, big-endian),
              - читает payload,
              - декодирует JSON,
              - обрабатывает через process_request(),
              - отправляет JSON-ответ с префиксом длины.
              При ошибке или разрыве соединения завершает обработку клиента.
    @raises: None (все исключения перехватываются и логируются).
    """
    logger.info(f"[+] Подключен клиент: {addr}")
    with conn:
        while True:
            try:
                # Проверка длины сообщения (4 байта)
                raw_msglen = recvall(conn, 4)
                if not raw_msglen:
                    break
                msglen = struct.unpack('>I', raw_msglen)[0]
                
                # Читение сообщения
                data = recvall(conn, msglen)
                if not data:
                    break
                
                request = json.loads(data.decode('utf-8'))
                response = process_request(request)
                
                # Отправляем ответ (учесть что сначала длина, а потом данные)
                response_data = json.dumps(response, cls=CustomJSONEncoder).encode('utf-8')
                conn.sendall(struct.pack('>I', len(response_data)) + response_data)
                
            except Exception as e:
                logger.error(f"[-] Ошибка с клиентом {addr}: {e}")
                break
    logger.info(f"[-] Клиент отключен: {addr}")

def process_request(req):
    """
    @requires: req — словарь с ключом "action" и необязательным "kwargs".
               Доступны функции auth и kernel.
    @modifies: Может изменять состояние БД (регистрация, отзывы, удаление рынков).
    @effects: Обрабатывает действие клиента:
              - login_user / register_user,
              - load_markets / search_markets,
              - find_markets_by_distance,
              - add_review / delete_market,
              - get_market_details.
              Возвращает словарь формата {"status": "...", ...}.
    @raises: None (все исключения перехватываются и возвращаются как ошибка).
    """
    action = req.get("action")
    kwargs = req.get("kwargs", {})

    try:
        # Авторизация пользователя
        if action == "login_user":
            ok, res = login_user(kwargs["username"], kwargs["password"])
            return {"status": "success", "ok": ok, "data": res}
        
        elif action == "register_user":
            ok, res = register_user(kwargs["username"], kwargs["password"], 
                                         kwargs["first_name"], kwargs["last_name"], kwargs.get("middle_name", ""))
            return {"status": "success", "ok": ok, "data": res}
        
        # Загрузка рынков
        elif action == "load_markets":
            markets = kernel.load_markets()
            return {"status": "success", "data": markets}
            
        elif action == "search_markets":
            # На сервере нам не нужен весь список, kernel.py сам ходит в БД
            res = kernel.search_markets(None, kwargs["query"]) 
            return {"status": "success", "data": res}
            
        elif action == "find_markets_by_distance":
            logger.info(f"[*] Сервер получил запрос на поиск по координатам: {kwargs}")
            markets = kernel.load_markets()
            if not markets:
                logger.error("[-] Ошибка сервера: Список рынков пуст (база не загрузилась)")
                return {"status": "error", "message": "Список рынков пуст на сервере"}
                
            res = kernel.find_markets_by_distance(markets, kwargs["lat"], kwargs["lon"])
            logger.info(f"[*] Сервер нашел {len(res)} ближайших рынков.")
            return {"status": "success", "data": res}
            '''
            markets = kernel.load_markets() # Берем из кэша сервера
            res = kernel.find_markets_by_distance(markets, kwargs["lat"], kwargs["lon"])
            return {"status": "success", "data": res}
            '''
            
        elif action == "add_review":
            kernel.add_review(kwargs["fmid"], kwargs["username"], kwargs["rating"], kwargs["text"])
            return {"status": "success"}
            
        elif action == "delete_market":
            res = kernel.delete_market(kwargs["fmid"])
            return {"status": "success", "data": res}
            
        elif action == "get_market_details":
            res = kernel.get_market_details(kwargs["market"])
            return {"status": "success", "data": res}

        return {"status": "error", "message": "Неизвестная команда"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_db_connection():
    """
    @requires: Доступна функция get_db_connection().
    @modifies: Логирование через logger.
    @effects: Проверяет подключение к базе данных, открывая и закрывая соединение.
              Логирует результат (успех или ошибка).
    @raises: None (исключения перехватываются и логируются).
    """
    try:
        # Для проеверки пробуем открыть и сразу закрыть соединение
        with get_db_connection() as conn:
            logger.info("[+] База данных farmers_markets.sql успешно подключена!")
    except Exception as e:
        logger.error(f"[-] Внимание! Ошибка подключения к базе данных: {e}")

check_db_connection()


def start_server():
    """
    @requires: Заданы HOST и PORT.
               Доступны socket, threading, ensure_admin_in_db(), handle_client().
    @modifies: Сетевые ресурсы (создание сокета), потоки выполнения, состояние БД (создание администратора).
    @effects: Запускает TCP-сервер:
              - создает администратора при необходимости,
              - биндуется к HOST:PORT,
              - принимает входящие подключения,
              - для каждого клиента запускает отдельный поток handle_client().
    @raises: socket.error при ошибках создания/биндинга/прослушивания сокета.
    """
    ensure_admin_in_db()
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        s.bind((HOST, PORT))
        s.listen()
        print(f"[*] Сервер запущен на {HOST}:{PORT}...")
        
        while True:
            conn, addr = s.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()

if __name__ == "__main__":
    start_server()