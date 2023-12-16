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
        amount REAL NOT NULL
    )
    """
    )
    return connection


def insert_value_in_db(value) -> bool:
    conn = connect("milk.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Records (amount) VALUES (?)",
        (value,),
    )
    conn.commit()
    conn.close()
    return True


def count_records() -> int:
    conn = connect("milk.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Records")
    result = cursor.fetchone()[0]
    conn.close()
    return result


def sum_records() -> int:
    conn = connect("milk.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM Records")
    result = cursor.fetchone()[0]
    conn.close()
    return result
