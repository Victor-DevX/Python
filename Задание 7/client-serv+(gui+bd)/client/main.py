# -*- coding: utf-8 -*-
import sys
from gui import start_gui

def main():
    """
    @requires: Доступна функция start_gui() из модуля gui;
               окружение поддерживает запуск GUI-приложения.
    @modifies: Системные ресурсы (инициализация GUI, обработка ввода/вывода).
    @effects: Запускает графический интерфейс приложения.
              Обрабатывает завершение программы:
              - при KeyboardInterrupt (Ctrl+C) выводит сообщение о завершении,
              - при других исключениях выводит текст ошибки.
    @raises: None (все исключения перехватываются внутри функции).
    @returns: None
    """
    try:
        start_gui()
    except KeyboardInterrupt:
        print("\nПрограмма завершена пользователем.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    main()