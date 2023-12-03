import sqlite3
from datetime import datetime


def connect(db_name: str):
    # Создаем подключение к базе данных (файл my_database.db будет создан)
    connection = sqlite3.connect(db_name)

    cursor = connection.cursor()

    # Создаем таблицу Users
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS Records (
        id INTEGER PRIMARY KEY,
        amount REAL NOT NULL,
        date TIMESTAMP NOT NULL
    )
    """
    )
    return connection


def insert_value_in_db(value) -> bool:
    conn = connect("milk.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Records (amount, date) VALUES (?, ?)",
        (value, datetime.now().strftime("%B %d, %Y %I:%M%p")),
    )
    conn.commit()
    conn.close()
    return True


def select_all_records() -> list:
    conn = connect("milk.db")
    cursor = conn.cursor()
    cursor.execute("SELECT amount, date FROM Records")
    result = list(cursor.fetchall())
    conn.close()
    return result
