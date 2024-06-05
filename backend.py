import sqlite3
from datetime import datetime
from datetime import timedelta
import requests
import whisper
import io
from config import BOT_TOKEN, OPENAI_API_KEY, SYSTEM_PROMPT
from openai import OpenAI
import random
import numpy as np
import ffmpeg
import logging

TYPE = ("text", "audio", "empty")

# Загрузка модели Whisper вне функций для улучшения производительности
model = whisper.load_model('small')  # Или 'base' 'small' 'medium' 'large'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Инициализация пользователя
def init_user(user_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()

    cursor.execute("INSERT OR REPLACE INTO user (id, active) VALUES (?, ?)",
                   (user_id, 1))

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
        return ("Количество заданных вопросов: 0\n"
                "Правильных ответов: 0%\n"
                "Неправильных: 0%")

    correct_percentage = round((correct_answers / total_questions) * 100)
    incorrect_percentage = 100 - correct_percentage

    report = (f"Количество заданных вопросов: {total_questions}\n"
              f"Правильных ответов: {correct_percentage}%\n"
              f"Неправильных: {incorrect_percentage}%")

    # Закрываем соединение с базой данных
    conn.close()

    return report


# Получение вопроса
def get_question(user_id):
    try:
        questions = get_unresolved_questions(user_id)

        if not questions:  # Если список вопросов пустой
            return "Все вопросы были уже правильно отвечены или нет доступных активных вопросов."

        # Взвешенный выбор случайного вопроса
        total_weights = sum(rate for _, _, rate in questions)
        question_id, question_text, _ = random.choices(questions, weights=[rate for _, _, rate in questions], k=1)[0]
        question = {"id": question_id, "name": question_text}
        logging.info(f"{user_id} - {question_id}: {question_text}")
        set_timer(user_id, question_id)

    except sqlite3.Error as e:
        print("SQLite error:", e)
        return "Произошла ошибка при работе с базой данных. Пожалуйста, попробуйте позже."

    return question


# Получение ответа (ChatGPT)
def process_answer(user_id, data, type: TYPE):
    if not isinstance(user_id, int) or user_id <= 0:
        return "Ошибка", "Некорректный идентификатор пользователя."

    if type not in ["audio", "empty", "text"]:
        return "Ошибка", "Некорректный тип ответа."

    try:
        result = get_active_question(user_id)
        if result:
            question_id, question_text = result
        else:
            return "Ошибка", "Активный вопрос не найден."

        if type == "audio":
            try:
                user_answer = audio_to_text(data)
            except Exception as e:
                return "Ошибка", f"Ошибка при распознавании аудиофайла: {str(e)}"
        elif type == "empty":
            return "Ошибка", "Пустой ответ."
        else:
            user_answer = data

        logging.info(f"process_answer->gpt : {user_answer} ")
        user_response = ask_chatgpt((question_text, user_answer))

        if user_response['result'] == "Верно":
            correct = True
        elif user_response['result'] == "Неверно":
            correct = False
        else:
            return "Ошибка", "Некорректный формат ответа от ChatGPT."

        update_user_stat(user_id, question_id, correct)
        skip_question(user_id)

    except sqlite3.Error as e:
        return "Ошибка", f"Ошибка при сохранении вашего ответа: {str(e)}"
    except Exception as e:
        return "Ошибка", f"Неизвестная ошибка: {str(e)}"

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
    file_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
    response = requests.get(file_url)
    if response.status_code != 200:
        return None
    file_path = response.json()['result']['file_path']
    download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    audio_response = requests.get(download_url)
    if audio_response.status_code != 200:
        logging.info(f"download_audio_file : {audio_response.text} ")
        return None
    audio_data = io.BytesIO(audio_response.content)
    logging.info(f"download_audio_file : {audio_response} ")
    return audio_data


# Функция для преобразования аудио в массив NumPy
def audio_to_numpy(audio_data):
    try:
        # Использование ffmpeg для декодирования байтового потока в массив NumPy
        audio_np, _ = (
            ffmpeg
            .input('pipe:0', format='ogg')
            .output('pipe:1', format='wav', acodec='pcm_s16le', ar='16000')
            .run(input=audio_data.read(), capture_stdout=True, capture_stderr=True)
        )
    except Exception as e:
        logging.info(f"audio_to_numpy : {e} ")
        return None
    audio_np = np.frombuffer(audio_np, np.int16).astype(np.float32)
    audio_np = audio_np / 32768.0  # Нормализация
    audio_np = audio_np.flatten()
    return audio_np


# Функция для преобразования аудио в текст
def audio_to_text(file_id):
    audio_data = download_audio_file(file_id)
    if audio_data is None:
        return None
    audio_np = audio_to_numpy(audio_data)
    if audio_np is None:
        return None
    try:
        result = model.transcribe(audio_np, language='ru')
    except Exception as e:
        logging.info(f"audio_to_text : {e} ")
        return None
    logging.info(f"audio_to_text :  {result['text']} ")
    return result['text']


# Отслеживание уведомлений
def get_notify(user_id):
    process_answer(user_id, "я не знаю", "empty")


# Создаём таймер - в БД
def set_timer(user_id, question_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()

    current_datetime = datetime.now() + timedelta(minutes=2)
    timedate = current_datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("INSERT OR REPLACE INTO user_notify (user_id, question_id, timedate, active) VALUES (?, ?, ?, ?)",
                   (user_id, question_id, timedate, 1))
    conn.commit()
    conn.close()


# Удаление уведомлений
def skip_timer(user_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()

    # SQL-запрос для получения статистики
    query = '''
            UPDATE user_notify
               SET active = 0
             WHERE user_id = ?
               AND active = 1
        '''
    logging.info(f"skip_timer {user_id} ")
    cursor.execute(query, (user_id,))
    conn.commit()
    conn.close()


def get_unresolved_questions(user_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    query = '''
        SELECT q.id, q.name, q.rate
        FROM question q
        LEFT JOIN user_stat us ON q.id = us.question_id AND us.user_id = ? AND us.correct = 1
        WHERE us.question_id IS NULL AND q.active = 1
    '''
    cursor.execute(query, (user_id,))
    questions = cursor.fetchall()
    conn.close()
    return questions


def get_active_question(user_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    query = '''
        SELECT qq.id, qq.name
        FROM user_notify as un, question as qq
        WHERE un.question_id = qq.id
          AND qq.active = 1
          AND un.active = 1
          AND un.user_id = ? LIMIT 1
    '''
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def update_user_stat(user_id, question_id, correct):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO user_stat (user_id, question_id, correct, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, question_id, correct, datetime.now()))
    conn.commit()
    conn.close()


def clear_user_stat(user_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM user_stat WHERE user_id = ?",
        (user_id,))
    conn.commit()
    conn.close()


def skip_question(user_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE user_notify SET active = 0 WHERE user_id = ?",
                   (user_id,))
    conn.commit()
    conn.close()
