# -*- coding: utf-8 -*-
"""
Главный файл запуска приложения
"""

from ui import main_menu
from auth import ensure_users_file, ensure_admin

ensure_users_file()  # создаём users.json, если отсутсвует
ensure_admin()       # создаём admin/root, если отсутсвует

if __name__ == "__main__":
    main_menu()