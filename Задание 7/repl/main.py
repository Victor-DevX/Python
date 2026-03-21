# -*- coding: utf-8 -*-
"""
Главный файл запуска приложения
"""

from auth import ensure_users_file, ensure_admin
from ui import main_menu
import sys

def main():
    """
    @requires: Ничего
    @modifies: users.json (если отсутствует)
    @effects: Запускает интерфейс приложения
    @raises: Ничего
    @returns: None
    """
    try:
        ensure_users_file()  # создаём users.json, если отсутствует
        ensure_admin()       # создаём admin/root, если отсутствует
    except Exception as e:
        print(f"Ошибка инициализации пользователей: {e}")
        sys.exit(1)

    # Запуск интерфейса пользователя
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nПрограмма завершена пользователем.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    main()