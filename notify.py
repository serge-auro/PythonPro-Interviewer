import sqlite3
import schedule
import time
from backend import get_notify


# Проверка всех пользователей
def notify_users():
    user_id = 0
    # TODO ТУТ БУДЕТ КОД
    get_notify(user_id, question_id)


# Расписание крон задачи
schedule.every().second.do(notify_users) # test message

# Запуск крон задачи
while True:
    schedule.run_pending()
    time.sleep(1)
