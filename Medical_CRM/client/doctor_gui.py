import sys
import tempfile
import os
import threading
from api_client import APIClient
import webbrowser
from functools import partial
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QCheckBox,
    QLabel, QLineEdit, QTextEdit, QMessageBox, QComboBox,
    QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QHeaderView, QHBoxLayout, QFileDialog, QDateEdit, QSizePolicy
)


# Глобальные стили интерфейса (единый дизайн приложения)
def get_global_style():
    """
    @requires:
        - Ничего

    @modifies:
        - Ничего

    @effects:
        - Возвращает CSS-стили для всего приложения

    @raises:
        - Ничего

    @returns:
        - str (stylesheet для PyQt)
    """

    return """
    /* === ОСНОВА === */
    QWidget {
        background-color: #f5f7fa;
        font-family: Segoe UI, Arial;
        font-size: 13px;
        color: #2c3e50;
    }

    /* === LABEL === */
    QLabel {
        font-size: 13px;
    }

    /* === INPUT === */
    QLineEdit, QTextEdit, QComboBox {
        background-color: white;
        border: 1px solid #dcdfe6;
        border-radius: 8px;
        padding: 6px 8px;
    }

    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
        border: 1px solid #4CAF50;
    }

    /* === BUTTON BASE === */
    QPushButton {
        background-color: rgba(76, 175, 80, 0.95);
        color: white;
        border-radius: 0px;
        padding: 0px 0px;
        font-weight: 500;
        border: none;
    }

    QPushButton:hover {
        background-color: rgba(56, 142, 60, 1);
    }

    QPushButton:pressed {
        background-color: rgba(46, 125, 50, 1);
    }

    QPushButton:disabled {
        background-color: #cfcfcf;
        color: #777;
    }

    /* === SECONDARY BUTTON === */
    QPushButton[variant="secondary"] {
        background-color: #e4e7ed;
        color: #333;
    }

    QPushButton[variant="secondary"]:hover {
        background-color: #d5d8de;
    }

    /* === ICON BUTTON === */
    QPushButton[variant="icon"] {
        background-color: transparent;
        font-size: 16px;
        padding: 4px;
    }

    QPushButton[variant="icon"]:hover {
        background-color: #eaeaea;
        border-radius: 6px;
    }

    /* === TABLE === */
    QTableWidget {
        background-color: white;
        border: 1px solid #ebeef5;
        border-radius: 10px;
        gridline-color: #f0f0f0;
        selection-background-color: #e8f5e9;
    }

    QHeaderView::section {
        background-color: #f5f7fa;
        border: none;
        padding: 6px;
        font-weight: 600;
    }

    QTableWidget::item {
        padding: 6px;
    }

    /* === SCROLL === */
    QScrollBar:vertical {
        border: none;
        background: #f0f0f0;
        width: 8px;
        margin: 2px;
    }

    QScrollBar::handle:vertical {
        background: #c1c1c1;
        border-radius: 4px;
    }

    QScrollBar::handle:vertical:hover {
        background: #a8a8a8;
    }

    
    /* === QDateEdit === */
    QLineEdit, QTextEdit, QComboBox, QDateEdit {
        background-color: white;
        border: 1px solid #dcdfe6;
        border-radius: 8px;
        padding: 6px 8px;
        min-height: 20px;
    }

    QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {
        border: 1px solid #4CAF50;
    }

    /* Стилизация календаря */
    QDateEdit::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 28px;
        border-left: 1px solid #dcdfe6;
    }

    QDateEdit::down-arrow {
        image: none;
    }

    QDateEdit::drop-down:enabled {
        color: #555;
    }

    CalendarWidget QWidget {
    alternate-background-color: #f5f7fa;
    }

    QCalendarWidget QAbstractItemView:disabled {
        color: #b0b0b0;
    }

    QCalendarWidget QAbstractItemView {
        selection-background-color: #4CAF50;
        selection-color: white;
    }
    """


