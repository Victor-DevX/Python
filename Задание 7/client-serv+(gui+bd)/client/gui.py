# -*- coding: utf-8 -*-
"""
PyQt6 GUI для Farmers Markets (PRO версия, единый интерфейс)

Добавлено:
- QStackedWidget для единого окна
- Стартовая страница, авторизация, регистрация, просмотр рынков
- Роли пользователей (скрытие кнопок и защита)
- Проверки регистрации и авторизации
- Docstring в стиле @requires/@modifies/@effects/@raises
- Иконка приложения для всего окна
- Адаптивные и отцентрированные элементы UI
- Единое окно поиска
"""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem,
    QInputDialog, QDialog, QTextEdit, QStackedWidget, QSizePolicy, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from client_api import (
    login_user, register_user, load_markets, search_markets, 
    find_markets_by_distance, add_review, delete_market, get_market_details
)

current_user = {"username": None, "role": None}
PER_PAGE = 15

def show_message(parent, title, text, icon="info"):
    """
    @requires: parent — виджет, title и text — строки, icon — тип иконки.
    @modifies: Создает и отображает модальное окно QMessageBox.
    @effects: Выводит сообщение пользователю, автоматически подбирая ширину окна под текст.
    @raises: None
    """
    msg = QMessageBox(parent)
    msg.setText(text)
    msg.setWindowTitle(title)

    if icon == "info":
        msg.setIcon(QMessageBox.Icon.Information)
    elif icon == "warning":
        msg.setIcon(QMessageBox.Icon.Warning)
    elif icon == "error":
        msg.setIcon(QMessageBox.Icon.Critical)

    msg.setMinimumWidth(350)
    font_metrics = msg.fontMetrics()
    lines = text.split("\n")
    max_line_length = max(font_metrics.horizontalAdvance(line) for line in lines)
    msg.setMinimumWidth(max(350, max_line_length + 50))

    msg.exec()


def start_gui():
    """
    @requires: Наличие установленной библиотеки PyQt6.
    @modifies: Запускает цикл обработки событий QApplication.
    @effects: Инициализирует и отображает главное окно приложения.
    @raises: SystemExit при закрытии приложения.
    """
    app = QApplication(sys.argv)

    base_path = os.path.dirname(os.path.abspath(__file__))
    ico_file = os.path.join(base_path, "icon.ico")
    png_file = os.path.join(base_path, "icon.png")

    if os.path.exists(ico_file):
        app.setWindowIcon(QIcon(ico_file))
    elif os.path.exists(png_file):
        app.setWindowIcon(QIcon(png_file))
    else:
        print("⚠ Иконка не найдена, убедись что icon.ico или icon.png лежит рядом с файлом")

    window = AppWindow()
    window.show()
    sys.exit(app.exec())


# ============================
# ДИАЛОГ ПОИСКА РЫНКА
# ============================
class SearchDialog(QDialog):
    """
    Единое окно для поиска рынка (по критериям и по координатам).
    """
    def __init__(self, parent=None):
        """
        @requires: parent — объект AppWindow (MainWindow).
        @modifies: Создает интерфейс диалогового окна поиска.
        @effects: Инициализирует два режима поиска: по текстовым критериям и по координатам.
        @raises: None
        """
        super().__init__(parent)
        self.setWindowTitle("Поиск рынка")
        self.resize(400, 250)
        
        layout = QVBoxLayout()
        
        # --- Текстовый поиск ---
        lbl_crit = QLabel("Поиск по критериям (город, штат, ZIP):")
        lbl_crit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_crit)
        
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Введите запрос...")
        self.query_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.query_input)
        
        btn_search = QPushButton("Найти по критериям")
        btn_search.clicked.connect(self.do_search)
        layout.addWidget(btn_search)
        
        layout.addSpacing(20)
        
        # --- Поиск по координатам ---
        lbl_coord = QLabel("Поиск по координатам (широта,долгота):")
        lbl_coord.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_coord)
        
        self.coord_input = QLineEdit()
        self.coord_input.setPlaceholderText("Например: 40.71,-74.00")
        self.coord_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.coord_input)
        
        btn_dist = QPushButton("Найти по координатам")
        btn_dist.clicked.connect(self.do_distance)
        layout.addWidget(btn_dist)
        
        self.setLayout(layout)
        
    def do_search(self):
        """
        @requires: Поле self.query_input инициализировано; введена непустая строка запроса.
        @modifies: Состояние родительского окна (self.parent().filtered, self.parent().page).
        @effects: Вызывает perform_text_search у родителя, закрывает диалог при успешном вводе.
        @raises: None (ошибки ввода обрабатываются через QMessageBox).
        """
        text = self.query_input.text().strip()
        if text:
            self.parent().perform_text_search(text)
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Введите запрос для поиска.")

    def do_distance(self):
        """
        @requires: Поле self.coord_input инициализировано; введена строка формата "lat,lon".
        @modifies: Состояние родительского окна (self.parent().filtered, self.parent().page).
        @effects: Вызывает perform_coord_search у родителя, закрывает диалог при корректном вводе.
        @raises: None (ошибки ввода обрабатываются внутри вызываемого метода и через QMessageBox).
        """
        text = self.coord_input.text().strip()
        if text:
            self.parent().perform_coord_search(text)
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Введите координаты.")


