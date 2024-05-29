# Заполнение таблицы вопросов из файла csv

# Импорт библиотек
import sqlite3
import csv


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
        next(csv_reader)

        # Чтение строк и вставка данных в БД
        for row in csv_reader:
            # column1 = row[0]
            # column2 = row[1]
            # column3 = row[2]
            cursor.execute('''
                    INSERT INTO question (name, theme, active, rate) 
                    VALUES (?, ?, ?, ?)
                ''', (row[1], row[2], 1, row[0]))


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


def view_tables(name_table):
    conn = sqlite3.connect('sqlite.db')
    # Создаем курсор
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM " + name_table)

    rows = cursor.fetchall()

    # Печать заголовков столбцов
    print(f"Проверка таблицы - {name_table}")
    column_names = [description[0] for description in cursor.description]
    print(column_names)

    # Печать всех строк
    for row in rows:
        print(row)

    # Закрытие соединения
    conn.close()


db_from_csv()

# Проверка содержимого таблицы
view_tables(table_name)