# Универсальная функция создания кнопок с параметрами (стиль, размер, обработчик)
def create_button(text, *, variant=None, height=32, width=None, on_click=None):
    """
    @requires:
        - text — строка
        - on_click — callable или None

    @modifies:
        - Создает QPushButton

    @effects:
        - Применяет стиль, размер и обработчик клика

    @raises:
        - Exception при некорректном обработчике

    @returns:
        - QPushButton
    """

    btn = QPushButton(text)

    if variant:
        btn.setProperty("variant", variant)

    btn.setMinimumHeight(height)

    if width:
        btn.setMaximumWidth(width)

    if on_click:
        btn.clicked.connect(lambda checked=False: on_click())

    return btn


# Диалог авторизации и регистрации пользователя (врач)
class AuthDialog(QDialog):
    def __init__(self, client: APIClient, parent=None):
        super().__init__(parent)
        self.client = client

        self.setWindowTitle("Авторизация")
        self.setMinimumWidth(340)
        self.setMinimumHeight(260)
        self.resize(340, 260)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Логин или Email")
        self.username.setMinimumHeight(32)
        
        self.password = QLineEdit()
        self.password.setPlaceholderText("Пароль")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.password.setMinimumHeight(32)

        self.login_btn = create_button("Войти", on_click=self.login)

        self.register_btn = create_button(
            "Регистрация",
            variant="secondary",
            on_click=self.toggle_register
        )

        # блок регистрации (изначально скрыт)
        self.reg_widget = QWidget()
        reg_layout = QFormLayout()
        reg_layout.setSpacing(10)
        reg_layout.setContentsMargins(0, 10, 0, 0)
        reg_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        reg_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.reg_username = QLineEdit()
        reg_layout.addRow("Логин:", self.reg_username)

        self.reg_first = QLineEdit()
        self.reg_last = QLineEdit()
        self.reg_email = QLineEdit()
        self.reg_password = QLineEdit()
        self.reg_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_spec = QComboBox()
        self.reg_spec.setMinimumHeight(32)
        self.load_specialties()

        reg_layout.addRow("Имя:", self.reg_first)
        reg_layout.addRow("Фамилия:", self.reg_last)
        reg_layout.addRow("Email:", self.reg_email)
        reg_layout.addRow("Пароль:", self.reg_password)
        reg_layout.addRow("Специальность:", self.reg_spec)


        for field in [
        self.reg_username,
        self.reg_first,
        self.reg_last,
        self.reg_email,
        self.reg_password
        ]:
            field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            field.setMinimumHeight(32)


        self.submit_reg = create_button(
            "Создать аккаунт",
            height=34,
            on_click=self.register
        )

        reg_layout.addRow(self.submit_reg)

        self.reg_widget.setLayout(reg_layout)
        self.reg_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.reg_widget.hide()

        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(self.login_btn)
        layout.addWidget(self.register_btn)
        layout.addWidget(self.reg_widget)

        self.setLayout(layout)     


# Загрузка списка медицинских специальностей в форму регистрации
    def load_specialties(self):
        """
        @requires:
            - API доступен
            - endpoint specialties работает

        @modifies:
            - self.reg_spec (QComboBox)

        @effects:
            - Загружает список специальностей в форму

        @raises:
            - Показывает QMessageBox при ошибке

        @returns:
            - None
        """

        try:
            specs = self.client.get_specialties_for_ui()

            self.reg_spec.clear()

            for name, sid in specs:
                self.reg_spec.addItem(name, sid)

        except Exception as e:
            self.reg_spec.clear()
            self.reg_spec.addItem("Ошибка загрузки", None)
            QMessageBox.critical(self, "Ошибка.", f"Не удалось загрузить специальности: {e}")


# Переключение отображения формы регистрации
    def toggle_register(self):
        """
        @requires:
            - self.reg_widget существует

        @modifies:
            - Видимость формы регистрации
            - Размер окна

        @effects:
            - Переключает отображение формы регистрации

        @raises:
            - Ничего

        @returns:
            - None
        """

        visible = not self.reg_widget.isVisible()
        self.reg_widget.setVisible(visible)

        if visible:
            self.resize(340, 520)
        else:
            self.resize(340, 260)

    
