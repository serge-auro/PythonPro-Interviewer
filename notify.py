import sqlite3
import schedule
import time
from backend import get_notify
from datetime import datetime
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("PythonPro Interviewer notify is being started")


def notify_users():
    conn = sqlite3.connect('sqlite.db')
    try:
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        query = '''
        SELECT user_id, question_id
          FROM user_notify
         WHERE timedate <= ?
           AND active = 1
        '''

        cursor.execute(query, (current_time,))
        notifications = cursor.fetchall()

        for user_id, question_id in notifications:
            logging.info(f"Sending notification {user_id} user with {question_id} question.")
            get_notify(user_id)

        # Опционально, обновить записи, чтобы они больше не были активны
        cursor.execute('''
        UPDATE user_notify
           SET active = 0
         WHERE timedate <= ?
           AND active = 1
        ''', (current_time,))

        conn.commit()
    except sqlite3.Error as e:
        print("SQLite error:", e)
    finally:
        conn.close()


# Расписание крон задачи
schedule.every().second.do(notify_users)  # test message

# Запуск крон задачи
while True:
    schedule.run_pending()
    time.sleep(1)
