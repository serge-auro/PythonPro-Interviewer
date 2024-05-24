import telebot
from config import BOT_TOKEN
from backend import *
import time
from datetime import datetime


print("PythonPro Interviewer is being started", datetime.now())

bot = telebot.TeleBot(BOT_TOKEN)


# Декоратор - Обработчик ошибок
def error_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error in {func.__name__}: {e}")
            bot.stop_polling()
            time.sleep(5)  # Дайте немного времени перед перезапуском
            # bot.polling(none_stop=True)
            # TODO вызвать стартовое меню handle_start()
    return wrapper


# ТУТ БУДЕТ КОД
# ТУТ БУДЕТ КОД
# ТУТ БУДЕТ КОД
# ТУТ БУДЕТ КОД
# ТУТ БУДЕТ КОД



# bot.polling(none_stop=True)
if __name__ == "__main__":
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)