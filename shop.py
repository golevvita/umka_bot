from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from db import (
    get_all_items, get_item, buy_item, get_inventory,
    add_item, update_item, delete_item, get_user
)

router = Router()

# Команда /shop — показать все товары
@router.message(Command("shop"))
async def cmd_shop(message: Message):
    items = await get_all_items()
    if not items:
        await message.answer("🛒 Магазин временно пуст.")
        return

    text = "🛒 **Магазин:**\n\n"
    for item in items:
        stock_info = f" (осталось {item['stock']})" if item['stock'] != -1 else " (∞)"
        text += f"{item['emoji']} **{item['name']}** — {item['price']} монет{stock_info}\n"
        text += f"   _{item['description']}_\n\n"

    await message.answer(text, parse_mode="Markdown")

# Команда /buy <название> [количество]
@router.message(Command("buy"))
async def cmd_buy(message: Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("❌ Укажите название товара. Например: /buy Меч")
        return

    item_name = args[1].strip()
    quantity = 1
    if len(args) == 3:
        try:
            quantity = int(args[2])
            if quantity <= 0:
                raise ValueError
        except:
            await message.answer("❌ Количество должно быть положительным числом.")
            return

    # Ищем товар по имени (без учёта регистра)
    items = await get_all_items()
    found_item = None
    for it in items:
        if it['name'].lower() == item_name.lower():
            found_item = it
            break

    if not found_item:
        await message.answer("❌ Товар с таким названием не найден.")
        return

    user_id = message.from_user.id
    success, msg = await buy_item(user_id, found_item['id'], quantity)
    await message.answer(msg)

# Команда /inventory — показать свои предметы
@router.message(Command("inventory"))
async def cmd_inventory(message: Message):
    user_id = message.from_user.id
    inv = await get_inventory(user_id)
    if not inv:
        await message.answer("📦 У вас пока нет предметов.")
        return

    text = "📦 **Ваш инвентарь:**\n"
    for item in inv:
        text += f"{item['emoji']} {item['name']} — {item['quantity']} шт.\n"

    await message.answer(text, parse_mode="Markdown")

# ----- АДМИНСКИЕ КОМАНДЫ (для владельца) -----
# Проверка, является ли пользователь админом (по tg_id)
# Для простоты сделаем проверку по списку admin_ids. Ты можешь указать свой ID.
ADMIN_IDS = [1254211105]  # <--- ЗАМЕНИ НА СВОЙ TELEGRAM ID

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# Команда /additem
@router.message(Command("additem"))
async def cmd_additem(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора.")
        return

    # Формат: /additem Название | Описание | Цена | Эмодзи | Количество(-1 для бесконечно)
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Использование: /additem Название | Описание | Цена | Эмодзи | Количество")
        return

    parts = [p.strip() for p in args[1].split('|')]
    if len(parts) < 3:
        await message.answer("❌ Должно быть минимум: Название | Описание | Цена")
        return

    name = parts[0]
    description = parts[1]
    try:
        price = float(parts[2])
    except:
        await message.answer("❌ Цена должна быть числом.")
        return

    emoji = parts[3] if len(parts) > 3 else '📦'
    stock = -1
    if len(parts) > 4:
        try:
            stock = int(parts[4])
        except:
            await message.answer("❌ Количество должно быть целым числом или -1.")
            return

    success = await add_item(name, description, price, emoji, stock)
    if success:
        await message.answer(f"✅ Товар «{name}» добавлен.")
    else:
        await message.answer("❌ Товар с таким именем уже существует.")

# Команда /edititem (аналогично, но требует ID товара)
@router.message(Command("edititem"))
async def cmd_edititem(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора.")
        return

    # Формат: /edititem ID | поле=значение | поле=значение ...
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Использование: /edititem ID | name=Новое название | price=150")
        return

    parts = [p.strip() for p in args[1].split('|')]
    try:
        item_id = int(parts[0])
    except:
        await message.answer("❌ Первым параметром должен быть ID товара.")
        return

    updates = {}
    for part in parts[1:]:
        if '=' not in part:
            continue
        key, value = part.split('=', 1)
        key = key.strip().lower()
        value = value.strip()
        if key in ['name', 'description', 'emoji']:
            updates[key] = value
        elif key == 'price':
            try:
                updates['price'] = float(value)
            except:
                await message.answer(f"❌ Цена должна быть числом: {value}")
                return
        elif key == 'stock':
            try:
                updates['stock'] = int(value)
            except:
                await message.answer(f"❌ Количество должно быть целым числом: {value}")
                return

    if not updates:
        await message.answer("❌ Нет полей для обновления.")
        return

    success = await update_item(item_id, **updates)
    if success:
        await message.answer(f"✅ Товар ID {item_id} обновлён.")
    else:
        await message.answer("❌ Товар с таким ID не найден.")

# Команда /removeitem ID
@router.message(Command("removeitem"))
async def cmd_removeitem(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /removeitem ID")
        return

    try:
        item_id = int(args[1])
    except:
        await message.answer("❌ ID должен быть числом.")
        return

    await delete_item(item_id)

    await message.answer(f"✅ Товар ID {item_id} удалён (если существовал).")
