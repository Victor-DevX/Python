# -*- coding: utf-8 -*-
"""
Безопасная версия приложения с проверкой ролей.
Поддерживает guest/user/admin и базовый REPL.
"""

from auth import register, authenticate, logout, check_permission, create_admin_if_missing
from markets_service import load_markets, display_paginated_markets, search_markets, delete_market
from reviews import add_review, get_reviews_by_fmid
from view import display_reviews_console

current_user = None
def show_menu():
    """
    @requires: Ничего
    @modifies: Ничего
    @effects: Выводит список доступных команд в консоль
    @returns: None
    """
    print("\n=== Доступные команды ===")
    print("list   - показать рынки")
    print("search - поиск рынков")
    print("review - добавить отзыв")
    print("delete - удалить рынок")
    print("exit   - выход")


def main():
    """
    @requires: Файл CSV должны существовать, модуль auth.py корректен
    @modifies: current_user
    @effects: Запускает безопасный REPL с авторизацией и обработкой команд
    @raises: FileNotFoundError если отсутствует CSV файл
    @returns: None
    """
    global current_user
    print("=== Безопасная версия приложения ===")

    while True:
        username = input("Логин (или 'reg' для регистрации): ").strip()
        if username.lower() == "reg":
            first_name = input("Имя: ").strip()
            last_name = input("Фамилия: ").strip()
            middle_name = input("Отчество (необязательно): ").strip()
            new_user = input("Введите логин: ").strip()
            new_pass = input("Пароль: ").strip()
            register(new_user, new_pass)
            print(f"Пользователь {new_user} зарегистрирован.")
            continue

        if username.lower() == "admin":
            create_admin_if_missing()

        password = input("Пароль: ").strip()
        if authenticate(username, password):
            current_user = username
            print(f"Добро пожаловать, {username}!")
            break
        else:
            print("Неверный логин или пароль.")

while True:
        show_menu()
        cmd = input("Введите команду: ").strip().lower()
        if cmd == "exit":
            logout(current_user)
            current_user = None
            break

        elif cmd == "list":
            markets = load_markets()
            display_paginated_markets(markets)

        elif cmd == "search":
            city = input("Город (Enter чтобы пропустить): ").strip() or None
            state = input("Штат (Enter чтобы пропустить): ").strip() or None
            zip_code = input("ZIP (Enter чтобы пропустить): ").strip() or None
            results = search_markets(city=city, state=state, zip_code=zip_code)
            display_paginated_markets(results)

            for m in results:
                print(f"\nОтзывы для рынка: {m.get('MarketName')}")

                reviews = get_reviews_by_fmid(m.get("FMID"))
                display_reviews_console(reviews)

        elif cmd == "review":
            if not check_permission(current_user, "edit"):
                print("Нет прав на добавление отзывов")
                continue

            fmid = input("FMID: ").strip()

            while True:
                try:
                    rating = int(input("Рейтинг (1-5): ").strip())
                    if 1 <= rating <= 5:
                        break
                    else:
                        print("Рейтинг должен быть от 1 до 5")
                except ValueError:
                    print("Введите число")

            comment = input("Комментарий: ").strip()

            first_name = input("Имя: ").strip()
            last_name = input("Фамилия: ").strip()
            middle_name = input("Отчество (необязательно): ").strip()

            add_review(
                fmid,
                current_user,
                rating,
                comment,
                first_name,
                last_name,
                middle_name
            )

            reviews = get_reviews_by_fmid(fmid)
            display_reviews_console(reviews)

        elif cmd == "delete":
            if not check_permission(current_user, "delete"):
                print("Нет прав на удаление")
                continue
            fmid = input("FMID: ").strip()
            delete_market(fmid, current_user)
            print("Рынок удален.")

        else:
            print("Неизвестная команда.")


if __name__ == "__main__":
    main()