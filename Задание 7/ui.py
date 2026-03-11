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

def input_q(prompt: str):
    """
    @requires: prompt — строка приглашения для ввода пользователя
    @modifies: Ничего
    @effects: Запрашивает ввод пользователя через input(), удаляет пробелы по краям строки.
              Если пользователь вводит 'q' (в любом регистре), возвращает None,
              что используется вызывающей функцией как сигнал выхода в предыдущее меню.
    @raises: Ничего
    @returns: str — введённая пользователем строка без пробелов по краям,
              либо None если введено 'q'
    """
    value = input(prompt).strip()
    if value.lower() == "q":
        return None
    return value


def main_menu():
    """
    @requires: Ничего
    @modifies: current_user
    @effects: Запускает главное REPL меню, обрабатывает команды login, register, list, review, delete, logout, exit
    @raises: Ничего
    @returns: Ничего
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
    @returns: Ничего
    """
    username = input_q("Имя пользователя (q — выход): ")
    if username is None:
        return

    password = input_q("Пароль (q — выход): ")
    if password is None:
        return

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
    @requires: Функция register_user(username, password, first_name, last_name, middle_name)
               должна быть доступна из модуля auth. Логин и пароль — строки, логин ≥2 символов,
               пароль ≥4 символов, без пробелов.
    @modifies: Файл пользователей через функцию register_user
    @effects: Запрашивает у пользователя логин, пароль и персональные данные.
              Проверяет корректность логина и пароля. Позволяет выйти в главное меню
              при вводе 'q'. Если ввод корректен, вызывает auth.register_user для создания
              нового пользователя и выводит сообщение о результате регистрации.
    @raises: Ничего, ошибки регистрации обрабатываются и выводятся
    @returns: None
    """

    while True:
        username = input("Введите логин (min 2 символа, без пробелов, q — выход): ").strip()
        if username.lower() == "q":
            return

        if len(username) < 2:
            print("Ошибка: логин должен содержать минимум 2 символа.")
            continue

        if " " in username:
            print("Ошибка: логин не должен содержать пробелы.")
            continue
        break

    while True:
        password = input("Введите пароль (min 4 символа, q — выход): ").strip()
        if password.lower() == "q":
            return

        if len(password) < 4:
            print("Ошибка: пароль должен содержать минимум 4 символа.")
            continue
        break

    first_name = input("Имя: ").strip()
    last_name = input("Фамилия: ").strip()
    middle_name = input("Отчество: ").strip()

    success, message = register_user(
        username,
        password,
        first_name,
        last_name,
        middle_name
    )

    print(message)

MARKETS_PER_PAGE = 15

def list_markets_ui(markets):
    """
    @requires: markets — список словарей с информацией о рынках
    @modifies: Ничего
    @effects: Обеспечивает постраничный просмотр рынков с поиском, показом деталей, навигацией и функцией ближайшего рынка
    @raises: Исключения при неверном вводе команд, ошибки логируются
    @returns: Ничего
    """
    page = 1
    total_pages = (len(markets) + MARKETS_PER_PAGE - 1) // MARKETS_PER_PAGE
    current_coords = None  # для dist/info
    filtered_markets = markets

    while True:
        start = (page - 1) * MARKETS_PER_PAGE
        page_markets = filtered_markets[start:start + MARKETS_PER_PAGE]

        print(f"\n=== Страница {page} из {total_pages} ===")
        for idx, m in enumerate(page_markets, start + 1):
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
                if 1 <= idx <= len(filtered_markets):
                    market = filtered_markets[idx - 1]
                    show_market_details(market, current_coords)
                    input("\nНажмите Enter чтобы вернуться к списку...")
                else:
                    print("Неверный номер рынка.")
            else:
                print("Неверная команда. Используйте: info <номер>")
        elif cmd == "dist":
            try:
                coords = input("Укажите свои координаты в виде широта,долгота, например 52.3676,4.9041 : ").strip()
                lat_str, lon_str = coords.split(",")

                user_lat = float(lat_str)
                user_lon = float(lon_str)

                nearest = find_nearest_market(filtered_markets, user_lon, user_lat)
                dist_km = haversine(user_lat, user_lon, nearest["y"], nearest["x"])

                current_coords = (user_lon, user_lat)
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
    @returns: Ничего
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
    @returns: Ничего
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
    @returns: Ничего
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
    @modifies: REVIEWS_FILE
    @effects: Позволяет пользователю добавить отзыв к выбранному рынку
    @raises: Ничего, ошибки ввода обрабатываются
    @returns: Ничего
    """

    zip_code = input_q("Укажите ZIP код рынка (q — выход): ")
    if zip_code is None:
        return

    markets = load_markets()
    zip_markets = [m for m in markets if str(m.get("zip","")) == zip_code]

    if not zip_markets:
        print("Рынки с таким ZIP кодом не найдены.")
        return

    print("\nНайденные рынки:")

    for i, m in enumerate(zip_markets, 1):
        print(f"{i}. {m.get('MarketName')} - {m.get('city')}")

    print("\nВведите номер рынка для добавления отзыва.")
    print("Введите q чтобы вернуться в главное меню.")

    choice = input_q("Ваш выбор (q — выход): ")
    if choice is None:
        return
    choice = choice.lower()

    if choice == "q":
        return

    if not choice.isdigit():
        print("Неверный ввод.")
        return

    idx = int(choice)

    if idx < 1 or idx > len(zip_markets):
        print("Неверный номер рынка.")
        return

    market = zip_markets[idx - 1]

    print(f"\nДобавление отзыва для: {market.get('MarketName')} ({market.get('city')})")

    # ввод рейтинга
    while True:
        try:
            rating = int(input("Рейтинг (1-5): ").strip())
            if 1 <= rating <= 5:
                break
            else:
                print("Рейтинг должен быть от 1 до 5.")
        except ValueError:
            print("Введите число от 1 до 5.")

    text = input("Комментарий: ").strip()

    fmid = market.get("FMID")

    add_review(fmid, current_user["username"], rating, text)

    avg = get_average_rating(fmid)

    print("\nОтзыв добавлен.")
    print(f"Средний рейтинг рынка: {avg}")

def delete_menu():
    """
    @requires: current_user['role'] == 'admin'
    @modifies: markets.json через delete_market
    @effects: Позволяет удалить рынок по FMID
    @raises: Ничего, ошибки удаления логируются
    @returns: Ничего
    """
    while True:
        fmid = input("FMID (q — выход): ").strip()

        if fmid.lower() == "q":
            return

        confirm = input(f"Подтвердите удаление рынка {fmid} (y/n): ").strip().lower()

        if confirm == "y":
            if delete_market(fmid):
                print(f"Рынок {fmid} удален.")
            else:
                print("Ошибка удаления. Рынок не найден или произошла ошибка.")
            return

        elif confirm == "n":
            print("Удаление отменено. Введите другой FMID или q для выхода.")
            continue

        else:
            print("Введите y или n.")
