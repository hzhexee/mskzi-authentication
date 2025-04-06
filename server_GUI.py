import sys
import os
import socket
import threading
import datetime
import hashlib
import secrets
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QTextEdit, QFileDialog, QMessageBox, QFrame)
from PyQt6.QtCore import Qt, QDir, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette
from server import users, skey_db, skey_lock, handle_client

class ServerGUI(QMainWindow):
    # Сигнал для логирования из других потоков
    log_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Сервер аутентификации")
        self.resize(800, 600)
        self.setMinimumSize(700, 500)
        
        # Переменные состояния
        self.server_running = False
        self.server_socket = None
        self.server_thread = None
        self.save_dir = "received_files"
        
        # Создаем директорию для сохранения файлов, если она не существует
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        
        # Настройка темной темы
        self.apply_dark_theme()
        
        # Создание основного виджета и компоновки
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Создание элементов GUI
        self.create_control_frame(main_layout)
        self.create_log_frame(main_layout)
        
        # Подключаем сигнал логирования
        self.log_signal.connect(self.append_log)
        
        # Вывод начального сообщения
        self.log("Сервер аутентификации инициализирован")
        self.log(f"Текущая директория сохранения: {os.path.abspath(self.save_dir)}")
    
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
        }
        QFrame {
            background-color: #333337;
            border: 1px solid #3F3F46;
            border-radius: 4px;
        }
        """
        self.setStyleSheet(style)
    
    def create_control_frame(self, main_layout):
        """Создает виджет с элементами управления сервером"""
        control_frame = QFrame()
        control_layout = QVBoxLayout(control_frame)
        control_layout.setSpacing(10)
        control_layout.setContentsMargins(10, 10, 10, 10)
        
        # Информация о директории сохранения
        dir_widget = QWidget()
        dir_layout = QHBoxLayout(dir_widget)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        
        dir_label = QLabel("Директория сохранения:")
        dir_layout.addWidget(dir_label)
        
        self.dir_entry = QLineEdit(os.path.abspath(self.save_dir))
        self.dir_entry.setReadOnly(True)
        dir_layout.addWidget(self.dir_entry)
        
        dir_button = QPushButton("Изменить")
        dir_button.clicked.connect(self.select_directory)
        dir_button.setFixedWidth(120)
        dir_layout.addWidget(dir_button)
        
        control_layout.addWidget(dir_widget)
        
        # Кнопки управления сервером
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.start_button = QPushButton("Запустить сервер")
        self.start_button.clicked.connect(self.start_server)
        self.start_button.setStyleSheet("QPushButton { background-color: #2E7D32; }")
        self.start_button.setMinimumSize(150, 50)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Остановить сервер")
        self.stop_button.clicked.connect(self.stop_server)
        self.stop_button.setStyleSheet("QPushButton { background-color: #C62828; }")
        self.stop_button.setEnabled(False)
        self.stop_button.setMinimumSize(150, 50)
        button_layout.addWidget(self.stop_button)
        
        button_layout.addStretch()
        control_layout.addWidget(button_widget)
        
        # Статус сервера
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        status_layout.addWidget(QLabel("Статус сервера:"))
        
        self.status_label = QLabel("Остановлен")
        self.status_label.setStyleSheet("QLabel { color: #F44336; font-weight: bold; }")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        control_layout.addWidget(status_widget)
        
        # Информация о порте
        port_widget = QWidget()
        port_layout = QHBoxLayout(port_widget)
        port_layout.setContentsMargins(0, 0, 0, 0)
        
        port_layout.addWidget(QLabel("Порт:"))
        
        self.port_entry = QLineEdit("8080")
        self.port_entry.setFixedWidth(100)
        port_layout.addWidget(self.port_entry)
        
        port_layout.addStretch()
        control_layout.addWidget(port_widget)
        
        main_layout.addWidget(control_frame)
    
    def create_log_frame(self, main_layout):
        """Создает виджет с логами сервера"""
        log_frame = QFrame()
        log_layout = QVBoxLayout(log_frame)
        log_layout.setSpacing(5)
        log_layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок
        log_layout.addWidget(QLabel("Логи сервера:"))
        
        # Окно логов
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        log_font = QFont("Consolas", 10)
        self.log_area.setFont(log_font)
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
        """Добавляет сообщение в лог с отметкой времени"""
        # Используем сигнал для безопасного обновления GUI из других потоков
        self.log_signal.emit(message)
    
    def append_log(self, message):
        """Метод, который фактически добавляет сообщения в лог (вызывается через сигнал)"""
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
    
    def select_directory(self):
        """Открывает диалог выбора директории для сохранения файлов"""
        if self.server_running:
            QMessageBox.warning(
                self, 
                "Предупреждение", 
                "Невозможно изменить директорию сохранения при запущенном сервере"
            )
            return
            
        new_dir = QFileDialog.getExistingDirectory(
            self, 
            "Выберите директорию сохранения", 
            self.save_dir
        )
        
        if new_dir:
            self.save_dir = new_dir
            self.dir_entry.setText(os.path.abspath(self.save_dir))
            self.log(f"Директория сохранения изменена на: {os.path.abspath(self.save_dir)}")
            
            # Создаем директорию если она не существует
            if not os.path.exists(self.save_dir):
                os.makedirs(self.save_dir)
    
    def start_server(self):
        """Запускает сервер в отдельном потоке"""
        if self.server_running:
            return
            
        try:
            port = int(self.port_entry.text())
            if port < 1024 or port > 65535:
                raise ValueError("Порт должен быть в диапазоне 1024-65535")
                
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind(("0.0.0.0", port))
            self.server_socket.listen(5)
            
            self.server_running = True
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.status_label.setText("Запущен")
            self.status_label.setStyleSheet("QLabel { color: #4CAF50; font-weight: bold; }")
            
            self.log(f"Сервер запущен на порту {port}")
            self.log(f"Ожидание клиентов...")
            
            # Запуск сервера в отдельном потоке
            self.server_thread = threading.Thread(target=self.server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить сервер: {str(e)}")
            self.log(f"Ошибка запуска сервера: {str(e)}")
    
    def server_loop(self):
        """Основной цикл сервера для обработки новых подключений"""
        try:
            while self.server_running:
                try:
                    # Небольшой таймаут для возможности остановки
                    self.server_socket.settimeout(1.0)
                    client_socket, addr = self.server_socket.accept()
                    
                    # Логируем подключение
                    self.log(f"Клиент подключился: {addr}")
                    
                    # Запуск обработчика клиента в отдельном потоке
                    client_thread = threading.Thread(
                        target=self.handle_client_wrapper, 
                        args=(client_socket, addr)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                    self.log(f"Запущен новый поток для клиента {addr}")
                    active_threads = threading.active_count() - 2  # -2 для main и server_loop
                    self.log(f"Активных соединений: {active_threads}")
                    
                except socket.timeout:
                    # Таймаут - нормальная ситуация, продолжаем работу
                    continue
                except OSError as e:
                    # Ошибка операционной системы - возможно, сокет закрыт при остановке сервера
                    if not self.server_running:
                        break
                    self.log(f"Ошибка сокета: {str(e)}")
                except Exception as e:
                    # Другие ошибки
                    if self.server_running:
                        self.log(f"Ошибка в цикле сервера: {str(e)}")
        except Exception as e:
            self.log(f"Критическая ошибка сервера: {str(e)}")
        finally:
            # Закрываем сокет сервера
            if hasattr(self, 'server_socket') and self.server_socket:
                try:
                    self.server_socket.close()
                except:
                    pass
                self.log("Сокет сервера закрыт")
    
    def handle_client_wrapper(self, client_socket, addr):
        """Обертка для функции handle_client для перехвата логов"""
        try:
            # Перенаправляем обработку клиента в функцию из server.py,
            # но передаем директорию сохранения 
            self.custom_handle_client(client_socket, addr, self.save_dir)
        except Exception as e:
            self.log(f"Ошибка при обработке клиента {addr}: {str(e)}")
    
    def custom_handle_client(self, client_socket, addr, save_dir):
        """Модифицированная функция handle_client с перенаправлением вывода в GUI"""
        self.log(f"Обработка клиента: {addr}")

        try:
            # Устанавливаем таймаут для сокета, чтобы избежать зависания
            client_socket.settimeout(30.0)  # 30 секунд таймаут для операций с сокетом
            
            # Получаем выбранный протокол
            protocol_data = client_socket.recv(1024).decode().strip()
            try:
                protocol = int(protocol_data)
                if protocol not in [1, 2, 3]:
                    raise ValueError(f"Недопустимый протокол: {protocol}")
                self.log(f"Клиент {addr} выбрал протокол: {protocol}")
            except ValueError as e:
                self.log(f"Ошибка при получении протокола от {addr}: {e}")
                self.log(f"Полученные данные: '{protocol_data}'")
                client_socket.send(b"ERROR: Invalid protocol")
                client_socket.close()
                return
            
            auth_success = False
            
            if protocol == 1:  # PAP (Password Authentication Protocol)
                # Получаем имя пользователя
                username = client_socket.recv(1024).decode()
                self.log(f"Получено имя пользователя от {addr}: {username}")
                
                # Получаем пароль
                password = client_socket.recv(1024).decode()
                self.log(f"Получен пароль для пользователя {username} от {addr}")
                
                # Проверяем учетные данные
                if username in users and users[username] == password:
                    auth_success = True
                    self.log(f"Пользователь {username} от {addr} успешно аутентифицирован")
                else:
                    self.log(f"Ошибка аутентификации для пользователя {username} от {addr}")
                
            elif protocol == 2:  # CHAP (Challenge-Handshake Authentication Protocol)
                # Получаем имя пользователя
                username = client_socket.recv(1024).decode()
                self.log(f"Получено имя пользователя от {addr}: {username}")
                
                # Генерируем случайный challenge
                challenge = secrets.token_bytes(16)
                client_socket.send(challenge)
                self.log(f"Отправлен challenge клиенту {addr}: {challenge.hex()}")
                
                # Получаем ответ
                response = client_socket.recv(1024)
                self.log(f"Получен ответ от {addr}: {response.hex()}")
                
                # Проверяем ответ
                if username in users:
                    # Вычисляем ожидаемый ответ
                    m = hashlib.md5()
                    m.update(challenge + users[username].encode())
                    expected_response = m.digest()
                    
                    if response == expected_response:
                        auth_success = True
                        self.log(f"Пользователь {username} от {addr} успешно аутентифицирован по CHAP")
                    else:
                        self.log(f"Ошибка аутентификации для пользователя {username} от {addr}: неверный ответ")
                else:
                    self.log(f"Пользователь {username} от {addr} не найден")
                
            elif protocol == 3:  # S/KEY (One-Time Password)
                # Получаем имя пользователя
                username = client_socket.recv(1024).decode()
                self.log(f"Получено имя пользователя от {addr}: {username}")
                
                # Используем блокировку для безопасного доступа к общим данным
                with skey_lock:
                    if username in skey_db:
                        # Отправляем текущее значение счетчика
                        client_socket.send(str(skey_db[username]["count"]).encode())
                        self.log(f"Отправлен счетчик клиенту {addr}: {skey_db[username]['count']}")
                        
                        # Получаем одноразовый пароль
                        otp = client_socket.recv(1024)
                        self.log(f"Получен одноразовый пароль от {addr}: {otp.hex()}")
                        
                        # В реальной системе мы бы проверили хеш против сохраненного предыдущего хеша
                        # Для демонстрации, предположим что хеш верен
                        auth_success = True
                        
                        # Уменьшаем счетчик
                        skey_db[username]["count"] -= 1
                        self.log(f"Обновлен счетчик для {username} от {addr}: {skey_db[username]['count']}")
                    else:
                        self.log(f"Пользователь {username} от {addr} не найден в базе S/KEY")
            
            if auth_success:
                client_socket.send(b"AUTH_SUCCESS")
                self.log(f"Аутентификация клиента {addr} успешна!")
                self.log(f"Ожидание данных файла от {addr}...")

                # Получаем имя файла
                self.log(f"Ожидание имени файла от {addr}...")
                filename_data = client_socket.recv(1024).decode()
                self.log(f"Получены данные: '{filename_data}'")

                if not filename_data.startswith("FILENAME:"):
                    self.log(f"Ошибка от {addr}: неверный формат имени файла")
                    return

                filename = filename_data.replace("FILENAME:", "")
                self.log(f"Распознано имя файла: '{filename}'")

                # Получаем размер файла
                self.log(f"Ожидание размера файла от {addr}...")
                filesize_data = client_socket.recv(1024).decode()
                self.log(f"Получены данные о размере: '{filesize_data}'")

                if not filesize_data.startswith("FILESIZE:"):
                    self.log(f"Ошибка от {addr}: неверный формат размера файла")
                    return
                    
                filesize = int(filesize_data.replace("FILESIZE:", ""))
                self.log(f"Получаю файл от {addr}: {filename}, размер: {filesize} байт")
                
                # Отправляем готовность к приему
                client_socket.send(b"READY")
                self.log(f"Отправлен сигнал готовности к приему для {addr}")
                
                # Принимаем файл с отображением прогресса и улучшенной обработкой ошибок
                save_path = os.path.join(save_dir, filename)
                bytes_received = 0
                last_progress = 0
                
                try:
                    with open(save_path, 'wb') as f:
                        # Устанавливаем меньший таймаут для приема данных
                        client_socket.settimeout(10.0)
                        
                        # Будем показывать прогресс каждые 10%
                        progress_step = max(1, filesize // 10)
                        
                        start_time = datetime.datetime.now()
                        
                        while bytes_received < filesize:
                            try:
                                # Читаем данные
                                data = client_socket.recv(8192)  # Увеличим размер буфера для ускорения
                                
                                if not data:
                                    # Если данных нет, но должны быть еще - возможно, соединение разорвано
                                    self.log(f"Предупреждение: Соединение с {addr} разорвано во время передачи")
                                    break
                                    
                                # Записываем данные в файл
                                f.write(data)
                                bytes_received += len(data)
                                
                                # Показываем прогресс
                                current_progress = (bytes_received * 100) // filesize
                                if current_progress >= last_progress + 10:
                                    elapsed = (datetime.datetime.now() - start_time).total_seconds()
                                    speed = bytes_received / (1024 * elapsed) if elapsed > 0 else 0
                                    self.log(f"Прогресс приема файла от {addr}: {current_progress}% (скорость: {speed:.2f} KB/s)")
                                    last_progress = current_progress
                                    
                            except socket.timeout:
                                self.log(f"Таймаут при приеме файла от {addr}. Попытка продолжить...")
                                continue
                            except Exception as e:
                                self.log(f"Ошибка при приеме данных от {addr}: {str(e)}")
                                break
                    
                    # Проверяем, полностью ли получен файл
                    if bytes_received >= filesize:
                        self.log(f"Файл {filename} от {addr} получен полностью и сохранен как {save_path}")
                        # Отправляем подтверждение
                        client_socket.send(f"FILE_RECEIVED: Файл {filename} успешно получен".encode())
                    else:
                        self.log(f"Предупреждение: Получено только {bytes_received} из {filesize} байт для файла {filename} от {addr}")
                        # Сообщаем о неполном приеме
                        client_socket.send(f"FILE_INCOMPLETE: Получено только {bytes_received} из {filesize} байт".encode())
                        
                except Exception as e:
                    self.log(f"Ошибка при сохранении файла от {addr}: {str(e)}")
                    try:
                        # Уведомляем клиента о проблеме
                        client_socket.send(f"ERROR: {str(e)}".encode())
                    except:
                        pass
                    
            else:
                client_socket.send(b"AUTH_FAILED")
                self.log(f"Аутентификация клиента {addr} провалена!")
                
        except socket.timeout:
            self.log(f"Таймаут соединения с клиентом {addr}")
        except ConnectionResetError:
            self.log(f"Соединение с клиентом {addr} было неожиданно разорвано")
        except Exception as e:
            self.log(f"Ошибка при обработке клиента {addr}: {str(e)}")
        finally:
            # Убедимся, что сокет закрыт в любом случае
            try:
                client_socket.close()
            except:
                pass
            self.log(f"Соединение с клиентом {addr} закрыто")
    
    def stop_server(self):
        """Останавливает сервер"""
        if not self.server_running:
            return
            
        self.server_running = False
        
        try:
            # Разрываем соединение с сервером для завершения accept()
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            temp_socket.connect(('localhost', int(self.port_entry.text())))
            temp_socket.close()
        except:
            pass
            
        # Ждем завершения потока сервера
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(2.0)
            
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Остановлен")
        self.status_label.setStyleSheet("QLabel { color: #F44336; font-weight: bold; }")
        
        self.log("Сервер остановлен")

def main():
    app = QApplication(sys.argv)
    
    # Установка темной темы для всего приложения
    app.setStyle("Fusion")
    
    window = ServerGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
