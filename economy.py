import logging
from datetime import datetime, timedelta
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberUpdated
from aiogram.exceptions import TelegramAPIError

router = Router()
logger = logging.getLogger(__name__)

def is_admin(chat_member):
    return chat_member.status in ['administrator', 'creator']

# Проверка прав бота и пользователя
async def check_permissions(message: Message):
    if message.chat.type not in ['group', 'supergroup']:
        await message.answer("Эта команда работает только в группах.")
        return False
    bot_member = await message.chat.get_member(message.bot.id)
    if not bot_member.can_restrict_members:
        await message.answer("У бота нет прав на ограничение участников.")
        return False
    user_member = await message.chat.get_member(message.from_user.id)
    if not is_admin(user_member):
        await message.answer("Вы не администратор.")
        return False
    return True

@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if not await check_permissions(message):
        return
    if not message.reply_to_message:
        await message.answer("Ответьте на сообщение пользователя, которого хотите забанить.")
        return
    target = message.reply_to_message.from_user
    try:
        await message.chat.ban(target.id)
        await message.answer(f"Пользователь {target.full_name} забанен.")
    except TelegramAPIError as e:
        await message.answer(f"Ошибка: {e}")

@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if message.chat.type not in ['group', 'supergroup']:
        await message.answer("Эта команда работает только в группах.")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Укажите ID пользователя. Пример: /unban 123456789")
        return
    try:
        user_id = int(args[1])
        await message.chat.unban(user_id)
        await message.answer(f"Пользователь {user_id} разбанен.")
    except ValueError:
        await message.answer("ID должен быть числом.")
    except TelegramAPIError as e:
        await message.answer(f"Ошибка: {e}")

@router.message(Command("mute"))
async def cmd_mute(message: Message):
    if not await check_permissions(message):
        return
    if not message.reply_to_message:
        await message.answer("Ответьте на сообщение пользователя.")
        return
    args = message.text.split()
    duration = 60  # по умолчанию 1 минута
    if len(args) >= 2:
        try:
            duration = int(args[1])
        except ValueError:
            pass
    until_date = datetime.now() + timedelta(seconds=duration)
    target = message.reply_to_message.from_user
    try:
        await message.chat.restrict(target.id, can_send_messages=False, until_date=until_date)
        await message.answer(f"Пользователь {target.full_name} замьючен на {duration} секунд.")
    except TelegramAPIError as e:
        await message.answer(f"Ошибка: {e}")

@router.message(Command("unmute"))
async def cmd_unmute(message: Message):
    if not await check_permissions(message):
        return
    if not message.reply_to_message:
        await message.answer("Ответьте на сообщение пользователя.")
        return
    target = message.reply_to_message.from_user
    try:
        await message.chat.restrict(target.id, can_send_messages=True)
        await message.answer(f"Пользователь {target.full_name} размьючен.")
    except TelegramAPIError as e:
        await message.answer(f"Ошибка: {e}")
