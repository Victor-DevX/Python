# -*- coding: utf-8 -*-
"""
Модуль для отображения рынков и отзывов в консоли.
"""

def display_markets_console(markets):
    """
    @requires: markets — list[dict]
    @modifies: None
    @effects: Выводит информацию о рынках в консоль
    @raises: Ничего
    @returns: None
    """
    if not markets:
        print("Нет рынков для отображения.")
        return
    print("\n=== Список рынков ===")
    for m in markets:
        print(f"{m.get('FMID', '')}: {m.get('MarketName', '')} - {m.get('city', '')}, {m.get('state', '')} {m.get('zip', '')}")


def display_reviews_console(reviews):
    """
    @requires: reviews — list[dict]
    @modifies: None
    @effects: Выводит список отзывов в консоль
    @raises: Ничего
    @returns: None
    """
    if not reviews:
        print("Нет отзывов для отображения.")
        return
    print("\n=== Отзывы ===")
    for r in reviews:
        print(f"{r.get('username', '')} ({r.get('rating', '')}): {r.get('text', '')}")