import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, BotCommand
from aiogram.exceptions import TelegramAPIError

from database import create_table, add_user, get_user, get_balance, update_balance, get_top_users
from middlewares import ActivityMiddleware
from games import router as games_router
from shop import router as shop_router
from moderation import router as moderation_router
from ai import router as ai_router

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
WELCOME_TEXT = os.getenv("WELCOME_TEXT")

if not BOT_TOKEN:
    print("❌ Токен не найден! Проверь файл .env")
    exit()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключаем middleware для подсчёта сообщений
dp.message.middleware(ActivityMiddleware())

# Подключаем роутер с играми
dp.include_router(games_router)
dp.include_router(shop_router)
dp.include_router(moderation_router)
dp.include_router(ai_router)

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    logging.info(f"Пользователь {user.full_name} (id: {user.id}) запустил бота")
    await add_user(user.id, user.username, user.first_name)

    try:
        invite_link = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
            name=f"invite_for_{user.id}"
        )
        link = invite_link.invite_link
    except TelegramAPIError as e:
        logging.error(f"Не удалось создать ссылку: {e}")
        link = f"https://t.me/{CHANNEL_ID.lstrip('@')}" if CHANNEL_ID and CHANNEL_ID.startswith('@') else "Ссылка временно недоступна"
    except Exception as e:
        logging.error(f"Неизвестная ошибка: {e}")
        link = "Ошибка при получении ссылки"

    response_text = f"{WELCOME_TEXT}\n\n{link}"
    await message.answer(response_text)

# Команда /balance
@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    user_id = message.from_user.id
    balance = await get_balance(user_id)
    if balance is not None:
        await message.answer(f"💰 Твой баланс: {balance:.2f} монет.")
    else:
        await message.answer("❌ Ты не найден в базе. Попробуй /start сначала.")

# Команда /top
@dp.message(Command("top"))
async def cmd_top(message: Message):
    args = message.text.split()
    period = args[1] if len(args) > 1 else 'week'

    if period == 'day':
        days = 1
    elif period == 'week':
        days = 7
    elif period == 'month':
        days = 30
    elif period == 'all':
        days = None
    else:
        await message.answer("❌ Неправильный период. Используй: day, week, month, all")
        return

    top_users = await get_top_users(message.chat.id, days)

    if not top_users:
        await message.answer("Нет данных за этот период.")
        return

    text = f"🏆 Топ за {period}:\n"
    for i, (user_id, total) in enumerate(top_users, 1):
        try:
            chat_member = await message.bot.get_chat_member(message.chat.id, user_id)
            name = chat_member.user.full_name
        except:
            name = f"ID {user_id}"
        text += f"{i}. {name} – {total} сообщений\n"

    await message.answer(text)

# Запуск бота
async def main():
    await create_table()
    # Устанавливаем команды в меню
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="balance", description="Проверить баланс"),
        BotCommand(command="top", description="Топ активности"),
        BotCommand(command="guess", description="Угадай число"),
        BotCommand(command="coin", description="Орёл или решка"),
        BotCommand(command="rps", description="Камень, ножницы, бумага"),
        BotCommand(command="dice", description="Бросок кубика"),
        BotCommand(command="daily", description="Ежедневный бонус"),
        BotCommand(command="shop", description="Магазин"),
        BotCommand(command="buy", description="Купить предмет"),
        BotCommand(command="inventory", description="Мои предметы"),
    ]
    await bot.set_my_commands(commands)
    logging.info("Бот запускается...")
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())