# ============================
# MAIN APP WINDOW
# ============================

class MainWindow(QWidget):
    def __init__(self, parent=None):
        """
        @requires: Данные от сервера (load_markets).
        @modifies: self.markets, self.filtered, self.page.
        @effects: Инициализирует состояние главного окна и загружает список рынков.
        @raises: None
        """
        super().__init__(parent)
        self.parent = parent
        self.markets = load_markets()
        self.filtered = self.markets
        self.page = 0
        self.total_pages = 1

        self.init_ui()
        self.update_table()

    def init_ui(self):
            """
            @requires: Экземпляр MainWindow инициализирован.
            @modifies: self.layout, self.table, кнопки управления.
            @effects: Формирует основной интерфейс приложения. Устанавливает фиксированную ширину кнопок 
                    по самому длинному тексту. Настраивает таблицу так, чтобы столбец 'Name' 
                    занимал максимум пространства (Stretch), а остальные — по размеру контента.
            @raises: None
            """
            layout = QVBoxLayout()

            # Верхние кнопки
            top = QHBoxLayout()
            top.addStretch(1)

            # Расчет ширины кнопок по самому широкому тексту
            font_metrics = self.fontMetrics()
            max_btn_width = font_metrics.horizontalAdvance("Возврат на страницу регистрации/авторизации") + 40

            btn_all = QPushButton("Вернуться к началу списка")
            btn_all.setFixedWidth(max_btn_width)
            btn_all.clicked.connect(self.reset)
            top.addWidget(btn_all)

            btn_search = QPushButton("Поиск рынка")
            btn_search.setFixedWidth(max_btn_width)
            btn_search.clicked.connect(self.open_search_dialog)
            top.addWidget(btn_search)

            btn_logout = QPushButton("Возврат на страницу регистрации/авторизации")
            btn_logout.setFixedWidth(max_btn_width)
            btn_logout.clicked.connect(self.logout)
            top.addWidget(btn_logout)

            top.addStretch(1)
            layout.addLayout(top)

            # Таблица рынков
            self.table = QTableWidget()
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["Name", "City", "State", "ZIP"])
            self.table.cellDoubleClicked.connect(self.open_card)
            
            # --- НАСТРОЙКА ШИРИНЫ СТОЛБЦОВ ---
            header = self.table.horizontalHeader()
            
            # Меняем режим на Fixed, чтобы мы могли управлять шириной вручную
            # и чтобы столбцы не пытались сами подгоняться под контент
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            
            layout.addWidget(self.table)

            # Пагинация
            bottom = QHBoxLayout()
            
            # Смещение всего блока к центру/вправо
            bottom.addStretch(1) 

            # --- Перелистывание страниц ---
            btn_prev = QPushButton("◀")
            btn_prev.setFixedWidth(40)
            btn_prev.clicked.connect(self.prev_page)
            
            self.page_label = QLabel()
            self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.page_label.setMinimumWidth(80) 
            
            btn_next = QPushButton("▶")
            btn_next.setFixedWidth(40)
            btn_next.clicked.connect(self.next_page)

            bottom.addWidget(btn_prev)
            bottom.addWidget(self.page_label)
            bottom.addWidget(btn_next)

            # --- Отступ между группами ---
            bottom.addSpacing(30)

            # --- Группа быстрого перехода к странице---
            self.page_input = QLineEdit()
            self.page_input.setPlaceholderText("№")
            self.page_input.setFixedWidth(45)
            self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            btn_jump = QPushButton("Перейти")
            btn_jump.clicked.connect(self.jump_to_page)

            bottom.addWidget(self.page_input)
            bottom.addWidget(btn_jump)
            
            # Чтобы элементы не прилипали к правому краю экрана
            bottom.addStretch(1) 

            layout.addLayout(bottom)
            
            # ВАЖНО: Эта строка собирает весь интерфейс и выводит его на экран!
            self.setLayout(layout)

    def jump_to_page(self):
        """
        @requires: Введенное число в page_input.
        @modifies: self.page, self.table.
        @effects: Переключает таблицу на указанную пользователем страницу.
        @raises: None (ошибки ввода обрабатываются через QMessageBox).
        """
        text = self.page_input.text().strip()
        if not text:
            return
        if not text.isdigit():
            show_message(self, "Ошибка ввода", "Введите корректный номер страницы (только цифры).", "warning")
            return
            
        target = int(text)
        total_items = len(self.filtered)
        total_pages = (total_items + PER_PAGE - 1) // PER_PAGE if total_items > 0 else 1

        if 1 <= target <= total_pages:
            self.page = target - 1 
            self.update_table()
            self.page_input.clear()
            self.page_input.clearFocus()
        else:
            msg = f"Страница не найдена.\n\nДоступный диапазон: от 1 до {total_pages}."
            show_message(self, "Внимание", msg, "warning")

    def reset(self):
        """
        @requires: None
        @modifies: self.filtered, self.page, self.table.
        @effects: Сбрасывает фильтры и возвращает таблицу к полному списку.
        @raises: None
        """
        self.filtered = self.markets
        self.page = 0
        self.update_table()

    def paginate(self):
        """
        @requires: self.filtered — список (может быть пустым).
        @modifies: self.total_pages.
        @effects: Вычисляет общее число страниц и возвращает срез данных для текущей страницы.
        @raises: None
        """
        start = self.page * PER_PAGE
        end = start + PER_PAGE
        self.total_pages = max(1, (len(self.filtered) + PER_PAGE - 1) // PER_PAGE)
        return self.filtered[start:end]

    def update_table(self):
            """
            @requires: Наличие данных в self.filtered.
            @modifies: self.table content, self.table headers, self.page_label.
            @effects: Отрисовывает строки таблицы для текущей страницы и устанавливает сквозную нумерацию.
            @raises: None
            """
            data = self.paginate()
            self.table.setRowCount(len(data))
            
            # --- СКВОЗНАЯ НУМЕРАЦИЯ ---
            # Вычисляем стартовый индекс для текущей страницы
            start_index = self.page * PER_PAGE
            
            # Генерируем список номеров [ "1", "2", ... ] или [ "16", "17", ... ]
            row_labels = [str(start_index + i + 1) for i in range(len(data))]
            self.table.setVerticalHeaderLabels(row_labels)
            
            # Заполнение таблицы данными
            for i, m in enumerate(data):
                self.table.setItem(i, 0, QTableWidgetItem(m.get("marketname", "")))
                self.table.setItem(i, 1, QTableWidgetItem(m.get("city_name", "")))
                self.table.setItem(i, 2, QTableWidgetItem(m.get("state_name", "")))
                self.table.setItem(i, 3, QTableWidgetItem(str(m.get("zip", ""))))
                
            self.page_label.setText(f"Страница {self.page+1}/{self.total_pages}")
            self.adjust_table_columns()

    def next_page(self):
        """
        @requires: self.total_pages >= 1.
        @modifies: self.page, self.table.
        @effects: Увеличивает номер страницы на 1 (если не достигнут конец) и обновляет таблицу.
        @raises: None
        """
        if self.page + 1 < self.total_pages:
            self.page += 1
            self.update_table()

    def prev_page(self):
        """
        @requires: self.total_pages >= 1.
        @modifies: self.page, self.table.
        @effects: Уменьшает номер страницы на 1 (если не первая страница) и обновляет таблицу.
        @raises: None
        """
        if self.page > 0:
            self.page -= 1
            self.update_table()

    def open_card(self, row, col):
        """
        @requires: row — корректный индекс строки в текущей странице; self.filtered — список рынков.
        @modifies: None.
        @effects: Открывает модальное окно MarketDialog для выбранного рынка.
        @raises: None
        """
        idx = self.page * PER_PAGE + row
        if idx >= len(self.filtered):
            return
        market = self.filtered[idx]
        dlg = MarketDialog(market, parent=self)
        dlg.exec()

    # --- Методы для работы поиска ---
    def open_search_dialog(self):
        """
        @requires: None
        @modifies: None
        @effects: Вызывает единое окно поиска.
        @raises: None
        """
        dlg = SearchDialog(self)
        dlg.exec()

    def perform_text_search(self, text):
        """
        @requires: text — строка поиска; self.markets — список рынков.
        @modifies: self.filtered, self.page, self.table.
        @effects: Фильтрует список рынков через search_markets, сбрасывает страницу на первую и обновляет таблицу.
        @raises: None
        """
        self.filtered = search_markets(self.markets, text)
        self.page = 0
        self.update_table()

    def perform_coord_search(self, text):
        """
        @requires: text — строка формата "lat,lon"; self.markets — список рынков.
        @modifies: self.filtered, self.page, self.table.
        @effects: Выполняет поиск ближайших рынков через find_markets_by_distance, обновляет таблицу и выводит результат пользователю.
        @raises: None (исключения обрабатываются внутри метода с выводом сообщений).
        """
        try:
            parts = text.split(",")
            if len(parts) != 2:
                QMessageBox.critical(self, "Ошибка", "Нужно ввести два числа через запятую.")
                return
            
            lat, lon = map(float, parts)
            res = find_markets_by_distance(self.markets, lat, lon)
            
            if isinstance(res, dict):
                markets_list = res.get("data", [])
            else:
                markets_list = res

            if markets_list:
                self.filtered = markets_list 
                self.page = 0
                self.update_table() 
                m = markets_list[0]
                QMessageBox.information(self, "Успех", f"Найдено ближайших рынков: {len(markets_list)}\nСамый близкий: {m.get('marketname')}")
            else:
                QMessageBox.warning(self, "Результат", "Рынки не найдены.")

        except ValueError:
            QMessageBox.critical(self, "Ошибка", "Некорректный формат координат.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")
    
    def adjust_table_columns(self):
        """
        @requires: self.table инициализирован; таблица имеет 4 столбца.
        @modifies: Ширины столбцов self.table.
        @effects: Устанавливает пропорциональную ширину столбцов (50% / ~16.6% / ~16.6% / ~16.6%) без появления горизонтального скролла.
        @raises: None
        """
        # Если таблица еще не видна или скрыта, ширина может быть некорректной
        width = self.table.viewport().width()
        if width <= 0:
            return

        col0 = width // 2
        col_others = (width - col0) // 3
        
        self.table.setColumnWidth(0, col0)
        self.table.setColumnWidth(1, col_others)
        self.table.setColumnWidth(2, col_others)
        self.table.setColumnWidth(3, col_others)

    def showEvent(self, event):
        """
        @requires: event — объект события отображения Qt.
        @modifies: Ширины столбцов таблицы.
        @effects: После первого отображения окна пересчитывает ширину столбцов.
        @raises: None
        """
        """Срабатывает один раз при открытии окна."""
        super().showEvent(event)
        # Вызываем пересчет, как только окно отобразилось
        self.adjust_table_columns()

    def resizeEvent(self, event):
        """
        @requires: event — объект события изменения размера Qt.
        @modifies: Ширины столбцов таблицы.
        @effects: При изменении размера окна пересчитывает ширину столбцов.
        @raises: None
        """
        super().resizeEvent(event)
        self.adjust_table_columns()

    def logout(self):
        """
        @requires: None
        @modifies: current_user.
        @effects: Сбрасывает сессию и возвращает пользователя на стартовый экран.
        @raises: None
        """
        current_user["username"] = None
        current_user["role"] = None
        self.parent.show_start()


class MarketDialog(QDialog):
    def __init__(self, market, parent=None):
        """
        @requires: market — словарь данных.
        @modifies: self.info, self.btn_review.
        @effects: Создает окно карточки рынка с отзывами и функционалом администратора.
        @raises: None
        """
        super().__init__(parent)
        self.market = market
        self.parent = parent
        self.setWindowTitle(market.get("marketname", "Market"))
        self.resize(600, 500)

        layout = QVBoxLayout()

        self.status_label = QLabel()
        self.update_status_label()
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignRight)

        self.info = QTextEdit()
        self.info.setReadOnly(True)
        self.refresh_market_info()
        layout.addWidget(self.info)

        btn_layout = QHBoxLayout()

        self.btn_review = QPushButton("Добавить отзыв")
        self.btn_review.clicked.connect(self.add_review) 
        btn_layout.addWidget(self.btn_review)

        if current_user.get("role") == "admin":
            self.btn_delete = QPushButton("Удалить рынок")
            self.btn_delete.clicked.connect(self.delete_market)
            btn_layout.addWidget(self.btn_delete)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def update_status_label(self):
        """
        @requires: Глобальный словарь current_user доступен.
        @modifies: self.status_label.
        @effects: Устанавливает текст статуса пользователя (гость / пользователь / администратор).
        @raises: None
        """
        if current_user.get("username"):
            if current_user["role"] == "admin":
                self.status_label.setText("Администратор")
            else:
                self.status_label.setText(f"Логин: {current_user['username']}")
        else:
            self.status_label.setText("Гость")

    def refresh_market_info(self):
        """
        @requires: self.market — словарь с данными рынка.
        @modifies: self.info.
        @effects: Запрашивает актуальные данные через get_market_details и обновляет текстовое поле.
        @raises: None (ошибки API не обрабатываются явно).
        """
        data = get_market_details(self.market)
        self.info.setText(self.format_market_text(data))

    def format_market_text(self, data):
        """
        @requires: data — словарь с ключами name, address, city, state, zip, coords, products, reviews, avg_rating (возможны пустые значения).
        @modifies: None.
        @effects: Формирует и возвращает строковое представление информации о рынке.
        @raises: None
        """
        if not data:
            return "Нет данных"
        lines = [f"=== {data['name']} ===",
                 f"Адрес: {data['address']}",
                 f"{data['city']}, {data['state']} ({data['zip']})",
                 f"Координаты: {data['coords']}"]
        if data["products"]:
            lines.append("\nТовары:")
            lines += [f" - {p}" for p in data["products"]]
        if data["reviews"]:
            lines.append("\nОтзывы:")
            lines += [f" - {r['username']}: {r['rating']}/5 — {r['text']}" for r in data["reviews"]]
        else:
            lines.append("\nНет отзывов")
        lines.append(f"\nСредний рейтинг: {data['avg_rating']}")
        return "\n".join(lines)

    def add_review(self):
        """
        @requires: Пользователь может быть неавторизован; self.market содержит ключ "fmid".
        @modifies: Внешнее состояние (БД через API), self.info.
        @effects: При авторизации запрашивает рейтинг и текст, добавляет отзыв через API, обновляет информацию о рынке.
        @raises: None (ошибки обрабатываются через QMessageBox).
        """
        if not current_user.get("username"):
            QMessageBox.information(self, "Авторизация", "Сначала войдите в систему")
            if hasattr(self.parent, 'show_login'):
                self.parent.show_login()
            return

        rating, ok = QInputDialog.getInt(self, "Рейтинг", "1-5", 5, 1, 5)
        if not ok:
            return
        text, ok = QInputDialog.getText(self, "Отзыв", "Текст")
        if not ok or not text.strip():
            return

        add_review(self.market["fmid"], current_user["username"], rating, text)
        QMessageBox.information(self, "OK", "Отзыв добавлен")
        self.refresh_market_info()
        self.update_status_label()
    
    def delete_market(self):
        """
        @requires: current_user["role"] == "admin"; self.market содержит ключ "fmid".
        @modifies: Внешнее состояние (БД через API), данные родительского окна (self.parent.markets, self.parent.filtered).
        @effects: После подтверждения удаляет рынок, обновляет список в родительском окне и закрывает диалог.
        @raises: None
        """
        if current_user.get("role") != "admin":
            QMessageBox.warning(self, "Ошибка", "Нет прав")
            return

        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            "Удалить этот рынок?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            delete_market(self.market["fmid"])
            QMessageBox.information(self, "OK", "Рынок удалён")

            if hasattr(self.parent, 'update_table'):
                self.parent.markets = load_markets()
                self.parent.filtered = self.parent.markets
                self.parent.update_table()

            self.close()