# Авторизация пользователя через API
    def login(self):
        """
        @requires:
            - username и password введены

        @modifies:
            - состояние клиента (token, role)
            - состояние диалога

        @effects:
            - Выполняет авторизацию через API
            - Закрывает окно при успехе

        @raises:
            - Показывает QMessageBox при ошибке

        @returns:
            - None
        """


        self.login_btn.setEnabled(False)

        try:
            # скрыть регистрацию если она открыта
            if self.reg_widget.isVisible():
                self.reg_widget.hide()
                self.resize(340, 260)

            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents()

            self.client.login(
                self.username.text(),
                self.password.text()
            )

            self.accept()

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", str(e))

        finally:
            QApplication.restoreOverrideCursor()
            self.login_btn.setEnabled(True)


    # Регистрация нового врача через API
    def register(self):
        """
        @requires:
            - все поля формы заполнены
            - specialty выбран

        @modifies:
            - состояние API (создание пользователя)
            - UI поля формы

        @effects:
            - Регистрирует врача
            - Очищает форму
            - Скрывает блок регистрации

        @raises:
            - Показывает QMessageBox при ошибке

        @returns:
            - None
        """

        if not all([
            self.reg_username.text(),
            self.reg_first.text(),
            self.reg_last.text(),
            self.reg_email.text(),
            self.reg_password.text()
        ]):

            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
            return
        
        if "@" not in self.reg_email.text():
            QMessageBox.warning(self, "Ошибка", "Введите корректный email")
            return


        try:
            role = "doctor"

            self.submit_reg.setEnabled(False)
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents()


            self.client.register(
                username=self.reg_username.text(),
                email=self.reg_email.text(),
                password=self.reg_password.text(),
                role=role,
                first_name=self.reg_first.text(),
                last_name=self.reg_last.text(),
                specialty_id=self.reg_spec.currentData()
            )

            QMessageBox.information(self, "Успех", "Аккаунт создан")

            self.reg_widget.hide()
            self.resize(340, 260)

            self.reg_first.clear()
            self.reg_last.clear()
            self.reg_email.clear()
            self.reg_password.clear()
            self.reg_username.clear()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

        finally:
            QApplication.restoreOverrideCursor()
            self.submit_reg.setEnabled(True)


# Главное окно приложения врача (работа с приемами и файлами)
class DoctorApp(QWidget):
    def __init__(self, client):
        super().__init__()
        self.client = client

        self.setWindowTitle("Doctor CRM")
        self.setGeometry(300, 300, 600, 500)
        self.setMinimumSize(720, 520)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout()  
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        #  Профиль 
        profile_layout = QHBoxLayout()

        self.profile_label = QLabel("Не авторизован")
        self.profile_label.setMinimumHeight(28)

        self.refresh_btn = create_button(
            "Обновить",
            variant="secondary",
            on_click=self.load_appointments
        )
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setMinimumWidth(110)

        self.logout_btn = create_button(
            "Завершить сеанс",
            variant="secondary",
            on_click=self.logout
        )
        self.logout_btn.setMinimumWidth(150)

        profile_layout.addWidget(self.profile_label)
        profile_layout.addStretch()
        profile_layout.addWidget(self.refresh_btn)
        profile_layout.addWidget(self.logout_btn)

        layout.addLayout(profile_layout)

        # таблица
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setMinimumHeight(300)
        self.table.setHorizontalHeaderLabels([
            "ID", "Дата", "Пациент", "Примечание", "Вложения"
        ])
        self.table.horizontalHeaderItem(4).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.verticalHeader().setVisible(False)


        # --- Динамическая ширина колонок ---
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # ID по контенту
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Дата по контенту
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          # Пациент с растяжением поля
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 140)
        # ----------------------------------------

        self.table.cellDoubleClicked.connect(self.open_record_dialog)
        self.table.setEnabled(False)


        layout.addWidget(QLabel("Приемы:"))
        layout.addWidget(self.table)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)

        self.setLayout(layout)

        self.on_login_success()


# Открытие файла во внешнем приложении (через временный файл)
    def open_file(self, file_id, filename):
        try:
            file_data = self.client.download_file_with_name(file_id)
            suffix = os.path.splitext(filename)[-1] or ".tmp"

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_data["content"])
                temp_path = tmp.name



            if sys.platform.startswith("win"):
                os.startfile(temp_path)
            else:
                webbrowser.open(temp_path)



            # Отложенное удаление файла (через 60 секунд)
            def cleanup():
                try:
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except PermissionError:
                            pass
                        except Exception:
                            pass
                except OSError:
                    pass

            timer = threading.Timer(120.0, cleanup)
            timer.daemon = True
            timer.start()

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", str(e))

