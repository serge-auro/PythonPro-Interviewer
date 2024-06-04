import sqlite3


def init_db():
    conn = sqlite3.connect('sqlite.db')

    # Создаем курсор
    cursor = conn.cursor()

    # SQL-запросы для создания таблиц
    create_user_table = '''
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY,
            active BOOLEAN DEFAULT 1,
            date_created DATE DEFAULT CURRENT_DATE,
            user_lvl TEXT DEFAULT 'junior',
            user_minute INTEGER DEFAULT 2
        );
       '''

    create_question_table = '''
        CREATE TABLE IF NOT EXISTS question (
            id INTEGER PRIMARY KEY,
            name TEXT,
            answer TEXT,
            active BOOLEAN DEFAULT 1,
            theme TEXT,
            rate INTEGER
        );
        '''

    create_user_stat_table = '''
        CREATE TABLE IF NOT EXISTS user_stat (
            user_id INTEGER,
            question_id INTEGER,
            correct BOOLEAN,
            timestamp DATE DEFAULT CURRENT_DATE,
            FOREIGN KEY (user_id) REFERENCES user (id),
            FOREIGN KEY (question_id) REFERENCES question (id),
            UNIQUE(user_id, question_id)
        );
        '''

    create_user_notify_table = '''
        CREATE TABLE IF NOT EXISTS user_notify (
            user_id INTEGER,
            question_id INTEGER,
            timedate TEXT,
            active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES user (id)
        );
        '''

    create_question_state_table = '''
        CREATE TABLE IF NOT EXISTS question_state (
            user_id INTEGER,
            question_id INTEGER,
            active BOOLEAN,
            PRIMARY KEY (user_id, question_id)
        );
    '''

    # Выполнение SQL - запросов
    cursor.execute(create_user_table)
    cursor.execute(create_question_table)
    cursor.execute(create_user_stat_table)
    cursor.execute(create_user_notify_table)
    cursor.execute(create_question_state_table)

    # Сохранение изменений и закрытие соединения
    conn.commit()
    conn.close()


def add_test_info():
    conn = sqlite3.connect('sqlite.db')
    # Создаем курсор
    cursor = conn.cursor()

    # SQL-запросы для заполнения таблиц тестовыми данными
    test_user = '''
    INSERT INTO user(id, active, date_created, user_lvl, user_minute)
        VALUES
        (1234567891, 1, '2023-01-01', 'junior', 1),
        (1234567892, 0, '2023-02-01', 'middle', 2),
        (1234567893, 1, '2023-03-01', 'senior', 2),
        (1234567894, 0, '2023-04-01', 'junior', 3),
        (1234567895, 1, '2023-05-01', 'middle', 1)
        '''

    test_question = '''
    INSERT INTO question (name, answer, active, theme, rate)
        VALUES
         ('Question 1', 'Answer 1', 1, 'Theme 1', 3),
         ('Question 2', 'Answer 2', 0, 'Theme 2', 5),
         ('Question 3', 'Answer 3', 1, 'Theme 3', 20),
         ('Question 4', 'Answer 4', 0, 'Theme 4', 50),
         ('Question 5', 'Answer 5', 1, 'Theme 5', 70)
         '''

    test_user_stat = '''
    INSERT INTO user_stat (user_id, question_id, correct) 
        VALUES 
        (1234567891, 1, 1),
        (1234567892, 2, 0),
        (1234567893, 3, 1),
        (1234567894, 4, 1),
        (1234567895, 5, 0)
    '''

    test_user_notify = '''
    INSERT INTO user_notify (user_id, timedate, active, question_id) 
        VALUES
        (1234567891, '2024-05-01 10:00:00', 1, 1),
        (1234567892, '2024-05-02 11:05:00', 0, 2),
        (1234567893, '2024-05-03 12:10:30', 1, 3),
        (1234567894, '2024-05-04 13:30:00', 1, 4),
        (1234567895, '2024-05-05 14:00:55', 0, 5)
    '''

    test_question_state = '''
    INSERT INTO question_state (user_id, question_id, active) 
        VALUES
        (1234567891, 1, 1),
        (1234567892, 2, 0),
        (1234567893, 3, 1),
        (1234567894, 4, 1),
        (1234567895, 5, 0)
    '''

    cursor.execute(test_user)
    cursor.execute(test_question)
    cursor.execute(test_user_stat)
    cursor.execute(test_user_notify)
    cursor.execute(test_question_state)

    # Сохранение изменений и закрытие соединения
    conn.commit()
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


# Создание таблиц и тестовое заполнение
init_db()
# add_test_info()


# Проверка таблиц
view_tables("user")
view_tables("question")
view_tables("user_stat")
view_tables("user_notify")
view_tables("question_state")
