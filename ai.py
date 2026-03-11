import os
from openai import OpenAI
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

router = Router()

# ВСТАВЬ СВОЙ ПОЛНЫЙ КЛЮЧ СЮДА (между кавычек)
MY_API_KEY = "sk-or-v1-0bb...c8c"  # замени на свой ключ

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=MY_API_KEY,
    default_headers={
        "HTTP-Referer": "http://localhost",
        "X-Title": "Umka Bot",
    }
)

@router.message(Command("ask"))
async def cmd_ask(message: Message):
    prompt = message.text.replace('/ask', '').strip()
    if not prompt:
        await message.answer("❌ Напиши вопрос после /ask. Например: /ask Как дела?")
        return

    try:
        completion = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct:free",  # бесплатная модель
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        answer = completion.choices[0].message.content
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"❌ Ошибка AI: {e}")