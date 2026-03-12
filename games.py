import random
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("guess"))
async def cmd_guess(message: Message):
    await message.answer("Тест: команда guess работает!")

@router.message(Command("dice"))
async def cmd_dice(message: Message):
    await message.answer("🎲 Бросаем кубик... (тест)")






