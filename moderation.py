from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions
from aiogram.exceptions import TelegramAPIError
from datetime import timedelta, datetime

router = Router()

# Вспомогательная функция для проверки прав администратора у пользователя
async def is_user_admin(chat_id: int, user_id: int, bot) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

# Вспомогательная функция для проверки прав бота
async def bot_has_permission(chat_id: int, bot, permission: str) -> bool:
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        if permission == 'restrict':
            return bot_member.can_restrict_members or bot_member.status == 'creator'
        elif permission == 'delete':
            return bot_member.can_delete_messages or bot_member.status == 'creator'
        else:
            return False
    except:
        return False

# Команда /ban
@router.message(Command("ban"))
async def cmd_ban(message: Message):
    # Проверяем, что команда вызвана в группе
    if message.chat.type not in ['group', 'supergroup']:
        await message.answer("❌ Эта команда работает только в группах.")
        return

    # Проверяем, что это ответ на сообщение
    if not message.reply_to_message:
        await message.answer("❌ Ответьте на сообщение пользователя, которого хотите забанить.")
        return

    # Проверяем права бота
    if not await bot_has_permission(message.chat.id, message.bot, 'restrict'):
        await message.answer("❌ У бота нет прав банить участников. Сделайте его администратором.")
        return

    # Проверяем, что отправитель команды — администратор
    if not await is_user_admin(message.chat.id, message.from_user.id, message.bot):
        await message.answer("❌ Только администраторы могут использовать эту команду.")
        return

    target = message.reply_to_message.from_user
    # Не даём забанить администратора
    if await is_user_admin(message.chat.id, target.id, message.bot):
        await message.answer("❌ Нельзя забанить администратора.")
        return

    try:
        await message.chat.ban(target.id)
        await message.answer(f"⛔ Пользователь {target.full_name} забанен.")
    except TelegramAPIError as e:
        await message.answer(f"❌ Ошибка: {e}")

# Команда /unban
@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if message.chat.type not in ['group', 'supergroup']:
        await message.answer("❌ Эта команда работает только в группах.")
        return

    if not message.reply_to_message:
        await message.answer("❌ Ответьте на сообщение пользователя, которого хотите разбанить.")
        return

    if not await bot_has_permission(message.chat.id, message.bot, 'restrict'):
        await message.answer("❌ У бота нет прав разбанивать участников.")
        return

    if not await is_user_admin(message.chat.id, message.from_user.id, message.bot):
        await message.answer("❌ Только администраторы могут использовать эту команду.")
        return

    target = message.reply_to_message.from_user
    try:
        await message.chat.unban(target.id)
        await message.answer(f"✅ Пользователь {target.full_name} разбанен.")
    except TelegramAPIError as e:
        await message.answer(f"❌ Ошибка: {e}")

# Команда /mute (замьютить на время)
@router.message(Command("mute"))
async def cmd_mute(message: Message):
    if message.chat.type not in ['group', 'supergroup']:
        await message.answer("❌ Эта команда работает только в группах.")
        return

    if not message.reply_to_message:
        await message.answer("❌ Ответьте на сообщение пользователя, которого хотите замьютить.")
        return

    if not await bot_has_permission(message.chat.id, message.bot, 'restrict'):
        await message.answer("❌ У бота нет прав мутить участников.")
        return

    if not await is_user_admin(message.chat.id, message.from_user.id, message.bot):
        await message.answer("❌ Только администраторы могут использовать эту команду.")
        return

    target = message.reply_to_message.from_user
    if await is_user_admin(message.chat.id, target.id, message.bot):
        await message.answer("❌ Нельзя замьютить администратора.")
        return

    # Парсим время из аргументов (например, /mute 10m, /mute 1h)
    args = message.text.split()
    mute_duration = None
    if len(args) >= 2:
        time_str = args[1]
        try:
            if time_str.endswith('m'):
                mute_duration = timedelta(minutes=int(time_str[:-1]))
            elif time_str.endswith('h'):
                mute_duration = timedelta(hours=int(time_str[:-1]))
            elif time_str.endswith('d'):
                mute_duration = timedelta(days=int(time_str[:-1]))
            else:
                mute_duration = timedelta(minutes=int(time_str))  # по умолчанию минуты
        except:
            await message.answer("❌ Неправильный формат времени. Пример: 10m, 1h, 2d")
            return
    else:
        mute_duration = timedelta(hours=1)  # по умолчанию 1 час

    until_date = datetime.now() + mute_duration

    try:
        # Запрещаем отправлять сообщения
        permissions = ChatPermissions(can_send_messages=False)
        await message.chat.restrict(target.id, permissions, until_date=until_date)
        await message.answer(f"🔇 Пользователь {target.full_name} замьючен на {mute_duration}.")
    except TelegramAPIError as e:
        await message.answer(f"❌ Ошибка: {e}")

# Команда /unmute
@router.message(Command("unmute"))
async def cmd_unmute(message: Message):
    if message.chat.type not in ['group', 'supergroup']:
        await message.answer("❌ Эта команда работает только в группах.")
        return

    if not message.reply_to_message:
        await message.answer("❌ Ответьте на сообщение пользователя, которого хотите размутить.")
        return

    if not await bot_has_permission(message.chat.id, message.bot, 'restrict'):
        await message.answer("❌ У бота нет прав размучивать участников.")
        return

    if not await is_user_admin(message.chat.id, message.from_user.id, message.bot):
        await message.answer("❌ Только администраторы могут использовать эту команду.")
        return

    target = message.reply_to_message.from_user

    try:
        # Сбрасываем ограничения (разрешаем всё)
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        await message.chat.restrict(target.id, permissions)
        await message.answer(f"🔊 Пользователь {target.full_name} размучен.")
    except TelegramAPIError as e:
        await message.answer(f"❌ Ошибка: {e}")