from notify import *
import sqlite3
from datetime import datetime
from datetime import timedelta
import requests
import whisper
import io
# from config import BOT_TOKEN

from config import BOT_TOKEN, OPENAI_API_KEY, SYSTEM_PROMPT
from openai import OpenAI
import random

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
    try:
        conn = sqlite3.connect('sqlite.db')  # Подключение к базе данных
        cursor = conn.cursor()  # Создание объекта курсора для выполнения SQL-запросов

        query = '''
        SELECT q.id, q.name 
        FROM question q
        LEFT JOIN user_stat us ON q.id = us.question_id AND us.user_id = ? AND us.correct = 1
        WHERE us.question_id IS NULL AND q.active = 1
        '''  # SQL-запрос для выборки случайного вопроса, который пользователь еще не отвечал

        cursor.execute(query, (user_id,))  # Выполнение SQL-запроса с передачей параметра user_id
        questions = cursor.fetchall()  # Получение всех строк результата запроса

        if not questions:  # Если список вопросов пустой
            return "Все вопросы были уже правильно отвечены или нет доступных активных вопросов."

        question_id, question_text = random.choice(questions)  # Выбор случайного вопроса из списка

        set_timer(user_id)

        return question_text  # Возвращает текст случайного вопроса

    except sqlite3.Error as e:  # Обработка исключения SQLite
        print("Ошибка SQLite:", e)  # Вывод сообщения об ошибке
        return "Произошла ошибка при работе с базой данных. Пожалуйста, попробуйте позже."

    finally:
        conn.close()  # Закрытие соединения с базой данных в любом случае, даже если возникло исключение


# Получение ответа (ChatGPT)
def get_answer(question: str, data, type : TYPE):  # описание в backend_documentation.md
    if type == "audio":
        user_answer: str = audio_to_text(data)
        question_pack: tuple[str, str] = (question, user_answer)
    elif type == "empty":
        return (None, None)
    else:
        question_pack: tuple[str, str] = (question, data)
        pass

    user_response = ask_chatgpt(question_pack)

    return (user_response["result"], user_response["comment"])


# Запрос к OpenAI
def ask_chatgpt(question_pack: tuple):
    """
    Функция принимает пакет вопрос-ответ, отправляет его модели GPT-3.5 и возвращает результат и комментарий.
    Более подробное описание в backend_documentation.md
    """
    user_question, user_answer = question_pack
    ask_content = f"Question: {user_question}\nAnswer: {user_answer}"

    client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://api.proxyapi.ru/openai/v1", timeout=30)

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": ask_content}
        ]
    )

    gpt_answer_content = completion.choices[0].message.content
    result, comment = gpt_answer_content.split(' || ')

    response = {
        "result": result.strip(),
        "comment": comment.strip(),
    }

    return response

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