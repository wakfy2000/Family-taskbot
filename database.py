import sqlite3
import logging
from datetime import datetime, timedelta
from config import DATABASE_FILE

logger = logging.getLogger(__name__)


def init_db():
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            message_id INTEGER,
            task_text TEXT,
            created_by TEXT,
            taken_by TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'open',
            urgency TEXT DEFAULT 'Важная',
            repeat TEXT DEFAULT 'none',
            taken_at TEXT
        )
        ''')
    logger.info("База данных готова")


def add_task(chat_id, message_id, task_text, created_by, urgency="Важная", repeat="none"):
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO tasks (chat_id, message_id, task_text, created_by, created_at, urgency, repeat) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (chat_id, message_id, task_text, created_by, datetime.now().isoformat(), urgency, repeat)
        )
    logger.info(f"Задача добавлена: '{task_text[:50]}...'")

def take_task(message_id, taken_by):
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE tasks SET taken_by = ?, status = "taken", taken_at = ? WHERE message_id = ?',
            (taken_by, datetime.now().isoformat(), message_id)
        )
    logger.info(f"Задача взята пользователем: {taken_by}")


def mark_task_done(message_id):
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE tasks SET status = "done" WHERE message_id = ?', (message_id,))
    logger.info(f"Задача отмечена как выполненная, message_id: {message_id}")


def get_task_by_message(message_id):
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tasks WHERE message_id = ?', (message_id,))
        return cursor.fetchone()


def get_chat_tasks(chat_id):
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT task_text, created_by, taken_by, status, urgency, repeat FROM tasks WHERE chat_id = ? ORDER BY created_at DESC',
            (chat_id,)
        )
        return cursor.fetchall()


def get_user_tasks(chat_id, username):
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT task_text, created_by, taken_by, status, urgency, repeat FROM tasks WHERE chat_id = ? AND taken_by = ? ORDER BY created_at DESC',
            (chat_id, username)
        )
        return cursor.fetchall()


def delete_task(message_id):
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE message_id = ?', (message_id,))
    logger.info(f"Задача удалена, message_id: {message_id}")


def get_overdue_tasks():
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        threshold = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor.execute(
            'SELECT chat_id, message_id, task_text, taken_by FROM tasks WHERE status = "taken" AND taken_at IS NOT NULL AND taken_at < ?',
            (threshold,)
        )
        return cursor.fetchall()

def update_task_urgency(message_id, new_urgency):
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE tasks SET urgency = ? WHERE message_id = ?', (new_urgency, message_id))
    logger.info(f"Срочность задачи обновлена, message_id: {message_id}, urgency: {new_urgency}")