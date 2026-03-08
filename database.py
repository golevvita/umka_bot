import aiosqlite
from datetime import date, datetime

DB_NAME = 'bot.db'

async def create_table():
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0.0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_daily TIMESTAMP NULL,
                is_admin INTEGER DEFAULT 0   -- добавим позже, но сейчас можно не трогать
            )
        ''')
        # Таблица сообщений
        await db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                date DATE NOT NULL,
                count INTEGER DEFAULT 0,
                UNIQUE(user_id, chat_id, date)
            )
        ''')
        # --- НОВЫЕ ТАБЛИЦЫ ---
        # Таблица товаров
        await db.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                price REAL NOT NULL,
                emoji TEXT DEFAULT '📦',
                stock INTEGER DEFAULT -1,   -- -1 означает бесконечно
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Таблица инвентаря (что купили пользователи)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES items(id),
                UNIQUE(user_id, item_id)   -- один пользователь может иметь только одну запись на товар (количество накапливается)
            )
        ''')
        await db.commit()

        # Добавим колонку is_admin, если её нет (для будущих админ-команд)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
            await db.commit()
        except:
            pass

        # Добавим колонку last_daily, если её нет (уже делали, но на всякий случай)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN last_daily TIMESTAMP NULL")
            await db.commit()
        except:
            pass

    print("Все таблицы созданы или уже существуют.")

# ----- Функции для пользователей (были ранее) -----
async def add_user(tg_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                'INSERT INTO users (tg_id, username, first_name) VALUES (?, ?, ?)',
                (tg_id, username, first_name)
            )
            await db.commit()
            print(f"Пользователь {tg_id} добавлен в БД.")
        except aiosqlite.IntegrityError:
            pass

async def get_user(tg_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM users WHERE tg_id = ?', (tg_id,))
        return await cursor.fetchone()

async def get_balance(tg_id: int):
    user = await get_user(tg_id)
    return user['balance'] if user else None

async def update_balance(tg_id: int, amount: float):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET balance = balance + ? WHERE tg_id = ?', (amount, tg_id))
        await db.commit()

async def update_last_daily(tg_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET last_daily = CURRENT_TIMESTAMP WHERE tg_id = ?', (tg_id,))
        await db.commit()

async def can_claim_daily(tg_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('SELECT last_daily FROM users WHERE tg_id = ?', (tg_id,))
        row = await cursor.fetchone()
        if not row or row[0] is None:
            return True
        last = datetime.fromisoformat(row[0])
        now = datetime.now()
        delta = now - last
        return delta.total_seconds() >= 24 * 60 * 60

# ----- Функции для сообщений (были) -----
async def add_message_count(user_id: int, chat_id: int, msg_date: date):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            'UPDATE messages SET count = count + 1 WHERE user_id = ? AND chat_id = ? AND date = ?',
            (user_id, chat_id, msg_date.isoformat())
        )
        if cursor.rowcount == 0:
            await db.execute(
                'INSERT INTO messages (user_id, chat_id, date, count) VALUES (?, ?, ?, 1)',
                (user_id, chat_id, msg_date.isoformat())
            )
        await db.commit()

async def get_top_users(chat_id: int, days: int = None):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        if days is None:
            cursor = await db.execute('''
                SELECT user_id, SUM(count) as total
                FROM messages
                WHERE chat_id = ?
                GROUP BY user_id
                ORDER BY total DESC
                LIMIT 10
            ''', (chat_id,))
        else:
            cursor = await db.execute('''
                SELECT user_id, SUM(count) as total
                FROM messages
                WHERE chat_id = ? AND date >= date('now', ?)
                GROUP BY user_id
                ORDER BY total DESC
                LIMIT 10
            ''', (chat_id, f'-{days} days'))
        rows = await cursor.fetchall()
        return [(row['user_id'], row['total']) for row in rows]

# ----- НОВЫЕ ФУНКЦИИ ДЛЯ МАГАЗИНА -----

async def get_all_items():
    """Возвращает список всех товаров (для магазина)."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM items ORDER BY price')
        rows = await cursor.fetchall()
        return rows

async def get_item(item_id: int = None, name: str = None):
    """Получить товар по ID или имени."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        if item_id:
            cursor = await db.execute('SELECT * FROM items WHERE id = ?', (item_id,))
        elif name:
            cursor = await db.execute('SELECT * FROM items WHERE name = ?', (name,))
        else:
            return None
        return await cursor.fetchone()

async def add_item(name: str, description: str, price: float, emoji: str = '📦', stock: int = -1):
    """Добавить новый товар (для админа)."""
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                'INSERT INTO items (name, description, price, emoji, stock) VALUES (?, ?, ?, ?, ?)',
                (name, description, price, emoji, stock)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False  # товар с таким именем уже есть

async def update_item(item_id: int, **kwargs):
    """Обновить поля товара (для админа)."""
    async with aiosqlite.connect(DB_NAME) as db:
        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ['name', 'description', 'price', 'emoji', 'stock']:
                fields.append(f"{key} = ?")
                values.append(value)
        if not fields:
            return False
        values.append(item_id)
        query = f"UPDATE items SET {', '.join(fields)} WHERE id = ?"
        await db.execute(query, values)
        await db.commit()
        return True

async def delete_item(item_id: int):
    """Удалить товар (для админа)."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM items WHERE id = ?', (item_id,))
        await db.commit()
        return True

async def buy_item(user_id: int, item_id: int, quantity: int = 1):
    """
    Обрабатывает покупку: проверяет наличие, списывает деньги, добавляет в инвентарь.
    Возвращает True при успехе, иначе False с описанием ошибки.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        # Получаем товар
        cursor = await db.execute('SELECT * FROM items WHERE id = ?', (item_id,))
        item = await cursor.fetchone()
        if not item:
            return False, "Товар не найден."

        # Проверяем баланс пользователя
        user = await get_user(user_id)
        if not user:
            return False, "Пользователь не найден."
        total_price = item[3] * quantity  # price * quantity (price на позиции 3)
        if user['balance'] < total_price:
            return False, f"Недостаточно средств. Нужно {total_price}, у вас {user['balance']}"

        # Проверяем наличие на складе
        if item[5] != -1 and item[5] < quantity:  # stock на позиции 5
            return False, f"Недостаточно товара на складе. Осталось: {item[5]}"

        # Начинаем транзакцию
        try:
            # Списание денег
            await db.execute('UPDATE users SET balance = balance - ? WHERE tg_id = ?', (total_price, user_id))
            # Обновление склада
            if item[5] != -1:
                await db.execute('UPDATE items SET stock = stock - ? WHERE id = ?', (quantity, item_id))
            # Добавление в инвентарь
            await db.execute('''
                INSERT INTO inventory (user_id, item_id, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + ?
            ''', (user_id, item_id, quantity, quantity))
            await db.commit()
            return True, f"✅ Вы купили {quantity} x {item[1]} за {total_price} монет."
        except Exception as e:
            await db.rollback()
            return False, f"Ошибка при покупке: {e}"

async def get_inventory(user_id: int):
    """Возвращает список предметов пользователя."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT i.*, inv.quantity
            FROM inventory inv
            JOIN items i ON inv.item_id = i.id
            WHERE inv.user_id = ?
        ''', (user_id,))
        rows = await cursor.fetchall()
        return rows