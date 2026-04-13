import psycopg2
import os
from datetime import datetime, timezone


def get_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        income REAL DEFAULT 0,
        limit_amount REAL DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        amount REAL,
        category TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()


def save_income(user_id, income):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO users (user_id, income)
    VALUES (%s, %s)
    ON CONFLICT (user_id) DO UPDATE SET income=EXCLUDED.income
    """, (user_id, income))

    conn.commit()
    cursor.close()
    conn.close()


def get_income(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT income FROM users WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()
    return result[0] if result else 0


def save_limit(user_id, limit_amount):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO users (user_id, limit_amount)
    VALUES (%s, %s)
    ON CONFLICT (user_id) DO UPDATE SET limit_amount=EXCLUDED.limit_amount
    """, (user_id, limit_amount))

    conn.commit()
    cursor.close()
    conn.close()


def get_limit(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT limit_amount FROM users WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()
    return result[0] if result else 0


def get_total_expenses(user_id):
    now = datetime.now(timezone.utc)
    month_prefix = now.strftime("%Y-%m")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE user_id = %s AND created_at LIKE %s
        """,
        (user_id, f"{month_prefix}%"),
    )
    row = cursor.fetchone()

    cursor.close()
    conn.close()
    return float(row[0]) if row else 0.0


def save_expense(user_id, amount, category):
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        """
        INSERT INTO expenses (user_id, amount, category, created_at)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, amount, category, created_at),
    )

    conn.commit()
    cursor.close()
    conn.close()


def get_expenses_by_category(user_id):
    now = datetime.now(timezone.utc)
    month_prefix = now.strftime("%Y-%m")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT category, COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE user_id = %s AND created_at LIKE %s
        GROUP BY category
        ORDER BY SUM(amount) DESC
        """,
        (user_id, f"{month_prefix}%"),
    )
    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    return rows