# Сохранение файла на устройство пользователя
    def save_file(self, file_id, fallback_name):
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents()
            
            file_data = self.client.download_file_with_name(file_id)

            filename = file_data.get("filename") or fallback_name

            save_path, _ = QFileDialog.getSaveFileName(
                self, "Сохранить файл", filename
            )

            if not save_path:
                return

            with open(save_path, "wb") as f:
                f.write(file_data["content"])

            QMessageBox.information(self, "Успех", "Файл сохранен")

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", str(e))

        finally:
            QApplication.restoreOverrideCursor()


# Обработка успешного входа (загрузка профиля и приемов)
    def on_login_success(self):
            """
            @requires:
                - пользователь авторизован
                - API доступен

            @modifies:
                - UI (label, table, кнопки)

            @effects:
                - Загружает профиль
                - Активирует интерфейс
                - Загружает приемы

            @raises:
                - Показывает QMessageBox при ошибке

            @returns:
                - None
            """

            try:
                user_info = self.client.get_me()
                name = f"{user_info.get('last_name', '')} {user_info.get('first_name', '')}"
                self.profile_label.setText(f"Вы вошли в систему как {name}")

                self.table.setEnabled(True)
                self.refresh_btn.setEnabled(True)

                self.load_appointments()

            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))


# Открыть панель админинстратора
    def open_admin_window(self):
        self.admin_window = AdminWindow(self.client)
        self.admin_window.show()


# Выход пользователя из системы и сброс интерфейса
    def logout(self):
        """
        @requires:
            - Ничего

        @modifies:
            - состояние клиента
            - UI

        @effects:
            - Завершает сессию
            - Очищает интерфейс

        @raises:
            - Ничего

        @returns:
            - None
        """

        self.client.logout()

        self.profile_label.setText("Не авторизован")

        self.table.clearContents()
        self.table.setRowCount(0)

        self.refresh_btn.setEnabled(False)
        self.table.setEnabled(False)

        auth = AuthDialog(self.client, self)

        if auth.exec():
            role = getattr(self.client, "role", None)

            if role == "admin":
                self.close()

                self.admin_window = AdminWindow(self.client)
                self.admin_window.show()

            else:
                self.on_login_success()

    
# Загрузка списка приемов врача и отображение в таблице
    def load_appointments(self):
        """
        @requires:
            - пользователь авторизован
            - API доступен

        @modifies:
            - self.table

        @effects:
            - Загружает список приемов
            - Заполняет таблицу
            - Добавляет кнопки файлов

        @raises:
            - Показывает QMessageBox при ошибке

        @returns:
            - None
        """

        try:
            appointments = self.client.get_doctor_appointments()

            self.table.setRowCount(len(appointments))

            for row, app in enumerate(appointments):

                item_id = QTableWidgetItem(str(app["id"]))
                item_id.setData(Qt.ItemDataRole.UserRole, app.get("has_record", False))
                self.table.setItem(row, 0, item_id)

                formatted = app.get("formatted_dt", "-")

                self.table.setItem(row, 1, QTableWidgetItem(formatted))

                self.table.setItem(
                    row, 2,
                    QTableWidgetItem(app.get("patient_name", "—"))
                )

                self.table.setItem(
                    row, 3,
                    QTableWidgetItem(app.get("note") or "")
                )

                # серые если уже есть запись
                if app.get("has_record"):
                    for col in range(4):
                        item = self.table.item(row, col)
                        if item:
                            item.setForeground(QColor("gray"))

 
                files_count = app.get("files_count", 0)

                btn_text = "Файлы" if files_count == 0 else f"Файлы ({files_count})"

                btn = create_button(
                    btn_text,
                    variant="secondary",
                    height=28,
                    on_click=partial(self.open_files, app["id"])
                )

                # отключаем кнопку если файлов нет
                btn.setEnabled(files_count > 0)

                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                btn.setMinimumHeight(0)
                self.table.setCellWidget(row, 4, btn)
                

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    
# Открытие диалога создания медицинской записи по приему
    def open_record_dialog(self, row, column):
        """
        @requires:
            - выбран валидный row
            - запись еще не создана

        @modifies:
            - UI

        @effects:
            - Открывает диалог записи
            - Обновляет таблицу после сохранения

        @raises:
            - Показывает QMessageBox при ошибке

        @returns:
            - None
        """

        if self.table.item(row, 0) is None:
            return

        # если строка уже серая → запись есть
        item = self.table.item(row, 0)
        if item.data(Qt.ItemDataRole.UserRole):
            QMessageBox.information(self, "Инфо", "Запись уже создана")
            return
        
        try:
            appointment_id = int(self.table.item(row, 0).text())

            dialog = RecordDialog(self.client, appointment_id, self)
            dialog.exec()

            self.load_appointments()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    
