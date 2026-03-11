import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message

from db import get_items, buy_item, get_inventory, add_item_to_db

router = Router()
logger = logging.getLogger(__name__)

# Просмотр магазина
@router.message(Command("shop"))
async def cmd_shop(message: Message):
    items = await get_items()
    if not items:
        await message.answer("🛒 Магазин пуст.")
        return
    text = "🛒 **Магазин:**\n\n"
    for item in items:
        stock = f" (осталось {item['stock']})" if item['stock'] > 0 else " (∞)"
        text += f"{item['emoji']} **{item['name']}** – {item['price']} монет{stock}\n"
        text += f"   {item['description']}\n\n"
    await message.answer(text)

# Покупка
@router.message(Command("buy"))
async def cmd_buy(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажите название предмета. Пример: /buy Меч")
        return
    item_name = args[1].strip()
    user_id = message.from_user.id
    success, msg = await buy_item(user_id, item_name)
    await message.answer(msg)

# Инвентарь
@router.message(Command("inventory"))
async def cmd_inventory(message: Message):
    user_id = message.from_user.id
    items = await get_inventory(user_id)
    if not items:
        await message.answer("🎒 У вас пока нет предметов.")
        return
    text = "🎒 **Ваш инвентарь:**\n"
    for item in items:
        text += f"{item['emoji']} {item['name']} – {item['quantity']} шт.\n"
    await message.answer(text)

# Добавление товара (админ-команда)
@router.message(Command("additem"))
async def cmd_additem(message: Message):
    # Простейшая проверка: можно добавить список admin_ids, но пока без неё
    args = message.text.split(maxsplit=4)
    if len(args) < 5:
        await message.answer("Использование: /additem Название | Описание | Цена | Эмодзи | Количество\n"
                             "Пример: /additem Меч | Рубит врагов | 100 | ⚔️ | -1")
        return
    try:
        parts = message.text.split('|')
        name = parts[0].replace('/additem', '').strip()
        description = parts[1].strip()
        price = float(parts[2].strip())
        emoji = parts[3].strip()
        stock = int(parts[4].strip())
    except (IndexError, ValueError):
        await message.answer("Ошибка формата. Используйте разделитель | и правильные числа.")
        return

    await add_item_to_db(name, description, price, emoji, stock)
    await message.answer(f"✅ Товар '{name}' добавлен в магазин.")
