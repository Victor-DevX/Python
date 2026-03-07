# -*- coding: utf-8 -*-
"""
Модуль интерфейса пользователя в стиле REPL
"""

import os
import json
from auth import login_user, register_user
from model import (
    load_markets,
    search_markets,
    get_reviews_by_fmid,
    add_review,
    delete_market,
    get_average_rating,
    find_nearest_market,
#    filter_by_radius,
    haversine
)
from logger import logger

current_user = {"username": None, "role": None}

def main_menu():
    """
    @requires: Ничего
    @modifies: current_user
    @effects: Запускает главное REPL меню, обрабатывает команды login, register, list, review, delete, logout, exit
    @raises: Ничего
    @returns: None
    """
    while True:
        print("\n=== Главное меню ===")
        if not current_user["username"]:
            print("login  - Войти")
            print("reg    - Зарегистрироваться")
        else:
            print(f"Вы вошли как: {current_user['username']} (роль: {current_user['role']})")
            print("logout - Выйти из аккаунта")

        print("list   - показать список рынков")
        if current_user["role"] in ("user", "admin"):
            print("review - добавить отзыв")
        if current_user["role"] == "admin":
            print("delete - удалить рынок")
        print("exit   - выход")

        cmd = input("\nВведите команду: ").strip().lower()

        if cmd == "login" and not current_user["username"]:
            login_menu()
        elif cmd == "reg" and not current_user["username"]:
            register_menu()
        elif cmd == "logout" and current_user["username"]:
            print(f"Пользователь {current_user['username']} вышел из аккаунта.")
            current_user["username"] = None
            current_user["role"] = None
        elif cmd == "list":
            markets = load_markets()
            list_markets_ui(markets)
        elif cmd == "review" and current_user["role"] in ("user", "admin"):
            review_menu()
        elif cmd == "delete" and current_user["role"] == "admin":
            delete_menu()
        elif cmd == "exit":
            print("Выход из программы...")
            break
        else:
            print("Неверная команда или нет прав для выполнения.")

def login_menu():
    """
    @requires: Ничего
    @modifies: current_user
    @effects: Выполняет вход пользователя, обновляет current_user при успешном входе
    @raises: Ничего, ошибки входа логируются
    @returns: None
    """
    username = input("Имя пользователя: ").strip()
    password = input("Пароль: ").strip()

    success, result = login_user(username, password)
    if success:
        current_user["username"] = result["username"]
        current_user["role"] = result.get("role", "user")
        print(f"Успешный вход. Роль: {current_user['role']}")
        logger.info(f"Пользователь '{username}' вошел в систему")
    else:
        print(f"Произошла ошибка: {result}")
        logger.warning(f"Неудачная попытка входа пользователя '{username}'")


def register_menu():
    """
    @requires: Ничего
    @modifies: current_user
    @effects: Выполняет вход пользователя, обновляет current_user при успешном входе
    @raises: Ничего, ошибки входа логируются
    @returns: None
    """
    print("\n=== Регистрация нового пользователя ===")
    username = input("Введите имя пользователя: ").strip()
    password = input("Введите пароль: ").strip()
    first_name = input("Имя: ").strip()
    last_name = input("Фамилия: ").strip()
    middle_name = input("Отчество (необязательно): ").strip()

    try:
        success, msg = register_user(username, password, first_name, last_name, middle_name)
    except Exception as e:
        print("Произошла ошибка при регистрации:", e)
        return

    print(msg)
    if success:
        logger.info(f"Новый пользователь '{username}' зарегистрирован")

MARKETS_PER_PAGE = 15