# Открытие списка файлов, прикрепленных к приему
    def open_files(self, appointment_id):
        """
        @requires:
            - appointment_id валиден

        @modifies:
            - UI (создает диалог)

        @effects:
            - Отображает список файлов
            - Позволяет открыть или скачать файл

        @raises:
            - Показывает QMessageBox при ошибке

        @returns:
            - None
        """

        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents()


            files = self.client.get_files_for_ui(appointment_id)

            if not files:
                QMessageBox.information(self, "Файлы", "Нет файлов")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle("Файлы приема")
            dialog.setMinimumWidth(400)

            layout = QVBoxLayout()
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(8)

            for f in files:
                row = QHBoxLayout()

                label = QLabel(f["name"])
                label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

                btn_open = create_button(
                    "Открыть",
                    variant="secondary",
                    height=28,
                    on_click=partial(self.open_file, f["file_id"], f["name"])
                )

                btn_download = create_button(
                    "Скачать",
                    height=28,
                    on_click=partial(self.save_file, f["file_id"], f["name"])
                )

                row.addWidget(label)
                row.addWidget(btn_open)
                row.addWidget(btn_download)

                layout.addLayout(row)

            dialog.setLayout(layout)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

        finally:
            QApplication.restoreOverrideCursor()


# Диалог заполнения медицинской записи (диагноз, лечение, рекомендации)
class RecordDialog(QDialog):
    def __init__(self, client, appointment_id, parent=None):
        super().__init__(parent)
        self.client = client
        self.appointment_id = appointment_id
        self.setWindowTitle("Результаты приема")
        self.setMinimumWidth(450)
        self.setStyleSheet(get_global_style())

        layout = QFormLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.diagnosis = QLineEdit()
        self.medication = QLineEdit()
        self.recommendations = QTextEdit()
        
        # Настройка даты (как в вебе)
        self.next_date = QDateEdit()
        self.next_date.setButtonSymbols(QDateEdit.ButtonSymbols.UpDownArrows)
        self.next_date.setCalendarPopup(True)
        self.next_date.setDisplayFormat("dd.MM.yyyy")
        self.next_date.setDate(QDate.currentDate())
        self.next_date.setMinimumDate(QDate.currentDate())
        self.next_date.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Настройка времени (шаг 30 мин)
        self.next_time = QComboBox()
        self.next_time.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for hour in range(8, 21):
            for minute in [0, 30]:
                if hour == 20 and minute > 0: break
                self.next_time.addItem(f"{hour:02d}:{minute:02d}")

        self.enable_next_visit = QCheckBox("Назначить повторный прием")
        self.enable_next_visit.setChecked(False)

        # Группировка даты и времени в одну строку
        time_layout = QHBoxLayout()
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(5)
        time_layout.addWidget(self.next_date)
        time_layout.addWidget(self.next_time)

        save_btn = create_button(
            "Сохранить запись",
            height=35,
            on_click=self.save
        )


        layout.addRow("Диагноз:", self.diagnosis)
        layout.addRow("Препараты:", self.medication)
        layout.addRow("Рекомендации:", self.recommendations)
        self.next_visit_row_label = QLabel("След. визит:")
        self.next_visit_container = QWidget()
        self.next_visit_container.setLayout(time_layout)

        layout.addRow(QLabel(""), self.enable_next_visit)
        layout.addRow(self.next_visit_row_label, self.next_visit_container)

        # скрыть по умолчанию
        self.next_visit_row_label.setVisible(False)
        self.next_visit_container.setVisible(False)
        layout.addRow(save_btn)

        self.enable_next_visit.stateChanged.connect(self.toggle_next_visit)

        self.setLayout(layout)


