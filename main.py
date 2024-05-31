import telebot
from config import BOT_TOKEN
import time
import logging
from datetime import datetime, timedelta
import sqlite3
from telebot import types
from backend import (init_user as backend_init_user, get_report as backend_get_report, skip_timer as backend_skip_timer,
                     get_question as backend_get_question, process_answer as backend_process_answer)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}

# Вывод сообщения о запуске бота
logging.info("PythonPro Interviewer is being started")


# Декоратор - Обработчик ошибок
def error_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {e}")
            bot.stop_polling()
            time.sleep(5)  # Дайте немного времени перед перезапуском
            if args and args[0]:
                handle_start(args[0])  # Вызов стартового меню

    return wrapper


# Обработчик команды /start
@bot.message_handler(commands=['start'])
@error_handler
def handle_start(message):
    user_id = message.from_user.id
    backend_init_user(user_id)
    bot.send_message(user_id, "Я твой бот-интервьюер по Python")
    show_menu(user_id)


# Функция для отображения основного меню
def show_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button_start_interview = types.KeyboardButton("🚀 Начать интервью")
    button_request_report = types.KeyboardButton("📊 Запросить отчет")
    button_reset_result = types.KeyboardButton("🔄 Обнулить результат")
    button_description = types.KeyboardButton("ℹ️ Описание бота")

    markup.add(button_start_interview, button_request_report, button_reset_result, button_description)
    bot.send_message(user_id, "Выберите действие:", reply_markup=markup)


# Функция для отображения меню окончания интервью
@error_handler
def start_interview(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_end_interview = types.KeyboardButton("⛔️ Закончить интервью")
    markup.add(button_end_interview)

    question = backend_get_question(user_id)
    user_states[user_id] = "waiting_for_answer"
    bot.send_message(user_id, question["name"], reply_markup=markup)


# Функция для обработки ответов
@error_handler
def handle_answer(message):
    user_id = message.from_user.id
    if user_states.get(user_id) == "waiting_for_answer":
        if message.content_type == 'text':
            user_response = message.text
            response_type = "text"
        elif message.content_type == 'voice':
            file_info = bot.get_file(message.voice.file_id)
            file = bot.download_file(file_info.file_path)
            user_response = file  # Здесь вместо простого присвоения вы можете сохранить файл и передать путь к нему
            response_type = "audio"
        else:
            bot.send_message(user_id, "Пожалуйста, отправьте текстовое сообщение или аудио.")
            return

        bot.send_message(user_id, "Ваш ответ принят...")
        backend_process_answer(user_id, user_response, response_type)  # Вызываем метод бэкенда для обработки ответа
        show_menu(user_id)
    else:
        bot.send_message(user_id, "Пожалуйста, выберите действие из меню.")


# Функция для пропуска вопроса
@error_handler
def skip_question(user_id):
    backend_skip_timer(user_id)
    show_menu(user_id)


# Словарь для обработки текстовых сообщений
commands = {
    "🚀 Старт": handle_start,
    "🚀 Начать интервью": start_interview,
    "📊 Запросить отчет": lambda user_id: bot.send_message(user_id, backend_get_report(user_id)),
    "🔄 Обнулить результат": lambda user_id: bot.send_message(user_id, "Ваш результат был обнулен."),
    "ℹ️ Описание бота": lambda user_id: bot.send_message(user_id,
                                                         "Этот бот предназначен для тренировки навыков интервью по Python."),
    "⛔️ Пропустить вопрос": lambda user_id: skip_question(user_id)
}


# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
@error_handler
def handle_text(message):
    user_id = message.from_user.id
    if message.text in commands:
        commands[message.text](user_id)
    elif user_states.get(user_id) == "waiting_for_answer":
        handle_answer(message)
    else:
        bot.send_message(user_id, "Добро пожаловать. Пожалуйста, выберите действие из меню.")


# Основной цикл для опроса и обработки сообщений
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logging.error(f"Error: {e}")
        time.sleep(1)
