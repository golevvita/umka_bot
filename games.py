import random
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from database import get_user, update_balance, can_claim_daily, update_last_daily

router = Router()

# ---------- Состояния для игр ----------
class GuessGame(StatesGroup):
    waiting_for_bet = State()
    waiting_for_number = State()

class CoinGame(StatesGroup):
    waiting_for_bet = State()
    waiting_for_choice = State()   # выбор: орёл или решка

class RPSGame(StatesGroup):
    waiting_for_bet = State()
    waiting_for_choice = State()   # камень, ножницы, бумага

class DiceGame(StatesGroup):
    waiting_for_bet = State()
    waiting_for_number = State()   # число от 1 до 6

# ---------- Вспомогательная функция для проверки баланса и ставки ----------
async def process_bet_common(message: Message, state: FSMContext, next_state, game_name: str):
    """Общая логика для первого шага игр: проверка ставки и баланса."""
    try:
        bet = float(message.text)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число (например, 10).")
        return

    if bet <= 0:
        await message.answer("❌ Ставка должна быть положительной.")
        return

    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        await message.answer("❌ Сначала введите /start, чтобы зарегистрироваться.")
        return

    if user['balance'] < bet:
        await message.answer(f"❌ Недостаточно средств. Твой баланс: {user['balance']:.2f}")
        await state.clear()
        return

    # Сохраняем ставку и переходим к следующему шагу
    await state.update_data(bet=bet)
    await state.set_state(next_state)

# ---------- ИГРА 1: Угадай число (уже есть) ----------
@router.message(Command("guess"))
async def cmd_guess(message: Message, state: FSMContext):
    await message.answer("🎲 Игра «Угадай число» (1–10)!\nВведите ставку:")
    await state.set_state(GuessGame.waiting_for_bet)

@router.message(GuessGame.waiting_for_bet)
async def process_guess_bet(message: Message, state: FSMContext):
    await process_bet_common(message, state, GuessGame.waiting_for_number, "guess")

@router.message(GuessGame.waiting_for_number)
async def process_guess_number(message: Message, state: FSMContext):
    try:
        guess = int(message.text)
    except ValueError:
        await message.answer("❌ Введите целое число от 1 до 10.")
        return

    if guess < 1 or guess > 10:
        await message.answer("❌ Число должно быть от 1 до 10.")
        return

    data = await state.get_data()
    bet = data['bet']
    secret = random.randint(1, 10)
    user_id = message.from_user.id

    if guess == secret:
        win = bet * 2
        await update_balance(user_id, win)
        await message.answer(f"🎉 Поздравляю! Ты угадал число {secret}.\nТы выиграл {win:.2f} монет!")
    else:
        await update_balance(user_id, -bet)
        await message.answer(f"😞 Не угадал. Я загадал {secret}. Ты потерял {bet:.2f} монет.")
    await state.clear()

# ---------- ИГРА 2: Орёл или решка ----------
@router.message(Command("coin"))
async def cmd_coin(message: Message, state: FSMContext):
    await message.answer("🪙 Игра «Орёл или решка»!\nВведите ставку:")
    await state.set_state(CoinGame.waiting_for_bet)

@router.message(CoinGame.waiting_for_bet)
async def process_coin_bet(message: Message, state: FSMContext):
    await process_bet_common(message, state, CoinGame.waiting_for_choice, "coin")

@router.message(CoinGame.waiting_for_choice)
async def process_coin_choice(message: Message, state: FSMContext):
    choice = message.text.lower().strip()
    if choice not in ['орёл', 'орел', 'решка']:
        await message.answer("❌ Напиши «орёл» или «решка».")
        return

    data = await state.get_data()
    bet = data['bet']
    user_id = message.from_user.id

    # Приводим к каноничному виду
    if choice in ['орёл', 'орел']:
        user_choice = 'орёл'
    else:
        user_choice = 'решка'

    coin = random.choice(['орёл', 'решка'])
    if user_choice == coin:
        win = bet * 2
        await update_balance(user_id, win)
        await message.answer(f"🪙 Выпал {coin}! Ты выиграл {win:.2f} монет!")
    else:
        await update_balance(user_id, -bet)
        await message.answer(f"🪙 Выпал {coin}. Ты проиграл {bet:.2f} монет.")
    await state.clear()

