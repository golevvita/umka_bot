from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
from datetime import date
from database import add_message_count, update_balance, get_user, add_user

class ActivityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем, что сообщение из группы
        if event.chat.type in ['group', 'supergroup']:
            user = event.from_user
            # Игнорируем сообщения от ботов (чтобы не считать самого себя)
            if user.is_bot:
                return await handler(event, data)

            # Убедимся, что пользователь есть в БД
            db_user = await get_user(user.id)
            if not db_user:
                await add_user(user.id, user.username, user.first_name)

            # Добавляем +1 к счётчику сообщений за сегодня
            await add_message_count(user.id, event.chat.id, date.today())

            # Начисляем валюту за сообщение
            await update_balance(user.id, 0.1)

            # Для отладки можно выводить в консоль
            print(f"➕ {user.full_name} написал сообщение в чате {event.chat.id}")

        # Обязательно передаём событие дальше
        return await handler(event, data)