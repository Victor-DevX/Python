# -*- coding: utf-8 -*-
"""
Модуль модели: работа с рынками, отзывами и алгоритмы.
Содержит функции загрузки рынков, поиска, постраничного вывода, добавления отзывов,
удаления рынков и поиска ближайшего рынка.
"""

import os
import math
from auth import get_db_connection
from logger import logger
from decimal import Decimal
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

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT 
                m.fmid,
                m.marketname,
                m.street,
                m.zip,
                m.lat,
                m.lon,
                c.city_name,
                s.state_name,
                ARRAY_REMOVE(ARRAY_AGG(p.product_name), NULL) AS products
            FROM markets m
            LEFT JOIN cities c ON m.city_id = c.city_id
            LEFT JOIN states s ON c.state_id = s.state_id
            LEFT JOIN market_products mp ON m.fmid = mp.fmid
            LEFT JOIN products p ON mp.product_id = p.product_id
            GROUP BY m.fmid, m.marketname, m.street, m.zip, m.lat, m.lon, c.city_name, s.state_name
            ORDER BY m.fmid
        """)

        markets = cur.fetchall()

        cur.close()
        conn.close()

        # сохраняем в кэш
        _markets_cache = markets

        return markets

    except Exception as e:
        logger.error(f"Ошибка загрузки рынков: {e}")
        return []

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

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        m.fmid,
                        m.marketname,
                        m.street,
                        m.zip,
                        m.lat AS x,
                        m.lon AS y,
                        c.city_name,
                        s.state_name,
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
    Возвращает структурированные данные рынка (без UI)
    """
    if not market:
        return None

    reviews = get_reviews_by_fmid(market.get("fmid"))

    return {
        "name": market.get("marketname"),
        "address": market.get("street"),
        "city": market.get("city_name"),
        "state": market.get("state_name"),
        "zip": market.get("zip"),
        "coords": (market.get("x"), market.get("y")),
        "products": market.get("products", []),
        "reviews": reviews,
        "avg_rating": market.get("avg_rating", 0),
        "reviews_count": market.get("reviews_count", 0)
    }



'''
def show_market_info(market):
    """
    @requires: market — словарь с ключами: fmid, marketname, street, zip, city_name, state_name, x, y, products
    @modifies: None
    @effects: Формирует строковое представление информации о рынке, включая адрес, координаты, товары и отзывы
    @raises: Исключения не выбрасываются, ошибки логируются (через get_reviews_by_fmid)
    """
    if not market:
        return "Информация о рынке отсутствует."
    lines = [f"=== {market.get('marketname','Без имени')} ==="]
    lines.append(f"Адрес: {market.get('street','')}")
    lines.append(f"Город: {market.get('city_name','')}, Штат: {market.get('state_name','')}, ZIP: {market.get('zip','')}")
    lines.append(f"Координаты: ({market.get('x','')},{market.get('y','')})")

    products = market.get("products", [])
    if products:
        lines.append("Товары:")
    for p in products:
        if p:
            lines.append(f" - {p}")  # каждый товар отдельной строкой
    else:
        lines.append("Информация о товарах отсутствует.")

    reviews = get_reviews_by_fmid(market.get("fmid"))
    if reviews:
        lines.append("Отзывы:")
        for r in reviews:
            name = " ".join(filter(None, [r.get("first_name"), r.get("last_name")])).strip()
            name = name if name else r.get("username","")
            lines.append(f" - {name}: {r.get('rating',0)} / 5 — {r.get('text','')}")
        avg = round(sum(r.get("rating",0) for r in reviews)/len(reviews),2)
    else:
        lines.append("Нет отзывов.")
        avg = 0.0
    lines.append(f"\nСредний рейтинг: {avg}")
    return "\n".join(lines)
'''

def get_reviews_by_fmid(fmid):
    """
    @requires: Таблица reviews существует
    @modifies: None
    @effects: Возвращает все отзывы для указанного рынка
    @raises: Исключения при чтении логируются
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM reviews WHERE fmid=%s ORDER BY review_id;",
                    (fmid,)
                )
                return cur.fetchall()

    except Exception as e:
        logger.error(f"Ошибка загрузки отзывов для fmid={fmid}: {e}")
        return []


def add_review(fmid, username, rating, text):
    """
    @requires: Таблица reviews существует, rating 1-5, username и fmid валидны
    @modifies: Таблица reviews
    @effects: Добавляет новый отзыв к указанному рынку
    @raises: Исключения при записи логируются
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO reviews (fmid, username, rating, text)
            VALUES (%s,%s,%s,%s);
        """, (fmid, username, rating, text))
        conn.commit()
        conn.close()
        logger.info(f"Добавлен отзыв пользователя {username} для рынка {fmid}")
    except Exception as e:
        logger.error(f"Ошибка добавления отзыва: {e}")


def get_average_rating(fmid):
    """
    @requires: Таблица reviews существует
    @modifies: None
    @effects: Вычисляет средний рейтинг рынка
    @raises: Исключения при чтении логируются
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT COALESCE(AVG(rating), 0)
                    FROM reviews
                    WHERE fmid=%s;
                """, (fmid,))

                return round(cur.fetchone()[0], 2)

    except Exception as e:
        logger.error(f"Ошибка расчета рейтинга: {e}")
        return 0.0


def delete_market(fmid):
    """
    @requires: Таблицы markets и reviews существуют
    @modifies: Таблицы markets и reviews, кэш _markets_cache
    @effects: Удаляет рынок и все его отзывы, сбрасывает кэш
    @raises: Исключения при удалении логируются
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:

                cur.execute("DELETE FROM markets WHERE fmid=%s RETURNING fmid;", (fmid,))
                deleted = cur.fetchone()

                if not deleted:
                    return False

                conn.commit()

        clear_markets_cache()

        return True

    except Exception as e:
        logger.error(f"Ошибка удаления рынка {fmid}: {e}")
        return False


def haversine(lat1, lon1, lat2, lon2):
    """
    @requires: Координаты двух точек
    @modifies: None
    @effects: Вычисляет расстояние между точками в км
    @raises: None
    """
    R = 6371
    phi1, phi2 = map(math.radians, [lat1, lat2])
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def find_markets_by_distance(markets, lat, lon, n=5):
    """
    @requires: markets — итерируемая коллекция словарей, каждый из которых содержит
               координаты рынка по ключам "x" (широта) и "y" (долгота).
               lat и lon — числовые значения (float или приводимые к float),
               задающие точку отсчёта.
               Функция haversine(lat1, lon1, lat2, lon2) определена.

    @modifies:  None

    @effects: Фильтрует рынки, оставляя только те, у которых координаты "x" и "y"
              можно корректно привести к float.
              Вычисляет расстояние от заданной точки (lat, lon) до каждого
              валидного рынка с использованием функции haversine.
              Сортирует рынки по возрастанию расстояния и возвращает список
              из n ближайших рынков.

    @raises: ValueError — если ни один рынок не содержит корректных координат.
             Исключения TypeError и ValueError при преобразовании координат
             перехватываются внутри функции.
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
    @modifies: Глобальный кэш _markets_cache
    @effects: Очищает кэш рынков
    @raises: None
    """
    global _markets_cache
    _markets_cache = None