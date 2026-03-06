import csv
import os

MARKETS_FILE = "markets.csv"
REVIEWS_FILE = "reviews.csv"


def ensure_file(filename, fieldnames):
    """
    @requires: filename — путь к CSV, fieldnames — список заголовков
    @modifies: CSV файл
    @effects: Создает CSV файл с заголовками, если файла нет
    @raises: IOError если невозможно создать файл
    @returns: None
    """
    if not os.path.exists(filename):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


def load_markets():
    """
    @requires: markets.csv может существовать или нет
    @modifies: Ничего
    @effects: Загружает рынки из CSV в список словарей
    @raises: Ничего
    @returns: list[dict] — список рынков
    """
    ensure_file(MARKETS_FILE, ["fmid", "name", "city", "state", "zip"])
    markets = []
    with open(MARKETS_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            markets.append(row)
    return markets


def save_markets(markets):
    """
    @requires: markets — список словарей с ключами fmid, name, city, state, zip
    @modifies: markets.csv
    @effects: Сохраняет список рынков в CSV
    @raises: IOError если запись невозможна
    @returns: None
    """
    ensure_file(MARKETS_FILE, ["fmid", "name", "city", "state", "zip"])
    with open(MARKETS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["fmid", "name", "city", "state", "zip"])
        writer.writeheader()
        for m in markets:
            writer.writerow(m)


def load_reviews():
    """
    @requires: reviews.csv может существовать или нет
    @modifies: Ничего
    @effects: Загружает отзывы из CSV, приводит rating к int
    @raises: ValueError если rating некорректен
    @returns: list[dict]
    """
    ensure_file(REVIEWS_FILE, ["fmid", "username", "rating", "text"])
    reviews = []
    with open(REVIEWS_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["rating"] = int(row["rating"])
            reviews.append(row)
    return reviews


def save_reviews(reviews):
    """
    @requires: reviews — список словарей с ключами fmid, username, rating, text
    @modifies: reviews.csv
    @effects: Сохраняет отзывы в CSV
    @raises: IOError если запись невозможна
    @returns: None
    """
    ensure_file(REVIEWS_FILE, ["fmid", "username", "rating", "text"])
    with open(REVIEWS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["fmid", "username", "rating", "text"])
        writer.writeheader()
        for r in reviews:
            writer.writerow(r)