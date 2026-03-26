# -*- coding: utf-8 -*-
import sys
from auth import ensure_admin_in_db
#from ui import main_menu
from gui import start_gui



def main():
    """
    @requires: Таблица users в PostgreSQL создана
    @modifies: Таблица users (создаёт admin при необходимости)
    @effects: Запускает интерфейс приложения
    @raises: Исключения при инициализации админа или интерфейса логируются
    @returns: None
    """
    try:
        # Создаём админа в БД, если его нет
        ensure_admin_in_db()
    except Exception as e:
        print(f"Ошибка инициализации админа: {e}")
        sys.exit(1)

    # Запуск интерфейса пользователя
    try:
#        main_menu()
        start_gui()
    except KeyboardInterrupt:
        print("\nПрограмма завершена пользователем.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    main()