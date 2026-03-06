# -*- coding: utf-8 -*-
"""
Модуль операций с рынками и отзывами
"""

import csv
import os
from logger import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MARKETS_FILE = os.path.join(BASE_DIR, "Export.csv")
REVIEWS_FILE = os.path.join(BASE_DIR, "reviews.csv")
PER_PAGE = 15


# ==========================================================
# Работа с рынками
# ==========================================================
def load_markets():
    """
    @requires: Export.csv может существовать
    @modifies: Ничего
    @effects: Загружает все рынки из CSV, включая координаты x и y
    @raises: FileNotFoundError если файл отсутствует
    @returns: list[dict] — список рынков
    """
    markets = []
    if not os.path.exists(MARKETS_FILE):
        logger.error("Файл Export.csv не найден")
        return markets

    try:
        with open(MARKETS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    x = float(row["x"]) if row.get("x") else None
                    y = float(row["y"]) if row.get("y") else None
                except ValueError:
                    x = None
                    y = None

                markets.append({
                    "FMID": row.get("FMID", ""),
                    "name": row.get("MarketName", ""),
                    "city": row.get("city", ""),
                    "state": row.get("State", ""),
                    "zip": row.get("zip", ""),
                    "x": x,
                    "y": y
                })
        logger.info(f"Загружено рынков: {len(markets)}")
    except Exception as e:
        logger.error(f"Ошибка чтения Export.csv: {e}")

    return markets


def paginate_markets(markets, page):
    """
    @requires: markets — list[dict], page — int
    @modifies: Ничего
    @effects: Возвращает список рынков для указанной страницы
    @raises: Ничего
    @returns: list[dict]
    """
    start = page * PER_PAGE
    end = start + PER_PAGE
    return markets[start:end]


def search_markets(markets, field, query):
    """
    @requires: markets — list[dict], field — ключ словаря, query — строка
    @modifies: Ничего
    @effects: Возвращает рынки, удовлетворяющие критерию поиска
    @raises: Ничего
    @returns: list[dict]
    """
    query = query.lower()
    results = []
    for m in markets:
        if field == "zip" and m["zip"] == query:
            results.append(m)
        elif field == "name" and query in m["name"].lower():
            results.append(m)
        elif field == "city" and query in m["city"].lower():
            results.append(m)
        elif field == "state" and query in m["state"].lower():
            results.append(m)
    return results


def show_market_info(market):
    """
    Возвращает подробную информацию по рынку в виде строки.
    
    @requires: market — словарь с ключами 'FMID', 'name', 'city', 'state', 'zip', ...
    @modifies: Ничего
    @effects: Формирует читаемую информацию для пользователя
    @raises: Ничего
    @returns: str — информация о рынке
    """
    if not market:
        return "Информация о рынке отсутствует."

    lines = [
        f"FMID: {market.get('FMID', '')}",
        f"Название: {market.get('name', '')}",
        f"Город: {market.get('city', '')}",
        f"Штат/Регион: {market.get('state', '')}",
        f"ZIP: {market.get('zip', '')}"
    ]
    
    # Если есть дополнительные поля из CSV, можно добавить их все динамически
    for key, value in market.items():
        if key not in ('FMID', 'name', 'city', 'state', 'zip'):
            lines.append(f"{key}: {value}")
    
    return "\n".join(lines)


# ==========================================================
# Работа с отзывами
# ==========================================================
def load_reviews():
    """
    @requires: reviews.csv может существовать
    @modifies: Может создать reviews.csv
    @effects: Загружает все отзывы из файла
    @raises: ValueError если rating некорректен
    @returns: list[dict]
    """
    reviews = []
    if not os.path.exists(REVIEWS_FILE):
        return reviews
    try:
        with open(REVIEWS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                reviews.append(row)
    except Exception as e:
        logger.error(f"Ошибка чтения reviews.csv: {e}")
    return reviews


def get_market_reviews(fmid):
    """
    @requires: fmid — строка
    @modifies: Ничего
    @effects: Возвращает список отзывов по FMID рынка
    @raises: Ничего
    @returns: list[dict]
    """
    return [r for r in load_reviews() if r["market_id"] == fmid]


def add_review(fmid, username, text):
    """
    @requires: fmid, username, text — строки
    @modifies: reviews.csv
    @effects: Добавляет новый отзыв в CSV
    @raises: IOError при ошибке записи
    @returns: bool — True если успешно, иначе False
    """
    reviews = load_reviews()
    reviews.append({"market_id": fmid, "username": username, "review": text})
    try:
        file_exists = os.path.exists(REVIEWS_FILE)
        with open(REVIEWS_FILE, "w", newline='', encoding='utf-8') as f:
            fieldnames = ["market_id", "username", "review"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in reviews:
                writer.writerow(r)
        logger.info(f"Добавлен отзыв для рынка {fmid} пользователем {username}")
        return True
    except Exception as e:
        logger.error(f"Ошибка добавления отзыва: {e}")
        return False

    
def show_reviews(market):
    """
    @requires: market — словарь с ключом 'FMID'
    @modifies: Ничего
    @effects: Выводит все отзывы для указанного рынка
    @raises: Ничего
    @returns: None
    """
    reviews = get_market_reviews(market["FMID"])
    if not reviews:
        print(f"\nОтзывы для {market['name']} отсутствуют.")
        return

    print(f"\nОтзывы для {market['name']}:")
    for idx, r in enumerate(reviews, start=1):
        print(f"\n{idx}. Автор: {r['username']}")
        print(f"   Отзыв: {r['review']}")


def delete_market(fmid: str) -> bool:
    """
    @requires: fmid — строка
    @modifies: Export.csv и reviews.csv
    @effects: Удаляет рынок и все его отзывы
    @raises: IOError если невозможно удалить
    @returns: bool — True если успешно, иначе False
    """
    success = False

    # Удаляем рынок из Export.csv
    try:
        if not os.path.exists(MARKETS_FILE):
            return False

        markets = []
        with open(MARKETS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("FMID") != fmid:
                    markets.append(row)

        # Сохраняем обратно
        if markets:
            fieldnames = markets[0].keys()
        else:
            fieldnames = ["FMID", "MarketName", "city", "State", "zip"]  # базовые поля
        with open(MARKETS_FILE, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in markets:
                writer.writerow(row)
        success = True
    except Exception as e:
        logger.error(f"Ошибка удаления рынка из Export.csv: {e}")
        success = False

    # Удаляем отзывы из reviews.csv
    try:
        if os.path.exists(REVIEWS_FILE):
            reviews = []
            with open(REVIEWS_FILE, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for r in reader:
                    if r.get("market_id") != fmid:
                        reviews.append(r)
            fieldnames = ["market_id", "username", "review"]
            with open(REVIEWS_FILE, "w", newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in reviews:
                    writer.writerow(r)
    except Exception as e:
        logger.error(f"Ошибка удаления отзывов для рынка {fmid}: {e}")
        success = False

    if success:
        logger.info(f"Рынок {fmid} и все его отзывы удалены")
    return success
