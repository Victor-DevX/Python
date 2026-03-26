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
"""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem,
    QInputDialog, QDialog, QTextEdit, QStackedWidget,QSizePolicy, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from auth import login_user, register_user
from kernel import (
    load_markets, search_markets, find_markets_by_distance,
    add_review, delete_market, get_market_details
)

current_user = {"username": None, "role": None}
PER_PAGE = 15

def show_message(parent, title, text, icon="info"):
    """
    Показывает окно с сообщением с автоматическим увеличением ширины для длинного текста.

    @requires: parent — виджет PyQt6, text — строка, title — строка, icon — один из ["info","warning","error"]
    @modifies: отображаемое окно QMessageBox
    @effects: Создаёт и показывает QMessageBox с заданным текстом, автоматически устанавливает минимальную ширину для текста
    @raises: None
    """
    msg = QMessageBox(parent)
    msg.setText(text)
    msg.setWindowTitle(title)

    # Устанавливаем иконку
    if icon == "info":
        msg.setIcon(QMessageBox.Icon.Information)
    elif icon == "warning":
        msg.setIcon(QMessageBox.Icon.Warning)
    elif icon == "error":
        msg.setIcon(QMessageBox.Icon.Critical)

    # Растягиваем окно под текст
    msg.setMinimumWidth(350)
    # Можно динамически расширять по длине текста
    font_metrics = msg.fontMetrics()
    lines = text.split("\n")
    max_line_length = max(font_metrics.horizontalAdvance(line) for line in lines)
    msg.setMinimumWidth(max(350, max_line_length + 50))

    msg.exec()


def start_gui():
    """
    Запускает GUI приложение Farmers Markets.

    Создаёт QApplication, устанавливает иконку окна, создаёт главное окно AppWindow
    и запускает главный цикл приложения.

    Иконка ищется в текущей папке рядом с файлом: сначала 'icon.ico', затем 'icon.png'.

    @modifies: QApplication, создаёт главное окно
    @effects: Показывает GUI и блокирует поток до закрытия окна
    @raises: SystemExit при закрытии приложения
    """

    app = QApplication(sys.argv)

    # Путь к иконке рядом с main.py или gui.py
    base_path = os.path.dirname(os.path.abspath(__file__))
    ico_file = os.path.join(base_path, "icon.ico")
    png_file = os.path.join(base_path, "icon.png")

    if os.path.exists(ico_file):
        app.setWindowIcon(QIcon(ico_file))
    elif os.path.exists(png_file):
        app.setWindowIcon(QIcon(png_file))
    else:
        print("⚠ Иконка не найдена, убедись что icon.ico или icon.png лежит рядом с файлом")

    # Создаём окно напрямую
    window = AppWindow()
    window.show()
    sys.exit(app.exec())

# ============================
# MAIN APP WINDOW
# ============================

class MainWindow(QWidget):
    """
    Страница просмотра рынков.

    @requires: load_markets(), search_markets(), find_markets_by_distance(), add_review(), delete_market() доступны;
               current_user содержит информацию о пользователе
    @modifies: UI компоненты страницы, внутренние списки self.markets и self.filtered
    @effects: Создаёт интерфейс просмотра рынков с таблицей, кнопками фильтрации, поиска, добавления отзывов (для авторизованных), удаления (для админа)
    @raises: None (ошибки через QMessageBox)
    """
    def __init__(self, parent=None):
        """
        @requires: parent — QWidget с методами навигации
        @modifies: self (создаются элементы интерфейса, загружается список рынков)
        @effects: Инициализирует страницу просмотра рынков, загружает данные и настраивает UI
        @raises: None
        """
        super().__init__(parent)
        self.parent = parent

        # Загружаем рынки
        self.markets = load_markets()
        self.filtered = self.markets
        self.page = 0
        self.total_pages = 1

        self.init_ui()
        self.update_table()

    def init_ui(self):
        """
        @requires: None
        @modifies: self.table, кнопки фильтров и действий, лэйаут страницы
        @effects: Создаёт UI: верхние кнопки, таблицу рынков, пагинацию
        @raises: None
        """
        layout = QVBoxLayout()

        # Верхние кнопки
        top = QHBoxLayout()
        btn_all = QPushButton("К началу списка")
        btn_all.clicked.connect(self.reset)
        top.addWidget(btn_all)

        btn_search = QPushButton("Поиск рынка")
        btn_search.clicked.connect(self.search)
        top.addWidget(btn_search)

        btn_dist = QPushButton("Ближайший")
        btn_dist.clicked.connect(self.distance)
        top.addWidget(btn_dist)

        btn_logout = QPushButton("На страницу регистрации/авторизации")
        btn_logout.clicked.connect(self.logout)
        top.addWidget(btn_logout)

        layout.addLayout(top)

        # Таблица (центрированная и растягиваемая)
        table_container = QHBoxLayout()

        # Левый отступ
        table_container.addStretch(1)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "City", "State", "ZIP"])
        self.table.cellDoubleClicked.connect(self.open_card)

        # 👉 Растягивание таблицы
        self.table.setSizePolicy(
            self.table.sizePolicy().horizontalPolicy(),
            self.table.sizePolicy().verticalPolicy()
        )

        # 👉 Растягивание колонок
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            self.table.horizontalHeader().ResizeMode.Stretch
        )

        # 👉 Растягивание по всему доступному месту
        self.table.setMinimumWidth(600)
        self.table.setMinimumHeight(300)

        table_container.addWidget(self.table)

        # Правый отступ
        table_container.addStretch(1)

        layout.addLayout(table_container)

        # Пагинация
        bottom = QHBoxLayout()

        btn_prev = QPushButton("◀")
        btn_prev.clicked.connect(self.prev_page)
        bottom.addWidget(btn_prev)

        # Левый спейсер
        bottom.addStretch(1)

        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom.addWidget(self.page_label)

        # Правый спейсер
        bottom.addStretch(1)

        btn_next = QPushButton("▶")
        btn_next.clicked.connect(self.next_page)
        bottom.addWidget(btn_next)

        layout.addLayout(bottom)
        self.setLayout(layout)

    # Методы для MainWindow
    def reset(self):
        """
        @requires: None
        @modifies: self.filtered, self.page, UI таблицу
        @effects: Сбрасывает фильтры и обновляет таблицу
        @raises: None
        """
        self.filtered = self.markets
        self.page = 0
        self.update_table()

    def paginate(self):
        """
        @requires: None
        @modifies: self.total_pages
        @effects: Возвращает список рынков для текущей страницы
        @raises: None
        """
        start = self.page * PER_PAGE
        end = start + PER_PAGE
        self.total_pages = max(1, (len(self.filtered) + PER_PAGE - 1) // PER_PAGE)
        return self.filtered[start:end]

    def update_table(self):
        """
        @requires: None
        @modifies: self.table, self.page_label
        @effects: Обновляет отображаемые данные в таблице на текущей странице
        @raises: None
        """
        data = self.paginate()
        self.table.setRowCount(len(data))
        for i, m in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(m.get("marketname", "")))
            self.table.setItem(i, 1, QTableWidgetItem(m.get("city_name", "")))
            self.table.setItem(i, 2, QTableWidgetItem(m.get("state_name", "")))
            self.table.setItem(i, 3, QTableWidgetItem(str(m.get("zip", ""))))
        self.page_label.setText(f"Страница {self.page+1}/{self.total_pages}")

    def next_page(self):
        """
        @requires: None
        @modifies: self.page, таблицу
        @effects: Переходит на следующую страницу, если возможно
        @raises: None
        """
        if self.page + 1 < self.total_pages:
            self.page += 1
            self.update_table()

    def prev_page(self):
        """
        @requires: None
        @modifies: self.page, таблицу
        @effects: Переходит на предыдущую страницу, если возможно
        @raises: None
        """
        if self.page > 0:
            self.page -= 1
            self.update_table()

    def open_card(self, row, col):
        """
        @requires: row, col — корректные индексы таблицы
        @modifies: None
        @effects: Открывает окно MarketDialog для выбранного рынка
        @raises: None
        """
        idx = self.page * PER_PAGE + row
        if idx >= len(self.filtered):
            return
        market = self.filtered[idx]
        dlg = MarketDialog(market, parent=self)
        dlg.exec()

    def search(self):
        """
        @requires: load_markets() и search_markets()
        @modifies: self.filtered, self.page, UI таблицу
        @effects: Фильтрует рынки по текстовому запросу
        @raises: None
        """
        text, ok = QInputDialog.getText(self, "Поиск", "Введите запрос")
        if ok:
            self.filtered = search_markets(self.markets, text)
            self.page = 0
            self.update_table()

    def distance(self):
        """
        @requires: self.markets — список рынков (итерируемая коллекция словарей), 
                   self.filtered и self.page определены, метод self.update_table() реализован, 
                   функция find_markets_by_distance определена и возвращает либо список рынков, 
                   либо словарь с ключом "data", используются компоненты PyQt: QInputDialog и QMessageBox.
        @modifies: self.filtered (обновляется список отображаемых рынков), 
                   self.page (сбрасывается на первую страницу), состояние GUI (обновление таблицы и отображение сообщений).
        @effects: Запрашивает координаты у пользователя в формате "широта,долгота", 
                  проверяет корректность ввода, преобразует в float, вызывает find_markets_by_distance, 
                  обрабатывает ответ (dict или list), обновляет self.filtered и self.page, перерисовывает таблицу через update_table(), 
                  отображает информацию о ближайших рынках или предупреждение, показывает сообщение об ошибке при некорректном вводе.
        @raises: Исключения не пробрасываются наружу, ValueError и другие исключения перехватываются и отображаются пользователю через QMessageBox.
        """
        text, ok = QInputDialog.getText(self, "Координаты", "Введите через запятую: широта,долгота")
        if ok and text.strip():
            try:
                parts = text.split(",")
                if len(parts) != 2:
                    QMessageBox.critical(self, "Ошибка", "Нужно ввести два числа через запятую.")
                    return
                
                lat, lon = map(float, parts)
                
                # Получаем ответ от сервера
                # ВАЖНО: клиентская функция find_markets_by_distance должна возвращать список
                res = find_markets_by_distance(self.markets, lat, lon)
                
                # Если сервер вернул словарь {'status': 'success', 'data': [...]}, извлекаем 'data'
                if isinstance(res, dict):
                    markets_list = res.get("data", [])
                else:
                    markets_list = res

                if markets_list:
                    # 1. ОБНОВЛЯЕМ список для таблицы
                    self.filtered = markets_list 
                    self.page = 0
                    
                    # 2. ПЕРЕРИСОВЫВАЕМ таблицу
                    self.update_table() 
                    
                    # 3. Опционально: показываем самый близкий во всплывающем окне
                    m = markets_list[0]
                    QMessageBox.information(self, "Успех", f"Найдено ближайших рынков: {len(markets_list)}\nСамый близкий: {m.get('marketname')}")
                else:
                    QMessageBox.warning(self, "Результат", "Рынки не найдены.")

            except ValueError:
                QMessageBox.critical(self, "Ошибка", "Некорректный формат координат.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка: {e}")

    def logout(self):
        """
        @requires: None
        @modifies: current_user, UI (переход на стартовую страницу)
        @effects: Разлогинивает пользователя и возвращает на StartPage
        @raises: None
        """
        current_user["username"] = None
        current_user["role"] = None
        self.parent.show_start()

class MarketDialog(QDialog):
    """
    Окно конкретного рынка.

    @requires: current_user — глобальный словарь с авторизацией
    @modifies: таблицу reviews в БД через add_review, таблицу markets через delete_market
    @effects: Показывает карточку рынка с кнопками:
              - Добавить отзыв (для всех, при отсутствии авторизации переводит на окно логина)
              - Удалить рынок (только для админа)
              Обновляет текстовое поле после добавления отзыва или удаления.
    @raises: None (ошибки через QMessageBox)
    """
    def __init__(self, market, parent=None):
        """
        Инициализирует окно рынка, добавляет текстовое поле с информацией и кнопки действий.

        @requires: market — словарь с данными рынка
        @modifies: интерфейс QDialog, текущее окно приложения
        @effects: Создаёт и отображает виджеты с информацией о рынке, кнопки добавления отзыва и удаления
        @raises: None
        """
        super().__init__(parent)
        self.market = market
        self.parent = parent
        self.setWindowTitle(market.get("marketname", "Market"))
        self.resize(600, 500)

        layout = QVBoxLayout()

        # Статус пользователя
        self.status_label = QLabel()
        self.update_status_label()
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignRight)

        # Информация о рынке
        self.info = QTextEdit()
        self.info.setReadOnly(True)
        self.refresh_market_info()
        layout.addWidget(self.info)

        # Кнопки
        btn_layout = QHBoxLayout()

        # Кнопка добавления отзыва
        self.btn_review = QPushButton("Добавить отзыв")
        self.btn_review.clicked.connect(self.add_review) 
        btn_layout.addWidget(self.btn_review)

        # Кнопка удаления — только для админа
        if current_user.get("role") == "admin":
            self.btn_delete = QPushButton("Удалить рынок")
            self.btn_delete.clicked.connect(self.delete_market)
            btn_layout.addWidget(self.btn_delete)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def update_status_label(self):
        """
        Обновляет верхнюю строку с информацией о пользователе.

        @requires: current_user глобально определён
        @modifies: статусный QLabel self.status_label
        @effects: Выводит имя и фамилию + роль, либо роль, либо "Гость"
        @raises: None
        """
        if current_user.get("username"):
            name = f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}".strip()
            role = current_user.get("role", "")
            self.status_label.setText(f"{name} ({role})" if name else role)
        else:
            self.status_label.setText("Гость")

    def refresh_market_info(self):
        """
        Обновляет текстовое поле с полной информацией о рынке.

        @requires: функция get_market_details доступна
        @modifies: QTextEdit self.info
        @effects: Перезаписывает текстовое поле с актуальными данными о рынке и отзывах
        @raises: None
        """
        data = get_market_details(self.market)
        self.info.setText(self.format_market_text(data))

    def format_market_text(self, data):
        """
        Форматирует данные рынка в текст для QTextEdit.

        @requires: data — словарь с информацией о рынке и отзывах
        @modifies: None
        @effects: Возвращает строку с полной информацией о рынке
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
            Добавляет отзыв текущего пользователя к этому рынку.

            @requires: current_user глобально определён
            @modifies: таблицу reviews в БД через add_review, статусный QLabel
            @effects: Создаёт отзыв и обновляет текстовое поле с информацией.
                    Если пользователь не авторизован, переходит на страницу авторизации
            @raises: None (ошибки через QMessageBox)
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
        Удаляет текущий рынок (только для администратора).

        @requires: current_user с ролью admin, delete_market доступна
        @modifies: таблицу markets в БД
        @effects: Удаляет рынок, закрывает окно и обновляет список рынков
        @raises: None (ошибки через QMessageBox)
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

            # 👉 обновляем таблицу в главном окне
            if hasattr(self.parent, 'update_table'):
                self.parent.markets = load_markets()
                self.parent.filtered = self.parent.markets
                self.parent.update_table()

            self.close()


