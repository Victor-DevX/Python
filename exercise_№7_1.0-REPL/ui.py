# -*- coding: utf-8 -*-
"""
Модуль интерфейса пользователя
"""

from auth import login_user, register_user
from market_ops import (
    load_markets,
    search_markets,
    paginate_markets,
    show_market_info,
    get_market_reviews,
    add_review,
    delete_market
)
from logger import logger
from markets_service import find_nearest_market

PER_PAGE = 15
current_user = {"username": None, "role": None}  # Текущий пользователь


def main_menu():
    """
    @requires: Ничего
    @modifies: current_user
    @effects: Показывает главное меню приложения и обрабатывает действия пользователя
    @raises: Ничего
    @returns: None
    """
    while True:
        print("\n=== Главное меню ===")
        print("1. Войти")
        print("2. Зарегистрироваться")
        print("3. Просмотр рынков")
        print("4. Завершить работу")
        if current_user["username"]:  # если кто-то уже вошел
            print("5. Выйти из аккаунта")
        choice = input("Выберите действие: ").strip()

        if choice == "1":
            login_menu()
        elif choice == "2":
            register_menu()
        elif choice == "3":
            markets_menu()
        elif choice == "4":
            print("Завершение работы...")
            break
        elif choice == "5" and current_user["username"]:
            # Выход из аккаунта
            print(f"Пользователь '{current_user['username']}' вышел из аккаунта.")
            current_user["username"] = None
            current_user["role"] = None
        else:
            print("Неверный выбор, попробуйте снова.")


def login_menu():
    """
    @requires: username и password вводятся пользователем
    @modifies: current_user
    @effects: Выполняет вход пользователя, устанавливает роль
    @raises: Ничего
    @returns: None
    """
    username = input("Имя пользователя: ").strip()
    password = input("Пароль: ").strip()
    success, result = login_user(username, password)
    if success:
        current_user["username"] = username
        current_user["role"] = result
        print(f"Успешный вход. Роль: {result}")
        logger.info(f"Пользователь '{username}' вошел в систему")
    else:
        print(f"Ошибка входа: {result}")
        logger.warning(f"Неудачная попытка входа пользователя '{username}'")


def register_menu():
    """
    @requires: username и password вводятся пользователем
    @modifies: users.json
    @effects: Регистрирует нового пользователя
    @raises: Ничего
    @returns: None
    """
    username = input("Введите имя пользователя: ").strip()
    password = input("Введите пароль: ").strip()
    success, msg = register_user(username, password)
    print(msg)
    if success:
        logger.info(f"Новый пользователь '{username}' зарегистрирован")


