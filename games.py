import random
import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from db import get_user_balance, update_user_balance  # функции, которые добавим в db.py

router = Router()
logger = logging.getLogger(__name__)

# Состояния для игр (FSM)
class GuessGame(StatesGroup):
    waiting_for_bet = State()
    waiting_for_number = State()

class RPSGame(StatesGroup):
    waiting_for_bet = State()
    waiting_for_choice = State()

# Игра "Угадай число"
@router.message(Command("guess"))
async def cmd_guess(message: Message, state: FSMContext):
    await message.answer("Введите ставку (количество монет):")
    await state.set_state(GuessGame.waiting_for_bet)

@router.message(GuessGame.waiting_for_bet)
async def process_guess_bet(message: Message, state: FSMContext):
    try:
        bet = float(message.text)
        if bet <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Ставка должна быть положительным числом. Попробуйте ещё раз или отмените командой /cancel.")
        return

    user_id = message.from_user.id
    balance = await get_user_balance(user_id)
    if balance < bet:
        await message.answer(f"Недостаточно средств. Ваш баланс: {balance} монет.")
        await state.clear()
        return

    # Замораживаем ставку (списываем)
    await update_user_balance(user_id, -bet)
    await state.update_data(bet=bet)

    await message.answer("Я загадал число от 1 до 10. Введите ваш вариант:")
    await state.set_state(GuessGame.waiting_for_number)

@router.message(GuessGame.waiting_for_number)
async def process_guess_number(message: Message, state: FSMContext):
    try:
        guess = int(message.text)
        if not 1 <= guess <= 10:
            raise ValueError
    except ValueError:
        await message.answer("Введите целое число от 1 до 10.")
        return

    data = await state.get_data()
    bet = data['bet']
    secret = random.randint(1, 10)
    if guess == secret:
        win = bet * 2
        await update_user_balance(message.from_user.id, win)
        await message.answer(f"🎉 Угадал! Было {secret}. Вы выиграли {win} монет!")
    else:
        await message.answer(f"Не угадал! Было {secret}. Вы проиграли {bet} монет.")

    await state.clear()

# Игра "Кубик"
@router.message(Command("dice"))
async def cmd_dice(message: Message):
    # Простой вариант без ставки: бросаем кубик через Telegram
    # Можно добавить ставку, но пока упростим
    dice = await message.answer_dice(emoji="🎲")
    # Здесь можно обработать результат, но пока просто выводим
    # Для простоты можно добавить небольшую награду случайно
    if dice.dice.value == 6:
        reward = 10
        await update_user_balance(message.from_user.id, reward)
        await message.answer(f"🎲 Вам выпало 6! Вы получили {reward} монет.")
    else:
        await message.answer(f"🎲 Вам выпало {dice.dice.value}. Повезёт в следующий раз!")

# Камень-ножницы-бумага
@router.message(Command("rps"))
async def cmd_rps(message: Message, state: FSMContext):
    await message.answer("Введите ставку (количество монет):")
    await state.set_state(RPSGame.waiting_for_bet)

@router.message(RPSGame.waiting_for_bet)
async def process_rps_bet(message: Message, state: FSMContext):
    try:
        bet = float(message.text)
        if bet <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Ставка должна быть положительным числом.")
        return

    user_id = message.from_user.id
    balance = await get_user_balance(user_id)
    if balance < bet:
        await message.answer(f"Недостаточно средств. Баланс: {balance}.")
        await state.clear()
        return

    await update_user_balance(user_id, -bet)
    await state.update_data(bet=bet)

    await message.answer("Выберите: камень 🪨, ножницы ✂️ или бумага 📄 (отправьте слово):")
    await state.set_state(RPSGame.waiting_for_choice)

@router.message(RPSGame.waiting_for_choice)
async def process_rps_choice(message: Message, state: FSMContext):
    user_choice = message.text.lower().strip()
    if user_choice not in ["камень", "ножницы", "бумага"]:
        await message.answer("Пожалуйста, выберите одно из: камень, ножницы, бумага")
        return

    choices = ["камень", "ножницы", "бумага"]
    bot_choice = random.choice(choices)

    # Определяем победителя
    if user_choice == bot_choice:
        result = "ничья"
    elif (user_choice == "камень" and bot_choice == "ножницы") or \
         (user_choice == "ножницы" and bot_choice == "бумага") or \
         (user_choice == "бумага" and bot_choice == "камень"):
        result = "вы выиграли"
    else:
        result = "вы проиграли"

    data = await state.get_data()
    bet = data['bet']
    user_id = message.from_user.id

    if result == "вы выиграли":
        win = bet * 2
        await update_user_balance(user_id, win)
        await message.answer(f"Бот выбрал {bot_choice}. {result}! Вы получаете {win} монет.")
    elif result == "ничья":
        await update_user_balance(user_id, bet)  # возвращаем ставку
        await message.answer(f"Бот выбрал {bot_choice}. Ничья! Ставка возвращена.")
    else:
        await message.answer(f"Бот выбрал {bot_choice}. {result}. Вы проиграли {bet} монет.")

    await state.clear()

# Игровой автомат (слоты)
@router.message(Command("slot"))
async def cmd_slot(message: Message):
    # Простая реализация: генерируем три случайных эмодзи
    emojis = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
    result = [random.choice(emojis) for _ in range(3)]
    text = f"{result[0]} | {result[1]} | {result[2]}"
    if result[0] == result[1] == result[2]:
        win = 50
        await update_user_balance(message.from_user.id, win)
        text += f"\n🎉 Джекпот! Вы выиграли {win} монет!"
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        win = 10
        await update_user_balance(message.from_user.id, win)
        text += f"\n🎉 Два в ряд! Вы выиграли {win} монет!"
    else:
        text += "\nПовезёт в следующий раз!"
    await message.answer(text)

# Ежедневный бонус
@router.message(Command("daily"))
async def cmd_daily(message: Message):
    user_id = message.from_user.id
    today = datetime.now().strftime('%Y-%m-%d')
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, когда пользователь последний раз получал бонус
        cursor = await db.execute('SELECT last_daily FROM users WHERE user_id = ?', (user_id,))
        row = await cursor.fetchone()
        last_daily = row[0] if row else None
        
        if last_daily == today:
            await message.answer("❌ Вы уже получали бонус сегодня. Приходите завтра!")
            return
        
        # Начисляем бонус (например, 50 монет)
        bonus = 50
        await db.execute('''
            UPDATE users SET balance = balance + ?, last_daily = ? WHERE user_id = ?
        ''', (bonus, today, user_id))
        await db.commit()
        
    await message.answer(f"✅ Вы получили ежедневный бонус: {bonus} монет!")



