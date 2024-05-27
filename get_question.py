import sqlite3
# import telebot
import random

# API_TOKEN = 'YOUR_TELEGRAM_BOT_API_TOKEN'  # Токен API вашего Telegram бота
# bot = telebot.TeleBot(API_TOKEN)  # Создание объекта бота с использованием токена API


def connect_to_database():  # Определение функции для подключения к базе данных SQLite
    return sqlite3.connect('sqlite.db')  # Возвращает объект соединения с базой данных


def get_random_question(user_id):  # Определение функции для получения случайного вопроса
    try:
        conn = connect_to_database()  # Подключение к базе данных
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

        return question_text  # Возвращает текст случайного вопроса

    except sqlite3.Error as e:  # Обработка исключения SQLite
        print("Ошибка SQLite:", e)  # Вывод сообщения об ошибке
        return "Произошла ошибка при работе с базой данных. Пожалуйста, попробуйте позже."

    finally:
        conn.close()  # Закрытие соединения с базой данных в любом случае, даже если возникло исключение

# Пример использования функции
user_id = 12345  # Пример user_id
print(get_random_question(user_id))  # Вывод случайного вопроса для пользователя с указанным user_id
