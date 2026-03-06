# -*- coding: utf-8 -*-
"""
Модуль market_ops.py

Реализует операции над рынками:
- загрузка данных из Export.csv
- поиск по городу / штату / ZIP
- фильтрация по радиусу (Haversine)
- сортировка
- удаление рынка (для admin)

Файл Export.csv должен находиться в той же директории.
"""

import csv
import os
import math


# ==========================================================
# Пути к файлам
# ==========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORT_FILE = os.path.join(BASE_DIR, "Export.csv")


# ==========================================================
# Загрузка рынков
# ==========================================================

def load_markets():
    """
    @requires: Export.csv существует
    @modifies: Ничего
    @effects: Загружает все рынки из CSV
    @raises: FileNotFoundError если файл отсутствует
    @returns: list[dict]
    """
    if not os.path.exists(EXPORT_FILE):
        raise FileNotFoundError("Файл Export.csv не найден")

    with open(EXPORT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


# ==========================================================
# Поиск рынков
# ==========================================================

def search_markets(city=None, state=None, zip_code=None):
    """
    @requires: city, state, zip_code — строки или None
    @modifies: Ничего
    @effects: Возвращает рынки, соответствующие указанным параметрам
    @raises: Ничего
    @returns: list[dict]
    """
    markets = load_markets()
    results = []

    for m in markets:
        city_match = True
        state_match = True
        zip_match = True

        if city:
            if m.get("city", "").lower() != city.lower():
                city_match = False

        if state:
            if m.get("State", "").lower() != state.lower():
                state_match = False

        if zip_code:
            if m.get("zip", "") != zip_code:
                zip_match = False

        if city_match and state_match and zip_match:
            results.append(m)

    return results


# ==========================================================
# Haversine
# ==========================================================

import csv

def haversine(lat1, lon1, lat2, lon2):
    """
    Вычисляет расстояние между двумя точками на Земле по координатам (широта, долгота) в километрах.
    """
    from math import radians, sin, cos, sqrt, atan2

    R = 6371.0  # Радиус Земли в километрах
    lat1_r, lon1_r, lat2_r, lon2_r = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = sin(dlat / 2)**2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def find_nearest_market(markets, x, y):
    """
    @requires: markets — список словарей с ключами 'x' и 'y' для координат
               x — широта (float)
               y — долгота (float)
    @modifies: Ничего
    @effects: Находит рынок, ближайший к указанным координатам
    @raises: ValueError если список рынков пуст или нет корректных координат
    @returns: dict — словарь рынка с наименьшей дистанцией
    """
    import math

    if not markets:
        raise ValueError("Список рынков пуст")

    # фильтруем только рынки с координатами
    valid_markets = [m for m in markets if isinstance(m.get("x"), (int, float)) and isinstance(m.get("y"), (int, float))]
    if not valid_markets:
        raise ValueError("Нет рынков с координатами")

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # радиус Земли в км
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    nearest = min(valid_markets, key=lambda m: haversine(x, y, m["y"], m["x"]))
    return nearest


def filter_by_radius(markets, lat, lon, radius):
    """
    @requires: markets — list[dict], lat/lon — координаты пользователя, radius — радиус в милях
    @modifies: Ничего
    @effects: Возвращает только рынки в пределах радиуса
    @raises: ValueError если координаты некорректны
    @returns: list[dict]
    """
    filtered = []

    for m in markets:
        m_lat = m.get("y")
        m_lon = m.get("x")

        if not m_lat or not m_lon:
            continue

        distance = haversine(lat, lon, m_lat, m_lon)

        if distance <= float(radius):
            filtered.append(m)

    return filtered


# ==========================================================
# Сортировка
# ==========================================================

def sort_markets(markets, key="MarketName", reverse=False):
    """
    @requires: markets — list[dict], key — существующий ключ словаря, reverse — bool
    @modifies: Ничего
    @effects: Возвращает список рынков, отсортированных по ключу
    @raises: KeyError если ключ отсутствует
    @returns: list[dict]
    """
    return sorted(markets, key=lambda x: x.get(key, ""), reverse=reverse)


# ==========================================================
# Удаление рынка
# ==========================================================

def delete_market(fmid):
    """
    @requires: fmid — строка (идентификатор рынка)
    @modifies: Export.csv
    @effects: Удаляет рынок с указанным FMID
    @raises: ValueError если рынок не найден, FileNotFoundError если CSV отсутствует
    @returns: None
    """
    markets = load_markets()
    new_markets = [m for m in markets if m.get("FMID") != fmid]

    if len(new_markets) == len(markets):
        raise ValueError("Рынок не найден")

    with open(EXPORT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=markets[0].keys())
        writer.writeheader()
        writer.writerows(new_markets)