def list_markets_ui(markets):
    """
    @requires: markets — список словарей с информацией о рынках
    @modifies: Ничего
    @effects: Обеспечивает постраничный просмотр рынков с поиском, показом деталей, навигацией и функцией ближайшего рынка
    @raises: Исключения при неверном вводе команд, ошибки логируются
    @returns: None
    """
    page = 1
    total_pages = (len(markets) + MARKETS_PER_PAGE - 1) // MARKETS_PER_PAGE
    current_coords = None  # для dist/info
    filtered_markets = markets

    while True:
        start = (page - 1) * MARKETS_PER_PAGE
        page_markets = filtered_markets[start:start + MARKETS_PER_PAGE]

        print(f"\n=== Страница {page} из {total_pages} ===")
        for idx, m in enumerate(page_markets, start=1):
            name = m.get("MarketName", "Без имени")
            city = m.get("city", "")
            print(f"{idx}. {name} - {city}")

        print("\nКоманды:")
        print("info <номер> - показать детали рынка")
        print("search       - поиск рынков по штату, городу или ZIP")
        print("dist         - найти ближайший рынок по координатам")
        print("n            - следующая страница")
        print("p            - предыдущая страница")
        print("page <номер> - перейти на указанную страницу")
        print("q            - выход в главное меню")

        cmd = input("Введите команду: ").strip().lower()

        if cmd == 'q':
            break
        elif cmd == 'n':
            if page < total_pages:
                page += 1
            else:
                print("Это последняя страница.")
        elif cmd == 'p':
            if page > 1:
                page -= 1
            else:
                print("Это первая страница.")
        elif cmd.startswith("page"):
            parts = cmd.split()
            if len(parts) == 2 and parts[1].isdigit():
                page_num = int(parts[1])
                if 1 <= page_num <= total_pages:
                    page = page_num
                else:
                    print(f"Неверный номер страницы. Допустимо: 1-{total_pages}")
            else:
                print("Неверная команда. Используйте: page <номер>")
        elif cmd.startswith("info"):
            parts = cmd.split()
            if len(parts) == 2 and parts[1].isdigit():
                idx = int(parts[1])
                if 1 <= idx <= len(page_markets):
                    market = page_markets[idx - 1]
                    show_market_details(market, current_coords)
                    input("\nНажмите Enter чтобы вернуться к списку...")
                else:
                    print("Неверный номер рынка.")
            else:
                print("Неверная команда. Используйте: info <номер>")
        elif cmd == "dist":
            try:
                coords = input("Укажите свои координаты в виде x,y: ").strip()
                x_str, y_str = coords.split(",")
                user_x, user_y = float(x_str), float(y_str)
                nearest = find_nearest_market(filtered_markets, user_x, user_y)
                dist_km = haversine(user_y, user_x, nearest["y"], nearest["x"])
                current_coords = (user_x, user_y)
                print(f"\nБлижайший рынок найден:")
                # Отображаем только этот рынок в списке
                filtered_markets = [nearest]
                total_pages = 1
                page = 1
            except Exception as e:
                print("Ошибка ввода координат или расчета расстояния:", e)
        elif cmd == "search":
            # поиск по штату, городу или ZIP
            query = input(
                'Введите сведения о рынке в формате "штат, город" или ZIP код: '
            ).strip()

            results = []

            if query.isdigit():  # поиск по ZIP
                for m in markets:
                    zip_code = str(m.get("zip", ""))
                    if query in zip_code:
                        results.append(m)
            else:  # поиск по "штат, город"
                parts = [p.strip() for p in query.split(",")]
                state_query = city_query = None
                if len(parts) == 1:
                    if len(parts[0]) == 2:
                        state_query = parts[0].lower()
                    else:
                        city_query = parts[0].lower()
                elif len(parts) >= 2:
                    state_query = parts[0].lower()
                    city_query = parts[1].lower()

                for m in markets:
                    state = str(m.get("State","")).lower()
                    city = str(m.get("city","")).lower()
                    match = True
                    if state_query:
                        match = match and (state_query in state)
                    if city_query:
                        match = match and (city_query in city)
                    if match:
                        results.append(m)

            if not results:
                print("Рынки не найдены.")
            else:
                print(f"\nНайдено {len(results)} рынков:")
                filtered_markets = results
                total_pages = (len(filtered_markets) + MARKETS_PER_PAGE - 1) // MARKETS_PER_PAGE
                page = 1
        else:
            print("Неверная команда.")

def show_nearest_market(markets, user_x, user_y):
    """
    @requires: markets — список рынков, user_x, user_y — координаты пользователя
    @modifies: Ничего
    @effects: Находит ближайший рынок к координатам пользователя и выводит его
    @raises: ValueError если рынок с координатами отсутствует
    @returns: None
    """
    try:
        nearest = find_nearest_market(markets, user_x, user_y)
    except ValueError:
        print("Нет рынков с координатами для поиска.")
        return

    if nearest is None:
        print("Ближайший рынок не найден.")
        return

    name = nearest.get("name", "Без имени")
    mx, my = nearest.get("x"), nearest.get("y")
    distance_km = haversine(user_y, user_x, my, mx)  # y=lat, x=lon
    print(f"Ближайший рынок: {name} | Расстояние: {distance_km:.2f} км | Координаты: x={mx}, y={my}")

