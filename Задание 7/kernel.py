# -*- coding: utf-8 -*-
"""
Модуль модели: работа с рынками, отзывами и алгоритмы
"""

import csv
import os
import math
from logger import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MARKETS_FILE = os.path.join(BASE_DIR, "Export.csv")
REVIEWS_FILE = os.path.join(BASE_DIR, "reviews.csv")
PER_PAGE = 15

# ==========================================================
# Работа с рынками
# ==========================================================

def ensure_markets_file():
    """
    @requires: MARKETS_FILE может существовать или нет
    @modifies: Ничего
    @effects: Загружает все рынки из CSV файла и преобразует координаты в float
    @raises: Исключения при чтении файла логируются
    @returns: list[dict] — список словарей с информацией о рынках
    """
    if not os.path.exists(MARKETS_FILE):
        with open(MARKETS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["FMID","MarketName","city","State","zip","x","y"])
            writer.writeheader()
        logger.info("Файл Export.csv создан")

def load_markets():
    """
    @requires: MARKETS_FILE может существовать или нет
    @modifies: Ничего
    @effects: Загружает все рынки из CSV файла и преобразует координаты в float
    @raises: Исключения при чтении файла логируются
    @returns: list[dict] — список словарей с информацией о рынках
    """
    ensure_markets_file()
    markets = []
    try:
        with open(MARKETS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    row["x"] = float(row.get("x") or 0)
                    row["y"] = float(row.get("y") or 0)
                except ValueError:
                    row["x"], row["y"] = 0, 0
                markets.append(row)
        logger.info(f"Загружено рынков: {len(markets)}")
    except Exception as e:
        logger.error(f"Ошибка чтения Export.csv: {e}")
    return markets

def save_markets(markets):
    """
    @requires: markets — список словарей с рынками
    @modifies: MARKETS_FILE
    @effects: Перезаписывает CSV файл рынков с текущим содержимым
    @raises: IOError если запись невозможна
    @returns: None
    """
    if not markets:
        return
    fieldnames = markets[0].keys()
    try:
        with open(MARKETS_FILE, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(markets)
        logger.info("Файл рынков обновлен")
    except Exception as e:
        logger.error(f"Ошибка записи Export.csv: {e}")

def paginate_markets(markets, page):
    """
    @requires: markets — список словарей, page — целое число >=0
    @modifies: Ничего
    @effects: Возвращает подсписок рынков для указанной страницы
    @raises: Ничего
    @returns: list[dict] — подсписок рынков для страницы
    """
    start = page * PER_PAGE
    end = start + PER_PAGE
    return markets[start:end]

def search_markets(markets, field, query):
    """
    @requires: markets — список словарей, field — ключ словаря, query — строка
    @modifies: Ничего
    @effects: Фильтрует рынки по полю field, сравнивая с query без учета регистра
    @raises: Ничего
    @returns: list[dict] — список рынков, удовлетворяющих условию
    """
    query = query.lower()
    return [m for m in markets if str(m.get(field, "")).lower() == query]

def show_market_info(market):
    """
    @requires: market — словарь или None
    @modifies: Ничего
    @effects: Формирует строковое представление информации о рынке
    @raises: Ничего
    @returns: str — строка с деталями рынка или сообщение об отсутствии информации
    """
    if not market:
        return "Информация о рынке отсутствует."
    lines = [f"{k}: {v}" for k, v in market.items()]
    return "\n".join(lines)

def delete_market(fmid):
    """
    @requires: market — словарь или None
    @modifies: Ничего
    @effects: Формирует строковое представление информации о рынке
    @raises: Ничего
    @returns: str — строка с деталями рынка или сообщение об отсутствии информации
    """
    success = False
    markets = load_markets()
    new_markets = [m for m in markets if m["FMID"] != fmid]
    if len(new_markets) != len(markets):
        save_markets(new_markets)
        success = True

    # удалить отзывы
    if os.path.exists(REVIEWS_FILE):
        reviews = load_reviews()
        reviews = [r for r in reviews if r["FMID"] != fmid]
        save_reviews(reviews)
    if success:
        logger.info(f"Рынок {fmid} удален вместе с отзывами")
    return success

# ==========================================================
# Работа с отзывами
# ==========================================================

def ensure_reviews_file():
    """
    @requires: Ничего
    @modifies: REVIEWS_FILE
    @effects: Создает файл reviews.csv с заголовком, если отсутствует
    @raises: IOError если создать файл невозможно
    @returns: None
    """
    if not os.path.exists(REVIEWS_FILE):
        with open(REVIEWS_FILE, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "FMID","username","rating","text","first_name","last_name","middle_name"])
            writer.writeheader()
        logger.info("Файл reviews.csv создан")

def load_reviews():
    """
    @requires: REVIEWS_FILE может существовать
    @modifies: Ничего
    @effects: Загружает все отзывы из CSV файла
    @raises: Ничего, ошибки логируются
    @returns: list[dict] — список словарей с отзывами
    """
    ensure_reviews_file()
    reviews = []
    with open(REVIEWS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["rating"] = int(row["rating"])
            reviews.append(row)
    return reviews

def save_reviews(reviews):
    """
    @requires: reviews — список словарей с отзывами
    @modifies: REVIEWS_FILE
    @effects: Перезаписывает CSV файл отзывов
    @raises: IOError если запись невозможна
    @returns: None
    """
    ensure_reviews_file()
    with open(REVIEWS_FILE, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "FMID","username","rating","text","first_name","last_name","middle_name"])
        writer.writeheader()
        writer.writerows(reviews)

def get_reviews_by_fmid(fmid):
    """
    @requires: fmid — строка идентификатора рынка
    @modifies: Ничего
    @effects: Возвращает все отзывы для указанного рынка
    @raises: Ничего
    @returns: list[dict] — список отзывов для рынка
    """
    return [r for r in load_reviews() if r["FMID"] == fmid]

def add_review(fmid, username, rating, text, first_name="", last_name="", middle_name=""):
    """
    @requires: rating — int 1-5, fmid, username, text — строки
    @modifies: REVIEWS_FILE
    @effects: Добавляет новый отзыв в CSV файл
    @raises: ValueError если rating вне диапазона 1-5
    @returns: None
    """
    if rating < 1 or rating > 5:
        raise ValueError("Рейтинг должен быть 1-5")
    reviews = load_reviews()
    reviews.append({
        "FMID": fmid,
        "username": username,
        "rating": int(rating),
        "text": text,
        "first_name": first_name,
        "last_name": last_name,
        "middle_name": middle_name
    })
    save_reviews(reviews)

def get_average_rating(fmid):
    """
    @requires: fmid — строка идентификатора рынка
    @modifies: Ничего
    @effects: Вычисляет средний рейтинг рынка по отзывам
    @raises: Ничего
    @returns: float — средний рейтинг, 0.0 если отзывов нет
    """
    reviews = get_reviews_by_fmid(fmid)
    if not reviews:
        return 0.0
    return round(sum(r["rating"] for r in reviews)/len(reviews),2)

# ==========================================================
# Haversine
# ==========================================================

def haversine(lat1, lon1, lat2, lon2):
    """
    @requires: lat1, lon1, lat2, lon2 — числа (широта и долгота)
    @modifies: Ничего
    @effects: Вычисляет расстояние между двумя точками на земной поверхности в км
    @raises: Ничего
    @returns: float — расстояние в километрах
    """
    R = 6371
    phi1, phi2 = map(math.radians, [lat1, lat2])
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def find_nearest_market(markets, x, y):
    """
    @requires: markets — список словарей с полями 'x' и 'y', x, y — координаты пользователя
    @modifies: Ничего
    @effects: Находит ближайший рынок к заданным координатам
    @raises: ValueError если нет рынков с координатами
    @returns: dict — словарь с информацией о ближайшем рынке
    """
    valid = [m for m in markets if isinstance(m.get("x"), (int,float)) and isinstance(m.get("y"),(int,float))]
    if not valid:
        raise ValueError("Нет рынков с координатами")
    return min(valid, key=lambda m: haversine(y, x, m["y"], m["x"]))

def filter_by_radius(markets, lat, lon, radius_km):
    """
    @requires: markets — список словарей с полями 'x','y', lat, lon — координаты центра, radius_km — радиус в км
    @modifies: Ничего
    @effects: Возвращает рынки в пределах указанного радиуса
    @raises: Ничего
    @returns: list[dict] — список рынков в радиусе radius_km
    """
    filtered = []
    for m in markets:
        mx, my = m.get("x"), m.get("y")
        if mx is None or my is None:
            continue
        if haversine(lat, lon, my, mx) <= radius_km:
            filtered.append(m)
    return filtered