class AppWindow(QWidget):
    """
    @requires: PyQt6 установлен, функции auth и model доступны
    @modifies: QStackedWidget с интерфейсом приложения
    @effects: Создаёт единое окно с разными страницами (старт, авторизация, регистрация, просмотр рынков)
    @raises: None
    """
    def __init__(self):
        """
        @requires: Нет входных параметров; все используемые классы страниц корректно импортированы
        @modifies: self.stack (добавляются страницы), UI окна
        @effects: Инициализирует окно приложения, создаёт страницы и добавляет их в стек, устанавливает стартовую страницу
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

        # Страницы
        self.start_page = StartPage(self)
        self.login_page = LoginPage(self)
        self.register_page = RegisterPage(self)
        self.main_page = MainWindow(self)  # MainWindow под parent

        # Добавляем страницы в стек
        self.stack.addWidget(self.start_page)
        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.register_page)
        self.stack.addWidget(self.main_page)

        self.show_start()

    def show_start(self):
        """
        @requires: None
        @modifies: отображаемая страница в QStackedWidget
        @effects: Показывает стартовую страницу
        @raises: None
        """
        self.stack.setCurrentWidget(self.start_page)

    def show_login(self):
        """
        @requires: None
        @modifies: отображаемая страница в QStackedWidget
        @effects: Показывает страницу авторизации
        @raises: None
        """
        self.stack.setCurrentWidget(self.login_page)

    def show_register(self):
        """
        @requires: None
        @modifies: отображаемая страница в QStackedWidget
        @effects: Показывает страницу регистрации
        @raises: None
        """
        self.stack.setCurrentWidget(self.register_page)

    def show_main(self):
        """
        @requires: Пользователь авторизован (для полного функционала)
        @modifies: отображаемая страница в QStackedWidget
        @effects: Показывает страницу просмотра рынков
        @raises: None
        """
        self.stack.setCurrentWidget(self.main_page)

    def update_status(self):
        """
        @requires: Глобальный словарь current_user содержит ключи "username" и "role",
                   а также опционально "first_name" и "last_name".
                   self.status_label — валидный QLabel.

        @modifies: self.status_label (изменяет отображаемый текст).

        @effects:Обновляет текст статуса пользователя в интерфейсе:
                - "admin", если пользователь администратор,
                - "Имя Фамилия (роль)", если обычный пользователь,
                - "Не авторизован", если пользователь не вошёл в систему.

        @raises: Исключения не генерируются при корректной структуре current_user.
        """
        if current_user.get("username"):
            if current_user["role"] == "admin":
                self.status_label.setText("admin")
            else:
                name = f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}".strip()
                self.status_label.setText(f"{name} ({current_user['role']})")
        else:
            self.status_label.setText("Не авторизован")

    def show_start(self):
        """
    @requires: self.stack — QStackedWidget.
            self.start_page — существующий виджет страницы.

    @modifies: self.stack (текущую отображаемую страницу интерфейса).

    @effects: Переключает интерфейс на стартовую страницу и обновляет статус пользователя.

    @raises: Исключения не генерируются при корректной инициализации виджетов.
    """    
        self.stack.setCurrentWidget(self.start_page)
        self.update_status()

    def show_login(self):
        """
    @requires: self.stack — QStackedWidget.
               self.login_page — существующий виджет страницы.

    @modifies: self.stack (текущую отображаемую страницу интерфейса).

    @effects: Переключает интерфейс на страницу входа и обновляет статус пользователя.

    @raises: Исключения не генерируются при корректной инициализации виджетов.
    """
        self.stack.setCurrentWidget(self.login_page)
        self.update_status()

    def show_register(self):
        """
    @requires: self.stack — QStackedWidget.
               self.register_page — существующий виджет страницы.

    @modifies: self.stack (текущую отображаемую страницу интерфейса).

    @effects: Переключает интерфейс на страницу регистрации и обновляет статус пользователя.

    @raises: Исключения не генерируются при корректной инициализации виджетов.
    """

        self.stack.setCurrentWidget(self.register_page)
        self.update_status()

    def show_main(self):
        """
    @requires:self.stack — QStackedWidget.
              self.main_page — существующий виджет страницы.

    @modifies: self.stack (текущую отображаемую страницу интерфейса).

    @effects: Переключает интерфейс на основную страницу приложения и обновляет статус пользователя.

    @raises: Исключения не генерируются при корректной инициализации виджетов.
    """
        self.stack.setCurrentWidget(self.main_page)
        self.update_status()

# ============================
# СТРАНИЦЫ
# ============================

class StartPage(QWidget):
    """
    Стартовая страница приложения.

    @requires: parent — экземпляр AppWindow с методами show_login, show_register, show_main
    @modifies: UI компоненты страницы
    @effects: Отображает приветствие и кнопки перехода (авторизация, регистрация, просмотр рынков)
    @raises: None
    """
    def __init__(self, parent):
        """
        @requires: parent — объект, содержащий методы навигации (show_login, show_register, show_main)
        @modifies: self (создаются и настраиваются элементы интерфейса)
        @effects: Инициализирует страницу и привязывает кнопки к методам навигации родительского окна
        @raises: None
        """
        super().__init__()
        self.parent = parent

        layout = QVBoxLayout()

        # Верхний отступ
        layout.addStretch(1)

        # Приветствие
        label = QLabel("Добро пожаловать,\nв приложение «Фермерские рынки!»")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(label)

        # Отступ
        layout.addSpacing(20)

        # Кнопки
        btn_login = QPushButton("Авторизация в приложении")
        btn_login.clicked.connect(self.parent.show_login)

        btn_register = QPushButton("Регистрация в приложении")
        btn_register.clicked.connect(self.parent.show_register)

        btn_view = QPushButton("Продолжить как гость")
        btn_view.clicked.connect(self.parent.show_main)

        layout.addWidget(btn_login)
        layout.addWidget(btn_register)
        layout.addWidget(btn_view)

        # Нижний отступ
        layout.addStretch(1)

        self.setLayout(layout)


class LoginPage(QWidget):
    """
    Страница авторизации пользователя.

    @requires: parent — экземпляр AppWindow с методом show_start
    @modifies: UI компоненты страницы
    @effects: Отображает форму авторизации (логин/пароль) и кнопки входа и возврата
    @raises: None
    """
    def __init__(self, parent):
        """
        @requires: parent — объект, содержащий метод show_start и логику навигации
        @modifies: self (создаются элементы интерфейса: поля ввода и кнопки)
        @effects: Инициализирует страницу авторизации и настраивает обработчики кнопок
        @raises: None
        """
        super().__init__()
        self.parent = parent

        layout = QVBoxLayout()

        title = QLabel("Авторизация")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 15px;
            """)

        layout.addWidget(title)

        self.user = QLineEdit()
        self.user.setPlaceholderText("Username")
        layout.addWidget(self.user)

        self.pwd = QLineEdit()
        self.pwd.setPlaceholderText("Password")
        self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pwd)

        btn_login = QPushButton("Войти")
        btn_login.clicked.connect(self.login)
        layout.addWidget(btn_login)

        btn_back = QPushButton("Назад")
        btn_back.clicked.connect(self.parent.show_start)
        layout.addWidget(btn_back)

        self.setLayout(layout)

    def login(self):
        """
        @requires: Поля username и password заполнены пользователем
        @modifies: current_user, интерфейс приложения
        @effects: Выполняет авторизацию и открывает главное окно при успехе
        @raises: None (ошибки отображаются через QMessageBox)
        """
        ok, res = login_user(self.user.text(), self.pwd.text())
        if ok:
            current_user["username"] = res.get("username")
            current_user["role"] = res.get("role", "user")
            self.parent.show_main()
        else:
            QMessageBox.critical(self, "Ошибка", res)