# Включение/отключение блока назначения повторного приема
    def toggle_next_visit(self, state):
        enabled = bool(state)
        self.next_visit_row_label.setVisible(enabled)
        self.next_visit_container.setVisible(enabled)


# Сохранение медицинской записи и (опционально) назначение следующего визита
    def save(self):
        """
        @requires:
            - appointment_id валиден

        @modifies:
            - данные на сервере
            - UI диалога

        @effects:
            - Сохраняет медицинскую запись
            - Опционально создает следующий визит

        @raises:
            - Показывает QMessageBox при ошибке

        @returns:
            - None
        """

        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents()

            next_visit_iso = None

            if self.enable_next_visit.isChecked():
                qdate = self.next_date.date()
                time_str = self.next_time.currentText()
                next_visit_iso = self.client.build_datetime(qdate, time_str)

            result = self.client.create_record(
                appointment_id=self.appointment_id,
                diagnosis=self.diagnosis.text(),
                medication=self.medication.text(),
                recommendations=self.recommendations.toPlainText(),
                next_visit=next_visit_iso
            )

            msg = "Данные сохранены"
            if result.get("next_visit") == "created":
                msg += "\nСледующий прием запланирован"

            elif isinstance(result.get("next_visit"), str) and result["next_visit"].startswith("failed"):
                msg += f"\nПовторный прием не создан: {result['next_visit']}"

            elif result.get("next_visit") == "already_exists":
                msg += "\nПовторный прием уже существует"

            QMessageBox.information(self, "Успешно", msg)
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

        finally:
            QApplication.restoreOverrideCursor()


# Диалог панели администратора
class AdminWindow(QWidget):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowTitle("Панель администратора")
        self.setMinimumWidth(400)
        self.setMinimumSize(600, 500)
        self.setStyleSheet(get_global_style())

        layout = QVBoxLayout()


# --- ВЕРХНЯЯ ПАНЕЛЬ ---
        top_bar = QHBoxLayout()

        self.logout_btn = create_button(
            "Выйти",
            variant="secondary",
            on_click=self.logout
        )

        top_bar.addStretch()
        top_bar.addWidget(self.logout_btn)

        layout.addLayout(top_bar)
        



        del_layout = QFormLayout()
        self.table_combo = QComboBox()
        self.table_combo.addItems([
            "users", "patients", "employees",
            "appointments", "medical_records",
            "specialties", "appointment_files"
        ])
        self.record_id_input = QLineEdit()
        self.record_id_input.setPlaceholderText("ID записи")
        
        del_btn = create_button("Удалить запись из БД", on_click=self.delete_record)
        
        del_layout.addRow("Таблица:", self.table_combo)
        del_layout.addRow("ID:", self.record_id_input)
        del_layout.addRow(del_btn)
        
        file_layout = QFormLayout()
        self.file_id_input = QLineEdit()
        self.file_id_input.setPlaceholderText("ID файла (MongoDB ObjectId)")
        
        file_del_btn = create_button("Удалить файл", on_click=self.delete_file)
        
        file_layout.addRow("File ID:", self.file_id_input)
        file_layout.addRow(file_del_btn)

        layout.addWidget(QLabel("<b>Удаление записей из базы данных</b>"))
        layout.addLayout(del_layout)
        layout.addWidget(QLabel("<hr>"))
        layout.addWidget(QLabel("<b>Управление файлами</b>"))
        layout.addLayout(file_layout)


        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск (ФИО / логин)")

        self.search_btn = create_button("Поиск", on_click=self.search)

        self.results_table = QTableWidget()
        self.results_table.verticalHeader().setDefaultSectionSize(36)
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["ID", "Логин", "Имя", "Роль", ""])
        self.results_table.setEnabled(True)

        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.results_table.setColumnWidth(4, 120)
        


        self.full_delete_checkbox = QCheckBox("Полное удаление")

        layout.addWidget(self.search_input)
        layout.addWidget(self.search_btn)
        layout.addWidget(self.results_table)
        layout.addWidget(self.full_delete_checkbox)

        self.setLayout(layout)


    # Выход из аккаунта
    def logout(self):
            self.client.logout()
            self.close()


