import aiosqlite
import os

DB_PATH = "bot.db"

async def init_db():
    """Создаёт таблицы, если их ещё нет"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Таблица для подсчёта сообщений по дням
        await db.execute('''
            CREATE TABLE IF NOT EXISTS message_counts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                date TEXT,
                count INTEGER DEFAULT 0,
                UNIQUE(user_id, chat_id, date)
            )
        ''')
        await db.commit()

async def add_user(user_id: int, username: str, first_name: str):
    """Добавляет пользователя в базу, если его там нет"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
        ''', (user_id, username, first_name))
        await db.commit()

async def increment_message_count(user_id: int, chat_id: int, date: str):
    """Увеличивает счётчик сообщений для пользователя в конкретном чате за указанную дату"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO message_counts (user_id, chat_id, date, count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id, chat_id, date) DO UPDATE SET count = count + 1
        ''', (user_id, chat_id, date))
        await db.commit()

async def get_top_users(chat_id: int, since_date: str, limit: int = 10):
    """Возвращает список (user_id, total_count) за период начиная с since_date"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            SELECT user_id, SUM(count) as total
            FROM message_counts
            WHERE chat_id = ? AND date >= ?
            GROUP BY user_id
            ORDER BY total DESC
            LIMIT ?
        ''', (chat_id, since_date, limit))
        rows = await cursor.fetchall()
        return rows