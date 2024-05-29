import telebot
from config import BOT_TOKEN
import time
from datetime import datetime
import sqlite3
from datetime import datetime
from datetime import timedelta
from telebot import types
from backend import (init_user as backend_init_user, get_report as backend_get_report, skip_timer as backend_skip_timer,
                     get_question as backend_get_question, get_answer as backend_get_answer)


bot = telebot.TeleBot(BOT_TOKEN)


# Вывод сообщения о запуске бота
print("PythonPro Interviewer is being started", datetime.now())
# TYPE = ("text", "audio", "empty")

# Декоратор - Обработчик ошибок
def error_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Вывод ошибки и остановка опроса
            print(f"Error in {func.__name__}: {e}")
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
def show_end_interview_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_end_interview = types.KeyboardButton("⛔️ Закончить интервью")
    markup.add(button_end_interview)
    bot.send_message(user_id, "Интервью началось. Для окончания выберите 'Закончить интервью'.", reply_markup=markup)

# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
@error_handler
def handle_text(message):
    user_id = message.from_user.id
    if message.text == "🚀 Старт":
        bot.send_message(user_id, "Инициализация пользователя...")
        backend_init_user(user_id)
        bot.send_message(user_id, "Пользователь успешно инициализирован.")
    elif message.text == "🚀 Начать интервью":
        bot.send_message(user_id, "Интервью начинается...")
        show_end_interview_menu(user_id)
        handle_question(message)
    elif message.text == "📊 Запросить отчет":
        bot.send_message(user_id, "Ваш отчет запрашивается. Пожалуйста, подождите.")
        report = backend_get_report(user_id)
        bot.send_message(user_id, report)
    elif message.text == "🔄 Обнулить результат":
        # TODO clear_result
        bot.send_message(user_id, "Ваш результат был обнулен.")
    elif message.text == "ℹ️ Описание бота":
        bot.send_message(user_id, "Этот бот предназначен для тренировки навыков интервью по Python.")
    elif message.text == "⛔️ Пропустить вопрос":
        backend_skip_timer(user_id)
        bot.send_message(user_id, "Интервью закончено. Для нового интервью воспользуйтесь командой /start или Начать интервью.")
        show_menu(user_id)
    else:
        bot.send_message(user_id, "Пожалуйста, выберите действие из меню.")

# Функция для обработки вопросов
def handle_question(message):
    user_id = message.from_user.id
    question = backend_get_question(user_id)

    answers = []
    # TODO добавить определение типа текст\аудио и исправить вызв backend_get_answer ниже
    for text, callback_data in backend_get_answer(question["name"], "что-то умное", "text"):
        answers.append((text, callback_data))

    markup = types.InlineKeyboardMarkup(row_width=1)
    for text, callback_data in answers:
        markup.add(types.InlineKeyboardButton(text, callback_data=callback_data))

    bot.send_message(user_id, question["name"], reply_markup=markup)

# Основной цикл для опроса и обработки сообщений
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)
