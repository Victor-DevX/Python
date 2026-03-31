# -*- coding: utf-8 -*-
"""
Модуль модели: работа с рынками, отзывами и алгоритмы.
Содержит функции загрузки рынков, поиска, постраничного вывода, добавления отзывов,
удаления рынков и поиска ближайшего рынка.
"""

import os
import math
from contextlib import closing
from auth import get_db_connection
from logger import logger
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PER_PAGE = 15

_markets_cache = None


def load_markets():
    """
    @requires: Доступна функция get_db_connection() для подключения к БД.
               Глобальная переменная _markets_cache определена.
               Структура БД содержит таблицы: markets, cities, states,
               market_products, products с корректными связями.

    @modifies: _markets_cache (заполняется данными при первом вызове).

    @effects: Загружает список рынков из базы данных с объединением информации
              о городе, штате и списке продуктов.
              Если данные уже были загружены ранее, возвращает их из кэша
              без повторного запроса к БД.
              В случае ошибки логирует сообщение и возвращает пустой список.

    @raises: Исключения не пробрасываются наружу — перехватываются внутри функции.
             Возможные ошибки (например, подключения к БД) логируются через logger.
    """
    global _markets_cache
    if _markets_cache is not None:
        return _markets_cache

    conn = None
    try:
        conn = get_db_connection()
        # ВАЖНО: Здесь частичный вызов cursor_factory, так как он уже прописана внутри функции get_db_connection в auth.py
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    m.fmid, m.marketname, m.street, m.zip, m.lat, m.lon,
                    c.city_name, s.state_name,
                    ARRAY_REMOVE(ARRAY_AGG(p.product_name), NULL) AS products
                FROM markets m
                LEFT JOIN cities c ON m.city_id = c.city_id
                LEFT JOIN states s ON c.state_id = s.state_id
                LEFT JOIN market_products mp ON m.fmid = mp.fmid
                LEFT JOIN products p ON mp.product_id = p.product_id
                GROUP BY m.fmid, m.marketname, m.street, m.zip, m.lat, m.lon, c.city_name, s.state_name
                ORDER BY m.fmid
            """)
            # Сначала забираем все данные, потом выходим из блока курсора
            data = cur.fetchall()
            markets_cache = data
            return data
    except Exception as e:
        logger.error(f"Ошибка загрузки рынков: {e}")
        return []
    finally:
        # Это гарантирует, что соединение вернется в пул/закроется, даже если запрос упал с ошибкой
        if conn:
            conn.close()

def search_markets(markets, query):
    """
    @requires: query — непустая строка для поиска.
               Доступна функция get_db_connection().
               База данных содержит таблицы: markets, cities, states,
               market_products, products с корректными связями.
               Параметр markets передаётся, но в текущей реализации не используется.

    @modifies: None

    @effects: Выполняет SQL-запрос к базе данных для поиска рынков:
             - по частичному совпадению города (city_name),
             - по частичному совпадению штата (state_name),
             - по точному совпадению ZIP-кода.
             Возвращает список словарей с информацией о рынках,
             включая координаты и список продуктов.
             В случае отсутствия совпадений возвращает пустой список.

    @raises: Исключения, связанные с подключением к БД или выполнением запроса,
             могут быть выброшены наружу (не перехватываются внутри функции).
    """
    q_like = f"%{query.lower().strip()}%"
    q_exact = query.strip()
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    m.fmid, m.marketname, m.street, m.zip,
                    m.lat AS x, m.lon AS y,
                    c.city_name, s.state_name,
                    ARRAY_REMOVE(ARRAY_AGG(p.product_name), NULL) AS products
                FROM markets m
                LEFT JOIN cities c ON m.city_id = c.city_id
                LEFT JOIN states s ON c.state_id = s.state_id
                LEFT JOIN market_products mp ON m.fmid = mp.fmid
                LEFT JOIN products p ON mp.product_id = p.product_id
                WHERE LOWER(c.city_name) LIKE %s
                   OR LOWER(s.state_name) LIKE %s
                   OR CAST(m.zip AS TEXT) = %s
                GROUP BY m.fmid, m.marketname, m.street, m.zip, m.lat, m.lon, c.city_name, s.state_name
                ORDER BY m.fmid;
            """, (q_like, q_like, q_exact))
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        return []
    finally:
        if conn:
            conn.close()


def paginate_markets(markets, page):
    """
    @requires: markets — список словарей, page — int >= 0
    @modifies: None
    @effects: Возвращает подсписок рынков для указанной страницы и общее число страниц
    @raises: None
    """
    total_pages = (len(markets) + PER_PAGE - 1) // PER_PAGE
    start = page * PER_PAGE
    end = start + PER_PAGE
    return markets[start:end], total_pages


