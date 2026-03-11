from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
from datetime import datetime
import pytz
import logging

from db import increment_message_count, add_user

logger = logging.getLogger(__name__)

class ActivityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Работаем только с сообщениями из групп/супергрупп
        if event.chat.type in ['group', 'supergroup']:
            # Текущее время по Москве
            msk_tz = pytz.timezone('Europe/Moscow')
            now_msk = datetime.now(msk_tz)
            hour = now_msk.hour

            # Проверяем, является ли сообщение командой (начинается с /)
            is_command = event.text and event.text.startswith('/')

            if is_command:
                logger.info(f"Команда от {event.from_user.id} проигнорирована в подсчёте")
            else:
                # Проверяем рабочее время (с 7 до 23)
                if True:   # всегда учитываем
                    # Добавляем пользователя в базу (если нет)
                    await add_user(
                        user_id=event.from_user.id,
                        username=event.from_user.username,
                        first_name=event.from_user.first_name
                    )
                    # Увеличиваем счётчик
                    today = now_msk.strftime('%Y-%m-%d')
                    await increment_message_count(
                        user_id=event.from_user.id,
                        chat_id=event.chat.id,
                        date=today
                    )
                    logger.info(f"✅ Сообщение от {event.from_user.id} учтено (время МСК: {hour} ч.)")
                else:
                    logger.info(f"⏳ Сообщение от {event.from_user.id} НЕ учтено (время МСК: {hour} ч.)")

        # Обязательно передаём управление дальше (чтобы команды обрабатывались)
        return await handler(event, data)