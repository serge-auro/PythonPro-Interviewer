import telebot
from config import BOT_TOKEN
import time
import logging
from telebot import types
import threading
from backend import (init_user as backend_init_user, get_report as backend_get_report, skip_timer as backend_skip_timer,
                     get_question as backend_get_question, process_answer as backend_process_answer, update_user_stat,
                     clear_user_stat as be_clear_user_stat)

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
            bot.stop_polling()
            time.sleep(5)  # Дайте немного времени перед перезапуском
            if args and args[0] and hasattr(args[0], 'chat'):
                handle_start(args[0])  # Вызов стартового меню
    return wrapper

# Обработчик команды /start
@bot.message_handler(commands=['start'])
@error_handler
def handle_start(message):
    user_id = message.from_user.id
    backend_init_user(user_id)
    bot.send_message(user_id, "Приветствую! Я ваш бот-интервьюер по Python")
    show_menu(user_id)

# Функция для отображения основного меню
def show_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button_start_interview = types.KeyboardButton("🚀 Получить вопрос")
    button_request_report = types.KeyboardButton("📊 Запросить отчет")
    button_reset_result = types.KeyboardButton("🔄 Обнулить результат")
    button_description = types.KeyboardButton("ℹ️ Описание бота")

    markup.add(button_start_interview, button_request_report, button_reset_result, button_description)
    bot.send_message(user_id, "Выберите действие:", reply_markup=markup)

# Функция для начала интервью
@error_handler
def start_interview(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_end_interview = types.KeyboardButton("⛔️ Пропустить вопрос")
    markup.add(button_end_interview)

    question = backend_get_question(user_id)
    question_id = question['id']

    if isinstance(question, dict) and "name" in question and "id" in question:
        user_states[user_id] = ("waiting_for_answer", question)
        bot.send_message(user_id, question["name"], reply_markup=markup)
        # Удаление вопроса через 2 минуты
        threading.Thread(target=go_to_next_question_after_timer, args=(user_id, question_id)).start()

    else:
        bot.send_message(user_id, "Похоже, проблема со связью... Давайте попробуем снова.")

@error_handler
def go_to_next_question_after_timer(user_id, question_id):
    time.sleep(120)
    if user_states.get(user_id) and user_states[user_id][1]['id'] == question_id and user_states[user_id][0] == "waiting_for_answer":
        bot.send_message(user_id, "Время вышло.")
        user_states[user_id] = ("menu", None)
        # Запись в user_stat, что ответ неверный
        update_user_stat(user_id, question_id, 0)
        show_menu(user_id)
        user_states[user_id] = ("menu", None)

# Функция для обработки ответов
@error_handler
def handle_answer(message):
    user_id = message.from_user.id
    user_state = user_states.get(user_id)

    if user_state and user_state[0] == "waiting_for_answer":
        question = user_state[1]
        if message.content_type == 'text':
            user_response = message.text
            response_type = "text"
        elif message.content_type == 'voice':
            try:
                # file_info = bot.get_file(message.voice.file_id)
                # file = bot.download_file(file_info.file_path)
                # user_response = file  # Здесь вместо простого присвоения вы можете сохранить файл и передать путь к нему
                file_id = message.voice.file_id
                logging.info(f"Requesting file id: {file_id}")
                user_response = file_id
                response_type = "audio"
                # bot.send_message(user_id, "Думаю...")
            except Exception as e:
                logging.info(f"handle_answer 1: {e} ")
                bot.send_message(user_id, "Не могу понять ваш ответ. Пожалуйста, попробуйте снова.")
                return
        else:
            bot.send_message(user_id, "Отправьте текстовое сообщение или запишите ответ.")
            return

        bot.send_message(user_id, "Вас понял, сейчас подумаю...")
        try:
            result, comment = backend_process_answer(user_id, user_response, response_type)  # Вызываем метод бэкенда для обработки ответа
            bot.send_message(user_id, result)
            bot.send_message(user_id, comment)

            # # Запись в user_stat, если ответ верный
            # if result.lower() == "верно":  # Проверяем, что результат соответствует "Верно"
            #     update_user_stat(user_id, question['id'], 1)
        except Exception as e:
            logging.info(f"handle_answer 2: {e} ")
            bot.send_message(user_id, "Мисскоммуникация... Пожалуйста, попробуйте снова.")

        show_menu(user_id)
        user_states[user_id] = ("menu", None)
    else:
        bot.send_message(user_id, "Выбери действие из меню.")

# Функция для пропуска вопроса
@error_handler
def skip_question(user_id):
    backend_skip_timer(user_id)
    show_menu(user_id)

@error_handler
def clear_user_stat(user_id):
    be_clear_user_stat(user_id)
    show_menu(user_id)

# Словарь для обработки текстовых сообщений
commands = {
    "🚀 Старт": handle_start,
    "🚀 Получить вопрос": lambda message: start_interview(message.from_user.id),
    "📊 Запросить отчет": lambda message: bot.send_message(message.from_user.id, backend_get_report(message.from_user.id)),
    "🔄 Обнулить результат": lambda message: (
        clear_user_stat(message.from_user.id),
        bot.send_message(message.from_user.id, "Ваш результат был обнулен.")
    ),
    "ℹ️ Описание бота": lambda message: bot.send_message(message.from_user.id, "Я - ваш бот, предназначеный для тренировки навыков интервью по Python."),
    "⛔️ Пропустить вопрос": lambda message: skip_question(message.from_user.id)
}

# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
@error_handler
def handle_text(message):
    user_id = message.from_user.id
    if message.text in commands:
        commands[message.text](message)
    elif user_states.get(user_id) and user_states[user_id][0] == "waiting_for_answer":
        handle_answer(message)
    else:
        bot.send_message(user_id, "Пожалуйста, выберите действие из меню.")

@bot.message_handler(content_types=['text', 'voice'])
@error_handler
def handle_text_and_voice(message):
    user_id = message.from_user.id

    if message.content_type == 'text' and message.text in commands:
        commands[message.text](message)
    elif user_states.get(user_id) and user_states[user_id][0] == "waiting_for_answer":
        handle_answer(message)
    else:
        bot.send_message(user_id, "Пожалуйста, выберите действие из меню.")

# Основной цикл для опроса и обработки сообщений
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        time.sleep(1)