class AppWindow(QWidget):
    def __init__(self):
        """
        @requires: None
        @modifies: self.stack.
        @effects: Инициализирует контейнер страниц (QStackedWidget) для навигации.
        @raises: None
        """
        super().__init__()
        self.setWindowTitle("Farmers Markets")
        self.resize(900, 550)

        self.stack = QStackedWidget()
        layout = QVBoxLayout()
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.status_label)
        layout.addWidget(self.stack)
        self.setLayout(layout)

        self.start_page = StartPage(self)
        self.login_page = LoginPage(self)
        self.register_page = RegisterPage(self)
        self.main_page = MainWindow(self)  

        self.stack.addWidget(self.start_page)
        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.register_page)
        self.stack.addWidget(self.main_page)

        self.show_start()

    def update_status(self):
        """
        @requires: Глобальный словарь current_user доступен.
        @modifies: self.status_label.
        @effects: Отображает статус пользователя (ФИО и роль или сообщение о неавторизованности).
        @raises: None
        """
        if current_user.get("username"):
            if current_user["role"] == "admin":
                self.status_label.setText("Администратор")
            else:
                name = f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}".strip()
                self.status_label.setText(f"{name} ({current_user['role']})")
        else:
            self.status_label.setText("Вы не авторизованы")

    def show_start(self):
        """
        @requires: None
        @modifies: self.stack.
        @effects: Переключает интерфейс на стартовую страницу.
        @raises: None
        """
        self.stack.setCurrentWidget(self.start_page)
        self.update_status()

    def show_login(self):
        """
        @requires: None
        @modifies: self.stack.
        @effects: Отображает страницу входа.
        @raises: None
        """
        self.stack.setCurrentWidget(self.login_page)
        self.update_status()

    def show_register(self):
        """
        @requires: None
        @modifies: self.stack.
        @effects: Отображает страницу регистрации.
        @raises: None
        """
        self.stack.setCurrentWidget(self.register_page)
        self.update_status()

    def show_main(self):
        """
        @requires: None
        @modifies: self.stack.
        @effects: Отображает главную страницу с данными.
        @raises: None
        """
        self.stack.setCurrentWidget(self.main_page)
        self.update_status()

