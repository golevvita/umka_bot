import asyncio
import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError

# Импорты из наших модулей
from db import init_db, get_top_users, add_user, increment_message_count
from middlewares import ActivityMiddleware

# Импорты роутеров для дополнительных команд
from games import router as games_router
from shop import router as shop_router
from moderation import router as moderation_router
from economy import router as economy_router  # если есть отдельно
# Если у тебя economy.py объединён с shop.py, то можно не импортировать отдельно.
# Но для ясности я предполагаю, что у тебя есть файл economy.py с командами /balance, /transfer и т.д.

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
WELCOME_TEXT = os.getenv("WELCOME_TEXT")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключаем middleware (для подсчёта сообщений)
dp.message.middleware(ActivityMiddleware())

# Подключаем роутеры из других модулей (порядок может быть любым)
dp.include_router(games_router)
dp.include_router(shop_router)
dp.include_router(moderation_router)
dp.include_router(economy_router)

# Команда /start (остаётся в главном файле)
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    logging.info(f"Пользователь {user.full_name} (id: {user.id}) запустил бота")

    try:
        invite_link = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
            name=f"invite_for_{user.id}"
        )
        link = invite_link.invite_link
    except TelegramAPIError:
        link = f"https://t.me/{CHANNEL_ID.lstrip('@')}" if CHANNEL_ID.startswith('@') else "Ссылка временно недоступна"
    except Exception:
        link = "Ошибка при получении ссылки"

    response_text = f"{WELCOME_TEXT}\n\n{link}"
    await message.answer(response_text)

# Команда /top (тоже остаётся)
@dp.message(Command("top"))
async def cmd_top(message: Message):
    if message.chat.type not in ['group', 'supergroup']:
        await message.answer("Эта команда работает только в группах.")
        return

    args = message.text.split()
    period = args[1].lower() if len(args) > 1 else 'week'

    now = datetime.now()
    if period == 'day':
        since = now - timedelta(days=1)
    elif period == 'week':
        since = now - timedelta(weeks=1)
    elif period == 'month':
        since = now - timedelta(days=30)
    elif period == 'all':
        since = datetime(2000, 1, 1)
    else:
        await message.answer("Использование: /top [day|week|month|all]")
        return

    since_str = since.strftime('%Y-%m-%d')
    logging.info(f"Запрос топа для чата {message.chat.id} с даты {since_str}")
    
    top_users = await get_top_users(chat_id=message.chat.id, since_date=since_str, limit=10)
    
    logging.info(f"Получено записей из БД: {len(top_users)}")

    if not top_users:
        await message.answer("За этот период нет сообщений.")
        return

    text = f"🏆 Топ за {period}:\n"
    for i, (user_id, total) in enumerate(top_users, start=1):
        try:
            member = await message.bot.get_chat_member(message.chat.id, user_id)
            name = member.user.full_name
        except:
            name = f"ID {user_id}"
        text += f"{i}. {name} – {total} сообщ.\n"

    await message.answer(text)

async def main():
    await init_db()
    logging.info("База данных готова")
    logging.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
