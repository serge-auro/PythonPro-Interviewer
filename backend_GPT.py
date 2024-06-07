import sqlite3
from datetime import datetime, timedelta
import requests
import io
from config import BOT_TOKEN, OPENAI_API_KEY, SYSTEM_PROMPT, OPENAI_WHISPER_API_KEY
from openai import OpenAI
import random
import ffmpeg
import logging
import os

TYPE = ("text", "audio", "empty")

client = OpenAI(api_key=OPENAI_WHISPER_API_KEY, base_url="https://api.proxyapi.ru/openai/v1")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Инициализация пользователя
def init_user(user_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()

    cursor.execute("INSERT OR REPLACE INTO user (id, active) VALUES (?, ?)", (user_id, 1))

    conn.commit()
    conn.close()
    return user_id


# Запрос статистики
def get_report(user_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()

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

    conn.close()
    return report


# Получение вопроса
def get_question(user_id):
    try:
        questions = get_unresolved_questions(user_id)

        if not questions:
            return "Все вопросы были уже правильно отвечены или нет доступных активных вопросов."

        total_weights = sum(rate for _, _, rate in questions)
        question_id, question_text, _ = random.choices(questions, weights=[rate for _, _, rate in questions], k=1)[0]
        question = {"id": question_id, "name": question_text}
        logging.info(f"{user_id} - {question_id}: {question_text}")
        set_timer(user_id, question_id)

    except sqlite3.Error as e:
        logging.error(f"SQLite error: {e}")
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
                os.remove(download_audio_file(data))
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
    user_question, user_answer = question_pack
    ask_content = f"Question: {user_question}\nAnswer: {user_answer}"

    completion = client.chat.completions.create(
        model="gpt-4o",
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
    logging.info(f"Requesting file info with URL: {file_url}")
    response = requests.get(file_url)
    logging.info(f"Response from Telegram API: {response.json()}")
    if response.status_code != 200:
        logging.error(f"Failed to get file info: {response.status_code}")
        return None

    file_path = response.json().get('result', {}).get('file_path')
    if not file_path:
        logging.error("Failed to get file path.")
        return None

    download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    audio_response = requests.get(download_url)
    if audio_response.status_code != 200:
        logging.error(f"Failed to download file: {audio_response.text}")
        return None

    voice_file = f"voice_{file_id}.ogg"
    with open(voice_file, 'wb') as f:
        f.write(audio_response.content)

    logging.info(f"File downloaded successfully and saved as {voice_file}")
    return voice_file


# Функция для конвертации аудио из формата .ogg в .wav
def convert_audio_to_wav(ogg_file_path):
    wav_data = io.BytesIO()
    try:
        process = (
            ffmpeg
            .input(ogg_file_path)
            .output('pipe:1', format='wav', acodec='pcm_s16le', ar='16000')
            .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True)
        )
        output, error = process.communicate()
        if process.returncode != 0:
            logging.error(f"FFmpeg error: {error.decode()}")
            return None
        wav_data.write(output)
        wav_data.seek(0)
        return wav_data
    except ffmpeg.Error as e:
        logging.error(f"FFmpeg error: {e.stderr.decode()}")
        return None


# Функция для преобразования аудио в текст с использованием OpenAI Whisper API
def audio_to_text(file_id):
    ogg_file_path = download_audio_file(file_id)
    if ogg_file_path is None:
        logging.error("Failed to download audio file.")
        return None
    wav_data = convert_audio_to_wav(ogg_file_path)
    if wav_data is None:
        print("Failed to convert audio to wav.")
        os.remove(ogg_file_path)
        return None
    response = client.audio.transcriptions.create(
        file=wav_data,
        model="whisper-1"
    )
    print(type(response))
    if hasattr(response, 'error'):
        logging.error(f"OpenAI Whisper error: {response.error}")
        os.remove(ogg_file_path)
        return None

    os.remove(ogg_file_path)
    return response.text


# Отслеживание уведомлений
def get_notify(user_id):
    process_answer(user_id, "я не знаю", "empty")


# Создаём таймер - в БД
def set_timer(user_id, question_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()

    current_datetime = datetime.now() + timedelta(minutes=2)
    timedate = current_datetime.strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("INSERT OR REPLACE INTO user_notify (user_id, question_id, timedate, active) VALUES (?, ?, ?, ?)",
                   (user_id, question_id, timedate, 1))
    conn.commit()
    conn.close()


# Удаление уведомлений
def skip_timer(user_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()

    query = '''
            UPDATE user_notify
               SET active = 0
             WHERE user_id = ?
               AND active = 1
        '''
    logging.info(f"skip_timer {user_id}")
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


def change_user_level(user_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE user
               SET user_lvl = CASE 
                   WHEN user_lvl = 'junior' THEN 'middle'
                   WHEN user_lvl = 'middle' THEN 'senior'
                   WHEN user_lvl = 'senior' THEN 'junior'
                   ELSE 'junior'
               END
             WHERE id = ?
        ''', (user_id,))
        conn.commit()

        cursor.execute('SELECT user_lvl FROM user WHERE id = ?', (user_id,))
        user_lvl = cursor.fetchone()[0]

        return f"Твой текущий уровень {user_lvl}."
    except sqlite3.Error as e:
        logging.error(f"SQLite error: {e}")
        return "Произошла ошибка при изменении уровня пользователя."
    finally:
        conn.close()


def change_user_time(user_id):
    conn = sqlite3.connect('sqlite.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE user
               SET user_minute = CASE 
                   WHEN user_minute + 1 > 3 THEN 1
                   ELSE user_minute + 1
               END
             WHERE id = ?
        ''', (user_id,))
        conn.commit()

        cursor.execute('SELECT user_minute FROM user WHERE id = ?', (user_id,))
        user_minute = cursor.fetchone()[0]

        return f"Текущее время на ответ {user_minute} минут."
    except sqlite3.Error as e:
        logging.error(f"SQLite error: {e}")
        return "Произошла ошибка при изменении времени на ответ."
    finally:
        conn.close()
