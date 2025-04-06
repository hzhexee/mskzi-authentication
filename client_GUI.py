import sys
import os
import socket
import hashlib
import time
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QLineEdit, QPushButton,
                            QTextEdit, QFileDialog, QMessageBox, QFrame,
                            QRadioButton, QGroupBox, QProgressBar, QButtonGroup)
from PyQt6.QtCore import Qt, QDir, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon

class ClientGUI(QMainWindow):
    # Сигналы для обновления GUI из других потоков
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    connection_status_signal = pyqtSignal(bool, str)
    auth_status_signal = pyqtSignal(bool, str)
    file_sent_signal = pyqtSignal(bool, str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Клиент аутентификации")
        self.resize(800, 600)
        self.setMinimumSize(700, 500)
        
        # Переменные состояния
        self.client_socket = None
        self.connected = False
        self.authenticated = False
        
        # Настройка темной темы
        self.apply_dark_theme()
        
        # Создание основного виджета и компоновки
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Создание элементов GUI
        self.create_connection_frame(main_layout)
        self.create_auth_frame(main_layout)
        self.create_file_frame(main_layout)
        self.create_log_frame(main_layout)
        
        # Подключаем сигналы
        self.log_signal.connect(self.append_log)
        self.progress_signal.connect(self.update_progress)
        self.connection_status_signal.connect(self.update_connection_status)
        self.auth_status_signal.connect(self.update_auth_status)
        self.file_sent_signal.connect(self.update_file_status)
        
        # Вывод начального сообщения
        self.log("Клиент аутентификации инициализирован")
    
    def apply_dark_theme(self):
        """Применяет темную тему к приложению"""
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        
        self.setPalette(dark_palette)
        
        # Установка стилей для элементов интерфейса
        style = """
        QMainWindow {
            background-color: #2D2D30;
        }
        QLabel {
            color: #FFFFFF;
        }
        QPushButton {
            background-color: #3A3A3A;
            color: #FFFFFF;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 5px;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QPushButton:pressed {
            background-color: #252525;
        }
        QTextEdit {
            background-color: #252526;
            color: #DCDCDC;
            border: 1px solid #3F3F46;
        }
        QLineEdit {
            background-color: #2D2D30;
            color: #FFFFFF;
            border: 1px solid #3F3F46;
            border-radius: 3px;
            padding: 3px;
        }
        QFrame {
            background-color: #333337;
            border: 1px solid #3F3F46;
            border-radius: 4px;
        }
        QRadioButton {
            color: #FFFFFF;
            spacing: 5px;
        }
        QRadioButton::indicator {
            width: 13px;
            height: 13px;
        }
        QRadioButton::indicator:checked {
            background-color: #4CAF50;
            border: 2px solid #FFFFFF;
            border-radius: 7px;
        }
        QGroupBox {
            border: 1px solid #3F3F46;
            border-radius: 4px;
            margin-top: 10px;
            color: #FFFFFF;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QProgressBar {
            border: 1px solid #3F3F46;
            border-radius: 4px;
            text-align: center;
            background-color: #252526;
            color: #FFFFFF;
        }
        QProgressBar::chunk {
            background-color: #2196F3;
            width: 20px;
        }
        """
        self.setStyleSheet(style)
    
    def create_connection_frame(self, main_layout):
        """Создает блок для настройки соединения с сервером"""
        connection_frame = QFrame()
        connection_layout = QVBoxLayout(connection_frame)
        connection_layout.setSpacing(10)
        connection_layout.setContentsMargins(10, 10, 10, 10)
        
        title_label = QLabel("Соединение с сервером")
        title_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        connection_layout.addWidget(title_label)
        
        # Настройки соединения (IP и Порт)
        conn_widget = QWidget()
        conn_layout = QHBoxLayout(conn_widget)
        conn_layout.setContentsMargins(0, 0, 0, 0)
        
        conn_layout.addWidget(QLabel("Адрес сервера:"))
        self.server_ip = QLineEdit("127.0.0.1")
        conn_layout.addWidget(self.server_ip)
        
        conn_layout.addWidget(QLabel("Порт:"))
        self.server_port = QLineEdit("8080")
        self.server_port.setFixedWidth(60)
        conn_layout.addWidget(self.server_port)
        
        # Кнопки подключения
        self.connect_button = QPushButton("Подключиться")
        self.connect_button.clicked.connect(self.connect_to_server)
        self.connect_button.setMinimumSize(120, 30)
        conn_layout.addWidget(self.connect_button)
        
        self.disconnect_button = QPushButton("Отключиться")
        self.disconnect_button.clicked.connect(self.disconnect_from_server)
        self.disconnect_button.setMinimumSize(120, 30)
        self.disconnect_button.setEnabled(False)
        conn_layout.addWidget(self.disconnect_button)
        
        connection_layout.addWidget(conn_widget)
        
        # Статус соединения
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        status_layout.addWidget(QLabel("Статус:"))
        self.conn_status_label = QLabel("Не подключено")
        self.conn_status_label.setStyleSheet("QLabel { color: #F44336; font-weight: bold; }")
        status_layout.addWidget(self.conn_status_label)
        
        status_layout.addStretch()
        connection_layout.addWidget(status_widget)
        
        main_layout.addWidget(connection_frame)
    
    def create_auth_frame(self, main_layout):
        """Создает блок для настройки аутентификации"""
        auth_frame = QFrame()
        auth_layout = QVBoxLayout(auth_frame)
        auth_layout.setSpacing(10)
        auth_layout.setContentsMargins(10, 10, 10, 10)
        
        title_label = QLabel("Настройки аутентификации")
        title_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        auth_layout.addWidget(title_label)
        
        # Блок выбора протокола
        protocol_group = QGroupBox("Выберите протокол аутентификации")
        protocol_layout = QVBoxLayout(protocol_group)
        
        self.protocol_group = QButtonGroup(self)
        
        self.pap_radio = QRadioButton("PAP (Password Authentication Protocol)")
        self.pap_radio.setChecked(True)
        self.protocol_group.addButton(self.pap_radio, 1)
        protocol_layout.addWidget(self.pap_radio)
        
        self.chap_radio = QRadioButton("CHAP (Challenge-Handshake Authentication Protocol)")
        self.protocol_group.addButton(self.chap_radio, 2)
        protocol_layout.addWidget(self.chap_radio)
        
        self.skey_radio = QRadioButton("S/KEY (One-Time Password)")
        self.protocol_group.addButton(self.skey_radio, 3)
        protocol_layout.addWidget(self.skey_radio)
        
        auth_layout.addWidget(protocol_group)
        
        # Блок учетных данных
        creds_widget = QWidget()
        creds_layout = QVBoxLayout(creds_widget)
        creds_layout.setContentsMargins(0, 0, 0, 0)
        
        # Строка для имени пользователя
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("Имя пользователя:"))
        self.username_input = QLineEdit()
        username_layout.addWidget(self.username_input)
        creds_layout.addLayout(username_layout)
        
        # Строка для пароля
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Пароль:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.password_input)
        creds_layout.addLayout(password_layout)
        
        # Строка для seed (только для S/KEY)
        seed_layout = QHBoxLayout()
        seed_layout.addWidget(QLabel("Seed (для S/KEY):"))
        self.seed_input = QLineEdit()
        seed_layout.addWidget(self.seed_input)
        creds_layout.addLayout(seed_layout)
        
        auth_layout.addWidget(creds_widget)
        
        # Кнопка аутентификации
        auth_button_layout = QHBoxLayout()
        self.auth_button = QPushButton("Аутентифицироваться")
        self.auth_button.clicked.connect(self.authenticate)
        self.auth_button.setMinimumSize(180, 40)
        self.auth_button.setStyleSheet("QPushButton { background-color: #2E7D32; }")
        self.auth_button.setEnabled(False)  # Изначально не активна
        auth_button_layout.addWidget(self.auth_button)
        
        # Статус аутентификации
        self.auth_status_label = QLabel("Ожидание аутентификации")
        self.auth_status_label.setStyleSheet("QLabel { color: #FFC107; font-weight: bold; }")
        auth_button_layout.addWidget(self.auth_status_label)
        
        auth_button_layout.addStretch()
        auth_layout.addLayout(auth_button_layout)
        
        main_layout.addWidget(auth_frame)
    
    def create_file_frame(self, main_layout):
        """Создает блок для отправки файла"""
        file_frame = QFrame()
        file_layout = QVBoxLayout(file_frame)
        file_layout.setSpacing(10)
        file_layout.setContentsMargins(10, 10, 10, 10)
        
        title_label = QLabel("Отправка файла")
        title_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        file_layout.addWidget(title_label)
        
        # Выбор файла
        file_select_widget = QWidget()
        file_select_layout = QHBoxLayout(file_select_widget)
        file_select_layout.setContentsMargins(0, 0, 0, 0)
        
        file_select_layout.addWidget(QLabel("Путь к файлу:"))
        self.file_path = QLineEdit()
        file_select_layout.addWidget(self.file_path)
        
        browse_button = QPushButton("Обзор")
        browse_button.clicked.connect(self.browse_file)
        browse_button.setFixedWidth(80)
        file_select_layout.addWidget(browse_button)
        
        file_layout.addWidget(file_select_widget)
        
        # Кнопка отправки и статус
        send_widget = QWidget()
        send_layout = QHBoxLayout(send_widget)
        send_layout.setContentsMargins(0, 0, 0, 0)
        
        self.send_button = QPushButton("Отправить файл")
        self.send_button.clicked.connect(self.send_file)
        self.send_button.setMinimumSize(150, 40)
        self.send_button.setEnabled(False)  # Изначально не активна
        send_layout.addWidget(self.send_button)
        
        self.file_status_label = QLabel("Файл не отправлен")
        self.file_status_label.setStyleSheet("QLabel { color: #9E9E9E; font-weight: bold; }")
        send_layout.addWidget(self.file_status_label)
        
        send_layout.addStretch()
        file_layout.addWidget(send_widget)
        
        # Прогресс отправки
        progress_layout = QVBoxLayout()
        progress_layout.addWidget(QLabel("Прогресс отправки:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        file_layout.addLayout(progress_layout)
        
        main_layout.addWidget(file_frame)
    
    def create_log_frame(self, main_layout):
        """Создает виджет с логами клиента"""
        log_frame = QFrame()
        log_layout = QVBoxLayout(log_frame)
        log_layout.setSpacing(5)
        log_layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок
        log_layout.addWidget(QLabel("Логи клиента:"))
        
        # Окно логов
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        log_font = QFont("Consolas", 10)
        self.log_area.setFont(log_font)
        self.log_area.setMaximumHeight(150)
        log_layout.addWidget(self.log_area)
        
        # Кнопка очистки логов
        clear_button = QPushButton("Очистить логи")
        clear_button.clicked.connect(self.clear_logs)
        clear_button.setFixedWidth(150)
        clear_layout = QHBoxLayout()
        clear_layout.addStretch()
        clear_layout.addWidget(clear_button)
        log_layout.addLayout(clear_layout)
        
        main_layout.addWidget(log_frame)
    
    def log(self, message):
        """Добавляет сообщение в лог"""
        self.log_signal.emit(message)
    
    def append_log(self, message):
        """Метод, который добавляет сообщения в лог (вызывается через сигнал)"""
        import datetime
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_message = f"{timestamp} {message}"
        self.log_area.append(log_message)
        
        # Прокручиваем вниз для отображения новых сообщений
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_logs(self):
        """Очищает содержимое лог-окна"""
        self.log_area.clear()
        self.log("Логи очищены")
    
    def browse_file(self):
        """Открывает диалог выбора файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл для отправки", "", "Все файлы (*.*)"
        )
        
        if file_path:
            self.file_path.setText(file_path)
            self.log(f"Выбран файл: {file_path}")
            
            # Если пользователь аутентифицирован, разрешаем отправку
            self.send_button.setEnabled(self.authenticated)
    
    def connect_to_server(self):
        """Подключается к серверу"""
        if self.connected:
            self.log("Соединение уже установлено")
            return
            
        try:
            # Получаем IP и порт
            ip = self.server_ip.text()
            try:
                port = int(self.server_port.text())
                if port < 1024 or port > 65535:
                    raise ValueError("Порт должен быть в диапазоне 1024-65535")
            except ValueError as e:
                self.log(f"Ошибка: {str(e)}")
                QMessageBox.critical(self, "Ошибка", f"Неверный порт: {str(e)}")
                return
            
            # Создаем сокет и подключаемся
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5.0)  # 5 секунд для подключения
            self.client_socket.connect((ip, port))
            
            # Обновляем статус
            self.connected = True
            self.connection_status_signal.emit(True, f"Подключено к {ip}:{port}")
            self.log(f"Успешное подключение к серверу {ip}:{port}")
            
            # Активируем кнопки
            self.auth_button.setEnabled(True)
            
        except Exception as e:
            self.log(f"Ошибка подключения: {str(e)}")
            QMessageBox.critical(self, "Ошибка подключения", f"Не удалось подключиться к серверу: {str(e)}")
    
    def disconnect_from_server(self):
        """Отключается от сервера"""
        if not self.connected:
            return
            
        try:
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
            
            # Обновляем статус
            self.connected = False
            self.authenticated = False
            self.connection_status_signal.emit(False, "Не подключено")
            self.auth_status_signal.emit(False, "Ожидание аутентификации")
            self.log("Отключено от сервера")
            
            # Деактивируем кнопки
            self.auth_button.setEnabled(False)
            self.send_button.setEnabled(False)
            
        except Exception as e:
            self.log(f"Ошибка при отключении: {str(e)}")
    
    def authenticate(self):
        """Выполняет аутентификацию на сервере"""
        if not self.connected:
            self.log("Невозможно выполнить аутентификацию: не подключено к серверу")
            return
            
        # Получаем данные
        username = self.username_input.text()
        password = self.password_input.text()
        protocol = self.protocol_group.checkedId()
        seed = self.seed_input.text()
        
        if not username:
            QMessageBox.warning(self, "Предупреждение", "Введите имя пользователя")
            return
            
        if not password:
            QMessageBox.warning(self, "Предупреждение", "Введите пароль")
            return
            
        if protocol == 3 and not seed:
            QMessageBox.warning(self, "Предупреждение", "Для S/KEY необходимо указать seed")
            return
        
        # Запускаем процесс аутентификации в отдельном потоке
        auth_thread = threading.Thread(
            target=self.authentication_process,
            args=(protocol, username, password, seed)
        )
        auth_thread.daemon = True
        auth_thread.start()
    
    def authentication_process(self, protocol, username, password, seed):
        """Процесс аутентификации в отдельном потоке"""
        try:
            self.log(f"Начало аутентификации с использованием протокола {protocol}")
            
            # Отправляем выбранный протокол
            self.client_socket.send(str(protocol).encode())
            time.sleep(0.1)
            self.log(f"Выбран протокол: {protocol}")
            
            # Аутентификация с использованием выбранного протокола
            if protocol == 1:  # PAP
                # Отправляем логин и пароль серверу
                self.client_socket.send(username.encode())
                time.sleep(0.1)
                self.client_socket.send(password.encode())
                
                self.log("Данные аутентификации PAP отправлены серверу")
                
            elif protocol == 2:  # CHAP
                # Отправляем только логин
                self.client_socket.send(username.encode())
                self.log(f"Отправлено имя пользователя: {username}")
                
                # Получаем случайный challenge от сервера
                challenge = self.client_socket.recv(1024)
                self.log(f"Получен challenge: {challenge.hex()}")
                
                # Вычисляем хеш MD5(challenge + password)
                m = hashlib.md5()
                m.update(challenge + password.encode())
                response = m.digest()
                
                # Отправляем ответ
                self.client_socket.send(response)
                self.log(f"Отправлен ответ CHAP: {response.hex()}")
                
            elif protocol == 3:  # S/KEY
                # Отправляем логин
                self.client_socket.send(username.encode())
                
                # Получаем текущее значение счетчика
                count = int(self.client_socket.recv(1024).decode())
                self.log(f"Счетчик запросов S/KEY: {count}")
                
                # Вычисляем одноразовый пароль путем последовательного хеширования
                # MD5(seed + secret + count)
                combined = (seed + password).encode()
                result = combined
                
                for _ in range(count):
                    h = hashlib.md5()
                    h.update(result)
                    result = h.digest()
                
                # Отправляем одноразовый пароль
                self.client_socket.send(result)
                self.log(f"Отправлен одноразовый пароль для счетчика {count}")
            
            # Получаем ответ
            result = self.client_socket.recv(1024).decode()
            self.log(f"Ответ от сервера: {result}")
            
            # Если аутентификация успешна
            if result == "AUTH_SUCCESS":
                self.authenticated = True
                self.auth_status_signal.emit(True, "Аутентификация успешна")
                
                # Активируем кнопку отправки файла, если выбран файл
                if self.file_path.text():
                    self.send_button.setEnabled(True)
            else:
                self.authenticated = False
                self.auth_status_signal.emit(False, "Аутентификация не удалась")
                
        except Exception as e:
            self.log(f"Ошибка аутентификации: {str(e)}")
            self.auth_status_signal.emit(False, f"Ошибка: {str(e)}")
    
    def send_file(self):
        """Отправляет файл на сервер"""
        if not self.authenticated:
            self.log("Невозможно отправить файл: не аутентифицирован")
            return
            
        file_path = self.file_path.text()
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Предупреждение", "Выберите существующий файл для отправки")
            return
            
        # Запускаем отправку файла в отдельном потоке
        send_thread = threading.Thread(target=self.file_sending_process, args=(file_path,))
        send_thread.daemon = True
        send_thread.start()
    
    def file_sending_process(self, file_path):
        """Процесс отправки файла в отдельном потоке"""
        try:
            self.log(f"Начало отправки файла: {file_path}")
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Отправляем имя файла
            self.client_socket.send(f"FILENAME:{file_name}".encode())
            self.log(f"Отправлено имя файла: {file_name}")
            time.sleep(0.5)  # Небольшая пауза
            
            # Отправляем размер файла
            self.client_socket.send(f"FILESIZE:{file_size}".encode())
            self.log(f"Отправлен размер файла: {file_size} байт")
            time.sleep(0.5)  # Небольшая пауза
            
            # Получаем подтверждение готовности
            self.log("Ожидание сигнала готовности от сервера...")
            ready = self.client_socket.recv(1024).decode().strip()
            self.log(f"Получен ответ от сервера: '{ready}'")
            
            if ready != "READY":
                self.log("Ошибка: сервер не готов к приему файла")
                self.file_sent_signal.emit(False, "Ошибка: сервер не готов")
                return
                
            # Отправляем содержимое файла
            bytes_sent = 0
            chunk_size = 8192
            
            with open(file_path, 'rb') as f:
                while bytes_sent < file_size:
                    # Читаем порцию файла
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                        
                    # Отправляем данные
                    self.client_socket.send(chunk)
                    bytes_sent += len(chunk)
                    
                    # Обновляем прогресс
                    progress = int((bytes_sent * 100) / file_size)
                    self.progress_signal.emit(progress)
                    
                    # Логируем каждые 20%
                    if progress % 20 == 0:
                        self.log(f"Прогресс отправки: {progress}%")
            
            # Получаем подтверждение о получении файла
            confirmation = self.client_socket.recv(1024).decode()
            self.log(f"Ответ сервера: {confirmation}")
            
            if "FILE_RECEIVED" in confirmation:
                self.log(f"Файл {file_name} успешно отправлен")
                self.file_sent_signal.emit(True, "Файл отправлен успешно")
            else:
                self.log(f"Проблема при отправке файла: {confirmation}")
                self.file_sent_signal.emit(False, f"Проблема: {confirmation}")
                
        except Exception as e:
            self.log(f"Ошибка при отправке файла: {str(e)}")
            self.file_sent_signal.emit(False, f"Ошибка: {str(e)}")
    
    def update_progress(self, value):
        """Обновляет прогресс-бар (вызывается через сигнал)"""
        self.progress_bar.setValue(value)
    
    def update_connection_status(self, connected, message):
        """Обновляет статус соединения (вызывается через сигнал)"""
        if connected:
            self.conn_status_label.setText(message)
            self.conn_status_label.setStyleSheet("QLabel { color: #4CAF50; font-weight: bold; }")
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
        else:
            self.conn_status_label.setText(message)
            self.conn_status_label.setStyleSheet("QLabel { color: #F44336; font-weight: bold; }")
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
    
    def update_auth_status(self, authenticated, message):
        """Обновляет статус аутентификации (вызывается через сигнал)"""
        if authenticated:
            self.auth_status_label.setText(message)
            self.auth_status_label.setStyleSheet("QLabel { color: #4CAF50; font-weight: bold; }")
            # Разрешаем отправку файла, если файл выбран
            if self.file_path.text():
                self.send_button.setEnabled(True)
        else:
            self.auth_status_label.setText(message)
            self.auth_status_label.setStyleSheet("QLabel { color: #F44336; font-weight: bold; }")
            self.send_button.setEnabled(False)
    
    def update_file_status(self, success, message):
        """Обновляет статус отправки файла (вызывается через сигнал)"""
        if success:
            self.file_status_label.setText(message)
            self.file_status_label.setStyleSheet("QLabel { color: #4CAF50; font-weight: bold; }")
        else:
            self.file_status_label.setText(message)
            self.file_status_label.setStyleSheet("QLabel { color: #F44336; font-weight: bold; }")

def main():
    app = QApplication(sys.argv)
    
    # Установка темной темы для всего приложения
    app.setStyle("Fusion")
    
    window = ClientGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
