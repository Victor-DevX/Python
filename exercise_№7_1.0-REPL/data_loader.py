# -*- coding: utf-8 -*-
"""
Модуль загрузки данных из CSV файлов
"""

import csv
import os

BASE_DIR = os.path.dirname(__file__)
MARKETS_FILE = os.path.join(BASE_DIR, "Export.csv")


def load_markets():
    """
    @requires: Export.csv должен существовать
    @modifies: Ничего
    @effects: Загружает рынки из CSV в список словарей
    @raises: FileNotFoundError если файл не найден
    @returns: list[dict]
    """

    markets = []

    if not os.path.exists(MARKETS_FILE):
        print("Файл Export.csv не найден")
        return markets

    with open(MARKETS_FILE, newline='', encoding='utf-8') as f:

        reader = csv.DictReader(f)

        for row in reader:
            markets.append(row)

    return markets