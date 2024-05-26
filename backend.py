from notify import *
import sqlite3
from datetime import datetime
from datetime import timedelta
from config import BOT_TOKEN, OPENAI_API_KEY, SYSTEM_PROMPT
from openai import OpenAI

TYPE = ("text", "audio", "empty")


# Инициализация пользоавтеля
def init_user(user_id):
    pass


# Запрос статистики
def get_report(user_id):
    return ("Количество заданных вопросов ***\n "
            "Правильных ответов **%\n"
            "Неправильных **%")


# Получение вопроса
def get_question(user_id):
    set_timer(user_id)
    return "Что такое SOLID?"


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


# Трансформация в текст
def audio_to_text(data):
    return "SOLID - это акроним, который представляет собой пять основных принципов объектно-ориентированного программирования и дизайна."


# Отслеживание уведомлений
def get_notify(user_id):
    get_answer(None, "text")