def show_market_details(market, user_coords=None):
    """
    @requires: market — словарь с информацией о рынке, user_coords — кортеж (x, y) или None
    @modifies: Ничего
    @effects: Выводит полные детали рынка, товары, отзывы и средний рейтинг
    @raises: Ничего
    @returns: None
    """
    print(f"\n=== {market.get('MarketName','Без имени')} ===")
    print(f"Адрес: {market.get('street','')}")
    print(f"Город: {market.get('city','')}, Штат: {market.get('State','')}, ZIP: {market.get('zip','')}")
    
    x = market.get("x")
    y = market.get("y")
    if x is not None and y is not None:
        print(f"Координаты: ({x},{y})")
        if user_coords:
            try:
                # y=lat, x=lon
                dist = haversine(user_coords[1], user_coords[0], y, x)
                print(f"Расстояние от вас: {dist:.2f} км")
            except Exception:
                print("Расстояние не вычислено")
    
    # Вывод доступных товаров
    product_fields = [
        "Organic", "Bakedgoods", "Cheese", "Crafts", "Flowers", "Eggs", "Seafood",
        "Herbs", "Vegetables", "Honey", "Jams", "Maple", "Meat", "Nursery", "Nuts",
        "Plants", "Poultry", "Prepared", "Soap", "Trees", "Wine", "Coffee", "Beans",
        "Fruits", "Grains", "Juices", "Mushrooms", "PetFood", "Tofu", "WildHarvested"
    ]
    products_available = [p for p in product_fields if market.get(p) and market[p].strip()]
    if products_available:
        print("Товары/услуги на рынке:", ", ".join(products_available))
    else:
        print("Информация о товарах отсутствует.")
    
    # Отзывы
    reviews = get_reviews_by_fmid(market.get("FMID")) or []
    if not reviews:
        print("Нет отзывов.")
    else:
        print("\nОтзывы:")
        for r in reviews:
            print(f"{r.get('username','')} ({r.get('rating','')}): {r.get('text','')}")
    
    # Средний рейтинг
    avg = get_average_rating(market.get("FMID"))
    if avg is not None:
        print(f"\nСредний рейтинг: {avg}")
    else:
        print("\nСредний рейтинг: нет данных")
        
def search_menu():
    """
    @requires: Ничего
    @modifies: Ничего
    @effects: Выполняет поиск рынков по ZIP или "штат, город" и показывает результаты через list_markets_ui
    @raises: Ничего
    @returns: None
    """
    query = input(
        'Введите сведения о рынке, который необходимо найти в формате "штат, город" или ZIP код: '
    ).strip()

    markets = load_markets()  # загружаем все рынки

    results = []

    if query.isdigit():  # поиск по ZIP
        for m in markets:
            zip_code = str(m.get("zip", ""))
            if query in zip_code:  # ищем совпадение последовательности
                results.append(m)
    else:  # поиск по "штат, город"
        parts = [p.strip() for p in query.split(",")]
        state_query = city_query = None
        if len(parts) == 1:
            # ввод только штата или города
            if len(parts[0]) == 2:  # предположим, что штат двухбуквенный код
                state_query = parts[0].lower()
            else:
                city_query = parts[0].lower()
        elif len(parts) >= 2:
            state_query = parts[0].lower()
            city_query = parts[1].lower()

        for m in markets:
            state = str(m.get("State","")).lower()
            city = str(m.get("city","")).lower()
            match = True
            if state_query:
                match = match and (state_query in state)
            if city_query:
                match = match and (city_query in city)
            if match:
                results.append(m)

    if not results:
        print("Рынки не найдены.")
        return

    # вывод результатов через list_markets_ui
    print(f"\nНайдено {len(results)} рынков:")
    list_markets_ui(results)

def review_menu():
    """
    @requires: current_user содержит 'username'
    @modifies: Отзывы рынка через add_review
    @effects: Позволяет пользователю добавить отзыв к рынку по ZIP, обновляет средний рейтинг
    @raises: Ничего, ошибки ввода логируются
    @returns: None
    """
    zip_code = input("Укажите ZIP код рынка: ").strip()
    markets = load_markets()
    
    # Ищем рынок по ZIP
    market = None
    for m in markets:
        if str(m.get("zip","")) == zip_code:
            market = m
            break
    
    if not market:
        print("Рынок с таким ZIP кодом не найден.")
        return

    print(f"Добавление отзыва для: {market.get('MarketName','')} ({market.get('city','')})")

    # Ввод рейтинга
    while True:
        try:
            rating = int(input("Рейтинг (1-5): ").strip())
            if 1 <= rating <= 5:
                break
            else:
                print("Рейтинг должен быть от 1 до 5")
        except ValueError:
            print("Введите число от 1 до 5")

    # Ввод комментария
    text = input("Комментарий: ").strip()

    # Добавляем отзыв, передавая ZIP и username текущего пользователя
    add_review(market.get("zip"), current_user["username"], rating, text)
    
    avg = get_average_rating(market.get("zip"))
    print("\nОтзыв добавлен.")
    print(f"Средний рейтинг рынка: {avg}")

def delete_menu():
    """
    @requires: current_user['role'] == 'admin'
    @modifies: markets.json через delete_market
    @effects: Позволяет удалить рынок по FMID
    @raises: Ничего, ошибки удаления логируются
    @returns: None
    """
    fmid = input("FMID: ").strip()
    confirm = input(f"Подтвердите удаление рынка {fmid} (y/n): ").strip().lower()
    if confirm == "y":
        if delete_market(fmid):
            print(f"Рынок {fmid} удален.")
        else:
            print("Ошибка удаления. Рынок не найден или произошла ошибка.")