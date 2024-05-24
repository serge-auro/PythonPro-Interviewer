import sqlite3


def init_db():
    conn = sqlite3.connect('sqlite.db')

    # TODO

    conn.commit()
    conn.close()


def add_test_info():
    conn = sqlite3.connect('sqlite.db')

    # TODO

    conn.commit()
    conn.close()