def markets_menu():
    """
    @requires: CSV-файл с рынками должен быть корректно загружен функцией load_markets()
    @modifies: Ничего
    @effects: 
        - Показывает постраничный список рынков с навигацией (f - вперед, b - назад, list <номер> - перейти к странице)
        - Позволяет искать рынки по zip, city, state или name (s - поиск)
        - Позволяет просматривать подробную информацию по рынку (info <номер>)
        - Для зарегистрированных пользователей:
            * user: возможность оставлять отзывы (r - оставить отзыв)
            * admin: возможность удалять рынки (d <номер>)
        - Позволяет найти ближайший рынок по координатам x,y (dfm)
        - После использования dfm меню списка скрывается, остаётся только возврат назад по команде b
        - Возврат в главное меню по команде m
    @raises: ValueError при некорректном формате координат в dfm или пустом списке рынков
    @returns: None
    """
    markets = load_markets()
    if not markets:
        print("Список рынков пуст.")
        return

    page = 0
    total_pages = (len(markets) - 1) // PER_PAGE + 1

    while True:
        # Постраничный вывод
        page_markets = paginate_markets(markets, page)
        print(f"\nСтраница {page+1}/{total_pages}")
        for i, market in enumerate(page_markets, start=1):
            print(f"{page*PER_PAGE+i}. {market['name']} ({market['city']}, {market['state']})")

        # Команды
        commands = "f - вперед, b - назад, s - поиск, info <номер> - подробности, m - главное меню, dfm - ближайший рынок"
        if current_user["role"] == "user":
            commands += ", r - оставить отзыв"
        if current_user["role"] == "admin":
            commands += ", d <номер> - удалить рынок, list <номер> - перейти к странице"
        print(f"\nКоманды: {commands}")

        command = input("Введите команду: ").strip().lower()

        # Листание страниц
        if command == "f":
            if page + 1 < total_pages:
                page += 1
            else:
                print("Вы достигли последней страницы.")
        elif command == "b":
            if page > 0:
                page -= 1
            else:
                print("Вы на первой странице.")
        elif command.startswith("list") and current_user["role"] == "admin":
            parts = command.split()
            if len(parts) == 2 and parts[1].isdigit():
                target = int(parts[1])
                if 1 <= target <= total_pages:
                    page = target - 1
                else:
                    print(f"Неверная страница. Укажите число от 1 до {total_pages}.")
            else:
                print("Введите команду в формате: list <номер страницы>")
        elif command.startswith("d") and current_user["role"] == "admin":
            parts = command.split()
            if len(parts) == 2 and parts[1].isdigit():
                idx = int(parts[1]) - 1
                if page*PER_PAGE <= idx < page*PER_PAGE + len(page_markets):
                    market = markets[idx]
                    confirm = input(f"Подтвердите удаление рынка {market['FMID']} - {market['name']} (y/n): ").strip().lower()
                    if confirm == "y":
                        if delete_market(market["FMID"]):
                            print(f"Рынок {market['FMID']} - {market['name']} удален.")
                            markets = load_markets()
                            total_pages = (len(markets) - 1) // PER_PAGE + 1
                            page = 0
                        else:
                            print("Ошибка при удалении.")
                    else:
                        print("Удаление отменено.")
                else:
                    print("Неверный номер рынка на текущей странице.")
            else:
                print("Введите команду в формате: d <номер>")
        elif command.startswith("info"):
            parts = command.split()
            if len(parts) == 2 and parts[1].isdigit():
                idx = int(parts[1]) - 1
                if 0 <= idx < len(markets):
                    market = markets[idx]
                    print("\n=== Подробная информация ===")
                    print(show_market_info(market))

                    reviews = get_market_reviews(market["FMID"])
                    if reviews:
                        print("\nОтзывы:")
                        for r in reviews:
                            print(f"- {r['username']}: {r['review']}")
                    else:
                        print("\nОтзывы отсутствуют.")

                    # Подменю выбранного рынка
                    while True:
                        sub_commands = "b - назад, m - главное меню"
                        if current_user["role"] == "user":
                            sub_commands += ", r - оставить отзыв"
                        if current_user["role"] == "admin":
                            sub_commands += ", d - удалить рынок"
                        print(f"\nКоманды для рынка: {sub_commands}")

                        sub_cmd = input("Введите команду: ").strip().lower()
                        if sub_cmd == "b":
                            break
                        elif sub_cmd == "m":
                            return
                        elif sub_cmd == "r" and current_user["role"] == "user":
                            leave_review_menu([market])
                        elif sub_cmd == "d" and current_user["role"] == "admin":
                            confirm = input(f"Подтвердите удаление рынка {market['FMID']} - {market['name']} (y/n): ").strip().lower()
                            if confirm == "y":
                                if delete_market(market["FMID"]):
                                    print(f"Рынок {market['FMID']} - {market['name']} удален.")
                                    markets = load_markets()
                                    total_pages = (len(markets) - 1) // PER_PAGE + 1
                                    page = 0
                                    break
                                else:
                                    print("Ошибка при удалении.")
                            else:
                                print("Удаление отменено.")
                        else:
                            print("Неизвестная команда.")
                else:
                    print("Некорректный номер рынка.")
            else:
                print("Введите команду в формате: info <номер>")
        elif command == "s":
            search_menu(markets)
        elif command == "r" and current_user["role"] == "user":
            leave_review_menu(markets)
        elif command == "m":
            break
        elif command == "dfm":
            coords_input = input("Введите координаты x,y (широта,долгота) через запятую: ").strip()
            try:
                x_str, y_str = coords_input.replace(" ", "").split(",")
                x = float(x_str)
                y = float(y_str)
            except ValueError:
                print("Некорректный формат. Введите через запятую, например: 44.411036,-72.140337")
                continue

            try:
                nearest = find_nearest_market(markets, x, y)
                print("\n=== Ближайший рынок ===")
                print(f"{nearest['name']} ({nearest['city']}, {nearest['state']})")
                print(f"FMID: {nearest['FMID']}")
                print(f"Название: {nearest['name']}")
                print(f"Город: {nearest['city']}")
                print(f"Штат/Регион: {nearest['state']}")
                print(f"ZIP: {nearest['zip']}")
                print(f"x: {nearest['x']}")
                print(f"y: {nearest['y']}")

                # Только возврат назад
                while True:
                    back_cmd = input("\nНажмите 'b' для возврата к списку рынков: ").strip().lower()
                    if back_cmd == "b":
                        break
            except ValueError as e:
                print(str(e))
        else:
            print("Неизвестная команда.")
            


