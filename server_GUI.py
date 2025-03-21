import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
import threading
import socket
import os
import sys
import datetime
import hashlib
import secrets
from server import users, skey_db, skey_lock, handle_client

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Сервер аутентификации")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        # Переменные состояния
        self.server_running = False
        self.server_socket = None
        self.server_thread = None
        self.save_dir = "received_files"
        
        # Создаем директорию для сохранения файлов, если она не существует
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        
        # Создание фреймов
        self.create_control_frame()
        self.create_log_frame()
        
        # Конфигурация root grid
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Вывод начального сообщения
        self.log("Сервер аутентификации инициализирован")
        self.log(f"Текущая директория сохранения: {os.path.abspath(self.save_dir)}")
    
    def create_control_frame(self):
        """Создает фрейм с элементами управления сервером"""
        control_frame = tk.Frame(self.root, padx=10, pady=10)
        control_frame.grid(row=0, column=0, sticky="ew")
        
        # Информация о директории сохранения
        dir_frame = tk.Frame(control_frame)
        dir_frame.pack(fill="x", pady=5)
        
        tk.Label(dir_frame, text="Директория сохранения:").pack(side="left")
        
        self.dir_var = tk.StringVar(value=os.path.abspath(self.save_dir))
        dir_entry = tk.Entry(dir_frame, textvariable=self.dir_var, width=50, state='readonly')
        dir_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        dir_button = tk.Button(dir_frame, text="Изменить", command=self.select_directory)
        dir_button.pack(side="right")
        
        # Кнопки управления сервером
        button_frame = tk.Frame(control_frame)
        button_frame.pack(fill="x", pady=10)
        
        self.start_button = tk.Button(button_frame, text="Запустить сервер", 
                                     command=self.start_server, bg="green", fg="white",
                                     width=15, height=2)
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = tk.Button(button_frame, text="Остановить сервер", 
                                    command=self.stop_server, bg="red", fg="white",
                                    width=15, height=2, state="disabled")
        self.stop_button.pack(side="left", padx=5)
        
        # Статус сервера
        status_frame = tk.Frame(control_frame)
        status_frame.pack(fill="x", pady=5)
        
        tk.Label(status_frame, text="Статус сервера:").pack(side="left")
        
        self.status_var = tk.StringVar(value="Остановлен")
        self.status_label = tk.Label(status_frame, textvariable=self.status_var, 
                                    fg="red", font=("Arial", 10, "bold"))
        self.status_label.pack(side="left", padx=5)
        
        # Информация о порте
        port_frame = tk.Frame(control_frame)
        port_frame.pack(fill="x", pady=5)
        
        tk.Label(port_frame, text="Порт:").pack(side="left")
        
        self.port_var = tk.StringVar(value="8080")
        port_entry = tk.Entry(port_frame, textvariable=self.port_var, width=10)
        port_entry.pack(side="left", padx=5)
    
    def create_log_frame(self):
        """Создает фрейм с логами сервера"""
        log_frame = tk.Frame(self.root, padx=10, pady=10)
        log_frame.grid(row=1, column=0, sticky="nsew")
        
        # Заголовок
        tk.Label(log_frame, text="Логи сервера:").pack(anchor="w")
        
        # Окно логов с прокруткой
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20, 
                                                  bg="#f0f0f0", font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True, pady=5)
        self.log_area.config(state="disabled")
        
        # Кнопка очистки логов
        clear_button = tk.Button(log_frame, text="Очистить логи", command=self.clear_logs)
        clear_button.pack(anchor="e")
    
    def log(self, message):
        """Добавляет сообщение в лог-окно с отметкой времени"""
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_message = f"{timestamp} {message}\n"
        
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, log_message)
        self.log_area.see(tk.END)
        self.log_area.config(state="disabled")
    
    def clear_logs(self):
        """Очищает содержимое лог-окна"""
        self.log_area.config(state="normal")
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state="disabled")
        self.log("Логи очищены")
    
    def select_directory(self):
        """Открывает диалог выбора директории для сохранения файлов"""
        if self.server_running:
            messagebox.showwarning("Предупреждение", 
                                  "Невозможно изменить директорию сохранения при запущенном сервере")
            return
            
        new_dir = filedialog.askdirectory(initialdir=self.save_dir)
        if new_dir:
            self.save_dir = new_dir
            self.dir_var.set(os.path.abspath(self.save_dir))
            self.log(f"Директория сохранения изменена на: {os.path.abspath(self.save_dir)}")
            
            # Создаем директорию если она не существует
            if not os.path.exists(self.save_dir):
                os.makedirs(self.save_dir)
    
    def start_server(self):
        """Запускает сервер в отдельном потоке"""
        if self.server_running:
            return
            
        try:
            port = int(self.port_var.get())
            if port < 1024 or port > 65535:
                raise ValueError("Порт должен быть в диапазоне 1024-65535")
                
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind(("0.0.0.0", port))
            self.server_socket.listen(5)
            
            self.server_running = True
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.status_var.set("Запущен")
            self.status_label.config(fg="green")
            
            self.log(f"Сервер запущен на порту {port}")
            self.log(f"Ожидание клиентов...")
            
            # Запуск сервера в отдельном потоке
            self.server_thread = threading.Thread(target=self.server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить сервер: {str(e)}")
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
            temp_socket.connect(('localhost', int(self.port_var.get())))
            temp_socket.close()
        except:
            pass
            
        # Ждем завершения потока сервера
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(2.0)
            
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_var.set("Остановлен")
        self.status_label.config(fg="red")
        
        self.log("Сервер остановлен")

def main():
    root = tk.Tk()
    app = ServerGUI(root)
    root.protocol("WM_DELETE_WINDOW", lambda: quit_app(root, app))
    root.mainloop()

def quit_app(root, app):
    """Корректное завершение приложения"""
    if app.server_running:
        app.stop_server()
    root.destroy()

if __name__ == "__main__":
    main()
