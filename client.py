import socket
import random
import os
import hashlib
import time
import getpass

# Запрашиваем путь к файлу
file_path = input("Введите путь к файлу для отправки: ")

# Проверяем существование файла
if not os.path.exists(file_path):
    print(f"[КЛИЕНТ] Ошибка: Файл {file_path} не найден")
    exit(1)

# Выбор протокола
print("Выберите протокол аутентификации:")
print("1. PAP (Password Authentication Protocol)")
print("2. CHAP (Challenge-Handshake Authentication Protocol)")
print("3. S/KEY (One-Time Password)")
protocol = int(input("Введите номер протокола (1-3): "))
# Validate input
if protocol not in [1, 2, 3]:
    print("Ошибка: Введите число от 1 до 3")
    exit(1)

# Подключаемся к серверу
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(("127.0.0.1", 8080))

# Отправляем выбранный протокол
client_socket.send(str(protocol).encode())
# Add a small delay or wait for acknowledgment
time.sleep(0.1)
print(f"[КЛИЕНТ] Выбран протокол: {protocol}")

# Аутентификация с использованием выбранного протокола
if protocol == 1:  # PAP
    # Запрашиваем логин и пароль
    username = input("Введите имя пользователя: ")
    password = getpass.getpass("Введите пароль: ")
    
    # Отправляем логин и пароль серверу
    client_socket.send(username.encode())
    time.sleep(0.1)
    client_socket.send(password.encode())
    
    print(f"[КЛИЕНТ] Данные аутентификации отправлены серверу")

elif protocol == 2:  # CHAP
    # Запрашиваем логин
    username = input("Введите имя пользователя: ")
    password = getpass.getpass("Введите пароль: ")
    
    # Отправляем только логин
    client_socket.send(username.encode())
    print(f"[КЛИЕНТ] Отправлено имя пользователя: {username}")
    
    # Получаем случайный challenge от сервера
    challenge = client_socket.recv(1024)
    print(f"[КЛИЕНТ] Получен challenge: {challenge.hex()}")
    
    # Вычисляем хеш MD5(challenge + password)
    m = hashlib.md5()
    m.update(challenge + password.encode())
    response = m.digest()
    
    # Отправляем ответ
    client_socket.send(response)
    print(f"[КЛИЕНТ] Отправлен ответ: {response.hex()}")

elif protocol == 3:  # S/KEY
    # Константы S/KEY
    username = input("Введите имя пользователя: ")
    seed = input("Введите seed (случайная строка): ")
    
    # Отправляем логин
    client_socket.send(username.encode())
    
    # Получаем текущее значение счетчика
    count = int(client_socket.recv(1024).decode())
    print(f"[КЛИЕНТ] Счетчик запросов: {count}")
    
    # В реальной системе пароль был бы предвычислен
    # Здесь мы имитируем для демонстрации
    secret = getpass.getpass("Введите секретный ключ: ")
    
    # Вычисляем одноразовый пароль путем последовательного хеширования
    # MD5(seed + secret + count)
    combined = (seed + secret).encode()
    result = combined
    
    for _ in range(count):
        h = hashlib.md5()
        h.update(result)
        result = h.digest()
    
    # Отправляем одноразовый пароль
    client_socket.send(result)
    print(f"[КЛИЕНТ] Отправлен одноразовый пароль для счетчика {count}")

# Получаем ответ
result = client_socket.recv(1024).decode()
print(f"[КЛИЕНТ] Ответ от сервера: {result}")

# Если аутентификация успешна, отправляем файл
if result == "AUTH_SUCCESS":
    print(f"[КЛИЕНТ] Аутентификация успешна. Начинаем передачу файла: {file_path}")
    try:
        # Отправляем имя файла
        file_name = os.path.basename(file_path)
        client_socket.send(f"FILENAME:{file_name}".encode())
        print(f"[КЛИЕНТ] Отправлено имя файла: {file_name}")
        time.sleep(1)  # Добавляем паузу
        
        # Отправляем размер файла
        file_size = os.path.getsize(file_path)
        client_socket.send(f"FILESIZE:{file_size}".encode())
        print(f"[КЛИЕНТ] Отправлен размер файла: {file_size} байт")
        time.sleep(1)  # Добавляем паузу
        
        # Получаем подтверждение готовности
        print(f"[КЛИЕНТ] Ожидание сигнала готовности от сервера...")
        ready = client_socket.recv(1024).decode().strip()
        print(f"[КЛИЕНТ] Получен ответ от сервера: '{ready}'")
        
        if ready != "READY":
            print(f"[КЛИЕНТ] Ошибка: сервер не готов к приему файла")
            client_socket.close()
            exit(1)
            
        # Отправляем содержимое файла
        with open(file_path, 'rb') as f:
            data = f.read(4096)
            while data:
                client_socket.send(data)
                data = f.read(4096)
                
        print(f"[КЛИЕНТ] Файл {file_name} успешно передан")
        
        # Получаем подтверждение о получении файла
        confirmation = client_socket.recv(1024).decode()
        print(f"[КЛИЕНТ] {confirmation}")
        
    except Exception as e:
        print(f"[КЛИЕНТ] Ошибка при передаче файла: {str(e)}")
else:
    print("[КЛИЕНТ] Аутентификация не удалась. Отправка файла невозможна.")

client_socket.close()