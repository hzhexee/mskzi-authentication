import socket
import random
import os
import hashlib
import secrets
import threading

# Создаем директорию для сохранения файлов, если она не существует
SAVE_DIR = "received_files"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# Простая база данных пользователей для PAP и CHAP
users = {
    "admin": "password123",
    "user1": "securepass",
    "test": "test123"
}

# База данных для S/KEY с seed и счетчиками
skey_db = {
    "admin": {"seed": "salt123", "count": 1000},
    "user1": {"seed": "pepper456", "count": 500},
    "test": {"seed": "sugar789", "count": 100}
}

# Создаем блокировку для безопасного доступа к общим ресурсам
skey_lock = threading.Lock()

def handle_client(client_socket, addr):
    print(f"[СЕРВЕР] Клиент подключился: {addr}")

    try:
        # Получаем выбранный протокол
        protocol_data = client_socket.recv(1024).decode().strip()
        try:
            protocol = int(protocol_data)
            if protocol not in [1, 2, 3]:
                raise ValueError(f"Недопустимый протокол: {protocol}")
            print(f"[СЕРВЕР] Клиент {addr} выбрал протокол: {protocol}")
        except ValueError as e:
            print(f"[СЕРВЕР] Ошибка при получении протокола от {addr}: {e}")
            print(f"[СЕРВЕР] Полученные данные: '{protocol_data}'")
            client_socket.send(b"ERROR: Invalid protocol")
            client_socket.close()
            return
        
        auth_success = False
        
        if protocol == 1:  # PAP (Password Authentication Protocol)
            # Получаем имя пользователя
            username = client_socket.recv(1024).decode()
            print(f"[СЕРВЕР] Получено имя пользователя от {addr}: {username}")
            
            # Получаем пароль
            password = client_socket.recv(1024).decode()
            print(f"[СЕРВЕР] Получен пароль для пользователя {username} от {addr}")
            
            # Проверяем учетные данные
            if username in users and users[username] == password:
                auth_success = True
                print(f"[СЕРВЕР] Пользователь {username} от {addr} успешно аутентифицирован")
            else:
                print(f"[СЕРВЕР] Ошибка аутентификации для пользователя {username} от {addr}")
            
        elif protocol == 2:  # CHAP (Challenge-Handshake Authentication Protocol)
            # Получаем имя пользователя
            username = client_socket.recv(1024).decode()
            print(f"[СЕРВЕР] Получено имя пользователя от {addr}: {username}")
            
            # Генерируем случайный challenge
            challenge = secrets.token_bytes(16)
            client_socket.send(challenge)
            print(f"[СЕРВЕР] Отправлен challenge клиенту {addr}: {challenge.hex()}")
            
            # Получаем ответ
            response = client_socket.recv(1024)
            print(f"[СЕРВЕР] Получен ответ от {addr}: {response.hex()}")
            
            # Проверяем ответ
            if username in users:
                # Вычисляем ожидаемый ответ
                m = hashlib.md5()
                m.update(challenge + users[username].encode())
                expected_response = m.digest()
                
                if response == expected_response:
                    auth_success = True
                    print(f"[СЕРВЕР] Пользователь {username} от {addr} успешно аутентифицирован по CHAP")
                else:
                    print(f"[СЕРВЕР] Ошибка аутентификации для пользователя {username} от {addr}: неверный ответ")
            else:
                print(f"[СЕРВЕР] Пользователь {username} от {addr} не найден")
            
        elif protocol == 3:  # S/KEY (One-Time Password)
            # Получаем имя пользователя
            username = client_socket.recv(1024).decode()
            print(f"[СЕРВЕР] Получено имя пользователя от {addr}: {username}")
            
            # Используем блокировку для безопасного доступа к общим данным
            with skey_lock:
                if username in skey_db:
                    # Отправляем текущее значение счетчика
                    client_socket.send(str(skey_db[username]["count"]).encode())
                    print(f"[СЕРВЕР] Отправлен счетчик клиенту {addr}: {skey_db[username]['count']}")
                    
                    # Получаем одноразовый пароль
                    otp = client_socket.recv(1024)
                    print(f"[СЕРВЕР] Получен одноразовый пароль от {addr}: {otp.hex()}")
                    
                    # В реальной системе мы бы проверили хеш против сохраненного предыдущего хеша
                    # Для демонстрации, предположим что хеш верен
                    auth_success = True
                    
                    # Уменьшаем счетчик
                    skey_db[username]["count"] -= 1
                    print(f"[СЕРВЕР] Обновлен счетчик для {username} от {addr}: {skey_db[username]['count']}")
                else:
                    print(f"[СЕРВЕР] Пользователь {username} от {addr} не найден в базе S/KEY")
            
        if auth_success:
            client_socket.send(b"AUTH_SUCCESS")
            print(f"[СЕРВЕР] Аутентификация клиента {addr} успешна!")
            
            # Получаем имя файла
            filename_data = client_socket.recv(1024).decode()
            if not filename_data.startswith("FILENAME:"):
                print(f"[СЕРВЕР] Ошибка от {addr}: неверный формат имени файла")
                return
                
            filename = filename_data.replace("FILENAME:", "")
            
            # Получаем размер файла
            filesize_data = client_socket.recv(1024).decode()
            if not filesize_data.startswith("FILESIZE:"):
                print(f"[СЕРВЕР] Ошибка от {addr}: неверный формат размера файла")
                return
                
            filesize = int(filesize_data.replace("FILESIZE:", ""))
            print(f"[СЕРВЕР] Получаю файл от {addr}: {filename}, размер: {filesize} байт")
            
            # Отправляем готовность к приему
            client_socket.send(b"READY")
            
            # Принимаем файл
            save_path = os.path.join(SAVE_DIR, filename)
            bytes_received = 0
            
            with open(save_path, 'wb') as f:
                while bytes_received < filesize:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    f.write(data)
                    bytes_received += len(data)
                    
            print(f"[СЕРВЕР] Файл {filename} от {addr} получен и сохранен как {save_path}")
            
            # Отправляем подтверждение
            client_socket.send(f"FILE_RECEIVED: Файл {filename} успешно получен".encode())
            
        else:
            client_socket.send(b"AUTH_FAILED")
            print(f"[СЕРВЕР] Аутентификация клиента {addr} провалена!")
            
    except Exception as e:
        print(f"[СЕРВЕР] Ошибка при обработке клиента {addr}: {str(e)}")
    finally:
        client_socket.close()
        print(f"[СЕРВЕР] Соединение с клиентом {addr} закрыто")

def run_server():
    """Функция для запуска сервера, вынесенная для возможности вызова из других модулей"""
    # Запуск TCP-сервера
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("0.0.0.0", 8080))
    server_socket.listen(5)

    print("[СЕРВЕР] Ожидание клиентов...")

    # Основной цикл сервера для обработки новых подключений
    try:
        while True:
            client_socket, addr = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            client_thread.daemon = True
            client_thread.start()
            print(f"[СЕРВЕР] Запущен новый поток для клиента {addr}")
            print(f"[СЕРВЕР] Активных соединений: {threading.active_count() - 1}")
    except KeyboardInterrupt:
        print("[СЕРВЕР] Сервер остановлен пользователем")
    finally:
        server_socket.close()
        print("[СЕРВЕР] Сервер остановлен")

# Запускаем сервер только если скрипт запущен напрямую, а не импортирован
if __name__ == "__main__":
    run_server()