# ---------- ИГРА 3: Камень, ножницы, бумага ----------
@router.message(Command("rps"))
async def cmd_rps(message: Message, state: FSMContext):
    await message.answer("✊✌️✋ Камень, ножницы, бумага!\nВведите ставку:")
    await state.set_state(RPSGame.waiting_for_bet)

@router.message(RPSGame.waiting_for_bet)
async def process_rps_bet(message: Message, state: FSMContext):
    await process_bet_common(message, state, RPSGame.waiting_for_choice, "rps")

@router.message(RPSGame.waiting_for_choice)
async def process_rps_choice(message: Message, state: FSMContext):
    choice = message.text.lower().strip()
    options = {'камень', 'ножницы', 'бумага'}
    if choice not in options:
        await message.answer("❌ Выбери: камень, ножницы или бумага.")
        return

    data = await state.get_data()
    bet = data['bet']
    user_id = message.from_user.id

    bot_choice = random.choice(list(options))
    # Определяем результат
    if choice == bot_choice:
        result = "Ничья"
        win = bet  # возвращаем ставку (не списываем)
        await update_balance(user_id, 0)  # ничего не меняем, просто для логики
        await message.answer(f"🤝 Ничья! Оба выбрали {choice}. Ставка возвращена.")
    elif (choice == 'камень' and bot_choice == 'ножницы') or \
         (choice == 'ножницы' and bot_choice == 'бумага') or \
         (choice == 'бумага' and bot_choice == 'камень'):
        win = bet * 2
        await update_balance(user_id, win)
        await message.answer(f"🎉 Ты выиграл! {choice} побеждает {bot_choice}. Выигрыш: {win:.2f} монет!")
    else:
        await update_balance(user_id, -bet)
        await message.answer(f"😞 Ты проиграл! {bot_choice} побеждает {choice}. Потеряно {bet:.2f} монет.")
    await state.clear()

# ---------- ИГРА 4: Бросок кубика ----------
@router.message(Command("dice"))
async def cmd_dice(message: Message, state: FSMContext):
    await message.answer("🎲 Игра «Кубик» (угадай число от 1 до 6)!\nВведите ставку:")
    await state.set_state(DiceGame.waiting_for_bet)

@router.message(DiceGame.waiting_for_bet)
async def process_dice_bet(message: Message, state: FSMContext):
    await process_bet_common(message, state, DiceGame.waiting_for_number, "dice")

@router.message(DiceGame.waiting_for_number)
async def process_dice_number(message: Message, state: FSMContext):
    try:
        guess = int(message.text)
    except ValueError:
        await message.answer("❌ Введите целое число от 1 до 6.")
        return

    if guess < 1 or guess > 6:
        await message.answer("❌ Число должно быть от 1 до 6.")
        return

    data = await state.get_data()
    bet = data['bet']
    roll = random.randint(1, 6)
    user_id = message.from_user.id

    if guess == roll:
        win = bet * 6
        await update_balance(user_id, win)
        await message.answer(f"🎉 Выпало {roll}! Ты угадал! Выигрыш: {win:.2f} монет!")
    else:
        await update_balance(user_id, -bet)
        await message.answer(f"😞 Выпало {roll}. Ты проиграл {bet:.2f} монет.")
    await state.clear()

# ---------- ИГРА 5: Ежедневный бонус ----------
@router.message(Command("daily"))
async def cmd_daily(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        await message.answer("❌ Сначала введите /start, чтобы зарегистрироваться.")
        return

    if await can_claim_daily(user_id):
        bonus = 50  # фиксированная сумма бонуса
        await update_balance(user_id, bonus)
        await update_last_daily(user_id)
        await message.answer(f"🎁 Ежедневный бонус получен! +{bonus} монет.\nВозвращайся через 24 часа!")
    else:
        await message.answer("⏳ Ты уже получал бонус сегодня. Приходи через 24 часа.")