# ============================
# СТРАНИЦЫ
# ============================

class StartPage(QWidget):
    def __init__(self, parent):
        """
        @requires: parent (AppWindow).
        @modifies: self.layout.
        @effects: Создает приветственный экран с кнопками навигации.
        @raises: None
        """
        super().__init__()
        self.parent = parent

        layout = QVBoxLayout()
        layout.addStretch(1)

        label = QLabel("Добро пожаловать,\nв приложение «Фермерские рынки!»")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(label)

        layout.addSpacing(20)

        btn_login = QPushButton("Авторизация в приложении")
        btn_login.clicked.connect(self.parent.show_login)

        btn_register = QPushButton("Регистрация в приложении")
        btn_register.clicked.connect(self.parent.show_register)

        btn_view = QPushButton("Продолжить как гость")
        btn_view.clicked.connect(self.parent.show_main)

        # Центрирование кнопок на главной
        def add_centered(widget):
            h = QHBoxLayout()
            h.addStretch(1)
            widget.setFixedWidth(250)
            h.addWidget(widget)
            h.addStretch(1)
            layout.addLayout(h)

        add_centered(btn_login)
        add_centered(btn_register)
        add_centered(btn_view)

        layout.addStretch(1)
        self.setLayout(layout)


class LoginPage(QWidget):
    def __init__(self, parent):
        """
        @requires: parent (AppWindow).
        @modifies: self.user, self.pwd.
        @effects: Создает форму входа, отцентрированную по центру окна.
        @raises: None
        """
        super().__init__()
        self.parent = parent

        layout = QVBoxLayout()
        layout.addStretch(1)

        title = QLabel("Авторизация")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; margin-bottom: 15px;")
        layout.addWidget(title)

        def add_centered(widget):
            h = QHBoxLayout()
            h.addStretch(1)
            h.addWidget(widget)
            h.addStretch(1)
            layout.addLayout(h)

        self.user = QLineEdit()
        self.user.setPlaceholderText("Username")
        self.user.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.user.setFixedWidth(300)
        add_centered(self.user)

        layout.addSpacing(10)

        self.pwd = QLineEdit()
        self.pwd.setPlaceholderText("Password")
        self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pwd.setFixedWidth(300)
        add_centered(self.pwd)

        layout.addSpacing(20)

        btn_login = QPushButton("Войти")
        btn_login.setFixedWidth(200)
        btn_login.clicked.connect(self.login)
        add_centered(btn_login)

        btn_back = QPushButton("Назад")
        btn_back.setFixedWidth(200)
        btn_back.clicked.connect(self.parent.show_start)
        add_centered(btn_back)

        layout.addStretch(1)
        self.setLayout(layout)

    def login(self):
        """
        @requires: Поля self.user и self.pwd инициализированы.
        @modifies: current_user, состояние AppWindow (через parent).
        @effects: Выполняет аутентификацию через login_user; при успехе сохраняет пользователя и открывает главную страницу.
        @raises: None (ошибки обрабатываются через QMessageBox).
        """
        username = self.user.text().strip()
        password = self.pwd.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль")
            return

        ok, res = login_user(username, password)
        
        if ok:
            current_user["username"] = res.get("username")
            current_user["role"] = res.get("role", "user")
            self.parent.update_status() 
            self.parent.show_main()
        else:
            QMessageBox.critical(self, "Ошибка", str(res))


