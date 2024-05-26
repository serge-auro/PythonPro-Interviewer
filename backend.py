from notify import *
import sqlite3
from datetime import datetime
from datetime import timedelta
import requests
import whisper
import io
from config import BOT_TOKEN
# Чтобы не подгружать в backend BOT_TOKEN, нужный в функции download_audio_file для загрузки голосового сообщения,
# надо передать его из фронтенда в функцию get_answer и далее в функцию audio_to_text

TYPE = ("text", "audio", "empty")


# Инициализация пользоавтеля
def init_user(user_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()

    print(f"DEBUG: Checking if user '{user_id}' exists in the database.")

    # Проверка, существует ли уже такой пользователь
    cursor.execute("SELECT id FROM user WHERE id = ?", (user_id,))
    result = cursor.fetchone()

    if result:
        # Если пользователь найден, обновляем его статус active
        cursor.execute("UPDATE user SET active = ? WHERE id = ?", (True, user_id))
        print(f"User with ID {user_id} already exists in the database and is now active.")
    else:
        # Если пользователь не найден, добавляем его
        date_created = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("INSERT INTO user (id, active, date_created) VALUES (?, ?, ?)",
                       (user_id, True, date_created))
        print(f"User with ID {user_id} added to the database.")

    conn.commit()
    conn.close()
    return user_id


# Запрос статистики
def get_report(user_id):
    # Подключаемся к базе данных
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()

    # SQL-запрос для получения статистики
    query = '''
            SELECT 
                COUNT(*) AS total_questions,
                SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) AS correct_answers,
                SUM(CASE WHEN correct = 0 THEN 1 ELSE 0 END) AS incorrect_answers
            FROM user_stat
            WHERE user_id = ?
        '''

    cursor.execute(query, (user_id,))
    result = cursor.fetchone()

    total_questions = result[0]
    correct_answers = result[1]
    incorrect_answers = result[2]

    if total_questions == 0:
        return ("Количество заданных вопросов: 0\n "
                "Правильных ответов: 0%\n"
                "Неправильных: 0%")

    correct_percentage = round((correct_answers / total_questions) * 100)
    incorrect_percentage = 100 - correct_percentage

    report = (f"Количество заданных вопросов: {total_questions}\n "
              f"Правильных ответов: {correct_percentage}%\n"
              f"Неправильных: {incorrect_percentage}%")

    # Закрываем соединение с базой данных
    conn.close()

    return report

    # return ("Количество заданных вопросов ***\n "
    #         "Правильных ответов **%\n"
    #         "Неправильных **%")


# Получение вопроса
def get_question(user_id):
    set_timer(user_id)
    return "Что такое SOLID?"


# Получение ответа (ChatGPT)
def get_answer(data, type : TYPE):
    if type == "audio":
        audio_to_text(data)
    elif type == "empty":
        pass  # TODO ТУТ БУДЕТ КОД

    return ("Ответ верный. Уточнения:"
            "SOLID - это акроним, который представляет собой пять основных принципов объектно-ориентированного программирования и дизайна. Каждая буква в слове SOLID представляет собой один из этих принципов:"
            "1. S - Принцип единственной ответственности (Single Responsibility Principle): Класс должен иметь только одну причину для изменения."
            "2. O - Принцип открытости/закрытости (Open/Closed Principle): Программные сущности должны быть открыты для расширения, но закрыты для изменения."
            "3. L - Принцип подстановки Барбары Лисков (Liskov Substitution Principle): Объекты в программе должны быть заменяемыми исходными объектами."
            "4. I - Принцип разделения интерфейса (Interface Segregation Principle): Клиенты не должны зависеть от интерфейсов, которые они не используют."
            "5. D - Принцип инверсии зависимостей (Dependency Inversion Principle): Модули верхнего уровня не должны зависеть от модулей нижнего уровня. Оба должны зависеть от абстракций.")


# Загрузка голосового сообщения в оперативную память
def download_audio_file(file_id, bot_token=BOT_TOKEN):
    """
    Скачивание голосового сообщения из Telegram и сохранение в оперативной памяти.
    """
    # Создаем URL для получения информации о файле
    file_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"

    # Запрашиваем информацию о файле у Telegram API
    response = requests.get(file_url)
    file_path = response.json()['result']['file_path']

    # Создаем URL для скачивания самого файла
    download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

    # Загружаем файл в оперативную память
    audio_response = requests.get(download_url)

    # Создаем объект BytesIO для хранения аудио данных в памяти
    audio_data = io.BytesIO(audio_response.content)

    return audio_data


# Трансформация в текст
def audio_to_text(data):
    """
    Преобразование голосового сообщения в текст с использованием OpenAI Whisper.
    """
    file_id = data['voice']['file_id']
    audio_data = download_audio_file(file_id)

    # Загрузка модели Whisper
    model = whisper.load_model("base")

    # Преобразование аудио в текст
    result = model.transcribe(audio_data)
    return result['text']


# Отслеживание уведомлений
def get_notify(user_id):
    get_answer(None, "text")