class RegisterPage(QWidget):
    """
    Страница регистрации нового пользователя.

    @requires: parent — экземпляр AppWindow с методом show_start
    @modifies: UI компоненты страницы, таблицу users в БД через метод register
    @effects: Создаёт форму регистрации с полями: логин, пароль, имя, фамилия, отчество, и кнопки "Зарегистрироваться" и "Назад"
    @raises: None
    """
    def __init__(self, parent):
        """
        @requires: parent — объект, содержащий метод show_start и логику навигации
        @modifies: self (создаются элементы интерфейса: поля ввода и кнопки)
        @effects: Инициализирует страницу регистрации и настраивает обработчики кнопок
        @raises: None
        """
        super().__init__()
        self.parent = parent

        layout = QVBoxLayout()

        title = QLabel("Регистрация")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 15px;
            """)

        layout.addWidget(title)

        # Логин
        layout.addWidget(QLabel("Логин (не менее 2 символов)"))
        self.user = QLineEdit()
        self.user.setPlaceholderText("Введите логин")
        layout.addWidget(self.user)

        # Пароль
        layout.addWidget(QLabel("Пароль (не менее 4 символов)"))
        self.pwd = QLineEdit()
        self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd.setPlaceholderText("Введите пароль")
        layout.addWidget(self.pwd)

        # Имя
        layout.addWidget(QLabel("Имя"))
        self.first = QLineEdit()
        self.first.setPlaceholderText("обязательно")
        layout.addWidget(self.first)

        # Фамилия
        layout.addWidget(QLabel("Фамилия"))
        self.last = QLineEdit()
        self.last.setPlaceholderText("обязательно")
        layout.addWidget(self.last)

        # Отчество
        layout.addWidget(QLabel("Отчество (необязательно)"))
        self.middle = QLineEdit()
        self.middle.setPlaceholderText("при наличии")
        layout.addWidget(self.middle)

        btn_create = QPushButton("Зарегистрироваться")
        btn_create.clicked.connect(self.register)
        layout.addWidget(btn_create)

        btn_back = QPushButton("Назад")
        btn_back.clicked.connect(self.parent.show_start)
        layout.addWidget(btn_back)

        self.setLayout(layout)

    def register(self):
        """
        @requires: Поля регистрации заполнены пользователем
        @modifies: БД (users), интерфейс приложения
        @effects: Проверяет поля, создаёт пользователя. Выводит сообщения об ошибках
                  через QMessageBox. При успешной регистрации возвращает на стартовую страницу
        @raises: None
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


