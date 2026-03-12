import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db import get_user_balance, update_user_balance, get_top_balance

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command(commands=["balance", "баланс"]))
async def cmd_balance(message: Message):
    user_id = message.from_user.id
    balance = await get_user_balance(user_id)
    await message.answer(f"💰 Ваш баланс: {balance} монет.")

@router.message(Command(commands=["topmoney", "топбогатых"]))
async def cmd_topmoney(message: Message):
    top = await get_top_balance(limit=10)
    if not top:
        await message.answer("Нет данных.")
        return
    text = "🏆 Топ по балансу:\n"
    for i, (user_id, balance) in enumerate(top, 1):
        try:
            user = await message.bot.get_chat(user_id)
            name = user.full_name
        except:
            name = f"ID {user_id}"
        text += f"{i}. {name} – {balance} монет\n"
    await message.answer(text)
