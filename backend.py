from notify import *
import sqlite3
from datetime import datetime
from datetime import timedelta

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
def get_answer(data, type : TYPE):
    if type == "audio":
        audio_to_text(data)
    elif type == "empty":
        pass  # TODO ТУТ БУДЕТ КОД

    return ("Ответ верный. Уточнения:"
            "SOLID - это акроним, который представляет собой пять основных принципов объектно-ориентированного программирования и дизайна. Каждая буква в слове SOLID представляет собой один из этих принципов:"
            "1. S - Принцип единственной ответственности (Single Responsibility Principle): Класс должен иметь только одну причину для изменения."
            "2. O - Принцип открытости/закрытости (Open/Closed Principle): Программные сущности должны быть открыты для расширения, но закрыты для изменения."
            "3. L - Принцип подстановки Барбары Лисков (Liskov Substitution Principle): Объекты в программе должны быть заменяемыми исходными объектами."
            "4. I - Принцип разделения интерфейса (Interface Segregation Principle): Клиенты не должны зависеть от интерфейсов, которые они не используют."
            "5. D - Принцип инверсии зависимостей (Dependency Inversion Principle): Модули верхнего уровня не должны зависеть от модулей нижнего уровня. Оба должны зависеть от абстракций.")



# Трансформация в текст
def audio_to_text(data):
    return "SOLID - это акроним, который представляет собой пять основных принципов объектно-ориентированного программирования и дизайна."


# Отслеживание уведомлений
def get_notify(user_id):
    get_answer(None, "text")