def get_market_details(market):
    """
    @requires: market — словарь с данными рынка (или None).
               Доступна функция get_reviews_by_fmid().
    @modifies: None
    @effects: Формирует структурированное представление рынка:
              - основная информация (адрес, координаты, продукты),
              - список отзывов,
              - средняя оценка и количество отзывов.
              Если market=None — возвращает None.
    @raises: None (ошибки внутри get_reviews_by_fmid обрабатываются отдельно).
    @returns: dict | None
    """
    if not market:
        return None

    reviews = get_reviews_by_fmid(market.get("fmid"))
    
    # Реализация динамического вычисления средней оценки на основе загруженных отзывов
    avg = sum(r["rating"] for r in reviews) / len(reviews) if reviews else 0.0

    return {
        "name": market.get("marketname"),
        "address": market.get("street"),
        "city": market.get("city_name"),
        "state": market.get("state_name"),
        "zip": market.get("zip"),
        "coords": (market.get("x"), market.get("y")),
        "products": market.get("products", []),
        "reviews": reviews,
        "avg_rating": round(avg, 2),
        "reviews_count": len(reviews)
    }


def get_reviews_by_fmid(fmid):
    """
    @requires: fmid — валидный идентификатор рынка;
               таблица reviews существует.
    @modifies: None
    @effects: Выполняет SELECT-запрос к таблице reviews и возвращает
              список отзывов для указанного рынка, отсортированных по review_id.
              При ошибке логирует её и возвращает пустой список.
    @raises: None (исключения перехватываются и логируются).
    @returns: list
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM reviews WHERE fmid=%s ORDER BY review_id;",
                (fmid,)
            )
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Ошибка загрузки отзывов для fmid={fmid}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def add_review(fmid, username, rating, text):
    """
    @requires: fmid — существующий рынок;
               username — существующий пользователь;
               rating — целое число от 1 до 5;
               text — строка (может быть пустой);
               таблица reviews существует.
    @modifies: Таблица reviews в БД.
    @effects: Добавляет новый отзыв в базу данных и фиксирует изменения (commit).
              При успешном добавлении логирует информацию.
              При ошибке логирует её.
    @raises: None (исключения перехватываются и логируются).
    @returns: None
    """
    try:
        with closing(get_db_connection()) as conn: # Исправлено: добавлено closing
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO reviews (fmid, username, rating, text)
                            VALUES (%s,%s,%s,%s);
                        """, (fmid, username, rating, text))
                        conn.commit()
        logger.info(f"Добавлен отзыв пользователя {username} для рынка {fmid}")
    except Exception as e:
        logger.error(f"Ошибка добавления отзыва: {e}")


def delete_market(fmid):
    """
    @requires: fmid — валидный идентификатор рынка;
               таблицы markets и reviews существуют.
    @modifies: Таблицы markets и reviews, а также кэш _markets_cache.
    @effects: Удаляет все отзывы, связанные с рынком, затем сам рынок.
              Если рынок был удалён — очищает кэш и возвращает True.
              Если рынок не найден — возвращает False.
              При ошибке логирует её и возвращает False.
    @raises: None (исключения перехватываются и логируются).
    @returns: bool
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Сначала отзывы
            cur.execute("DELETE FROM reviews WHERE fmid=%s;", (fmid,))
            # Затем рынок
            cur.execute("DELETE FROM markets WHERE fmid=%s RETURNING fmid;", (fmid,))
            deleted = cur.fetchone()
            conn.commit()
                
            if deleted:
                clear_markets_cache()
                return True
            return False
    except Exception as e:
        logger.error(f"Ошибка удаления рынка {fmid}: {e}")
        return False
    finally:
        if conn:
            conn.close()


def haversine(lat1, lon1, lat2, lon2):
    """
    @requires: lat1, lon1, lat2, lon2 — числовые значения координат (float).
    @modifies: None
    @effects: Вычисляет расстояние между двумя географическими точками
              по формуле гаверсинусов.
    @raises: None
    @returns: float — расстояние в километрах
    """
    R = 6371
    phi1, phi2 = map(math.radians, [lat1, lat2])
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def find_markets_by_distance(markets, lat, lon, n=5):
    """
    @requires: markets — итерируемая коллекция словарей с ключами "lat" и "lon";
               lat и lon — координаты точки отсчёта (float);
               n — положительное целое число;
               функция haversine определена.
    @modifies: None
    @effects: Отбирает рынки с корректными координатами,
              вычисляет расстояние до каждого,
              сортирует по возрастанию расстояния
              и возвращает n ближайших рынков.
    @raises: ValueError — если нет ни одного рынка с корректными координатами.
    @returns: list
    """
    valid = []
    for m in markets:
        try:
            # Принудительно пробуем превратить координаты в числа
            x = float(m.get("lat"))
            y = float(m.get("lon"))
            valid.append((m, x, y))
        except (TypeError, ValueError):
            # Если координаты битые, пустые (None) или отсутствуют — пропускаем рынок
            continue

    if not valid:
        raise ValueError("Нет рынков с корректными координатами")

    distances = [
        (m, haversine(lat, lon, x, y))
        for m, x, y in valid
    ]

    distances.sort(key=lambda item: item[1])
    return [m for m, _ in distances[:n]]

def clear_markets_cache():
    """
    @requires: None
    @modifies: Глобальная переменная _markets_cache.
    @effects: Очищает кэш рынков (устанавливает значение None).
    @raises: None
    @returns: None
    """
    global _markets_cache
    _markets_cache = None