class RegisterPage(QWidget):
    def __init__(self, parent):
        """
        @requires: parent (AppWindow).
        @modifies: Поля ввода регистрации.
        @effects: Создает форму регистрации с выравниванием элементов по центру.
        @raises: None
        """
        super().__init__()
        self.parent = parent

        layout = QVBoxLayout()
        layout.addStretch(1)

        title = QLabel("Регистрация")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; margin-bottom: 15px;")
        layout.addWidget(title)

        # Вспомогательная функция для центрирования Label и Input
        def add_centered_field(label_text, widget):
            lbl = QLabel(label_text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            h_lbl = QHBoxLayout()
            h_lbl.addStretch(1)
            h_lbl.addWidget(lbl)
            h_lbl.addStretch(1)
            layout.addLayout(h_lbl)

            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            widget.setFixedWidth(300)

            h_wid = QHBoxLayout()
            h_wid.addStretch(1)
            h_wid.addWidget(widget)
            h_wid.addStretch(1)
            layout.addLayout(h_wid)
            layout.addSpacing(5)

        self.user = QLineEdit()
        self.user.setPlaceholderText("Введите логин")
        add_centered_field("Логин (не менее 2 символов)", self.user)

        self.pwd = QLineEdit()
        self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd.setPlaceholderText("Введите пароль")
        add_centered_field("Пароль (не менее 4 символов)", self.pwd)

        self.first = QLineEdit()
        self.first.setPlaceholderText("обязательно")
        add_centered_field("Имя", self.first)

        self.last = QLineEdit()
        self.last.setPlaceholderText("обязательно")
        add_centered_field("Фамилия", self.last)

        self.middle = QLineEdit()
        self.middle.setPlaceholderText("при наличии")
        add_centered_field("Отчество (необязательно)", self.middle)

        layout.addSpacing(15)

        # Вспомогательная функция для кнопок
        def add_centered_button(btn):
            h = QHBoxLayout()
            h.addStretch(1)
            btn.setFixedWidth(200)
            h.addWidget(btn)
            h.addStretch(1)
            layout.addLayout(h)

        btn_create = QPushButton("Зарегистрироваться")
        btn_create.clicked.connect(self.register)
        add_centered_button(btn_create)

        btn_back = QPushButton("Назад")
        btn_back.clicked.connect(self.parent.show_start)
        add_centered_button(btn_back)

        layout.addStretch(1)
        self.setLayout(layout)

    def register(self):
        """
        @requires: Поля self.user, self.pwd, self.first, self.last инициализированы.
        @modifies: Внешнее состояние (БД через API).
        @effects: Валидирует ввод, регистрирует пользователя через register_user и возвращает на стартовую страницу при успехе.
        @raises: None (ошибки валидации и API обрабатываются через сообщения).
        """
        username = self.user.text().strip()
        password = self.pwd.text().strip()
        first = self.first.text().strip()
        last = self.last.text().strip()
        middle = self.middle.text().strip()

        if not username:
            show_message(self, "Ошибка", "Введите логин")
            return
        if len(username) < 2:
            show_message(self, "Ошибка", "Логин должен быть не менее 2 символов")
            return
        if not password:
            show_message(self, "Ошибка", "Введите пароль")
            return
        if len(password) < 4:
            show_message(self, "Ошибка", "Пароль должен быть не менее 4 символов")
            return
        if not first:
            show_message(self, "Ошибка", "Введите имя")
            return
        if not last:
            show_message(self, "Ошибка", "Введите фамилию")
            return

        ok, msg = register_user(username, password, first, last, middle)
        if ok:
            QMessageBox.information(self, "OK", "Пользователь создан")
            self.parent.show_start()
        else:
            QMessageBox.critical(self, "Ошибка", msg)