def search_menu(markets):
    """
    @requires: markets — list[dict]
    @modifies: Ничего
    @effects: Меню поиска рынков по zip/city/state/name, поддерживает постраничный просмотр результатов
    @raises: Ничего
    @returns: None
    """
    while True:
        field = input("Поиск по [zip/city/state/name] (b - назад к списку рынков): ").strip().lower()
        if field == "b":
            return  # возврат к списку рынков
        if field not in ["zip", "city", "state", "name"]:
            print("Неверное поле поиска. Укажите zip, city, state или name.")
            continue

        query = input("Введите значение: ").strip().lower()
        if query == "b":
            return  # возврат к списку рынков

        results = search_markets(markets, field=field, query=query)
        if not results:
            print("Совпадений не найдено.")
            continue

        # Постраничный просмотр результатов поиска
        per_page = 15
        page = 0
        total_pages = (len(results) - 1) // per_page + 1

        while True:
            start = page * per_page
            end = start + per_page
            page_results = results[start:end]

            print(f"\nРезультаты поиска, страница {page+1}/{total_pages}:")
            for i, m in enumerate(page_results, start=start+1):
                print(f"{i}. {m['name']} ({m['city']}, {m['state']})")

            print("\nКоманды: f - вперед, b - назад к списку рынков, list - показать текущую страницу, rr - прочитать отзывы, m - главное меню")
            command = input("Введите команду: ").strip().lower()

            if command == "f":
                if page + 1 < total_pages:
                    page += 1
                else:
                    print("Вы достигли последней страницы результатов.")
            elif command == "b":
                return  # назад к списку рынков
            elif command == "list":
                # просто показываем текущую страницу ещё раз
                continue
            elif command == "rr":
                idx = input("Введите номер рынка, чтобы посмотреть отзывы: ").strip()
                if not idx.isdigit() or not (1 <= int(idx) <= len(results)):
                    print("Неверный номер рынка.")
                    continue
                market = results[int(idx) - 1]
                reviews = get_market_reviews(market["FMID"])
                if reviews:
                    print(f"\nОтзывы для {market['name']}:")
                    for r in reviews:
                        print(f"- {r['username']}: {r['review']}")
                else:
                    print(f"\nОтзывы для {market['name']} отсутствуют.")
            elif command == "m":
                return  # главное меню
            else:
                print("Неизвестная команда. Введите f, b, list, rr или m.")


def leave_review_menu(markets):
    """
    @requires: markets — list[dict]
    @modifies: reviews.csv
    @effects: Позволяет пользователю оставить отзыв для выбранного рынка по ZIP
    @raises: ValueError если отзыв пустой, IOError при записи
    @returns: None
    """
    while True:
        zip_input = input("Введите ZIP рынка (m - главное меню): ").strip()
        if zip_input.lower() == "m":
            return

        # Ищем рынок по ZIP без учета пробелов
        market = next((m for m in markets if m["zip"].strip() == zip_input.strip()), None)
        if not market:
            print("Рынок с таким ZIP не найден.")
            continue

        review_text = input("Введите отзыв (m - главное меню): ").strip()
        if review_text.lower() == "m":
            return
        if not review_text:
            print("Отзыв не может быть пустым.")
            continue

        success = add_review(market["FMID"], current_user["username"], review_text)
        if success:
            print("Отзыв добавлен.")
        else:
            print("Ошибка при добавлении отзыва.")
        return