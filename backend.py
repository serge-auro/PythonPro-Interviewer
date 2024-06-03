import sqlite3
from datetime import datetime
from datetime import timedelta
import requests
import whisper
import io
from config import BOT_TOKEN, OPENAI_API_KEY, SYSTEM_PROMPT
from openai import OpenAI
import random
import time
import numpy as np
import ffmpeg
import logging


TYPE = ("text", "audio", "empty")

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


# Загрузка модели Whisper вне функций для улучшения производительности
model = whisper.load_model('small')  # Или 'base' 'small' 'medium' 'large'


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
    conn = sqlite3.connect('sqlite.db')  # Подключение к базе данных
    question = {"id": '', "name": ''}
    try:
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
        question = {"id": question_id, "name": question_text}

        # Запись вопроса в таблицу user_notify
        insert_query = '''
        INSERT OR REPLACE INTO user_notify (user_id, question_id, active) VALUES (?, ?, 1)
        '''
        cursor.execute(insert_query, (user_id, question_id))
        conn.commit()

        set_timer(user_id, question_id)

        return question  # Возвращает текст случайного вопроса

    except sqlite3.Error as e:  # Обработка исключения SQLite
        print("Ошибка SQLite:", e)  # Вывод сообщения об ошибке
        return "Произошла ошибка при работе с базой данных. Пожалуйста, попробуйте позже."

    finally:
        conn.close()  # Закрытие соединения с базой данных в любом случае, даже если возникло исключение


# Получение ответа (ChatGPT)
def process_answer(user_id, data, type: str):
    logging.info(f"Starting process_answer with type: {type}")
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    question_id = 0
    question_text = ""

    query = '''
        SELECT qq.id, qq.name
          FROM user_notify as un, question as qq
         WHERE un.question_id = qq.id
           AND qq.active = 1
           AND un.active = 1
           AND un.user_id = ? LIMIT 1
    '''

    try:
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        if result:
            question_id, question_text = result
        else:
            logging.error(f"No active question found for user {user_id}")
            # Добавим запрос для логирования активных вопросов
            cursor.execute('SELECT * FROM question WHERE active = 1')
            active_questions = cursor.fetchall()
            logging.info(f"Active questions: {active_questions}")

            # Добавим запрос для логирования активных записей в user_notify для данного пользователя
            cursor.execute('SELECT * FROM user_notify WHERE user_id = ? AND active = 1', (user_id,))
            active_user_notify = cursor.fetchall()
            logging.info(f"Active user_notify for user {user_id}: {active_user_notify}")

            return "Ошибка", "Активный вопрос не найден."

        if type == "audio":
            try:
                user_answer = audio_to_text(data)
                logging.info(f"Audio converted to text: {user_answer}")
            except Exception as e:
                logging.error(f"Error converting audio to text: {e}")
                return "Ошибка", "Ошибка при распознавании аудиофайла."
        elif type == "empty":
            return "Ошибка", "Пустой ответ."
        else:
            user_answer = data

        user_response = ask_chatgpt((question_text, user_answer))
        logging.info(f"ChatGPT response: {user_response}")

        # Сохранение ответа в БД
        cursor.execute(
            "INSERT OR REPLACE INTO user_stat (user_id, question_id, correct, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, question_id, user_response['result'] == 'correct', datetime.now()))

        # Деактивация вопроса в user_notify
        cursor.execute("UPDATE user_notify SET active = 0 WHERE user_id = ? AND question_id = ?",
                       (user_id, question_id))

        conn.commit()

    except sqlite3.Error as e:
        logging.error(f"SQLite error: {e}")
        return "Ошибка", "Ошибка при сохранении вашего ответа."
    finally:
        conn.close()

    return user_response['result'], user_response['comment']


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


# Функция для скачивания голосового сообщения
def download_audio_file(file_id, bot_token=BOT_TOKEN):
    logging.info("Downloading audio file...")
    start_time = time.time()
    file_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
    response = requests.get(file_url)
    if response.status_code != 200:
        logging.error(f"Failed to get file info: {response.content}")
        return None
    file_path = response.json()['result']['file_path']
    download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    audio_response = requests.get(download_url)
    if audio_response.status_code != 200:
        logging.error(f"Failed to download file: {audio_response.content}")
        return None
    audio_data = io.BytesIO(audio_response.content)
    end_time = time.time()
    logging.info(f"Audio file downloaded in {end_time - start_time} seconds.")
    return audio_data


# Функция для преобразования аудио в массив NumPy
def audio_to_numpy(audio_data):
    logging.info("Converting audio data to numpy array...")
    start_time = time.time()
    try:
        # Использование ffmpeg для декодирования байтового потока в массив NumPy
        audio_np, _ = (
            ffmpeg
            .input('pipe:0', format='ogg')
            .output('pipe:1', format='wav', acodec='pcm_s16le', ar='16000')
            .run(input=audio_data.read(), capture_stdout=True, capture_stderr=True)
        )
    except Exception as e:
        logging.error(f"FFmpeg error: {e}")
        return None
    audio_np = np.frombuffer(audio_np, np.int16).astype(np.float32)
    audio_np = audio_np / 32768.0  # Нормализация
    audio_np = audio_np.flatten()
    end_time = time.time()
    logging.info(f"Audio data converted to numpy array in {end_time - start_time} seconds.")
    return audio_np


# Функция для преобразования аудио в текст
def audio_to_text(file_id):
    logging.info("Converting audio to text...")
    start_time = time.time()
    audio_data = download_audio_file(file_id)
    if audio_data is None:
        logging.error("Failed to download audio file.")
        return None
    audio_np = audio_to_numpy(audio_data)
    if audio_np is None:
        logging.error("Failed to convert audio to numpy array.")
        return None
    try:
        result = model.transcribe(audio_np, language='ru')
        logging.info(f"Transcription result: {result}")
    except Exception as e:
        logging.error(f"Whisper model error: {e}")
        return None
    end_time = time.time()
    logging.info(f"Audio converted to text in {end_time - start_time} seconds.")
    return result['text']

# Отслеживание уведомлений
def get_notify(user_id):
    # TODO добавить вопрос
    process_answer(user_id, "я не знаю", "empty")


# Создаём таймер - в БД
def set_timer(user_id, question_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()

    current_datetime = datetime.now() + timedelta(minutes=2)
    timedate = current_datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("INSERT INTO user_notify (user_id, question_id, timedate, active) VALUES (?, ?, ?, ?)",
                   (user_id, question_id, timedate, True))
    conn.close()


# Удаление уведомлений
def skip_timer(user_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()

    # SQL-запрос для получения статистики
    query = '''
            UPDATE active = 0
              FROM user_notify
             WHERE user_id = ?
               AND active = 1
               AND question_id > 0
        '''

    cursor.execute(query, (user_id,))
    conn.close()

def update_user_stat(user_id, question_id, is_correct):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO user_stat (user_id, question_id, correct, timestamp) VALUES (?, ?, ?, ?)",
                   (user_id, question_id, is_correct, datetime.now()))
    conn.commit()
    conn.close()
