import aiosqlite
import os
from datetime import datetime

DB_PATH = "bot.db"

async def init_db():
    """Создаёт все необходимые таблицы"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей (уже была, добавим поле balance, last_daily)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0,
                last_daily DATE,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Таблица сообщений (без изменений)
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
        # Таблица товаров
        await db.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                price REAL,
                stock INTEGER DEFAULT -1,  -- -1 бесконечно
                emoji TEXT DEFAULT '📦'
            )
        ''')
        # Таблица инвентаря
        await db.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_id INTEGER,
                quantity INTEGER DEFAULT 1,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, item_id)
            )
        ''')
        # Таблица транзакций (для истории)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user INTEGER,
                to_user INTEGER,
                amount REAL,
                type TEXT,  -- 'transfer', 'game', 'purchase', 'bonus'
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.commit()

# ---------- Функции для пользователей и баланса ----------
async def add_user(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
        ''', (user_id, username, first_name))
        await db.commit()

async def get_user_balance(user_id: int) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0.0

async def update_user_balance(user_id: int, delta: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO users (user_id, balance) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
        ''', (user_id, delta, delta))
        await db.commit()

async def get_top_balance(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            SELECT user_id, balance FROM users
            ORDER BY balance DESC
            LIMIT ?
        ''', (limit,))
        rows = await cursor.fetchall()
        return rows

# ---------- Функции для магазина ----------
async def get_items():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            SELECT id, name, description, price, stock, emoji
            FROM items WHERE stock != 0 ORDER BY price
        ''')
        rows = await cursor.fetchall()
        return [dict(zip(['id','name','description','price','stock','emoji'], row)) for row in rows]

async def buy_item(user_id: int, item_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        # Найти предмет
        cursor = await db.execute('SELECT id, price, stock FROM items WHERE name = ?', (item_name,))
        item = await cursor.fetchone()
        if not item:
            return False, "Предмет не найден."
        item_id, price, stock = item
        # Проверить баланс
        cursor = await db.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        row = await cursor.fetchone()
        balance = row[0] if row else 0
        if balance < price:
            return False, "Недостаточно средств."
        # Списать баланс
        await db.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (price, user_id))
        # Уменьшить остаток
        if stock > 0:
            await db.execute('UPDATE items SET stock = stock - 1 WHERE id = ?', (item_id,))
        # Добавить в инвентарь
        await db.execute('''
            INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, 1)
            ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + 1
        ''', (user_id, item_id))
        # Записать транзакцию
        await db.execute('''
            INSERT INTO transactions (from_user, to_user, amount, type) VALUES (?, NULL, ?, 'purchase')
        ''', (user_id, price))
        await db.commit()
        return True, f"Вы купили {item_name}!"

async def get_inventory(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            SELECT i.name, i.emoji, inv.quantity
            FROM inventory inv
            JOIN items i ON inv.item_id = i.id
            WHERE inv.user_id = ?
        ''', (user_id,))
        rows = await cursor.fetchall()
        return [dict(zip(['name','emoji','quantity'], row)) for row in rows]

# Админские функции (добавление предметов)
async def add_item_to_db(name: str, description: str, price: float, emoji: str = '📦', stock: int = -1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO items (name, description, price, emoji, stock)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, description, price, emoji, stock))
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