# Поиск по пользователям для выполнения действий с ними
    def search(self):
        """
        @requires:
            - введен поисковый запрос

        @modifies:
            - results_table

        @effects:
            - Выполняет поиск пользователей
            - Заполняет таблицу результатов

        @raises:
            - Показывает QMessageBox при ошибке

        @returns:
            - None
        """

        try:
            data = self.client.admin_search(self.search_input.text())

            self.results_table.setRowCount(len(data))

            for row, item in enumerate(data):
                self.results_table.setItem(row, 0, QTableWidgetItem(str(item["id"])))
                self.results_table.setItem(row, 1, QTableWidgetItem(item["username"]))
                name = f"{item.get('last_name') or ''} {item.get('first_name') or ''}".strip()
                self.results_table.setItem(row, 2, QTableWidgetItem(name))
                self.results_table.setItem(row, 3, QTableWidgetItem(item["role"]))

                btn = create_button(
                    "Сброс",
                    height=28,
                    on_click=partial(self.open_reset_dialog, item["id"])
                )

                # стиль для красной кнопки - уникальный
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #d64545;
                        color: white;
                        border-radius: 0px;
                        padding: 0px 0px;
                    }
                    QPushButton:hover {
                        background-color: #b83a3a;
                    }
                """)

            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            btn.setMinimumHeight(0)

            btn.setStyleSheet("""
                QPushButton {
                    background-color: #d64545;
                    color: white;
                    border-radius: 6px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #b83a3a;
                }
            """)

            self.results_table.setCellWidget(row, 4, btn)


        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))


# Вызов окна 
    def open_reset_dialog(self, user_id):
        dialog = QDialog(self)
        dialog.setWindowTitle("Сброс пароля")
        dialog.setMinimumWidth(300)

        layout = QVBoxLayout()

        label = QLabel("Подтвердить сброс пароля?\nПользователь сможет задать новый.")
        layout.addWidget(label)

        confirm_btn = create_button(
            "Сбросить",
            on_click=lambda: self.confirm_reset(user_id, dialog)
        )

        layout.addWidget(confirm_btn)

        dialog.setLayout(layout)
        dialog.exec()

# логика сброса пароля для пользователей
    def confirm_reset(self, user_id, dialog):
        try:
            self.client.admin_reset_password(user_id)

            QMessageBox.information(self, "Успех", "Пароль сброшен")
            dialog.accept()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))


#
    def delete_record(self):
        """
        @requires:
            - выбрана строка
            - корректный ID

        @modifies:
            - данные на сервере

        @effects:
            - Удаляет запись из БД

        @raises:
            - Показывает QMessageBox при ошибке

        @returns:
            - None
        """

        try:
            row = self.results_table.currentRow()
            if row == -1:
                QMessageBox.warning(self, "Ошибка", "Выберите строку")
                return

            rec_id = int(self.results_table.item(row, 0).text())
            table = self.table_combo.currentText()

            if self.full_delete_checkbox.isChecked():
                self.client.admin_delete(table, rec_id, full=True)
            else:
                self.client.admin_delete(table, rec_id)

            QMessageBox.information(self, "Успех", "Удалено")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            


    def delete_file(self):
        """
        @requires:
            - file_id введен

        @modifies:
            - данные на сервере

        @effects:
            - Удаляет файл

        @raises:
            - Показывает QMessageBox при ошибке

        @returns:
            - None
        """

        try:
            file_id = self.file_id_input.text()
            self.client.admin_delete(file_id=file_id)
            QMessageBox.information(self, "Успех", "Файл удален")
            self.file_id_input.clear()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))


# Точка входа: запуск GUI приложения врача

def main():
    """
    @requires:
        - PyQt установлен
        - backend доступен

    @modifies:
        - запускает GUI приложение

    @effects:
        - открывает окно авторизации
        - запускает основной цикл приложения

    @raises:
        - Exception при ошибках запуска

    @returns:
        - None
    """

    app = QApplication(sys.argv)
    app.setStyleSheet(get_global_style())

    client = APIClient()

    while True:
        auth = AuthDialog(client)

        if auth.exec() != QDialog.DialogCode.Accepted:
            break

        role = getattr(client, "role", None)

        if role == "admin":
            window = AdminWindow(client)
        else:
            window = DoctorApp(client)

        window.show()
        app.exec()

    sys.exit()


if __name__ == "__main__":
    main()