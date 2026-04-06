import sqlite3


def get_connection():
    return sqlite3.connect("expenses.db")


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        income REAL DEFAULT 0,
        limit_amount REAL DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        category TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_income(user_id, income):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO users (user_id, income)
    VALUES (?, ?)
    ON CONFLICT(user_id) DO UPDATE SET income=excluded.income
    """, (user_id, income))

    conn.commit()
    conn.close()


def get_income(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT income FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    conn.close()
    return result[0] if result else 0


def save_limit(user_id, limit_amount):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO users (user_id, limit_amount)
    VALUES (?, ?)
    ON CONFLICT(user_id) DO UPDATE SET limit_amount=excluded.limit_amount
    """, (user_id, limit_amount))

    conn.commit()
    conn.close()


def get_limit(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT limit_amount FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    conn.close()
    return result[0] if result else 0