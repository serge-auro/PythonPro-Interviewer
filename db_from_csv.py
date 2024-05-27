# Заполнение таблицы вопросов из файла csv

# Импорт библиотек
import sqlite3
import csv
import init_db as db

# Настройка параметров
csv_file_path = 'easyoffer.csv'  # Путь к CSV файлу
sqlite_db_path = 'sqlite.db'  # Путь к базе данных SQLite
table_name = 'question'  # Имя таблицы в базе данных


def data_from_csv(cursor):
    # Берем нужные данные из файла, заполняем таблицу построчно
    # Открытие CSV файла и чтение данных
    with open(csv_file_path, 'r', newline='', encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file)

        # Пропуск заголовка CSV файла, если он есть
        header = next(csv_reader)

        # Чтение строк и вставка данных во второй и третий столбцы
        for row in csv_reader:
            column2 = row[1]  # второй столбец
            column3 = row[2]  # третий столбец
            cursor.execute('''
                    INSERT INTO question (name, theme, active) 
                    VALUES (?, ?, ?)
                ''', (column2, column3, 1))


def db_from_csv():
    # Соединение с базой данных SQLite
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()
    # Очистка таблицы
    cursor.execute('DELETE FROM ' + table_name)

    # Запись в таблицу из файла csv
    data_from_csv(cursor)
    # Сохранение изменений
    conn.commit()

    # Закрытие соединения с базой данных
    conn.close()


db_from_csv()

# Проверка содержимого таблицы
db.view_tables(table_name)
