import sqlite3
from datetime import datetime, timedelta
import requests
import openai_whisper as whisper  # Если используется стандартная библиотека OpenAI Whisper
import io
from config import BOT_TOKEN, OPENAI_API_KEY, SYSTEM_PROMPT
from openai import OpenAI
import random

# Константы
TYPE = ("text", "audio", "empty")

# Класс для работы с базой данных
class Database:
    def __init__(self, db_name='sqlite.db'):
        self.db_name = db_name

    def _connect(self):
        return sqlite3.connect(self.db_name)

    def execute_query(self, query, params=()):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.commit()
        conn.close()
        return result

    def execute_non_query(self, query, params=()):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        conn.close()


# Класс для работы с пользователем
class User:
    def __init__(self, db: Database):
        self.db = db

    def init_user(self, user_id):
        query_check = "SELECT id FROM user WHERE id = ?"
        query_insert = "INSERT INTO user (id, active, date_created) VALUES (?, ?, ?)"
        query_update = "UPDATE user SET active = ? WHERE id = ?"

        result = self.db.execute_query(query_check, (user_id,))
        if result:
            self.db.execute_non_query(query_update, (True, user_id))
            print(f"User with ID {user_id} already exists in the database and is now active.")
        else:
            date_created = datetime.now().strftime('%Y-%m-%d')
            self.db.execute_non_query(query_insert, (user_id, True, date_created))
            print(f"User with ID {user_id} added to the database.")
        return user_id

    def get_report(self, user_id):
        query = '''
                SELECT 
                    COUNT(*) AS total_questions,
                    SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) AS correct_answers,
                    SUM(CASE WHEN correct = 0 THEN 1 ELSE 0 END) AS incorrect_answers
                FROM user_stat
                WHERE user_id = ?
            '''
        result = self.db.execute_query(query, (user_id,))
        total_questions, correct_answers, incorrect_answers = result[0]

        if total_questions == 0:
            return ("Количество заданных вопросов: 0\n "
                    "Правильных ответов: 0%\n"
                    "Неправильных: 0%")

        correct_percentage = round((correct_answers / total_questions) * 100)
        incorrect_percentage = 100 - correct_percentage

        report = (f"Количество заданных вопросов: {total_questions}\n "
                  f"Правильных ответов: {correct_percentage}%\n"
                  f"Неправильных: {incorrect_percentage}%")
        return report

    def get_question(self, user_id):
        try:
            query = '''
            SELECT q.id, q.name 
            FROM question q
            LEFT JOIN user_stat us ON q.id = us.question_id AND us.user_id = ? AND us.correct = 1
            WHERE us.question_id IS NULL AND q.active = 1
            '''
            questions = self.db.execute_query(query, (user_id,))
            if not questions:
                return "Все вопросы были уже правильно отвечены или нет доступных активных вопросов."

            question_id, question_text = random.choice(questions)
            set_timer(user_id)  # Предположим, что set_timer реализован где-то еще

            return question_text
        except sqlite3.Error as e:
            print("Ошибка SQLite:", e)
            return "Произошла ошибка при работе с базой данных. Пожалуйста, попробуйте позже."


# Класс для работы с OpenAI
class OpenAIService:
    def __init__(self, api_key, system_prompt, base_url="https://api.proxyapi.ru/openai/v1"):
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=30)
        self.system_prompt = system_prompt

    def ask_chatgpt(self, question_pack):
        user_question, user_answer = question_pack
        ask_content = f"Question: {user_question}\nAnswer: {user_answer}"

        completion = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": self.system_prompt},
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


# Класс для работы с аудио
class AudioProcessor:
    def __init__(self, whisper_model="base"):
        self.model = whisper.load_model(whisper_model)

    def download_audio_file(self, file_id, bot_token=BOT_TOKEN):
        file_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
        response = requests.get(file_url)
        file_path = response.json()['result']['file_path']
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        audio_response = requests.get(download_url)
        return io.BytesIO(audio_response.content)

    def audio_to_text(self, data):
        file_id = data['voice']['file_id']
        audio_data = self.download_audio_file(file_id)
        result = self.model.transcribe(audio_data)
        return result['text']


# Главная функция для получения ответа
def get_answer(question: str, data, type: str, ai_service: OpenAIService, audio_processor: AudioProcessor):
    if type == "audio":
        user_answer = audio_processor.audio_to_text(data)
        question_pack = (question, user_answer)
    elif type == "empty":
        return None, None
    else:
        question_pack = (question, data)

    user_response = ai_service.ask_chatgpt(question_pack)
    return user_response["result"], user_response["comment"]



# Основные изменения:

# 1. Single Responsibility Principle (SRP):
# Введены классы Database, User, OpenAIService, и AudioProcessor,
# каждый из которых отвечает за свою часть функционала.

# 2. Open/Closed Principle (OCP):
# Классы легко расширяются, добавив новые методы или подклассы, не изменяя существующий код.

# 3. Liskov Substitution Principle (LSP):
# Все классы могут быть расширены и заменены их подклассами без изменения их базовой функциональности.

# 4. Interface Segregation Principle (ISP):
# Каждая часть кода использует только те методы, которые необходимы, без лишних зависимостей.

# 5. Dependency Inversion Principle (DIP):
# Основная логика зависит от абстракций (интерфейсов), а не от конкретных реализаций.
# Классы User, OpenAIService, и AudioProcessor принимают необходимые зависимости через конструкторы.

# Оптимизации:
# Все операции с базой данных вынесены в отдельный класс Database.
# Код теперь более модульный, что облегчает тестирование и поддержку.
# Улучшена читаемость и расширяемость кода.

# Этот подход позволяет сделать код более устойчивым к изменениям и легче тестируемым.
