# -*- coding: utf-8 -*-
"""
Модуль reviews.py

Реализует:
- создание файла reviews.csv
- загрузку отзывов
- добавление нового отзыва
- получение отзывов по FMID
- вычисление среднего рейтинга рынка

Файл reviews.csv хранится в той же директории.
"""

import csv
import os


# ==========================================================
# Пути к файлам
# ==========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REVIEWS_FILE = os.path.join(BASE_DIR, "reviews.csv")


# ==========================================================
# Создание файла при отсутствии
# ==========================================================

def ensure_reviews_file():
    """
    @requires: Ничего
    @modifies: reviews.csv (если отсутствует)
    @effects: Создает файл reviews.csv с заголовками
    @raises: IOError если невозможно создать файл
    @returns: None
    """
    if not os.path.exists(REVIEWS_FILE):
        with open(REVIEWS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=[
                            "FMID",
                            "username",
                            "rating",
                            "text",
                            "first_name",
                            "last_name",
                            "middle_name"
                             ]
                              )
            writer.writeheader()


# ==========================================================
# Загрузка отзывов
# ==========================================================

def load_reviews():
    """
    @requires: reviews.csv существует или может быть создан
    @modifies: Может создать reviews.csv
    @effects: Загружает все отзывы и приводит rating к int
    @raises: ValueError если rating некорректен
    @returns: list[dict]
    """
    ensure_reviews_file()

    reviews = []

    with open(REVIEWS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            row["rating"] = int(row["rating"])
            reviews.append(row)

    return reviews


# ==========================================================
# Добавление отзыва
# ==========================================================

def add_review(fmid, username, rating, text, first_name, last_name, middle_name):
    """
    @requires: fmid, username, text, first_name, last_name, middle_name — строки
               rating — int (1-5)
    @modifies: reviews.csv
    @effects: Добавляет новый отзыв в CSV
    @raises: ValueError если rating вне диапазона 1-5, IOError при ошибке записи
    @returns: None
    """
    ensure_reviews_file()
    rating = int(rating)
    if rating < 1 or rating > 5:
        raise ValueError("Рейтинг должен быть от 1 до 5")
    with open(REVIEWS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["FMID","username","rating","text","first_name","last_name","middle_name"]
        )
        writer.writerow({
            "FMID": fmid,
            "username": username,
            "rating": rating,
            "text": text,
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": middle_name
        })

    writer.writerow({
        "FMID": fmid,
        "username": username,
        "rating": rating,
        "text": text,
        "first_name": first_name,
        "last_name": last_name,
        "middle_name": middle_name
            })


# ==========================================================
# Получение отзывов по рынку
# ==========================================================

def get_reviews_by_fmid(fmid):
    """
    @requires: fmid — строка
    @modifies: Ничего
    @effects: Возвращает все отзывы, относящиеся к FMID рынка
    @raises: Ничего
    @returns: list[dict]
    """
    reviews = load_reviews()
    return [r for r in reviews if r["FMID"] == fmid]


# ==========================================================
# Средний рейтинг
# ==========================================================

def get_average_rating(fmid):
    """
    @requires: fmid — строка
    @modifies: Ничего
    @effects: Вычисляет средний рейтинг рынка, если отзывов нет — возвращает 0.0
    @raises: Ничего
    @returns: float — средний рейтинг
    """
    reviews = get_reviews_by_fmid(fmid)

    if not reviews:
        return 0.0

    total = sum(r["rating"] for r in reviews)
    return round(total / len(reviews), 2)